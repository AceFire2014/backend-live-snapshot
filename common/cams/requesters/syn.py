import logging
from typing import Any, Callable, Optional

import requests

from .common import CamsAPIRequester, maybe_json

log = logging.getLogger(__name__)


class CamsAPISyncRequester(CamsAPIRequester):
    """
    Sync version of requester
    """

    def get(self, uri: str, *, cb: Callable, query: Optional[dict] = None, raw: bool = False,
            error_log_level: int = logging.ERROR, skip_not_found_logging: bool = False, **kwargs) -> Any:
        debug_data = {}
        try:
            debug_data['request'] = {
                'url': f'{self.url}/{uri}',
                'query': dict(query) if query is not None else None,
            }

            result = requests.get(f'{self.url}/{uri}', params=query)
            response = result.content if raw else result.text

            debug_data['response'] = {
                'status': f'{result.status_code} {result.reason}',
                'value': maybe_json(response),
                'headers': dict(result.headers),
            }

        finally:
            log.debug(f'GET request to {self.url}/{uri}.', extra={'data': debug_data})

        if result.status_code == 404 and skip_not_found_logging:
            result.raise_for_status()

        try:
            result.raise_for_status()
            return cb(response, **kwargs)
        except Exception as e:
            log.log(error_log_level, f'Failed GET request to {self.url}/{uri}.', extra={'data': debug_data}, exc_info=e)
            raise

    def post(self, uri: str, *, cb: Callable, json: Optional[dict] = None, raw: bool = False,
             error_log_level: int = logging.ERROR, **kwargs) -> Any:
        debug_data = {}
        try:
            debug_data['request'] = {
                'url': f'{self.url}/{uri}',
                'query': dict(json) if json is not None else None,
            }

            result = requests.post(f'{self.url}/{uri}', json=json)
            response = result.content if raw else result.text

            debug_data['response'] = {
                'status': f'{result.status_code} {result.reason}',
                'value': maybe_json(response),
                'headers': dict(result.headers),
            }

        finally:
            log.debug(f'POST request to {self.url}/{uri}.', extra={'data': debug_data})

        try:
            result.raise_for_status()
            return cb(response, **kwargs)
        except Exception as e:
            log.log(error_log_level, f'Failed POST request to {self.url}/{uri}.',
                    extra={'data': debug_data}, exc_info=e)
            raise

    def delete(self, uri: str, *, cb: Callable, error_log_level: int = logging.ERROR, **kwargs) -> Any:
        debug_data = {}
        try:
            debug_data['request'] = {'url': f'{self.url}/{uri}'}

            result = requests.delete(f'{self.url}/{uri}')
            response = result.text

            debug_data['response'] = {
                'status': f'{result.status_code} {result.reason}',
                'value': maybe_json(response),
                'headers': dict(result.headers),
            }

        finally:
            log.debug(f'DELETE request to {self.url}/{uri}.', extra={'data': debug_data})

        try:
            result.raise_for_status()
            return cb(response, **kwargs)
        except Exception as e:
            log.log(error_log_level, f'Failed DELETE request to {self.url}/{uri}.',
                    extra={'data': debug_data}, exc_info=e)
            raise
