"""
Client module for Apptuit APIs
"""

import os
from collections import defaultdict
import json
from apptuit.utils import _contains_valid_chars, _get_tags_from_environment, _validate_tags
from apptuit import APPTUIT_PY_TOKEN, APPTUIT_PY_TAGS

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote
import sys
import time
import zlib
import requests
import pandas as pd


def _generate_query_string(query_string, start, end):
    ret = "?start=" + str(start)
    if end:
        ret += "&end=" + str(end)
    ret += "&q=" + quote(query_string, safe='')
    return ret

def _parse_response(resp, start, end=None):
    json_resp = json.loads(resp)
    outputs = json_resp["outputs"]
    if not outputs: # Pythonic way of checking if list is empty
        return None
    qresult = QueryResult(start, end)
    for output in outputs:
        results = output["result"]
        if not results:
            continue

        output_id = output["id"]
        qresult[output_id] = Output()
        for result in results:
            dps = result["dps"]
            index = []
            values = []
            for point in dps:
                if point[0] < start:
                    continue
                if end is not None and point[0] >= end:
                    continue
                index.append(point[0])
                values.append(point[1])
            series = TimeSeries(result["metric"], result["tags"], index, values)
            qresult[output_id].series.append(series)
    return qresult

class Apptuit(object):
    """
    Apptuit is the client object, encapsulating the functionalities provided by Apptuit APIs
    """

    def __init__(self, token=None, api_endpoint="https://api.apptuit.ai",
                 global_tags=None, ignore_environ_tags=False, debug=False):
        """
        Creates an apptuit client object
        Params:
            token: Token of the tenant to which we wish to connect
            api_endpoint: Apptuit API End point (including the protocol and port)
            global_tags: Tags for all datapoints (should be a dict),if you pass
                    global_tags, environmental tags will not be used,
                    even if ignore_environ_tags is false.
            ignore_environ_tags: A boolean value to include environmental variable or not
        """
        self.token = token
        if not self.token:
            self.token = os.environ.get(APPTUIT_PY_TOKEN)
            if not self.token:
                raise ValueError("Missing Apptuit API token, "
                                 "either pass it as a parameter or "
                                 "set as value of the environment variable '"
                                 + APPTUIT_PY_TOKEN + "'.")
        if not api_endpoint:
            raise ValueError("Invalid value for the 'api_endpoint' parameter")

        self.endpoint = api_endpoint
        if self.endpoint[-1] == '/':
            self.endpoint = self.endpoint[:-1]
        self.debug = debug
        self._global_tags = global_tags
        if not self._global_tags and not ignore_environ_tags:
            self._global_tags = _get_tags_from_environment()


    def _create_payload(self, datapoints):
        data = []
        for dp in datapoints:
            if dp.tags and self._global_tags:
                tags = self._global_tags.copy()
                tags.update(dp.tags)
            elif dp.tags:
                tags = dp.tags
            else:
                tags = self._global_tags
            if not tags:
                raise ValueError("Missing tags for the metric "
                                 + dp.metric +
                                 ". Either pass it as value of the tags"
                                 " parameter to DataPoint or"
                                 " set environment variable '"
                                 + APPTUIT_PY_TAGS +
                                 "' for global tags")
            row = {}
            row["metric"] = dp.metric
            row["timestamp"] = dp.timestamp
            row["value"] = dp.value
            row["tags"] = tags
            data.append(row)
        return data

    def send(self, datapoints):
        """
        Send the given set of datapoints to Apptuit for storing
        Params:
            datapoints: A list of DataPoint objects
        It raises an ApptuitException in case the backend API responds with an error
        """
        if not datapoints:
            return
        url = self.endpoint + "/api/put?sync&sync=60000&details"
        data = self._create_payload(datapoints)
        body = json.dumps(data)
        body = zlib.compress(body.encode("utf-8"))
        headers = {}
        headers["Authorization"] = "Bearer " + self.token
        headers["Content-Type"] = "application/json"
        headers["Content-Encoding"] = "deflate"
        response = requests.post(url, data=body, headers=headers)
        if response.status_code != 200 and response.status_code != 204:
            status_code = response.status_code
            if status_code == 400:
                resp_json = response.json()
                raise ApptuitSendException(
                    "Apptuit.send() failed, Due to %d error" % (status_code),
                    status_code, resp_json["success"],
                    resp_json["failed"], resp_json["errors"]
                )
            elif status_code == 401:
                error = "Apptuit API token is invalid."
            else:
                error = "Server Error."
            raise ApptuitSendException("Apptuit.send() failed, Due to %d error" % (status_code),
                                       status_code, 0, len(datapoints), error)

    def query(self, query_str, start, end=None, retry_count=0):
        """
            Execute the given query on Query service
            Params:
                query_str - The query string
                start - the start timestamp (unix epoch in seconds)
                end - the end timestamp (unix epoch in seconds)
            Returns a QueryResult object
            Individual queried items can be accessed by indexing the result object using either
            the integer index of the metric in the query or the metric name.

        Example:
            apptuit = Apptuit(token=token, api_endpoint='http://api.apptuit.ai')
            res = apptuit.query("cpu=fetch('node.cpu').downsample('1h', 'avg');\n \
                                 load=fetch('node.load1').downsample('1h', 'avg');\n \
                                 output(cpu, load)",start=start_time)
            # The resulting data can be accessed in two wasy
            # 1. using the output name used in the query:
            cpu_df = res['cpu'].to_df()
            load_df = res['load'].to_df()
            # 2. using integer index based on the ordering of the metric in the query
            cpu_df = res[0].to_df()
            load_df = res[1].to_df()
        """
        try:
            url = self.__generate_request_url(query_str, start, end)
            return self._execute_query(url, start, end)
        except (requests.exceptions.HTTPError, requests.exceptions.SSLError) as e:
            if retry_count > 0:
                time.sleep(1)
                return self.query(query_str, start, end, retry_count=retry_count - 1)
            else:
                raise ApptuitException("Failed to get response from Apptuit"
                                       "query service due to exception: %s" % str(e))

    def _execute_query(self, query_string, start, end):
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        hresp = requests.get(query_string, headers=headers)
        if self.debug:
            sys.stderr.write('%s\n' % hresp.url)
        body = hresp.content
        return _parse_response(body, start, end)

    def __generate_request_url(self, query_string, start, end):
        query_string = self.endpoint + "/api/query" + \
            _generate_query_string(query_string, start, end)
        return query_string


