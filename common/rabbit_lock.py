import asyncio
import logging
import sys
from contextlib import wraps
from typing import Callable

import aio_pika
import aiormq
import async_timeout

from common.background_tasks import BackgroundTasks
from common.config import config

if sys.version_info[:2] > (3, 6):
    from contextlib import AsyncExitStack
else:
    from async_exit_stack import AsyncExitStack

try:
    from contextlib import AsyncContextDecorator
except ImportError:

    class AsyncContextDecorator:
        def __call__(self, func: Callable):
            @wraps(func)
            async def inner(*args, **kwargs):
                async with self:
                    return await func(*args, **kwargs)

            return inner

log = logging.getLogger(__name__)


class LockError(Exception):
    pass


class LockExistsError(LockError):
    pass


class LockPostAcquisitionError(LockError):
    """Base for exceptions which occur after lock is acquired"""


class LockHandoverError(LockPostAcquisitionError):
    pass


class RabbitLock(AsyncContextDecorator):
    QUEUE_NAME_TEMPLATE = 'rabbit_lock_handover_bus_{}'

    def __init__(self, name: str, timeout: float, handover: bool = True, connection_pool=None) -> None:
        self._name = name
        self._timeout = timeout
        self._handover = handover
        self._connection_pool = connection_pool
        self._queue_name = self.QUEUE_NAME_TEMPLATE.format(self._name)
        self._stack = AsyncExitStack()
        self._connection = None
        self._channel = None
        self._queue = None
        self._background_tasks = None

    def __repr__(self):
        return f"{self.__class__.__name__}(" \
            f"name={repr(self._name)}, " \
            f"acquired={bool(self._background_tasks)}, " \
            f"id={id(self)}" \
            ")"

    async def __aenter__(self):
        async with AsyncExitStack() as stack:
            log.debug('%r: starting.', self)

            async def close_channel():
                if self._channel and not self._channel.is_closed:
                    await self._channel.close()
                self._channel = None
            # do it here, as otherwise connection.__aexit__ warns "Channel already closed"
            stack.push_async_callback(close_channel)

            if self._connection_pool is None and self._connection is None:
                self._connection = await stack.enter_async_context(
                    await aio_pika.connect_robust(config.AMQP_URL.format(config.AMQP_PASSWORD))
                )
            else:
                self._connection = await stack.enter_async_context(self._connection_pool.acquire())

            self._channel = await self._connection.channel()

            await self._acquire()

            self._background_tasks = await stack.enter_async_context(BackgroundTasks())
            if self._handover:
                self._background_tasks.add(self._handover_loop())
            await self._background_tasks.start()

            await self._stack.enter_async_context(stack.pop_all())
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        log.debug('%r: stopping.', self)

        try:
            rv = await self._stack.__aexit__(exc_type, exc_val, exc_tb)

            if self._background_tasks.result:
                raise LockError(f'Background tasks exited unexpectedly, result: {self._background_tasks.result}')

            return rv

        finally:
            # CDBCT-2644 Try to fix "queue.declare caused a channel exception resource_locked".
            await self._connection.close()
            self._connection = None

            self._channel = None
            self._queue = None
            self._background_tasks = None

    async def _send_handover(self) -> None:
        log.debug('Sending handover request(id=%s) to queue "%s".', id(self), self._queue_name)
        await self._channel.default_exchange.publish(
            aio_pika.Message(body=str(id(self)).encode('utf-8')),
            routing_key=self._queue_name
        )

    async def _handover_loop(self) -> None:
        try:
            async with self._queue.iterator() as queue_iter:
                async for message in queue_iter:
                    message.ack()
                    _id = message.body.decode('utf-8')
                    raise LockHandoverError(f'Handover request received from lock with id={_id}', _id)

        except asyncio.CancelledError:
            log.info("Has cancelled in the handover_loop")
            raise
        except LockHandoverError:
            log.info("Has LockHandover in the handover_loop")
            raise
        except Exception as e:
            raise LockPostAcquisitionError(e) from e

    async def _acquire(self) -> None:
        ex = None

        try:
            with async_timeout.timeout(timeout=self._timeout or None) as timer:
                while True:
                    try:
                        self._queue = await self._channel.declare_queue(
                            name=self._queue_name, exclusive=True, auto_delete=True
                        )
                        break

                    except aiormq.exceptions.ChannelLockedResource as e:
                        log.debug('Lock "%s" already exists.', self._name)

                        try:
                            raise LockExistsError('Unable to acquire existing lock within the time specified') from e
                        except Exception as ee:
                            if not self._timeout:
                                raise ee
                            ex = ee

                        if self._channel.is_closed:
                            await self._channel.reopen()

                        if self._handover:
                            await self._send_handover()

                        await asyncio.sleep(0.5)

        except TimeoutError:
            if self._timeout and timer.expired and ex:
                raise ex
            else:
                raise
