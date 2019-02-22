"""
Tests for token and global tags environment variables
"""

import math
import time
import os
import socket
import warnings
from nose.tools import assert_equals, assert_raises
from pyformance import MetricsRegistry

from apptuit import apptuit_client, Apptuit, DataPoint, APPTUIT_PY_TOKEN, APPTUIT_PY_TAGS, \
                    DEPRECATED_APPTUIT_PY_TAGS, DEPRECATED_APPTUIT_PY_TOKEN
from apptuit.pyformance import ApptuitReporter
from apptuit.pyformance.apptuit_reporter import DISABLE_HOST_TAG

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

def test_token_positive():
    """
        Test various combinations of token argument to apptuit, as parameter and as env variable
    """
    test_cases = [
        ("environ_token", "", "environ_token"),
        ("environ_token", None, "environ_token"),
        ("environ_token", "argument_token", "argument_token")
    ]
    for env_token, arg_token, expected in test_cases:
        mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: env_token})
        mock_environ.start()
        client = Apptuit(token=arg_token)
        assert_equals(client.token, expected)
        mock_environ.stop()

def test_tags_env_variable_parsing_negative():
    """
        Test that we fail when the value of global tags env variable is in an invalid format
    """
    test_cases = [
        '"tagk1": tagv1',
        ":a,",
        'tagk1: tagv11: tagv12',
        'tag',
        '  tagk1 : 22,error,tagk2  : tagv2  ',
        '  tagk1 : 22,tagk1:tagv11:tagv12,tagk2  : tagv2  '
    ]
    for env_tags_value in test_cases:
        mock_environ = patch.dict(os.environ, {APPTUIT_PY_TAGS: env_tags_value})
        mock_environ.start()
        with assert_raises(ValueError):
            apptuit_client._get_tags_from_environment()
        mock_environ.stop()

def test_tags_env_variable_parsing_positive():
    """
        Test that we are able to parse the global tags from environment variable
    """
    host = socket.gethostname()
    token = "test_token"
    test_cases = [
        (" ", {"host": host}),
        ("tagk1: 22, tagk2: tagv2", {"tagk1": "22", "tagk2": "tagv2", "host": host}),
        ("tagk1: 22, , tagk2: tagv2", {"tagk1": "22", "tagk2": "tagv2", "host": host}),
        ("  tagk1 : 22,,tagk2  : tagv2  ", {"tagk1": "22", "tagk2": "tagv2", "host": host}),
        (",tagk1: 22, tagk2: tagv2,", {"tagk1": "22", "tagk2": "tagv2", "host": host}),
        (", , , , tagk1: 22, tagk2: tagv2, , ,  , ,", {"tagk1": "22", "tagk2": "tagv2",
                                                       "host": host}),
        ("tagk1: tagv1, tagk2: tagv2, host: myhost", {"tagk1": "tagv1", "tagk2": "tagv2",
                                                      "host": "myhost"})
    ]
    for env_tags_value, expected_global_tags in test_cases:
        mock_environ = patch.dict(os.environ, {APPTUIT_PY_TAGS: env_tags_value})
        mock_environ.start()
        reporter = ApptuitReporter(token=token)
        assert_equals(reporter.tags, expected_global_tags)
        mock_environ.stop()

def test_env_tags_with_host_tag_disabled_env():
    """
    Test global tags from environment when host tag is disabled through
    the APPTUIT_DISABLE_HOST_TAG variable
    """
    token = "test_token"
    disable_host_tag_true_values = ["True", "true"]
    disable_host_tag_other_values = ["False", "false"]
    test_cases = [
        (" ", None),
        ("tagk1: 22, tagk2: tagv2", {"tagk1": "22", "tagk2": "tagv2"}),
        ("tagk1: 22, , tagk2: tagv2", {"tagk1": "22", "tagk2": "tagv2"}),
        ("  tagk1 : 22,,tagk2  : tagv2  ", {"tagk1": "22", "tagk2": "tagv2"}),
        (",tagk1: 22, tagk2: tagv2,", {"tagk1": "22", "tagk2": "tagv2"}),
        (", , , , tagk1: 22, tagk2: tagv2, , ,  , ,", {"tagk1": "22", "tagk2": "tagv2"}),
        ("tagk1: tagv1, tagk2: tagv2, host: myhost", {"tagk1": "tagv1", "tagk2": "tagv2",
                                                      "host": "myhost"})
    ]
    for env_tags_value, expected_global_tags in test_cases:
        for disable_value in disable_host_tag_true_values:
            mock_environ = patch.dict(os.environ, {APPTUIT_PY_TAGS: env_tags_value,
                                                   DISABLE_HOST_TAG: disable_value})
            mock_environ.start()
            reporter = ApptuitReporter(token=token)
            assert_equals(reporter.tags, expected_global_tags)
            mock_environ.stop()
        for disable_value in disable_host_tag_other_values:
            mock_environ = patch.dict(os.environ, {APPTUIT_PY_TAGS: env_tags_value,
                                                   DISABLE_HOST_TAG: disable_value})
            expected_global_tags = expected_global_tags.copy() if expected_global_tags else {}
            if "host" not in expected_global_tags:
                expected_global_tags["host"] = socket.gethostname()
            mock_environ.start()
            reporter = ApptuitReporter(token=token)
            assert_equals(reporter.tags, expected_global_tags)
            mock_environ.stop()

