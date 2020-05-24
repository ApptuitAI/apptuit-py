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

import os
import random
import time

import requests
from requests import Response

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from nose.tools import assert_raises, assert_is_not_none, assert_equals
from apptuit import Apptuit, DataPoint, TimeSeries, ApptuitException, APPTUIT_PY_TOKEN, \
    APPTUIT_PY_TAGS, ApptuitSendException, apptuit_client


def __get_apptuit_client():
    token = "asdashdsauh_8aeraerf"
    return Apptuit(token, api_endpoint="http://localhost")


def test_client_global_tags():
    """
    Test that client object is working as expected with _global_tags
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tagk1: 22, tagk2: tagv2'})
    mock_environ.start()
    client = Apptuit(sanitize_mode=None, )
    assert_equals(client._global_tags, {"tagk1": "22", "tagk2": "tagv2"})
    mock_environ.stop()

    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tagk1: 22, tagk2: tagv2'})
    mock_environ.start()
    client = Apptuit(sanitize_mode=None, ignore_environ_tags=True)
    assert_equals(client._global_tags, None)
    mock_environ.stop()

    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tk1: tv1, tk2: tv2'})
    mock_environ.start()
    client = Apptuit(sanitize_mode=None, global_tags={"tagk1": "22", "tagk2": "tagv2"})
    assert_equals(client._global_tags, {"tagk1": "22", "tagk2": "tagv2"})
    mock_environ.stop()


@patch('apptuit.apptuit_client.requests.post')
def test_send_positive(mock_post):
    """
    Test that send API is working as expected
    """
    mock_post.return_value.status_code = 204
    client = __get_apptuit_client()
    metric_name = "node.load_avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    dps = []
    client.send(dps)
    points_sent = 0
    while True:
        ts = int(time.time())
        dps.append(DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random()))
        if len(dps) == 100:
            client.send(dps)
            dps = []
            points_sent += 100
        if points_sent > 500:
            break


@patch('apptuit.apptuit_client.requests.post')
def test_send_server_error(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    mock_post.return_value.status_code = 500
    client = __get_apptuit_client()
    metric_name = "node.load_avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    dps = []
    points_sent = 0
    while True:
        ts = int(time.time())
        dps.append(DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random()))
        if len(dps) == 100:
            with assert_raises(ApptuitException):
                client.send(dps)
            dps = []
            points_sent += 100
        if points_sent > 500:
            break

@patch('apptuit.apptuit_client.requests.post')
def test_send_with_retry(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    err_response = Response()
    err_response.status_code = 505
    mock_post.return_value.status_code = 500
    mock_post.return_value.raise_for_status.side_effect = requests.exceptions.SSLError(response=err_response)
    client = __get_apptuit_client()
    metric_name = "node.load_avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    dps = []
    ts = int(time.time())
    for i in range(100):
        dps.append(DataPoint(metric=metric_name, tags=tags, timestamp=ts + i, value=random.random()))
    with assert_raises(ApptuitException):
        client.send(dps, retry_count=1)

@patch('apptuit.apptuit_client.requests.post')
def test_send_with_retry_con_err(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    mock_post.side_effect = requests.exceptions.ConnectionError
    client = __get_apptuit_client()
    metric_name = "node.load_avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    dps = []
    ts = int(time.time())
    for i in range(100):
        dps.append(DataPoint(metric=metric_name, tags=tags, timestamp=ts + i, value=random.random()))
    with assert_raises(requests.exceptions.ConnectionError):
        client.send(dps, retry_count=1)

@patch('apptuit.apptuit_client.requests.post')
def test_send_413_error(mock_post):
    """
    Test for the case when we get 413 from the PUT API
    """
    mock_post.return_value.status_code = 413
    token = "asdashdsauh_8aeraerf"
    client = __get_apptuit_client()
    metric_name = "node.load_avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    dps = []
    points_sent = 0
    while True:
        ts = int(time.time())
        dps.append(DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random()))
        if len(dps) == 100:
            with assert_raises(ApptuitSendException):
                client.send(dps)
            dps = []
            points_sent += 100
        if points_sent > 500:
            break


def test_no_token():
    """
            Test that no token raises error
    """
    with assert_raises(ValueError) as ex:
        client = Apptuit(sanitize_mode=None, token="")
    with assert_raises(ValueError) as ex:
        client = Apptuit(sanitize_mode=None, token=None)


def test_invalid_chars_in_tag_keys():
    """
    Test for invalid character in tag keys
    """
    metric_name = "node.load_avg.1m"
    tags = {"ho\\st": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    client = Apptuit(sanitize_mode=None, token="test")
    with assert_raises(ValueError) as ex:
        dp = DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())
        client.send([dp])
    with assert_raises(AttributeError) as ex:
        dp = DataPoint(metric=metric_name, tags="error", timestamp=ts, value=random.random())
        client.send([dp])
    dp = DataPoint(metric=metric_name, tags=None, timestamp=ts, value=random.random())
    assert_equals(dp.tags, None)


def test_invalid_chars_in_tag_values():
    """
    Test for invalid character in tag values
    """
    metric_name = "node.load_avg.1m"
    tags = {"host": "local:host", "region": "us east 1", "service": "web+server"}
    ts = int(time.time())
    DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())


def test_tags_not_dict():
    """
    Test to validate that only dict type values are expected for tags
    """
    metric_name = "node.load_avg.1m"
    tags = ["host", "localhost", "region", "us-east-1", "service", "web-server"]
    ts = int(time.time())
    client = Apptuit(sanitize_mode=None, token="test")
    with assert_raises(AttributeError) as ex:
        dp = DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())
        client.send([dp])


def test_invalid_metric_name():
    """
    Test for invalid character in metric name
    """
    metric_name = "node.load+avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    client = Apptuit(sanitize_mode=None, token="test")
    with assert_raises(ValueError) as ex:
        dp = DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())
        client.send([dp])


def test_invalid_datapoint_value():
    """
    Test for a non-numeric value for DataPoint
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 'abc'
    with assert_raises(ValueError) as ex:
        DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=value)


