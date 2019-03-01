"""
utilises for apptuit
"""
import os
import re
import warnings
from string import ascii_letters, digits

from apptuit import APPTUIT_PY_TAGS, DEPRECATED_APPTUIT_PY_TAGS

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

VALID_REGEX = re.compile(r"[-\w_/.]+$", re.U)
PROMETHEUS_VALID_CHARSET = set(ascii_letters + digits + "_")
APPTUIT_SANITIZE_REGEX = re.compile(r'([^-\w_./])', re.U)
REPLACE_WITH_SINGLE_UNDERSCORE_REGEX = re.compile('_+')


@lru_cache(maxsize=2048)
def sanitize_name_prometheus(name):
    """
    To make the metric name Prometheus compatible.
    :param name: a string value metric name or tag-key.
    :return: metric_name which is Prometheus compatible.
    """
    if name[0] in digits:
        name = "_" + name
    invalid_char_set = set(name).difference(PROMETHEUS_VALID_CHARSET)
    for invalid_char in invalid_char_set:
        if invalid_char in name:
            name = name.replace(invalid_char, "_")
    # to replace multiple '_' to one
    return REPLACE_WITH_SINGLE_UNDERSCORE_REGEX.sub("_", name)


@lru_cache(maxsize=2048)
def sanitize_name_apptuit(name):
    """
    To make the metric name Apptuit compatible.
    :param name: a string value metric name or tag-key.
    :return: metric_name which is Apptuit compatible.
    """
    substitute_string = APPTUIT_SANITIZE_REGEX.sub("_", name)
    # to replace multiple '_' to one
    return REPLACE_WITH_SINGLE_UNDERSCORE_REGEX.sub("_", substitute_string)


@lru_cache(maxsize=4096)
def _contains_valid_chars(string):
    return VALID_REGEX.match(string) is not None


def _validate_tags(tags):
    for tagk in tags.keys():
        if not tagk or not _contains_valid_chars(tagk):
            raise ValueError("Tag key %s contains an invalid character, "
                             "allowed characters are a-z, A-Z, 0-9, -, _, ., and /" % tagk)


def _get_tags_from_environment():
    tags_str = os.environ.get(APPTUIT_PY_TAGS)
    if not tags_str:
        tags_str = os.environ.get(DEPRECATED_APPTUIT_PY_TAGS)
        if tags_str:
            warnings.warn("The environment variable %s is deprecated, please use %s instead"
                          % (DEPRECATED_APPTUIT_PY_TAGS, APPTUIT_PY_TAGS), DeprecationWarning)
    if not tags_str:
        return {}
    tags = {}
    tags_str = tags_str.strip(", ")
    tags_split = tags_str.split(',')
    for tag in tags_split:
        tag = tag.strip()
        if not tag:
            continue
        try:
            key, val = tag.split(":")
            tags[key.strip()] = val.strip()
        except ValueError:
            raise ValueError("Invalid format for " + APPTUIT_PY_TAGS +
                             ", failed to parse tag key-value pair '" + tag + "', " +
                             APPTUIT_PY_TAGS + " should be in the format - "
                                               "'tag_key1:tag_val1,tag_key2:tag_val2"
                                               ",...,tag_keyN:tag_valN'")
    _validate_tags(tags)
    return tags


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
