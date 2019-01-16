import os
import random
import time

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from nose.tools import assert_raises, ok_, assert_is_not_none, assert_equals, assert_true
from apptuit import Apptuit, DataPoint, TimeSeries, ApptuitException, APPTUIT_PY_TOKEN, \
                    APPTUIT_PY_TAGS, ApptuitSendException


def test_client_global_tags():
    """
    Test that client object is working as expected with _global_tags
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tagk1: 22, tagk2: tagv2'})
    mock_environ.start()
    client = Apptuit()
    assert_equals(client._global_tags, {"tagk1": "22", "tagk2": "tagv2"})
    mock_environ.stop()

    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tagk1: 22, tagk2: tagv2'})
    mock_environ.start()
    client = Apptuit(ignore_environ_tags=True)
    assert_equals(client._global_tags, None)
    mock_environ.stop()

    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tk1: tv1, tk2: tv2'})
    mock_environ.start()
    client = Apptuit(global_tags={"tagk1": "22", "tagk2": "tagv2"})
    assert_equals(client._global_tags, {"tagk1": "22", "tagk2": "tagv2"})
    mock_environ.stop()


@patch('apptuit.apptuit_client.requests.post')
def test_send_positive(mock_post):
    """
    Test that send API is working as expected
    """
    mock_post.return_value.status_code = 204
    token = "asdashdsauh_8aeraerf"
    client = Apptuit(token)
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
    if dps:
        client.send(dps)

@patch('apptuit.apptuit_client.requests.post')
def test_send_server_error(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    mock_post.return_value.status_code = 500
    token = "asdashdsauh_8aeraerf"
    client = Apptuit(token)
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
    if len(dps) > 0:
        with assert_raises(ApptuitException):
            client.send(dps)

def test_no_token():
    """
            Test that no token raises error
    """
    with assert_raises(ValueError) as ex:
        client=Apptuit("")
    with assert_raises(ValueError) as ex:
        client=Apptuit(None)


def test_invalid_chars_in_tag_keys():
    """
    Test for invalid character in tag keys
    """
    metric_name = "node.load_avg.1m"
    tags = {"ho\\st": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())
    with assert_raises(AttributeError) as ex:
        DataPoint(metric=metric_name, tags="error", timestamp=ts, value=random.random())
    dp = DataPoint(metric=metric_name, tags=None, timestamp=ts, value=random.random())
    assert_equals(dp.tags,None)

def test_invalid_chars_in_tag_values():
    """
    Test for invalid character in tag values
    """
    metric_name = "node.load_avg.1m"
    tags = {"host": "local:host", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())

def test_tags_not_dict():
    """
    Test to validate that only dict type values are expected for tags
    """
    metric_name = "node.load_avg.1m"
    tags = ["host", "localhost", "region", "us-east-1", "service", "web-server"]
    ts = int(time.time())
    with assert_raises(AttributeError) as ex:
        DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())


def test_invalid_metric_name():
    """
    Test for invalid character in metric name
    """
    metric_name = "node.load+avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric=metric_name, tags=tags, timestamp=ts, value=random.random())

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

def test_apptuit_send_exception():
    """
    Test that ApptuitSendException str is valid
    """
    err = str(ApptuitSendException(
        "test", 400, 1, 1, [{"datapoint": "test", "error": "test_error"}]
    ))
    assert_equals(err, "1 errors occurred\nIn the datapoint test Error Occurred: test_error\n")
    err = str(ApptuitSendException(
        "test", 401, 0, 1, "test error"
    ))
    assert_equals(err, "Status Code: 401; Failed to send 1 datapoints; Error Occured: test error\n")

@patch('apptuit.apptuit_client.requests.post')
def test_apptuit_send_exception_400(mock_post):
    """
    Test for the case when there is an error from the backend for send
    """
    mock_post.return_value.status_code = 400
    mock_post.return_value.content = '{"success": 0, "failed": 1, "errors": [{"datapoint": "", "error": "test_error"}] }'
    token = "asdashdsauh_8aeraerf"
    client = Apptuit(token)
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
    client = Apptuit(token)
    dp = DataPoint(metric="test", tags={"tk": "tv"}, timestamp=123, value=123)
    dps = [dp]
    with assert_raises(ApptuitSendException):
        client.send(dps)

def test_timeseries_payload():
    """
    Test payload from timeseries list
    """
    token = "asdashdsauh_8aeraerf"
    client = Apptuit(token)
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
        {"metric": metric1_name, "tags": tags1, "timestamp": timestamp, "value":  val1},
        {"metric": metrics2_name, "tags": tags2, "timestamp": timestamp, "value": val2}]
    assert_equals(expected_payload, payload)

def test_timeseries_payload_negative():
    """
    Negative tests for payload creation from timeseries list
    """
    token = "asdashdsauh_8aeraerf"
    client = Apptuit(token)
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
    client = Apptuit(token, global_tags=global_tags)
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
        {"metric": metric1_name, "tags": global_tags, "timestamp": timestamp, "value":  val1},
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
    client = Apptuit(token)
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
        {"metric": metric1_name, "tags": {"gtagk1": "gtagv1"}, "timestamp": timestamp, "value":  val1},
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
    client = Apptuit(token)
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
    client = Apptuit(token)
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
        DataPoint("metric1", None, timestamp, value=None)

def test_datapoint_repr():
    """
    Test __repr__ of DataPoint
    """
    timestamp = int(time.time())
    point = DataPoint('metric1', {"tagk1": "tagv1", "tagk2": "tagv2"}, timestamp, 3.14)
    expected_repr = 'metric1{tagk1:tagv1, tagk2:tagv2, timestamp: %d, value: %f}' % (timestamp, 3.14)
    assert_equals(repr(point), expected_repr)
    assert_equals(str(point), expected_repr)