class TimeSeries(object):
    """
    Represents a timeseries consisting of metadata, such as tags and metric name, as well as
    the data (the index and the values)
    """

    def __init__(self, metric, tags, index, values):
        self.metric = metric
        self.tags = tags
        if index is None and values is not None:
            raise ValueError("index cannot be None if values is not None")
        if index is not None and values is None:
            raise ValueError("values cannot be None if index is not None")
        if index is not None and values is not None:
            if len(index) != len(values):
                raise ValueError("Length of index and values must be equal")
            self.timestamps = index
            self.values = values
        else:
            self.timestamps = []
            self.values = []

    @property
    def metric(self):
        return self._metric

    @metric.setter
    def metric(self, metric):
        if not _contains_valid_chars(metric):
            raise ValueError("metric contains characters which are not allowed, "
                             "only characters [a-z], [A-Z], [0-9] and [-_./] are allowed")
        self._metric = str(metric)

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        if not isinstance(tags, dict):
            raise ValueError("tags parameter is expected to be a dict type")
        _validate_tags(tags)
        self._tags = tags

    def __repr__(self):
        repr_str = '%s{' % self.metric
        for tagk in sorted(self.tags):
            tagv = self.tags[tagk]
            repr_str = repr_str + '%s:%s, ' % (tagk, tagv)
        repr_str = repr_str[:-2] + '}'
        return repr_str

    def __str__(self):
        return self.__repr__()


