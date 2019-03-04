# coding=utf-8

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

"""
Test for functions defined in the utils module
"""
from nose.tools import assert_true, assert_false, assert_raises, \
    assert_equals

from apptuit.utils import strtobool, sanitize_name_apptuit, \
    sanitize_name_prometheus, _contains_valid_chars


def test_strtobool():
    """
    Test strtobool
    """
    true_values = ('y', 'yes', 't', 'true', 'on', '1')
    false_values = ('n', 'no', 'f', 'false', 'off', '0')
    other_values = ('truee', 'ffalse', 'nno', '01')
    for val in true_values:
        assert_true(strtobool(val))
    for val in false_values:
        assert_false(strtobool(val))
    for val in other_values:
        with assert_raises(ValueError):
            strtobool(val)


def test_sanitize_apptuit():
    """
    Test that sanitize name for apptuit works
    """
    test_names = {
        "metric_name tag-key.str": "metric_name_tag-key.str",
        u"&*)": "_",
        "": "",
        "abc.abc-abc/abc_abc": "abc.abc-abc/abc_abc",
        " ": "_",
        u'日本語.abc': u'日本語.abc',
        u'abc.日本語': u"abc.日本語"

    }
    for test_name, expected_name in test_names.items():
        result = sanitize_name_apptuit(test_name)
        assert_equals(result, expected_name, "Validation failed for," + test_name)


def test_sanitize_prometheus():
    """
    Test that sanitize name for prometheus works
    """
    test_names = {
        "metric_name tag-key.str": "metric_name_tag_key_str",
        u"&*)": "_",
        "abc.abc-abc/abc_abc": "abc_abc_abc_abc_abc",
        " ": "_",
        u'日本語.abc': "_abc",
        u'abc.日本語': "abc_"
    }
    for test_name, expected_name in test_names.items():
        result = sanitize_name_prometheus(test_name)
        assert_equals(result, expected_name, "Validation failed for,'" + test_name+"'")


def test_contains_valid_chars():
    """
    Test that _contains_valid_chars works
    """
    test_names = {
        "metric_name tag-key.str": False,
        u"&*)": False,
        "abc.abc-abc/abc_abc": True,
        " ": False,
        u'日本語.abc': True,
        u'abc.日本語': True
    }
    for test_string, expected_name in test_names.items():
        result = _contains_valid_chars(test_string)
        assert_equals(result, expected_name, "Validation failed for,'" + test_string+"'")

