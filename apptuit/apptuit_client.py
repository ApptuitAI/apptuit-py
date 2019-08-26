#
# Copyright 2018 Agilx, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Client module for Apptuit APIs
"""
import json
import os
import random
import sys
import time
import warnings
import zlib
from collections import defaultdict

import requests

from apptuit import APPTUIT_PY_TOKEN, APPTUIT_PY_TAGS, DEPRECATED_APPTUIT_PY_TOKEN, __version__
from apptuit.utils import _contains_valid_chars, _get_tags_from_environment, \
    _validate_tags, sanitize_name_prometheus, sanitize_name_apptuit

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

MAX_TAGS_LIMIT = 25
SANITIZERS = {
    "apptuit": sanitize_name_apptuit,
    "prometheus": sanitize_name_prometheus
}
BASE_SLEEP_TIME_SECS = 2

def _get_user_agent():
    py_version = sys.version.split()[0]
    return "apptuit-py-" + __version__ + ", requests-" + requests.__version__ + ", Py-" + py_version


def _generate_query_string(query_string, start, end):
    ret = "?start=" + str(start)
    if end:
        ret += "&end=" + str(end)
    ret += "&q=" + quote(query_string, safe='')
    return ret


def _parse_response(resp, start, end=None):
    json_resp = json.loads(resp)
    outputs = json_resp["outputs"]
    if not outputs:  # Pythonic way of checking if list is empty
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
                if end is not None and point[0] > end:
                    continue
                index.append(point[0])
                values.append(point[1])
            series = TimeSeries(result["metric"], result["tags"], index, values)
            qresult[output_id].series.append(series)
    return qresult


class Apptuit(object):
    """
    Apptuit client - providing APIs to send and query data from Apptuit
    """

    def __init__(self, token=None, api_endpoint="https://api.apptuit.ai",
                 global_tags=None, ignore_environ_tags=False,
                 sanitize_mode="prometheus"):
        """
        Create an apptuit client object
        Params:
            token: Apptuit token for your tenant
            api_endpoint: Apptuit API End point (including the protocol and port)
            global_tags: Tags for all datapoints (should be a dict). If you pass
                    value for global_tags, the APPTUIT_PY_TAGS environment variable
                    will not be used, even if ignore_environ_tags is false.
            ignore_environ_tags: True/False - whether to use environment variable for
                    global tags (APPTUIT_PY_TAGS)
            sanitize_mode: Is a string value which will enable sanitizer, sanitizer will
                    automatically change your metric names to be compatible with apptuit
                    or prometheus. Set it to None if not needed.
        """
        self.sanitizer = None
        if sanitize_mode:
            self.sanitizer = SANITIZERS.get(sanitize_mode.lower(), None)
            if not self.sanitizer:
                raise ValueError("sanitizer_mode can only be set to apptuit"
                                 ",prometheus or None.")
        if not token:
            token = os.environ.get(APPTUIT_PY_TOKEN)
            if not token:
                token = os.environ.get(DEPRECATED_APPTUIT_PY_TOKEN)
                if token:
                    warnings.warn("The environment variable %s is deprecated,"
                                  "please use %s instead" %
                                  (DEPRECATED_APPTUIT_PY_TOKEN, APPTUIT_PY_TOKEN),
                                  DeprecationWarning)
            if not token:
                raise ValueError("Missing Apptuit API token, "
                                 "either pass it as a parameter or "
                                 "set as value of the environment variable '"
                                 + APPTUIT_PY_TOKEN + "'.")
        self.token = token
        if not api_endpoint:
            raise ValueError("Invalid value for the 'api_endpoint' parameter")

        self.endpoint = api_endpoint
        if self.endpoint[-1] == '/':
            self.endpoint = self.endpoint[:-1]
        self._global_tags = global_tags
        if not self._global_tags and not ignore_environ_tags:
            self._global_tags = _get_tags_from_environment()

    @property
    def put_apiurl(self):
        """
        Apptuit PUT API URL
        """
        return self.endpoint + "/api/put?details"

    def _combine_tags_with_globaltags(self, tags):
        if tags:
            if self._global_tags:
                combined_tags = self._global_tags.copy()
                combined_tags.update(tags)
            else:
                combined_tags = tags
            return combined_tags
        elif self._global_tags:
            return self._global_tags
        return None

    def _create_payload_from_datapoints(self, datapoints):
        data = []
        for point in datapoints:
            if self.sanitizer:
                sanitized_metric = self.sanitizer(point.metric)
            else:
                if not _contains_valid_chars(point.metric):
                    raise ValueError("Metric Name %s contains an invalid character, "
                                     "allowed characters are unicode letter, "
                                     "a-z, A-Z, 0-9, -, _, ., and /" % point.metric)
                sanitized_metric = point.metric
            tags = self._combine_tags_with_globaltags(point.tags)
            if not tags:
                raise ValueError("Missing tags for the metric "
                                 + point.metric +
                                 ". Either pass it as value of the tags"
                                 " parameter to DataPoint or"
                                 " set environment variable '"
                                 + APPTUIT_PY_TAGS +
                                 "' for global tags")
            if len(tags) > MAX_TAGS_LIMIT:
                raise ValueError("Too many tags for datapoint %s, maximum allowed number of tags "
                                 "is %d, found %d tags" % (point, MAX_TAGS_LIMIT, len(tags)))
            if self.sanitizer:
                sanitized_tags = {}
                for key, val in tags.items():
                    sanitized_tags[self.sanitizer(key)] = val
                tags = sanitized_tags
            else:
                _validate_tags(tags)
            row = dict()
            row["metric"] = sanitized_metric
            row["timestamp"] = point.timestamp
            row["value"] = point.value
            row["tags"] = tags
            data.append(row)
        return data

    def _create_payload_from_timeseries(self, timeseries_list):
        data = []
        points_count = 0
        for timeseries in timeseries_list:
            tags = self._combine_tags_with_globaltags(timeseries.tags)
            if not tags:
                raise ValueError("Missing tags for the metric '%s'. Either pass it as value "
                                 "of the tags parameter to TimeSeriesName, or set environment "
                                 "variable '%s' for global tags, or pass 'global_tags' parameter "
                                 "to the apptuit_client" % (timeseries.metric, APPTUIT_PY_TAGS))

            if len(tags) > MAX_TAGS_LIMIT:
                raise ValueError("Too many tags for timeseries %s, maximum allowed number of tags "
                                 "is %d, found %d tags" % (timeseries, MAX_TAGS_LIMIT, len(tags)))
            for timestamp, value in zip(timeseries.timestamps, timeseries.values):
                row = {"metric": timeseries.metric,
                       "tags": tags,
                       "timestamp": timestamp,
                       "value": value}
                data.append(row)
                points_count += 1
        return data, points_count

    def send(self, datapoints, timeout=60, retry_count=0):
        """
        Send the given set of datapoints to Apptuit
        Params:
            datapoints: A list of DataPoint objects
            timeout: Timeout (in seconds) for the HTTP request
            retry_count: This will allow you to retry to send
            DP's in case of errors. This uses Backoff-jitter
            algo to retry
            `https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/`
        It raises an ApptuitSendException in case the backend API responds with an error
        """
        if not datapoints:
            return
        payload = self._create_payload_from_datapoints(datapoints)
        try_number = 0
        while True:
            try:
                try_number += 1
                self.__send(payload, len(datapoints), timeout)
                return
            except ApptuitSendException as apptuit_exception:
                if retry_count >= try_number:
                    if 500 <= apptuit_exception.status_code <= 599:
                        self.backoff_with_jitter(try_number)
                        continue
                raise apptuit_exception
            except requests.exceptions.ConnectionError as conn_err:
                if retry_count >= try_number:
                    self.backoff_with_jitter(try_number)
                    continue
                raise conn_err

    @staticmethod
    def backoff_with_jitter(try_number):
        """
        This will add sleep to current execution, based on try number
        :param try_number: the retry_count
        :return: None
        """
        sleep_time = int(random.randrange(0, min(30, BASE_SLEEP_TIME_SECS * (2 ** try_number))))
        time.sleep(sleep_time)

    def send_timeseries(self, timeseries_list, timeout=60):
        """
        Send a list of timeseries to Apptuit
        Parameters
        ----------
            timeseries_list: A list of TimeSeries objects
            timeout: Timeout (in seconds) for the HTTP request
        """
        if not timeseries_list:
            return
        data, points_count = self._create_payload_from_timeseries(timeseries_list)
        if points_count != 0:
            self.__send(data, points_count, timeout)

    @staticmethod
    def __get_size_in_mb(buf):
        return sys.getsizeof(buf) * 1.0 / (1024 ** 2)

    def __send(self, payload, points_count, timeout):
        body = json.dumps(payload)
        body = zlib.compress(body.encode("utf-8"))
        headers = dict()
        headers["Authorization"] = "Bearer " + self.token
        headers["Content-Type"] = "application/json"
        headers["Content-Encoding"] = "deflate"
        headers["User-Agent"] = _get_user_agent()
        response = requests.post(self.put_apiurl, data=body, headers=headers, timeout=timeout)
        if response.status_code != 200 and response.status_code != 204:
            status_code = response.status_code
            if status_code == 400:
                resp_json = response.json()
                raise ApptuitSendException(
                    "Apptuit.send() failed due to %d error" % status_code,
                    status_code, resp_json["success"],
                    resp_json["failed"], resp_json["errors"]
                )
            if status_code == 413:
                raise ApptuitSendException("Too big payload for Apptuit.send(). Trying to send"
                                           " %f mb of data with %d points, please try sending "
                                           "again with fewer points" %
                                           (self.__get_size_in_mb(body), points_count),
                                           status_code, 0, points_count)
            if status_code == 401:
                error = "Apptuit API token is invalid"
            else:
                error = "Server Error"
            raise ApptuitSendException("Apptuit.send() failed, due to %d: %s" %
                                       (status_code, error),
                                       status_code, 0, points_count, [])

    def query(self, query_str, start, end=None, retry_count=0, timeout=180):
        """
            Execute the given query on Query service
            Params:
                query_str - The query string
                start - the start timestamp (unix epoch in seconds)
                end - the end timestamp (unix epoch in seconds)
                timeout - timeout (in seconds) for the HTTP request
                retry_count: This will allow you to retry to send
                DP's in case of errors. this uses Backoff-jitter
                algo to retry
                `https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/`
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
        url = self.__generate_request_url(query_str, start, end)
        try_number = 0
        while True:
            try:
                try_number += 1
                return self._execute_query(url, start, end, timeout)
            except requests.exceptions.HTTPError as http_error:
                if retry_count >= try_number:
                    if http_error.response is not None:
                        if 500 <= http_error.response.status_code <= 599:
                            self.backoff_with_jitter(try_number)
                            continue
                raise ApptuitException("Failed to get response from Apptuit"
                                       "query service due to exception: %s" % str(http_error))
            except requests.exceptions.SSLError as ssl_error:
                raise ApptuitException("Failed to get response from Apptuit"
                                       "query service due to exception: %s" % str(ssl_error))
            except requests.exceptions.ConnectionError as connection_error:
                if retry_count >= try_number:
                    self.backoff_with_jitter(try_number)
                    continue
                raise connection_error

    def _execute_query(self, query_string, start, end, timeout):
        headers = dict()
        headers["User-Agent"] = _get_user_agent()
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        hresp = requests.get(query_string, headers=headers, timeout=timeout)
        hresp.raise_for_status()
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

    def __init__(self, metric, tags, index=None, values=None):
        self.name = TimeSeriesName(metric, tags)
        if not index and values:
            raise ValueError("index cannot be None if values is not None")
        if index and not values:
            raise ValueError("values cannot be None if index is not None")
        if index and values:
            if len(index) != len(values):
                raise ValueError("Length of index and values must be equal")
        self.timestamps = index or []
        self.values = values or []

    @property
    def tags(self):
        return self.name.tags

    @property
    def metric(self):
        return self.name.metric

    def __repr__(self):
        repr_str = '%s{' % self.name.metric
        for tagk in sorted(self.name.tags):
            tagv = self.name.tags[tagk]
            repr_str = repr_str + '%s:%s, ' % (tagk, tagv)
        repr_str = repr_str[:-2] + '}'
        return repr_str

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        return len(self.timestamps)

    def add_point(self, timestamp, value):
        """
        Add a new point to the timeseries object
        """
        self.timestamps.append(timestamp)
        self.values.append(float(value))


