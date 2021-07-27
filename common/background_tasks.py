# -*- coding: utf-8 -*-
import asyncio
import sys
from typing import Union, Optional, List, Coroutine

if sys.version_info[:2] > (3, 6):
    from contextlib import asynccontextmanager
    _current_task = asyncio.current_task
else:
    from async_generator import asynccontextmanager
    _current_task = asyncio.Task.current_task


@asynccontextmanager
async def chain_task(task: Union[asyncio.Task, asyncio.Future]):
    """Chain the task to the current one so that when one completes, so does the other.
    This is a counterpart of `asyncio.futures._chain_future`.

    If one is cancelled, the other gets cancelled too.
    The result of the task will be copied to `yielded`.
    The exception of the task will be raised on cm exit.
    Compatible with both asyncio.Tasks and asyncio.Future.
    """
    yielded = []
    current_task = _current_task()

    def callback(fut):
        current_task.cancel()

    try:
        task.add_done_callback(callback)
        yield yielded

    finally:
        done = task.done()
        task.remove_done_callback(callback)
        task.cancel()

        result, exception = None, None
        try:
            result = await task
        except Exception as e:
            exception = e

        if done:
            if exception:
                raise exception
            yielded.append(result)


class BackgroundTasks:

    def __init__(self):
        self.tasks = None
        self._result = None
        self.chain_task = None

    async def __aenter__(self) -> 'BackgroundTasks':
        self.tasks = []
        self._result = None
        self.chain_task = None
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.chain_task:
                return await self.chain_task.__aexit__(exc_type, exc_val, exc_tb)

            else:
                for task in self.tasks:
                    try:
                        task.cancel()  # tasks, futures
                    except Exception:
                        pass

                    try:
                        task.close()  # coroutines
                    except Exception:
                        pass

                    try:
                        await task
                    except Exception:
                        pass
        finally:
            self.tasks = None
            self.chain_task = None

    async def start(self) -> None:
        if self.tasks:
            self.chain_task = chain_task(asyncio.gather(*self.tasks))
            self._result = await self.chain_task.__aenter__()

    @property
    def result(self) -> Optional[List]:
        if not self._result:
            return None
        return self._result[0]

    def add(self, task: Union[Coroutine, asyncio.Task, asyncio.Future]) -> None:
        self.tasks.append(task)
