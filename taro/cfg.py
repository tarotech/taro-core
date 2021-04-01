"""
Global configuration
Implementation of config pattern:
https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
"""

from enum import Enum


class PersistenceType(Enum):
    SQL_LITE = 1


DEF_LOG_ENABLED = False
DEF_LOG_STDOUT_LEVEL = 'off'
DEF_LOG_FILE_LEVEL = 'off'
DEF_LOG_FILE_PATH = None

DEF_PERSISTENCE_ENABLED = False
DEF_PERSISTENCE_TYPE = PersistenceType.SQL_LITE
DEF_PERSISTENCE_DATABASE = ''

DEF_PLUGINS = ()

log_enabled = DEF_LOG_ENABLED
log_stdout_level = DEF_LOG_STDOUT_LEVEL
log_file_level = DEF_LOG_FILE_LEVEL
log_file_path = DEF_LOG_FILE_PATH

persistence_enabled = DEF_PERSISTENCE_ENABLED
persistence_type = DEF_PERSISTENCE_TYPE
persistence_database = DEF_PERSISTENCE_DATABASE

plugins = DEF_PLUGINS