class TimeSeriesName(object):
    """
    Encapsulates a timeseries name representation by using the metric name and tags
    """

    def __init__(self, metric, tags):
        """
        Parameters
        ----------
            metric: name of the metric
            tags: tags for the metric (expected a dict type)
        """
        self.metric = metric
        self.tags = tags

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        if tags:
            for key in tags:
                if not key:
                    raise ValueError("Tag key can't be '%s'" % key)

        self._tags = tags

    @property
    def metric(self):
        return self._metric

    @metric.setter
    def metric(self, metric):
        if not metric:
            raise ValueError("metric name cannot be None or empty")
        self._metric = metric

    def __str__(self):
        return self.metric + json.dumps(self.tags, sort_keys=True)

    @staticmethod
    def encode_metric(metric_name, metric_tags):
        """
        Generate an encoded metric name by combining metric_name and metric_tags
        Params:
            metric_name: name of the metric
            metric_tags: tags (expected a dictionary of tag keys vs values)
        Returns: An string encoding the metric name and the tags which can be used when
                    creating metric objects, such as counters, timers etc.
        Example:
            s = reporter.encode_metric_name('node.cpu', {"type": "idle"})
            print(s) # 'node.cpu {"type": "idle"}'
        """
        if not isinstance(metric_name, str):
            raise ValueError("metric_name should be a string")
        if metric_name == "":
            raise ValueError("metric_name cannot be empty")
        if not isinstance(metric_tags, dict):
            raise ValueError("metric_tags must be a dictionary")

        encoded_metric_name = metric_name + json.dumps(metric_tags, sort_keys=True)
        return encoded_metric_name

    @staticmethod
    @lru_cache(maxsize=2048)
    def decode_metric(encoded_metric_name):
        """
        Decode the metric name as encoded by encode_metric_name
        Params:
            encoded_metric_name: a string encoded in a format as returned by encode_metric_name()
            example: 'metricName {"metricTagKey1":"metricValue1","metricTagKey2":"metricValue2"}'
        Returns:
            The metric name and the dictionary of tags
        """
        if encoded_metric_name is None or encoded_metric_name == "":
            raise ValueError("Invalid value for encoded_metric_name")

        metric_tags = {}
        metric_name = encoded_metric_name.strip()
        brace_index = encoded_metric_name.find('{')
        if brace_index > -1:
            try:
                metric_tags = json.loads(encoded_metric_name[brace_index:])
                metric_name = encoded_metric_name[:brace_index].strip()
            except Exception as err:
                raise ValueError("Failed to parse the encoded_metric_name %s, invalid format"
                                 % encoded_metric_name, err)
        return metric_name, metric_tags


