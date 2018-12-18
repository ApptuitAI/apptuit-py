"""
    Tests for apptuit pyformance reporter
"""
import os
import random
import time
from nose.tools import assert_raises, assert_equals, assert_greater_equal, assert_true
from requests.exceptions import HTTPError
from apptuit import ApptuitException, APPTUIT_PY_TOKEN, APPTUIT_PY_TAGS
from apptuit.pyformance.apptuit_reporter import ApptuitReporter
from pyformance import MetricsRegistry

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

@patch('apptuit.apptuit_client.requests.post')
def test_send_negative(mock_post):
    """
        Test negative responce from Apptuit backend
    """
    mock_post.return_value.status_code = 503
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    cput = registry.histogram("cpu")
    count = 0
    while True:
        cput.add(random.randint(1, 100))
        count = count + 1
        if count > 10000:
            break
    with assert_raises(ApptuitException):
        reporter.report_now()

@patch('apptuit.apptuit_client.requests.post')
def test_reporter_thread_active(mock_post):
    """
        Test that reporter thread is active even if we are not able to send data
    """
    mock_post.return_value.status_code = 503
    mock_post.side_effect = HTTPError()
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    reporter.start()
    cput = registry.histogram("cpu")
    cput.add(random.randint(1, 100))
    time.sleep(3)
    assert_greater_equal(mock_post.call_count, 2)

def test_invalid_metric_name():
    """
        Test for invalid metric name when reporting data
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr\\",
                               tags=tags)
    reporter.start()
    cpu = registry.histogram("cpu")
    for i in range(1, 10):
        cpu.add(random.randint(i, 100))
    with assert_raises(ValueError) as ex:
        reporter._collect_data_points(reporter.registry, None)

def test_invalid_tag():
    """
        Test for invalid tag key when reporting data
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"h\\ost": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    reporter.start()
    cpu = registry.histogram("cpu")
    for i in range(1, 10):
        cpu.add(random.randint(i, 100))
    with assert_raises(ValueError) as ex:
        reporter._collect_data_points(reporter.registry, None)

def test_invalid_registry():
    """
        Test for invalid registry object when reporting data
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = None
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    with assert_raises(AttributeError) as ex:
        reporter._collect_data_points(None, None)

@patch('apptuit.apptuit_client.requests.post')
def test_tags_with_key(mock_post):
    """
        Test that additions tags work
    """
    mock_post.return_value.status_code = 204
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    cpu = registry.histogram('cpu {"tagk1":22,"tagk2":"tagv2"}')
    for i in range(1, 10):
        cpu.add(random.randint(i, 100))
    reporter.report_now()

@patch('apptuit.apptuit_client.requests.post')
def test_tags_with_key_invalid(mock_post):
    """
            Test that invalid tags raise error
    """
    mock_post.return_value.status_code = 204
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    cpu = registry.histogram('cpu {"tagk1":1,"tagk2":"tagv2"')
    for i in range(1, 10):
        cpu.add(random.randint(i, 100))
    with assert_raises(ValueError):
        reporter.report_now()

def test_calling_report_now():
    """
        Test that report now is being called
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    counter_test = registry.counter("counter")
    counter_test.inc(2)
    with patch('apptuit.apptuit_client.requests.post') as mock_method:
        mock_method.return_value.status_code = 200
        reporter.report_now()
        assert_equals(mock_method.called, True)

def test_zero_tags():
    """
        Test that using reporter without tags raises error
    """
    token = "asdashdsauh_8aeraerf"
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.")
    counter_test = registry.counter('counter')
    counter_test.inc(2)
    with assert_raises(ValueError):
        reporter.report_now()


def test_no_token():
    """
            Test that no token raises error
    """
    registry = MetricsRegistry()
    with assert_raises(ValueError) as ex:
        ApptuitReporter(registry=registry,
                        reporting_interval=1,
                        prefix="apr.")

