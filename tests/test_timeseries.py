import time

from nose.tools import assert_raises, assert_equals

from apptuit import timeseries, TimeSeriesName, TimeSeries


def test_encode_tags():
    """
        Test encoding tags
    """
    with assert_raises(ValueError):
        timeseries.encode_metric("cpu", None)
    with assert_raises(ValueError) as ex:
        timeseries.encode_metric(None, {1: 2})
    with assert_raises(ValueError) as ex:
        timeseries.encode_metric("", None)
    tags = {"tk1": "tv1", "tk2": "tv2"}
    name = "test"
    assert_equals('test{"tk1": "tv1", "tk2": "tv2"}', timeseries.encode_metric(name, tags))


def test_decode_tags():
    """
        Test decoding tags
    """
    with assert_raises(ValueError):
        timeseries.decode_metric("cpu {sjd")
    with assert_raises(ValueError):
        timeseries.decode_metric(None)
    assert_equals(("test", {"tk1": "tv1", "tk2": "tv2"}),
                  timeseries.decode_metric('test {"tk1":"tv1","tk2":"tv2"}'))
    assert_equals(("apr.counter.count", {"tk1": "tv1", "tk2": "tv2"}),
                  timeseries.decode_metric('apr.counter.count{"tk1":"tv1","tk2":"tv2"}'))


def test_encode_tags2():
    """
        Test encoding tags with TimeSeries
    """
    with assert_raises(ValueError):
        TimeSeriesName.encode_metric("cpu", None)
    with assert_raises(ValueError) as ex:
        TimeSeriesName.encode_metric(None, {1: 2})
    with assert_raises(ValueError) as ex:
        TimeSeriesName.encode_metric("", None)
    tags = {"tk1": "tv1", "tk2": "tv2"}
    name = "test"
    assert_equals('test{"tk1": "tv1", "tk2": "tv2"}', TimeSeriesName.encode_metric(name, tags))


def test_decode_tags2():
    """
        Test decoding tags with TimeSeries
    """
    with assert_raises(ValueError):
        TimeSeriesName.decode_metric("cpu {sjd")
    with assert_raises(ValueError):
        TimeSeriesName.decode_metric(None)
    assert_equals(("test", {"tk1": "tv1", "tk2": "tv2"}),
                  TimeSeriesName.decode_metric('test {"tk1":"tv1","tk2":"tv2"}'))
    assert_equals(("apr.counter.count", {"tk1": "tv1", "tk2": "tv2"}),
                  TimeSeriesName.decode_metric('apr.counter.count{"tk1":"tv1","tk2":"tv2"}'))


def test_timeseries_length():
    """
    Test __len__ for TimeSeries
    """
    series = TimeSeries("metric1", {"tagk1": "tagv1"})
    for _ in range(10):
        series.add_point(int(time.time()), 3.14)
    assert_equals(len(series), 10)


def test_timeseriesname_str():
    """
    Test __str__ for TimeSeriesName
    """
    series_name = TimeSeriesName("metric1", {"tagk1": "tagv1", "tagk2": "tagv2"})
    expected_str = 'metric1{"tagk1": "tagv1", "tagk2": "tagv2"}'
    assert_equals(str(series_name), expected_str)


def test_empty_metric_name_tag_key_raise_error():
    """
    Test that empty tag-keys or metric names will raise errors
    """
    with assert_raises(ValueError):
        TimeSeriesName("metric1", {"": "tagv1", "tagk2": "tagv2"})
    with assert_raises(ValueError):
        TimeSeriesName("", {"tagk1": "tagv1", "tagk2": "tagv2"})
