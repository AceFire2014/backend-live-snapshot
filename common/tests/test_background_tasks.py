import asyncio
import inspect

import asynctest

from common.background_tasks import chain_task, BackgroundTasks


class TestChainTask(asynctest.TestCase):

    async def test_current_task_exits_first(self):
        task = asyncio.get_event_loop().create_task(asyncio.sleep(1))
        async with chain_task(task) as result:
            self.assertSequenceEqual(result, [])
        self.assertSequenceEqual(result, [])
        self.assertTrue(task.cancelled())

    async def test_chained_task_cancel_propagated(self):
        task = asyncio.get_event_loop().create_task(asyncio.sleep(1))
        with self.assertRaises(asyncio.CancelledError):
            async with chain_task(task) as result:
                self.assertSequenceEqual(result, [])
                task.cancel()
                await asyncio.sleep(1)
                self.assertSequenceEqual(result, [])
        self.assertSequenceEqual(result, [])

    async def test_chained_task_exception_propagated(self):
        async def exception(ex):
            raise ex
        task = asyncio.get_event_loop().create_task(exception(IndexError))
        with self.assertRaises(IndexError):
            async with chain_task(task) as result:
                self.assertSequenceEqual(result, [])
                await asyncio.sleep(1)
        self.assertSequenceEqual(result, [])

    async def test_chained_task_result_propagated(self):
        task = asyncio.get_event_loop().create_task(asyncio.sleep(0.1, result='result'))
        with self.assertRaises(asyncio.CancelledError):
            async with chain_task(task) as result:
                await asyncio.sleep(1)
        self.assertSequenceEqual(result, ['result'])


class TestBackgroundTasks(asynctest.TestCase):

    async def test_closes_nonstarted_tasks(self):
        tasks = [asyncio.sleep(i) for i in [0, 1]]
        async with BackgroundTasks() as bt:
            for task in tasks:
                bt.add(task)

        self.assertSequenceEqual(
            [inspect.getgeneratorstate(task) for task in tasks],
            [inspect.GEN_CLOSED] * len(tasks)
        )

    async def test_closes_started_tasks(self):
        tasks = [asyncio.sleep(i) for i in [0, 1]]
        async with BackgroundTasks() as bt:
            for task in tasks:
                bt.add(task)
            await bt.start()

        self.assertSequenceEqual(
            [inspect.getgeneratorstate(task) for task in tasks],
            [inspect.GEN_CLOSED] * len(tasks)
        )

    async def test_result_when_no_tasks(self):
        async with BackgroundTasks() as bt:
            self.assertIsNone(bt.result)
            await bt.start()

            self.assertIsNone(bt.result)
        self.assertIsNone(bt.result)

    async def test_result_of_canceled_tasks(self):
        tasks = [asyncio.sleep(i) for i in [0, 1]]
        async with BackgroundTasks() as bt:
            for task in tasks:
                bt.add(task)

            self.assertIsNone(bt.result)
            await bt.start()
            self.assertIsNone(bt.result)
        self.assertIsNone(bt.result)

    async def test_result_of_finished_tasks(self):
        tasks = [asyncio.sleep(0, result=i) for i in [0, 1]]
        with self.assertRaises(asyncio.CancelledError):
            async with BackgroundTasks() as bt:
                for task in tasks:
                    bt.add(task)
                self.assertIsNone(bt.result)
                await bt.start()
                await asyncio.sleep(1)

        self.assertSequenceEqual(bt.result, [0, 1])

    async def test_propagates_exceptions(self):
        async def exception(ex):
            raise ex
        tasks = [exception(IndexError)]
        with self.assertRaises(IndexError):
            async with BackgroundTasks() as bt:
                for task in tasks:
                    bt.add(task)
                await bt.start()
                await asyncio.sleep(1)

        self.assertIsNone(bt.result)
