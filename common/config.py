import importlib
import inspect
import logging
import os
import sys
from distutils.util import strtobool
from typing import Any, Optional, Mapping

import ujson

log = logging.getLogger(__name__)


config_path = os.getenv('CONFIG')
log.debug("Config path retrieved from 'CONFIG' variable is %s.", config_path)
assert config_path, 'CONFIG variable switch must not be empty'
config = importlib.import_module(config_path)


def environment_variables_processor(module: Any, env_variables_prefix: Optional[str] = None) -> Any:
    if env_variables_prefix is None:
        env_variables_prefix = config.ENV_CONFIG_VAR_PREFIX

    for k, v in os.environ.items():
        if k.startswith(env_variables_prefix):
            var_name = k.replace(env_variables_prefix, '')
            if hasattr(module, var_name):
                convert = type(getattr(module, var_name, 'default'))
                log.debug("Type converter for '%s' variable is %s.", var_name, convert)
                if convert is bool:
                    convert = strtobool
                elif convert in (list, tuple, dict):
                    convert = ujson.loads
                setattr(module, var_name, convert(v))

    return module


if hasattr(config, 'CONFIG_MODULE'):
    Env = environment_variables_processor
    config_processor = getattr(sys.modules[__name__], config.CONFIG_MODULE)
    log.debug("Config processor retrieved from 'CONFIG_MODULE' variable is %s.", config_processor)
    config = config_processor(config) if config_processor else config


def config_as_dict(config_module):
    return {k: v for k, v in config_module.__dict__.items() if not k.startswith('__')}


def load_class(class_name: str):
    if '.' in class_name:
        *package, class_name = class_name.split('.')
        module = importlib.import_module('.'.join(package))

    else:
        module_name = inspect.stack()[1].frame.f_globals['__name__']
        module = sys.modules[module_name]

    return getattr(module, class_name)


def load_logging_config(config_var_name: str = 'LOG_CONFIG') -> Mapping:
    calling_module_name = inspect.stack()[1].frame.f_globals['__name__']

    log_config_module_name = getattr(config, config_var_name, None)
    assert log_config_module_name, f'{config_var_name} may not be empty'
    log_config_module = importlib.import_module(log_config_module_name, calling_module_name)
    assert getattr(log_config_module, 'LOG_CONFIG', {}), f'{log_config_module_name}.LOG_CONFIG may not be empty'

    return log_config_module.LOG_CONFIG