def test_env_tags_with_host_tag_disabled_param():
    """
    Test global tags from environment when host tag is disabled through
    the disable_host_tag parameter to the reporter
    """
    token = "test_token"
    disable_host_tag_values = [True, False, None]
    test_cases = [
        (" ", None),
        ("tagk1: 22, tagk2: tagv2", {"tagk1": "22", "tagk2": "tagv2"}),
        ("tagk1: 22, , tagk2: tagv2", {"tagk1": "22", "tagk2": "tagv2"}),
        ("  tagk1 : 22,,tagk2  : tagv2  ", {"tagk1": "22", "tagk2": "tagv2"}),
        (",tagk1: 22, tagk2: tagv2,", {"tagk1": "22", "tagk2": "tagv2"}),
        (", , , , tagk1: 22, tagk2: tagv2, , ,  , ,", {"tagk1": "22", "tagk2": "tagv2"}),
        ("tagk1: tagv1, tagk2: tagv2, host: myhost", {"tagk1": "tagv1", "tagk2": "tagv2",
                                                      "host": "myhost"})
    ]
    for env_tags_value, expected_global_tags in test_cases:
        for disable_value in disable_host_tag_values:
            mock_environ = patch.dict(os.environ, {APPTUIT_PY_TAGS: env_tags_value})
            mock_environ.start()
            reporter = ApptuitReporter(token=token, disable_host_tag=disable_value)
            if disable_value is None or disable_value is False:
                if expected_global_tags:
                    if "host" not in expected_global_tags:
                        expected_global_tags["host"] = socket.gethostname()
                else:
                    expected_global_tags = {"host": socket.gethostname()}
            assert_equals(reporter.tags, expected_global_tags)
            mock_environ.stop()


def test_token_negative():
    """
        Test that if no token parameter is passed and no env variable is set, we get an error
    """
    mock_environ = patch.dict(os.environ, {})
    mock_environ.start()
    with assert_raises(ValueError):
        Apptuit()
    with assert_raises(ValueError):
        Apptuit(token="")
    with assert_raises(ValueError):
        Apptuit(token=None)
    mock_environ.stop()

def test_env_global_tags_positive():
    """
        Test that the client works with global tags env variable and without them
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'tagk1: 22, tagk2: tagv2'})
    mock_environ.start()
    client = Apptuit()
    assert_equals(client._global_tags, {"tagk1": "22", "tagk2": "tagv2"})
    mock_environ.stop()

    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token"})
    mock_environ.start()
    client1 = Apptuit()
    assert_equals({}, client1._global_tags)
    mock_environ.stop()

def test_env_global_tags_negative():
    """
        Negative test cases for global tags env variable
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: "{InvalidTags"})
    mock_environ.start()
    with assert_raises(ValueError):
        Apptuit()
    mock_environ.stop()
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: '"tagk1":"tagv1"'})
    mock_environ.start()
    with assert_raises(ValueError):
        Apptuit()
    mock_environ.stop()