def test_numeric_datapoint_value():
    """
    Test for a numeric DataPoint value
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 3.14
    point = DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=value)
    assert_is_not_none(point)


def test_numeric_string_datapoint_value():
    """
    Test for a valid DataPoint value which is a string
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = '3.14'
    point = DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=value)
    assert_is_not_none(point)


def test_datapoint_value_getter():
    """
    Test that the value used to create the DataPoint matches with the value
    returned by the object after creation
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 3.14
    point = DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=value)
    assert_equals(point.value, value)


def test_nonstring_invalid_datapoint_value():
    """
    Test for a non-str/numeric value for datapoint value
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = object()
    with assert_raises(ValueError):
        DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=value)


def test_apptuit_send_exception_str():
    """
    Test __star__ for ApptuitSendException
    """
    err = str(ApptuitSendException(
        "test", 400, 1, 1, [{"datapoint": "test", "error": "test_error"}]
    ))
    assert_equals(err, "1 points failed with status: 400\ntest_error error occurred in the "
                       "datapoint test\n")


def test_apptuit_send_exception_repr():
    """
    Test __repr__ for ApptuitSendException
    """
    err = repr(ApptuitSendException(
        "test", 400, 1, 1, [{"datapoint": "test", "error": "test_error"}]
    ))
    assert_equals(err, "1 points failed with status: 400\ntest_error error occurred in the "
                       "datapoint test\n")


def test_apptuit_send_exception_without_status():
    """
    Test __str__ for ApptuitSendException without status_code parameter
    """
    err = str(ApptuitSendException(
        "test", success=1, failed=1, errors=[{"datapoint": "test", "error": "test_error"}]
    ))
    assert_equals(err, "1 points failed\ntest_error error occurred in the "
                       "datapoint test\n")