class Output(object):
    """
    Represents the output of a query, consisting of a list of TimeSeries
    objects representing each time series returned for the query.
    """

    def __init__(self, debug=False):
        self.series = []
        self.__dataframe = None
        self.debug = debug

    def to_df(self, tz=None):
        """
            Create a Pandas DataFrame from this data
        """
        series_names = []
        series_list = []
        for s in self.series:
            series_name = str(s)
            series_names.append(series_name)
            series_index = pd.to_datetime(s.timestamps, unit='s').tz_localize(tz)
            pseries = pd.Series(data=s.values, index=series_index)
            series_list.append(pseries)
        dataframe = pd.concat(series_list, axis=1)
        dataframe.columns = series_names
        self.__dataframe = dataframe
        return dataframe

class QueryResult(object):
    """
    The object returned by Apptuit.query method. Represents the combined
    results of the query being executed. If the query which was executed consisted
    of multiple lines and multiple outputs were expected it will contain multiple Output
    objects for each of those.
    """

    def __init__(self, start, end=None):
        self.__outputs = defaultdict(Output)
        self.start = start
        self.end = end
        self.__output_keys = {}
        self.__output_index = 0

    def __repr__(self):
        return '{start: %d, end: %s, outputs: %s}' % \
        (self.start, str(self.end) if self.end is not None else '',
         ', '.join(self.__outputs.keys()))

    def __setitem__(self, key, value):
        self.__outputs[key] = value
        self.__output_keys[self.__output_index] = key
        self.__output_index += 1

    def __getitem__(self, key):
        output_id = key
        if isinstance(key, int):
            output_id = self.__output_keys[key]
        return self.__outputs[output_id]


class DataPoint(object):
    """
    A single datapoint, representing value of a metric at a specific timestamp
    """

    def __init__(self, metric, tags, timestamp, value):
        """
        Params:
            metric: The name of the metric
            tags: A dict representing the tag keys and values of this metric
            timestamp: Number of seconds since Unix epoch
            value: value of the metric at this timestamp (int or float)
        """
        self.metric = metric
        self.tags = tags
        self.timestamp = timestamp
        self.value = value

    @property
    def metric(self):
        return self._metric

    @metric.setter
    def metric(self, metric):
        if not _contains_valid_chars(metric):
            raise ValueError("Metric name contains invalid character(s), "
                             "allowed characters are a-z, A-Z, 0-9, -, _, ., and /")
        self._metric = metric

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        self._tags = None
        if tags is None:
            return
        if not isinstance(tags, dict):
            raise ValueError("Expected a value of type dict for tags")
        _validate_tags(tags)
        self._tags = tags

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if isinstance(value, (int, float)):
            self._value = value
        elif isinstance(value, str):
            try:
                self._value = float(value)
            except ValueError:
                raise ValueError("Expected a numeric value got %s" % value)
        else:
            raise ValueError("Expected a numeric value for the value parameter")

    def __repr__(self):
        repr = self.metric + "{"
        for tagk, tagv in self.tags.items():
            repr = repr + "%s:%s, " % (tagk, tagv)
        repr = repr[:-2] + ", timestamp: %d, value: %f}" % (self.timestamp, self.value)
        return repr

    def __str__(self):
        return self.__repr__()

class ApptuitException(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg

    def __str__(self):
        return self.msg

class ApptuitSendException(ApptuitException):
    """
        An exception raised by Apptuit.send()
    """
    def __init__(self, msg, status_code, success=None, failed=None, errors=None):
        super(ApptuitSendException, self).__init__(msg)
        self.msg = msg
        self.status_code = status_code
        self.errors = errors
        self.success = success
        self.failed = failed

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if self.status_code == 400:
            msg = str(self.failed) + " errors occurred\n"
            for error in self.errors:
                dp = error["datapoint"]
                error_msg = error["error"]
                msg += "In the datapoint " + str(dp) + " Error Occurred: " + str(error_msg) + '\n'
            return msg
        msg = "Status Code: " + str(self.status_code) + \
              "; Failed to send " + str(self.failed) + \
              " datapoints; Error Occured: " + self.errors + "\n"
        return msg