class Output(object):
    """
    Represents the output of a query, consisting of a list of TimeSeries
    objects representing each time series returned for the query.
    """

    def __init__(self):
        self.series = []
        self.__dataframe = None

    def to_df(self, tz=None):
        """
            Create a Pandas DataFrame from this data
        """
        import pandas as pd
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
        self.timestamp = timestamp
        self.timeseries_name = TimeSeriesName(metric, tags)
        try:
            self.value = float(value)
        except TypeError:
            raise ValueError("Expected a numeric value got %s" % value)

    @property
    def metric(self):
        return self.timeseries_name.metric

    @property
    def tags(self):
        return self.timeseries_name.tags

    def __repr__(self):
        _repr = self.metric + "{"
        for tagk in sorted(self.tags):
            _repr = _repr + "%s:%s, " % (tagk, self.tags[tagk])
        _repr = _repr[:-2] + ", timestamp: %d, value: %f}" % (self.timestamp, self.value)
        return _repr

    def __str__(self):
        return self.__repr__()


class ApptuitException(Exception):

    def __init__(self, msg):
        super(ApptuitException, self).__init__(msg)
        self.msg = msg

    def __repr__(self):
        return self.msg

    def __str__(self):
        return self.msg


class ApptuitSendException(ApptuitException):
    """
        An exception raised by Apptuit.send()
    """

    def __init__(self, msg, status_code=None, success=None, failed=None, errors=None):
        super(ApptuitSendException, self).__init__(msg)
        self.msg = msg
        self.status_code = status_code
        self.errors = errors or []
        self.success = success
        self.failed = failed

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        msg = str(self.failed) + " points failed"
        if self.status_code:
            msg += " with status: %d\n" % self.status_code
        else:
            msg += "\n"
        for error in self.errors:
            dp = error["datapoint"]
            error_msg = error["error"]
            msg += "%s error occurred in the datapoint %s\n" % (str(error_msg), str(dp))
        return msg