@patch('apptuit.apptuit_client.requests.post')
def test_apptuit_send_exception_400(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    mock_post.return_value.status_code = 400
    mock_post.return_value.content = '{"success": 0, "failed": 1, ' + \
                                     '"errors": [{"datapoint": "", "error": "test_error"}] }'
    client = __get_apptuit_client()
    dp = DataPoint(metric="test", tags={"tk": "tv"}, timestamp=123, value=123)
    dps = [dp]
    with assert_raises(ApptuitSendException):
        client.send(dps)


@patch('apptuit.apptuit_client.requests.post')
def test_apptuit_send_exception_401(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    mock_post.return_value.status_code = 401
    token = "asdashdsauh_8aeraerf"
    client = __get_apptuit_client()
    dp = DataPoint(metric="test", tags={"tk": "tv"}, timestamp=123, value=123)
    dps = [dp]
    with assert_raises(ApptuitSendException):
        client.send(dps)


def test_timeseries_payload():
    """
    Test payload from timeseries list
    """
    token = "asdashdsauh_8aeraerf"
    client = __get_apptuit_client()
    series_list = []
    tags1 = {"tagk1": "tagv1", "tagk2": "tagv2"}
    tags2 = {"tagk3": "tagv3"}
    metric1_name = 'metric1'
    metrics2_name = "metric2"
    series1 = TimeSeries(metric1_name, tags1)
    series2 = TimeSeries(metrics2_name, tags2)
    timestamp = int(time.time())
    val1 = 3.14
    val2 = 42.0
    series1.add_point(timestamp, val1)
    series2.add_point(timestamp, val2)
    series_list.append(series1)
    series_list.append(series2)
    payload, points_count = client._create_payload_from_timeseries(series_list)
    assert_equals(points_count, 2)
    expected_payload = [
        {"metric": metric1_name, "tags": tags1, "timestamp": timestamp, "value": val1},
        {"metric": metrics2_name, "tags": tags2, "timestamp": timestamp, "value": val2}]
    assert_equals(expected_payload, payload)


def test_timeseries_payload_negative():
    """
    Negative tests for payload creation from timeseries list
    """
    token = "asdashdsauh_8aeraerf"
    client = __get_apptuit_client()
    series_list = []
    metric1_name = 'metric1'
    metrics2_name = "metric2"
    tags2 = {"tagk3": "tagv3"}
    series1 = TimeSeries(metric1_name, tags=None)
    series2 = TimeSeries(metrics2_name, tags2)
    timestamp = int(time.time())
    val1 = 3.14
    val2 = 42.0
    series1.add_point(timestamp, val1)
    series2.add_point(timestamp, val2)
    series_list.append(series1)
    series_list.append(series2)
    with assert_raises(ValueError):
        payload, points_count = client._create_payload_from_timeseries(series_list)


def test_timeseries_payload_with_globaltags():
    """
    Test payload creation from timeseries list with global tags
    """
    token = "asdashdsauh_8aeraerf"
    global_tags = {"gtagk1": "gtagv1"}
    client = Apptuit(sanitize_mode=None, token=token, global_tags=global_tags)
    series_list = []
    metric1_name = 'metric1'
    metric2_name = "metric2"
    tags2 = {"tagk3": "tagv3"}
    series1 = TimeSeries(metric1_name, tags=None)
    series2 = TimeSeries(metric2_name, tags2)
    timestamp = int(time.time())
    val1 = 3.14
    val2 = 42.0
    series1.add_point(timestamp, val1)
    series2.add_point(timestamp, val2)
    series_list.append(series1)
    series_list.append(series2)
    payload, points_count = client._create_payload_from_timeseries(series_list)
    assert_equals(points_count, 2)
    expected_payload = [
        {"metric": metric1_name, "tags": global_tags, "timestamp": timestamp, "value": val1},
        {"metric": metric2_name, "tags": {"tagk3": "tagv3", "gtagk1": "gtagv1"},
         "timestamp": timestamp, "value": val2}]
    assert_equals(expected_payload, payload)


def test_timeseries_payload_with_envtags():
    """
    Test payload creation from timeseries list with global tags in env variable
    """
    token = "asdashdsauh_8aeraerf"
    global_tags = "gtagk1:gtagv1"
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TAGS: global_tags})
    mock_environ.start()
    client = __get_apptuit_client()
    series_list = []
    metric1_name = 'metric1'
    metric2_name = "metric2"
    tags2 = {"tagk3": "tagv3"}
    series1 = TimeSeries(metric1_name, tags=None)
    series2 = TimeSeries(metric2_name, tags2)
    timestamp = int(time.time())
    val1 = 3.14
    val2 = 42.0
    series1.add_point(timestamp, val1)
    series2.add_point(timestamp, val2)
    series_list.append(series1)
    series_list.append(series2)
    payload, points_count = client._create_payload_from_timeseries(series_list)
    mock_environ.stop()
    assert_equals(points_count, 2)
    expected_payload = [
        {"metric": metric1_name, "tags": {"gtagk1": "gtagv1"}, "timestamp": timestamp, "value": val1},
        {"metric": metric2_name, "tags": {"tagk3": "tagv3", "gtagk1": "gtagv1"},
         "timestamp": timestamp, "value": val2}]
    assert_equals(expected_payload, payload)


