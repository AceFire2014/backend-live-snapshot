from collections import namedtuple
from enum import Enum


class ChatTypeEnum(Enum):
    FREE = '1'
    TIPPING = '6'
    ELSE = '9'

    def __json__(self):
        return f'"{self.value}"'

    @classmethod
    def _missing_(cls, value):
        return ChatTypeEnum.ELSE


class StreamSession(namedtuple('StreamingEngineSession',
                               'stream_name, subdomain, chat_type')):
    __slots__ = ()

    @staticmethod
    def from_dict(d: dict) -> 'StreamSession':
        return StreamSession(
            stream_name=d['stream_name'],
            subdomain=d['subdomain'],
            chat_type=ChatTypeEnum(d['online'])
        )


class StreamSessions(namedtuple('StreamingEngineSessions', 'won_stream_names')):
    __slots__ = ()

    @staticmethod
    def from_dict(d: dict) -> 'StreamSessions':
        return StreamSessions(
            won_stream_names=list(d)
        )
