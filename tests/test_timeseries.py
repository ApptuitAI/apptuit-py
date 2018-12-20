from nose.tools import assert_raises, assert_equals
from apptuit import timeseries

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