@patch('apptuit.apptuit_client.requests.post')
def test_send_timeseries(mock_post):
    """
    Test the send_timeseries API
    """
    mock_post.return_value.status_code = 204
    token = "asdashdsauh_8aeraerf"
    client = __get_apptuit_client()
    series_list = []
    tags1 = {"tagk1": "tagv1", "tagk2": "tagv2"}
    tags2 = {"tagk3": "tagv3"}
    metric1_name = 'metric1'
    metrics2_name = "metric2"
    series1 = TimeSeries(metric1_name, tags1)
    series2 = TimeSeries(metrics2_name, tags2)
    timestamp = int(time.time())
    val1 = 3.14
    val2 = 42.0
    series1.add_point(timestamp, val1)
    series2.add_point(timestamp, val2)
    series_list.append(series1)
    series_list.append(series2)
    client.send_timeseries(series_list)


@patch('apptuit.apptuit_client.requests.post')
def test_send_timeseries_empty(mock_post):
    """
    Test the send_timeseries API with an empty series list
    """
    mock_post.return_value.status_code = 204
    token = "asdashdsauh_8aeraerf"
    client = __get_apptuit_client()
    series_list = []
    client.send_timeseries(series_list)
    series1 = TimeSeries("metric", {"tagk1": "tagv1"})
    client.send_timeseries([series1])


def test_none_datapoint_value():
    """
    Test DataPoint creation with None value
    """
    timestamp = int(time.time())
    with assert_raises(ValueError):
        DataPoint("metric1", None, timestamp, None)


def test_datapoint_repr():
    """
    Test __repr__ of DataPoint
    """
    timestamp = int(time.time())
    point = DataPoint('metric1', {"tagk1": "tagv1", "tagk2": "tagv2"}, timestamp, 3.14)
    expected_repr = 'metric1{tagk1:tagv1, tagk2:tagv2, timestamp: %d, value: %f}' % (timestamp, 3.14)
    assert_equals(repr(point), expected_repr)
    assert_equals(str(point), expected_repr)


@patch('apptuit.apptuit_client.requests.post')
def test_tags_limit_direct(mock_post):
    """
    Test for failure when too many tags are used for datapoints/series
    """
    tags = {'tagk-%d' % i: 'tagv-%d' % i for i in range(apptuit_client.MAX_TAGS_LIMIT + 1)}
    timestamp = int(time.time())
    client = Apptuit(sanitize_mode=None, token="test_token")
    point1 = DataPoint("metric1", {"tagk1": "tagv1"}, timestamp, 3.14)
    point2 = DataPoint("metric1", tags, timestamp, 3.14)
    with assert_raises(ValueError):
        client.send([point1, point2])
    series1 = TimeSeries('metric1', {"tagk1": "tagv1"})
    series1.add_point(timestamp, 3.14)
    series2 = TimeSeries('metric1', tags)
    series2.add_point(timestamp, 3.14)
    with assert_raises(ValueError):
        client.send_timeseries([series1, series2])


@patch('apptuit.apptuit_client.requests.post')
def test_tags_limit_indirect(mock_post):
    """
    Test for failure when too many tags are used indirectly (when combined with global tags)
    """
    gtags_list = ["gtk-%d:gtv-%d" % (i, i) for i in range(apptuit_client.MAX_TAGS_LIMIT // 2 + 1)]
    global_tags = ",".join(gtags_list)
    tags = {'tagk-%d' % i: 'tagv-%d' % i for i in range(apptuit_client.MAX_TAGS_LIMIT // 2 + 1)}
    timestamp = int(time.time())
    with patch.dict(os.environ, {APPTUIT_PY_TAGS: global_tags}):
        client = Apptuit(sanitize_mode=None, token="test_token")
        point1 = DataPoint("metric1", {"tagk1": "tagv1"}, timestamp, 3.14)
        point2 = DataPoint("metric1", tags, timestamp, 3.14)
        with assert_raises(ValueError):
            client.send([point1, point2])

    with patch.dict(os.environ, {APPTUIT_PY_TAGS: global_tags}):
        client = Apptuit(sanitize_mode=None, token="test_token")
        series1 = TimeSeries('metric1', {"tagk1": "tagv1"})
        series1.add_point(timestamp, 3.14)
        series2 = TimeSeries('metric1', tags)
        series2.add_point(timestamp, 3.14)
        with assert_raises(ValueError):
            client.send_timeseries([series1, series2])
