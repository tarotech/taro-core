from enum import Enum
from fnmatch import fnmatch
from operator import eq
from typing import Dict

from .containers import *
from .dt import *
from .files import *

TRUE_OPTIONS = ['yes', 'true', 'y', '1', 'on']
FALSE_OPTIONS = ['no', 'false', 'n', '0', 'off']
BOOLEAN_OPTIONS = TRUE_OPTIONS + FALSE_OPTIONS
LOG_LEVELS = ['critical', 'fatal', 'error', 'warn', 'warning', 'info', 'debug', 'off']


def and_(a, b):
    return a and b


def or_(a, b):
    return a or b


def split_params(params, kv_sep="=") -> Dict[str, str]:
    f"""
    Converts sequence of values in format "key{kv_sep}value" to dict[key, value]
    """

    def split(s):
        if len(s) < 3 or kv_sep not in s[1:-1]:
            raise ValueError(f"Parameter must be in format: param{kv_sep}value")
        return s.split(kv_sep)

    return {k: v for k, v in (split(set_opt) for set_opt in params)}


def truncate(text, max_len, truncated_suffix=''):
    text_length = len(text)
    suffix_length = len(truncated_suffix)

    if suffix_length > max_len:
        raise ValueError(f"Truncated suffix length {suffix_length} is larger than max length {max_len}")

    if text_length > max_len:
        return text[:(max_len - suffix_length)] + truncated_suffix

    return text


def partial_match(string, pattern):
    return bool(re.search(pattern, string))


class MatchingStrategy(Enum):
    """
    Define functions for string match testing where the first parameter is the tested string and the second parameter
    is the pattern.
    """
    EXACT = (eq,)
    FN_MATCH = (fnmatch,)
    PARTIAL = (partial_match,)

    def __call__(self, *args, **kwargs):
        return self.value[0](*args, **kwargs)