def test_datapoint_tags_and_envtags():
    """
        Test that datapoint tags take priority when global tags env variable is present
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'host: host1, ip: 1.1.1.1'})
    mock_environ.start()
    client = Apptuit()
    timestamp = int(time.time())
    test_val = math.pi
    dp1 = DataPoint(metric="test_metric", tags={"host": "host2", "ip": "2.2.2.2", "test": 1},
                    timestamp=timestamp, value=test_val)
    dp2 = DataPoint(metric="test_metric", tags={"test": 2}, timestamp=timestamp, value=test_val)
    dp3 = DataPoint(metric="test_metric", tags={}, timestamp=timestamp, value=test_val)
    dp4 = DataPoint(metric="test_metric", tags=None, timestamp=timestamp, value=test_val)
    payload = client._create_payload_from_datapoints([dp1, dp2, dp3, dp4])
    assert_equals(len(payload), 4)
    assert_equals(payload[0]["tags"], {"host": "host2", "ip": "2.2.2.2", "test": 1})
    assert_equals(payload[1]["tags"], {"host": "host1", "ip": "1.1.1.1", "test": 2})
    assert_equals(payload[2]["tags"], {"host": "host1", "ip": "1.1.1.1"})
    assert_equals(payload[3]["tags"], {"host": "host1", "ip": "1.1.1.1"})
    assert_equals(client._global_tags, {"host": "host1", "ip": "1.1.1.1"})
    mock_environ.stop()

def test_no_environ_tags():
    """
        Test tags work even if no global tags present as env variable
    """

    timestamp = int(time.time())
    test_val = math.pi
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token"})
    mock_environ.start()
    client = Apptuit()
    dp1 = DataPoint(metric="test_metric", tags={"host": "host2", "ip": "2.2.2.2", "test": 1},
                    timestamp=timestamp, value=test_val)
    dp2 = DataPoint(metric="test_metric", tags={"test": 2}, timestamp=timestamp, value=test_val)
    payload = client._create_payload_from_datapoints([dp1, dp2])
    assert_equals(len(payload), 2)
    assert_equals(payload[0]["tags"], {"host": "host2", "ip": "2.2.2.2", "test": 1})
    assert_equals(payload[1]["tags"], {"test": 2})

    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry, tags={"host": "reporter", "ip": "2.2.2.2"})
    counter = registry.counter("counter")
    counter.inc(1)
    payload = reporter.client._create_payload_from_datapoints(reporter._collect_data_points(reporter.registry))
    assert_equals(len(payload), 1)
    assert_equals(payload[0]["tags"], {'host': 'reporter', 'ip': '2.2.2.2'})
    mock_environ.stop()

def test_reporter_tags_with_global_env_tags():
    """
        Test that reporter tags take priority
        TODO:
        We have 8 possible combinations -
            1. global env tags: true, reporter tags: true, metric tags: true
            2. global env tags: true, reporter tags: true, metric tags: false
            3. global env tags: true, reporter tags: false, metric tags: true
            4. global env tags: true, reporter tags: false, metric tags: false
            5. global env tags: false, reporter tags: true, metric tags: true
            6. global env tags: false, reporter tags: true, metric tags: false
            7. global env tags: false, reporter tags: false, metric tags: true
            8. global env tags: false, reporter tags: false, metric tags: false
    """


    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'host: environ, ip: 1.1.1.1'})
    mock_environ.start()
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry, tags={"host": "reporter", "ip": "2.2.2.2"})
    counter = registry.counter("counter")
    counter.inc(1)
    payload = reporter.client._create_payload_from_datapoints(reporter._collect_data_points(reporter.registry))
    assert_equals(len(payload), 1)
    assert_equals(payload[0]["tags"], {'host': 'reporter', 'ip': '2.2.2.2'})
    reporter = ApptuitReporter(registry=registry)
    counter = registry.counter("counter")
    counter.inc(1)
    payload = reporter.client._create_payload_from_datapoints(reporter._collect_data_points(reporter.registry))
    assert_equals(len(payload), 1)
    assert_equals(payload[0]["tags"], {"host": "environ", "ip": "1.1.1.1"})
    mock_environ.stop()

def test_tags_of_metric_take_priority():
    """
        Test that metric tags take priority
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'host: environ, ip: 1.1.1.1'})
    mock_environ.start()
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry, tags={"host": "reporter", "ip": "2.2.2.2"})
    counter = registry.counter('counter {"host": "metric", "ip": "3.3.3.3"}')
    counter.inc(1)

    payload = reporter.client._create_payload_from_datapoints(reporter._collect_data_points(reporter.registry))
    assert_equals(len(payload), 1)
    assert_equals(payload[0]["tags"], {"host": "metric", "ip": "3.3.3.3"})
    mock_environ.stop()

def test_deprecated_tags_variable():
    """
    Test that reporter and client work with the deprecated tags env variable
    """
    warnings.filterwarnings('error')
    with patch.dict(os.environ, {DEPRECATED_APPTUIT_PY_TAGS: 'host: environ, ip: 127.0.0.1'}):
        registry = MetricsRegistry()
        with assert_raises(DeprecationWarning):
            reporter = ApptuitReporter(token="test_token", registry=registry,
                                       tags={'host': 'reporter'})
    warnings.resetwarnings()

def test_deprecated_token_variable():
    """
    Test that reporter and client work with the deprecated token env variable
    """
    warnings.filterwarnings('error')
    with patch.dict(os.environ, {DEPRECATED_APPTUIT_PY_TOKEN: "test_token"}):
        registry = MetricsRegistry()
        with assert_raises(DeprecationWarning):
            reporter = ApptuitReporter(registry=registry,
                                       tags={'host': 'reporter'})
    warnings.resetwarnings()
