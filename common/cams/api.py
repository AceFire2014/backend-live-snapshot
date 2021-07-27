from typing import Union, Coroutine
import ujson
from .requesters import CamsAPIRequester

from .objects import StreamSessions, StreamSession


class CamsAPI:
    def __init__(self, requester: CamsAPIRequester) -> None:
        self.requester = requester

    def get_won(self, **kwargs) -> Union[StreamSessions, Coroutine]:
        return self.requester.get('won',
                                  cb=lambda resp: StreamSessions.from_dict(ujson.loads(resp)))

    def get_stream(self, stream_name: str) -> Union[StreamSession, Coroutine]:
        return self.requester.get(f'models/stream/{stream_name.lower()}',
                                  cb=lambda resp: StreamSession.from_dict(ujson.loads(resp)),
                                  skip_not_found_logging=True)
