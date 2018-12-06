import json
import time
from nose.tools import assert_raises, assert_equals, assert_greater_equal
from apptuit.pyformance.apptuit_reporter import ApptuitReporter
from pyformance import MetricsRegistry
import random

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


@patch('apptuit.apptuit_client.requests.post')
def test_send_negative(mock_post):
    """
        Test negative responce
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
    reporter.start()
    cput = registry.histogram("cpu")
    count = 0
    while True:
        cput.add(random.randint(1, 100))
        count = count + 1
        if count > 10000:
            break


@patch('apptuit.apptuit_client.requests.post')
def test_reporter_thread_active(mock_post):
    """
        Test that reporter thread is active
    """
    mock_post.return_value.status_code = 503
    mock_post.side_effect = ValueError("Test Error")
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
        Test that acts on invalid metric name
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
        Test that acts on invalid tag names
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
        Test that acts on invalid registry
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
    with assert_raises(ValueError) as ex:
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
            Test that zero tags raise error
    """
    token = "asdashdsauh_8aeraerf"
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.")
    counter_test = registry.counter('counter')
    counter_test.inc(2)
    with assert_raises(ValueError) as ex:
        reporter.report_now()


def test_encode_tags():
    """
            Test encoding tags
    """
    token = "asdashdsauh_8aeraerf"
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.")
    counter_test = registry.counter('counter')
    counter_test.inc(2)
    with assert_raises(ValueError) as ex:
        reporter.encode_metric_name("cpu", None)
    with assert_raises(ValueError) as ex:
        reporter.encode_metric_name(None, {1: 2})
    with assert_raises(ValueError) as ex:
        reporter.encode_metric_name("", None)
    tags = {"tk1": "tv1", "tk2": "tv2"}
    name = "test"
    assert_equals('test{"tk1": "tv1", "tk2": "tv2"}', reporter.encode_metric_name(name, tags))

@patch('apptuit.apptuit_client.requests.post')
def test_decode_tags(mock_post):
    """
            Test decoding tags
    """
    mock_post.return_value.status_code = 204
    token = "asdashdsauh_8aeraerf"
    registry = MetricsRegistry()
    reporter = ApptuitReporter(registry=registry,
                               reporting_interval=1,
                               token=token,
                               prefix="apr.")
    counter_test = registry.counter('counter{"tk1": "tv1", "tk2": "tv2"}')
    counter_test.inc(2)
    with assert_raises(ValueError) as ex:
        reporter.decode_metric_name("cpu {sjd")
    with assert_raises(ValueError) as ex:
        reporter.decode_metric_name(None)
    assert_equals(("test", {"tk1": "tv1", "tk2": "tv2"}), reporter.decode_metric_name('test {"tk1":"tv1","tk2":"tv2"}'))
    reporter.report_now()
    assert_equals(("apr.counter.count", {"tk1": "tv1", "tk2": "tv2"}), reporter.decode_metric_name('apr.counter.count{"tk1":"tv1","tk2":"tv2"}'))


def test_no_token():
    """
            Test that no token raises error
    """
    registry = MetricsRegistry()
    with assert_raises(ValueError) as ex:
        ApptuitReporter(registry=registry,
                        reporting_interval=1,
                        prefix="apr.")


def test_collect_data_points():
    """
                Test that Collect Data Points is valid
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
    assert_equals(dps[0].tags, {'host': 'localhost', 'region': 'us-east-1', 'service': 'web-server', 'tk1': 'tv1',
                                'tk2': 'tv2'})
