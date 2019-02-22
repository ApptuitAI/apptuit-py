"""
Test for functions defined in the utils module
"""

from nose.tools import assert_true, assert_false, assert_raises
from apptuit.utils import strtobool

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
