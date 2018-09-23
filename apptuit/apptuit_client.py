from collections import defaultdict
import json
from string import ascii_letters, digits
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote
import urllib
import sys
import time
import zlib
import requests
import pandas as pd

VALID_CHARSET = set(ascii_letters + digits + "-_./")
INVALID_CHARSET = frozenset(map(chr, range(128))) - VALID_CHARSET

def __contains_valid_chars(string):
    return INVALID_CHARSET.isdisjoint(string)


class Apptuit(object):

    def __init__(self, token, host="https://api.apptuit.ai", port=443, debug=False):
        """
        Creates an apptuit client object
        Params:
            token: Token of the tenant to which we wish to connect
            host: Host name of the query service (including the protocol)
            port: Port on which the service is running

        """
        self.token = token
        self.start = None
        self.end = None
        self.host = host
        self.port = port
        self.debug = debug
    
    def send(self, datapoints):
        url = self.host + ":" + str(self.port) + "/api/put?sync&sync=60000"
        data = self.__create_payload(datapoints)
        body = json.dumps(data)
        body = zlib.compress(body.encode("utf-8"))
        headers = {}
        headers["Authorization"] = "Bearer " + self.token
        headers["Content-Type"] = "application/json"
        headers["Content-Encoding"] = "deflate"
        response = requests.post(url, data=body, headers=headers)
        if response.status_code != 200 and response.status_code != 204:
            raise ApptuitException("PUT request failed with response code: %d and response: %s" % (response.status_code, response.content))

    def query(self, q, start, end=None, retry_count=0):
        """
            Execute the given query on Query service
            Params:
                q - The query service query string
                start - the start timestamp (unix epoch in seconds)
                end - the end timestamp (unix epoch in seconds)
            Returns a QueryResult object
            Individual queried items can be accessed by indexing the result object using either
            the integer index of the metric in the query or the metric name.
        
        Example:
            apptuit = Apptuit(token=token, host='http://api.apptuit.ai')
            res = apptuit.query("cpu=fetch('node.cpu').downsample('1h', 'avg');\nload=fetch('node.load1').downsample('1h', 'avg');\n output(cpu, load)", start=start_time)
            # The resulting data can be accessed in two wasy
            # 1. using the output name used in the query:
            cpu_df = res['cpu'].to_df()
            load_df = res['load'].to_df()
            # 2. using integer index based on the ordering of the metric in the query
            cpu_df = res[0].to_df()
            load_df = res[1].to_df()
        """
        try:
            url = self.generate_request_url(q, start, end)
            return self._execute_query(url, start, end)
        except (requests.exceptions.HTTPError, requests.exceptions.SSLError):
            if retry_count > 0:
                time.sleep(1)
                return self.query(q, start, end, retry_count=retry_count - 1)

    def __create_payload(self, datapoints):
        data = []
        for dp in datapoints:
            row = {}
            row["metric"] = dp.metric
            row["timestamp"] = dp.timestamp
            row["value"] = dp.value
            row["tags"] = dp.tags
            data.append(row)
        return data
    
    def _parse_response(self, resp, start, end=None):
        json_resp = json.loads(resp)
        outputs = json_resp["outputs"]
        if len(outputs) == 0:
            return None
        qresult = QueryResult(start, end)
        for output in outputs:
            results = output["result"]
            if len(results) == 0:
                continue

            output_id = output["id"]
            qresult.add_output(output_id)
            for result in results:
                dps = result["dps"]
                tags = result["tags"]
                name = result["metric"]
                index = []
                values = []
                for dp in dps:
                    if dp[0] < start:
                        continue
                    if end is not None and dp[0] >= end:
                        continue
                    index.append(dp[0])
                    values.append(dp[1])
                series = TimeSeries(name, tags, index, values)
                qresult[output_id].series.append(series)
        
        return qresult

    def _execute_query(self, q, start, end):
        headers = {}
        if len(self.token) > 0:
            headers["Authorization"] = "Bearer " + self.token
        hresp = requests.get(q, headers=headers)
        if self.debug:
            sys.stderr.write('%s\n' % hresp.url)
        body = hresp.content.decode('utf-8')
        status = hresp.status_code
        if status != 200:
            raise Exception('Failed to get response from QS, response code: %d, url: %s, response body: %s' % (status, hresp.url, body))
        return self._parse_response(body, start, end)


    def generate_request_url(self, q, start, end):
        q = self.host + (':%d' % (self.port) if self.port not in {443, 80} else '') +  "/api/query" + self.generate_query_string(q, start, end)
        return q

    def generate_query_string(self, q, start, end):
        ret = "?start=" + str(start)
        if end:
            ret += "&end=" + str(end)
        ret += "&q=" + quote(q, safe='')
        return ret


