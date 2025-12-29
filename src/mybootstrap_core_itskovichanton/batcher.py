import asyncio
import json
from time import sleep


class TransportError(Exception):
    pass


class TransportRetry(Exception):
    pass


class TransportSlowDown(Exception):
    def __init__(self, delay):
        self.delay = delay


class AbstractTransport:
    async def send(self, batch):
        raise NotImplementedError


class AsyncUniqueKeyBuffer:
    def __init__(
            self,
            transport,
            flush_interval=3,
            batch_size=100,
            max_buffer=10_000,
            workers=3,
            backoff_min=1,
            backoff_max=30,
    ):
        self.transport = transport
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.max_buffer = max_buffer
        self.workers = workers
        self.backoff_min = backoff_min
        self.backoff_max = backoff_max

        self.buffer = {}
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self.stop_event = asyncio.Event()

        self.tasks = []

    async def push(self, obj):
        key = obj["key"]
        async with self.lock:
            if len(self.buffer) >= self.max_buffer:
                return
            self.buffer[key] = obj
            print(len(self.buffer))
            if len(self.buffer) >= self.batch_size:
                await self._emit()

    async def _emit(self):
        if not self.buffer:
            return
        batch = list(self.buffer.values())
        self.buffer.clear()
        await self.queue.put(batch)

    async def _flush_loop(self):
        while True:
            await asyncio.sleep(self.flush_interval)
            async with self.lock:
                await self._emit()

    async def _worker(self, wid):

        backoff = self.backoff_min

        while not self.stop_event.is_set():
            batch = await self.queue.get()

            while True:
                try:

                    await self.transport.send(batch)
                    backoff = self.backoff_min

                    break

                except TransportSlowDown as e:
                    await asyncio.sleep(e.delay)

                except TransportRetry:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.backoff_max)

                except TransportError:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.backoff_max)

            self.queue.task_done()

    async def start(self):
        self.tasks.append(asyncio.create_task(self._flush_loop()))
        for i in range(self.workers):
            self.tasks.append(asyncio.create_task(self._worker(i)))
        await asyncio.gather(*self.tasks)

    async def close(self):
        self.stop_event.set()
        async with self.lock:
            await self._emit()
        await self.queue.join()
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
