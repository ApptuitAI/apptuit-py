import random
import time
try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from nose.tools import assert_raises, ok_, assert_is_not_none, assert_equals
from apptuit import Apptuit, DataPoint, ApptuitException

@patch('apptuit.apptuit_client.requests.post')
def test_send_positive(mock_post):
    mock_post.return_value.status_code = 204
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
            try:
                client.send(dps)
            except ApptuitException:
                not ok_("ApptuitException should not have been raised")
            dps = []
            points_sent += 100
        if points_sent > 500:
            break
    if len(dps) > 0:
        try:
            client.send(dps)
        except ApptuitException:
            not ok_("ApptuitException should not have been raised")

@patch('apptuit.apptuit_client.requests.post')
def test_send_server_error(mock_post):
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

def test_invalid_chars_in_tag_keys():
    metric_name = "node.load_avg.1m"
    tags = {"ho\\st": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())

def test_invalid_chars_in_tag_values():
    metric_name = "node.load_avg.1m"
    tags = {"host": "local:host", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())

def test_tags_not_dict():
    metric_name = "node.load_avg.1m"
    tags = ["host", "localhost", "region", "us-east-1", "service", "web-server"]
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())


def test_invalid_metric_name():
    metric_name = "node.load+avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, random.random())

def test_invalid_datapoint_value():
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 'abc'
    with assert_raises(ValueError) as ex:
        DataPoint(metric_name, tags, ts, value)

def test_numeric_datapoint_value():
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 3.14
    dp = DataPoint(metric_name, tags, ts, value)
    assert_is_not_none(dp)

def test_numeric_string_datapoint_value():
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = '3.14'
    dp = DataPoint(metric_name, tags, ts, value)
    assert_is_not_none(dp)

def test_datapoint_value_getter():
    metric_name = "node.load.avg.1m"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    ts = int(time.time())
    value = 3.14
    dp = DataPoint(metric_name, tags, ts, value)
    assert_equals(dp.value, value)
