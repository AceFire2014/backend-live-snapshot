import abc
from typing import Any, Callable, Optional

import ujson


def maybe_json(text: str) -> Any:
    try:
        return ujson.loads(text)
    except Exception:
        return text


class CamsAPIRequester(abc.ABC):
    def __init__(self, url: str) -> None:
        self.url = url

    @abc.abstractmethod
    def get(self, uri: str, *, cb: Callable, query: Optional[dict] = None, raw: bool = False, **kwargs) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    def post(self, uri: str, *, cb: Callable, json: Optional[dict] = None, raw: bool = False, **kwargs) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, uri: str, *, cb: Callable, **kwargs) -> Any:
        raise NotImplementedError