def test_reporter_tags():
    """
    Test that reporter tags are working as expected
    """
    mock_environ = patch.dict(os.environ, {APPTUIT_PY_TOKEN: "environ_token",
                                           APPTUIT_PY_TAGS: 'host: environ, ip: 1.1.1.1'})
    mock_environ.start()
    reporter = ApptuitReporter(tags={"host": "reporter", "ip": "2.2.2.2"})
    assert_equals(reporter.tags, {"host": "reporter", "ip": "2.2.2.2"})
    reporter = ApptuitReporter()
    assert_equals(reporter.tags, {"host": "environ", "ip": "1.1.1.1"})
    reporter = ApptuitReporter(tags={"test": "val"})
    assert_equals(reporter.tags, {"host": "environ", "ip": "1.1.1.1", "test":"val"})
    mock_environ.stop()

def test_collect_data_points():
    """
        Test data is being collected correctly
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.",
                               tags=tags)
    counter_test = registry.counter('counter {"tk1":"tv1","tk2":"tv2"}')
    counter_test.inc(2)
    dps = reporter._collect_data_points(reporter.registry)
    assert_equals(len(dps), 1)
    assert_equals(dps[0].value, 2)
    assert_equals(dps[0].metric, "apr.counter.count")
    assert_equals(dps[0].tags, {'host': 'localhost', 'region': 'us-east-1',
                                'service': 'web-server', 'tk1': 'tv1',
                                'tk2': 'tv2'})

def test_globaltags_override():
    """
        Test that if the global tags and metric tags contain same tag key,
        the metric tags override global tags
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"region": "us-east-1"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               tags=tags)
    counter1 = registry.counter('counter1 {"region":"us-west-2","id": 1}')
    counter2 = registry.counter('counter2 {"region":"us-west-3","id": 2, "new_tag": "foo"}')
    counter3 = registry.counter('counter3')
    counter1.inc(2)
    counter2.inc()
    counter3.inc()
    dps = reporter._collect_data_points(reporter.registry)
    dps = sorted(dps, key=lambda x: x.metric)
    assert_equals(dps[0].tags, {"region": "us-west-2", "id": 1})
    assert_equals(dps[1].tags, {"region": "us-west-3", "id": 2, "new_tag": "foo"})
    assert_equals(dps[2].tags, {"region": "us-east-1"})
    assert_equals(reporter.tags, {"region": "us-east-1"})

def test_globaltags_none():
    """
        Test that metric tags work when global tags are not present
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"region": "us-east-1"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               tags=None)
    counter1 = registry.counter('counter1 {"region":"us-west-2","id": 1}')
    counter2 = registry.counter('counter2 {"region":"us-west-3","id": 2, "new_tag": "foo"}')
    counter1.inc(2)
    counter2.inc()
    dps = reporter._collect_data_points(reporter.registry)
    dps = sorted(dps, key=lambda x: x.metric)
    assert_equals(dps[0].tags, {"region": "us-west-2", "id": 1})
    assert_equals(dps[1].tags, {"region": "us-west-3", "id": 2, "new_tag": "foo"})
    assert_true(reporter.tags is None)

def test_valid_prefix():
    """
        Test that prefix works
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"region": "us-east-1"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               prefix="pre-",
                               token=token,
                               tags=tags)
    counter1 = registry.counter('counter1')
    counter1.inc()
    dps = reporter._collect_data_points(reporter.registry)
    assert_equals(dps[0].metric, "pre-counter1.count")

def test_none_prefix():
    """
        Test for None prefix
    """
    token = "asdashdsauh_8aeraerf"
    tags = {"region": "us-east-1"}
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               prefix=None,
                               token=token,
                               tags=tags)
    counter1 = registry.counter('counter1')
    counter1.inc()
    dps = reporter._collect_data_points(reporter.registry)
    assert_equals(dps[0].metric, "counter1.count")