class TimeSeries(object):

    def __init__(self, metric, tags, index, values):
        self._metric = metric
        self._tags = tags
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
        if not __contains_valid_chars(metric):
            raise ValueError("metric contains characters which are not allowed, only characters [a-z], [A-Z], [0-9] and [-_./] are allowed")
        self._metric = str(metric)

    @property
    def tags(self):
        return self._tags
    
    @tags.setter
    def tags(self, tags):
        if not isinstance(tags, dict):
            raise ValueError("tags parameter is expected to be a dict type")
        for tagk, tagv in tags.items():
            if not __contains_valid_chars(tagk):
                raise ValueError("tag key %s contains a character which is not allowed, only characters [a-z], [A-Z], [0-9] and [-_./] are allowed" % (tagk))
            if not __contains_valid_chars(tagv):
                raise ValueError("tag value %s contains a character which is not allowed, only characters [a-z], [A-Z], [0-9] and [-_./] are allowed" % (tagv))
        self._tags = tags


    def __repr__(self):
        repr = '%s{' % self.metric
        for tagk in sorted(self.tags):
            tagv = self.tags[tagk]
            repr = repr + '%s:%s, ' % (tagk, tagv)
        repr = repr[:-2] + '}'
        return repr

    def __str__(self):
        return self.__repr__()


class Output(object):
    def __init__(self, debug=False):
        self.series = []
        self.df = None
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
        if len(series_list) == 0:
            if self.debug:
                sys.stderr.write('No series returned\n')
            return None
        df = pd.concat(series_list, axis=1)
        df.columns = series_names
        self.df = df
        return df
    
    def get_tags_list(self):
        return [s.tags for s in self.series]
    

class QueryResult(object):
    def __init__(self, start, end=None):
        self.__outputs = defaultdict(Output)
        self.start = start
        self.end = end
        self.__output_keys = {}
        self.__output_index = 0

    def add_output(self, output_id, output=None):
        if output is None:
            output = Output()
        self.__outputs[output_id] = output
        self.__output_keys[self.__output_index] = output_id
        self.__output_index += 1


    def __repr__(self):
        return '{start: %d, end: %s, outputs: %s}' % (self.start, str(self.end) if self.end is not None else '', ', '.join(self.__outputs.keys()))

    def __setitem__(self, key, value):
        self.__outputs[key] = value
        if isinstance(key, int):
            return
        self.__output_keys[self.__output_index] = key
        self.__output_index += 1
        return

    def __getitem__(self, key):
        output_id = key
        if isinstance(key, int):
            output_id = self.__output_keys[key]
        return self.__outputs[output_id]


class DataPoint(object):
    def __init__(self, metric, tags, timestamp, value):
        self._metric = metric
        self._tags = tags
        self.timestamp = timestamp
        self.value = value

    @property
    def metric(self):
        return self._metric

    @metric.setter
    def metric(self, metric):
        if not __contains_valid_chars(metric):
            raise ValueError("Metric name contains invalid character(s), allowed characters are a-z, A-Z, 0-9, -, _, ., and /")
        self._metric = metric

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        if not isinstance(tags, dict):
            raise ValueError("Expected a value of type dict for tags")
        for tagk, tagv in tags.items():
            if not __contains_valid_chars(tagk):
                raise ValueError("Tag key %s contains an invalid character, allowed characters are a-z, A-Z, 0-9, -, _, ., and /" % tagk)
            if not __contains_valid_chars(tagv):
                raise ValueError("Tag value %s contains an invalid character, allowed characters are a-z, A-Z, 0-9, -, _, ., and /" % tagv)
        self._tags = tags

    def __repr__(self):
        repr = self.metric + "{"
        for tagk, tagv in self.tags.items():
            repr = repr + "%s:%s, " % (tagk, tagv)
        repr = repr[:-2] + " timestamp: %d, value: %f}" % (self.timestamp, self.value)
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
