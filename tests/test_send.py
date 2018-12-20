import os
import random
import time

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from nose.tools import assert_raises, ok_, assert_is_not_none, assert_equals
from apptuit import Apptuit, DataPoint, ApptuitException, APPTUIT_PY_TOKEN, APPTUIT_PY_TAGS, ApptuitSendException


def test_client_object():
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
        dps.append(DataPoint(metric_name, tags, ts, random.random()))
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
        dps.append(DataPoint(metric_name, tags, ts, random.random()))
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
        DataPoint(metric_name, tags, ts, random.random())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, "error", ts, random.random())
    dp = DataPoint(metric_name, None, ts, random.random())
    assert_equals(dp.tags,None)

def test_invalid_chars_in_tag_values():
    """
    Test for invalid character in tag values
    """
    metric_name = "node.load_avg.1m"
    tags = {"host": "local:host", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())

def test_tags_not_dict():
    """
    Test to validate that only dict type values are expected for tags
    """
    metric_name = "node.load_avg.1m"
    tags = ["host", "localhost", "region", "us-east-1", "service", "web-server"]
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())


def test_invalid_metric_name():
    """
    Test for invalid character in metric name
    """
    metric_name = "node.load+avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())

def test_invalid_datapoint_value():
    """
    Test for a non-numeric value for DataPoint
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 'abc'
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, value)

def test_numeric_datapoint_value():
    """
    Test for a numeric DataPoint value
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 3.14
    point = DataPoint(metric_name, tags, ts, value)
    assert_is_not_none(point)

def test_numeric_string_datapoint_value():
    """
    Test for a valid DataPoint value which is a string
    """
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = '3.14'
    point = DataPoint(metric_name, tags, ts, value)
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
    point = DataPoint(metric_name, tags, ts, value)
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
        DataPoint(metric_name, tags, ts, value)

def test_apptuit_send_exception():
    """
    Test that ApptuitSendException str is valid
    """
    err = str(ApptuitSendException(
        1, 1, [{"datapoint": "test", "error": "test_error"}]
    ))
    assert_equals(err, "1 errors occurred\nIn the datapoint test Error Occurred: test_error\n")

