import asyncio
from datetime import timedelta
import time
from typing import List
import array

from src.mybootstrap_core_itskovichanton.stats.sync_circular_window_counter import CircularWindowCounter


class AsyncCircularWindowCounter:
    """
    Асинхронная версия оконного счетчика

    Особенности:
    - Неблокирующие операции
    - Оптимизирована для высоких нагрузок в asyncio
    - Использует цикл событий для периодической очистки
    """

    def __init__(self, window: timedelta, resolution: float = 0.1,
                 auto_cleanup: bool = True):
        """
        Args:
            window: Оконный интервал
            resolution: Разрешение в секундах
            auto_cleanup: Автоматическая очистка в фоне
        """
        self.window_seconds = window.total_seconds()
        self.resolution = resolution

        self.buffer_size = int(self.window_seconds / resolution) + 1
        self._buffer = array.array('L', [0]) * self.buffer_size
        self._index = 0
        self._total = 0

        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

        # Для кэширования скорости
        self._cached_speed = 0.0
        self._last_speed_update = 0.0

        # Для фоновой очистки
        self._cleanup_task = None
        if auto_cleanup:
            self._cleanup_task = asyncio.create_task(self._auto_cleanup())

    def _update_index(self, now: float) -> int:
        """Синхронное обновление индекса (вызывается под блокировкой)"""
        delta = now - self._last_update
        steps = int(delta / self.resolution)

        if steps <= 0:
            return self._index

        max_steps = min(steps, self.buffer_size)

        for _ in range(max_steps):
            self._index = (self._index + 1) % self.buffer_size
            self._total -= self._buffer[self._index]
            self._buffer[self._index] = 0

        self._last_update = now + (steps - max_steps) * self.resolution

        return self._index

    async def add(self, count: int = 1) -> None:
        """Асинхронно добавить значение"""
        now = time.monotonic()

        async with self._lock:
            idx = self._update_index(now)
            self._buffer[idx] += count
            self._total += count
            self._cached_speed = 0.0

    async def add_batch(self, counts: List[int]) -> None:
        """Асинхронно добавить несколько значений"""
        now = time.monotonic()

        async with self._lock:
            idx = self._update_index(now)
            total_batch = sum(counts)
            self._buffer[idx] += total_batch
            self._total += total_batch
            self._cached_speed = 0.0

    async def speed(self) -> float:
        """Асинхронно получить скорость"""
        now = time.monotonic()

        # Быстрый путь - используем кэш
        if self._cached_speed > 0 and now - self._last_speed_update < 0.1:
            return self._cached_speed

        async with self._lock:
            self._update_index(now)

            if self.window_seconds <= 0:
                return 0.0

            self._cached_speed = self._total / self.window_seconds
            self._last_speed_update = now

            return self._cached_speed

    async def count(self) -> int:
        """Асинхронно получить количество"""
        now = time.monotonic()

        async with self._lock:
            self._update_index(now)
            return self._total

    async def reset(self) -> None:
        """Асинхронно сбросить счетчик"""
        async with self._lock:
            self._buffer = array.array('L', [0]) * self.buffer_size
            self._index = 0
            self._total = 0
            self._last_update = time.monotonic()
            self._cached_speed = 0.0

    async def _auto_cleanup(self) -> None:
        """Фоновая задача для автоматической очистки"""
        try:
            while True:
                await asyncio.sleep(self.resolution)
                await self.speed()  # Просто обновляем для очистки
        except asyncio.CancelledError:
            pass

    async def close(self) -> None:
        """Закрыть счетчик (остановить фоновые задачи)"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def __aenter__(self):
        """Контекстный менеджер"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие"""
        await self.close()

    def __repr__(self) -> str:
        return f"<AsyncCircularWindowCounter buffer={self.buffer_size}>"


# Адаптер для синхронного использования в асинхронном коде
class ThreadedWindowCounter:
    """
    Адаптер для использования синхронного счетчика в асинхронном коде
    через thread pool executor
    """

    def __init__(self, window: timedelta, resolution: float = 0.1):
        self._counter = CircularWindowCounter(window, resolution)
        self._loop = None
        self._executor = None

    async def add(self, count: int = 1) -> None:
        """Асинхронно добавить через executor"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._counter.add, count)

    async def speed(self) -> float:
        """Асинхронно получить скорость"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._counter.speed)
