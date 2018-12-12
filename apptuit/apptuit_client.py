"""
Client module for Apptuit APIs
"""

from collections import defaultdict
import json
from string import ascii_letters, digits
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote
import sys
import time
import zlib
import requests
import pandas as pd

VALID_CHARSET = set(ascii_letters + digits + "-_./")
INVALID_CHARSET = frozenset(map(chr, range(128))) - VALID_CHARSET

def _contains_valid_chars(string):
    return INVALID_CHARSET.isdisjoint(string)


def _create_payload(datapoints):
    data = []
    for dp in datapoints:
        row = {}
        row["metric"] = dp.metric
        row["timestamp"] = dp.timestamp
        row["value"] = dp.value
        row["tags"] = dp.tags
        data.append(row)
    return data


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

    def __init__(self, token, api_endpoint="https://api.apptuit.ai/", debug=False):
        """
        Creates an apptuit client object
        Params:
            token: Token of the tenant to which we wish to connect
            api_endpoint: Apptuit API End point (including the protocol and port)
            port: Port on which the service is running

        """
        if not token:
            raise ValueError("Invalid token")
        self.token = token
        self.endpoint = api_endpoint
        if self.endpoint[-1] == '/':
            self.endpoint = self.endpoint[:-1]
        self.debug = debug

    def send(self, datapoints):
        """
        Send the given set of datapoints to Apptuit for storing
        Params:
            datapoints: A list of DataPoint objects
        It raises an ApptuitException in case the backend API responds with an error
        """
        url = self.endpoint + "/api/put?sync&sync=60000"
        data = _create_payload(datapoints)
        body = json.dumps(data)
        body = zlib.compress(body.encode("utf-8"))
        headers = {}
        headers["Authorization"] = "Bearer " + self.token
        headers["Content-Type"] = "application/json"
        headers["Content-Encoding"] = "deflate"
        response = requests.post(url, data=body, headers=headers)
        if response.status_code != 200 and response.status_code != 204:
            raise ApptuitException("PUT request failed with response code: "
                                   "%d and response: %s" % (response.status_code, response.content))

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
        for tagk, tagv in tags.items():
            if not _contains_valid_chars(tagk):
                raise ValueError("tag key %s contains a character which is not allowed, "
                                 "only characters [a-z], [A-Z], [0-9] and [-_./] are allowed"
                                 % (tagk))
            if not _contains_valid_chars(str(tagv)):
                raise ValueError("tag value %s contains a character which is not allowed, "
                                 "only characters [a-z], [A-Z], [0-9] and [-_./] are allowed"
                                 % (tagv))
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
        if tags is None or tags == {}:
            raise ValueError("Ivalid tags: Metric: "+metric+" need minimum one tag.")
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
        if not isinstance(tags, dict):
            raise ValueError("Expected a value of type dict for tags")
        for tagk, tagv in tags.items():
            if not _contains_valid_chars(tagk):
                raise ValueError("Tag key %s contains an invalid character, "
                                 "allowed characters are a-z, A-Z, 0-9, -, _, ., and /" % tagk)
            if not _contains_valid_chars(str(tagv)):
                raise ValueError("Tag value %s contains an invalid character, "
                                 "allowed characters are a-z, A-Z, 0-9, -, _, ., and /" % tagv)
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
