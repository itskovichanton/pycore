from datetime import timedelta
import time
import threading
from typing import List
import array
import numpy as np


class CircularWindowCounter:
    """
    Высокопроизводительный оконный счетчик с кольцевым буфером
    
    Особенности:
    - O(1) добавление и получение скорости
    - Минимальное выделение памяти (нет объектов datetime)
    - Использует монотонное время для точности
    - Потокобезопасный
    
    Пример:
        counter = CircularWindowCounter(timedelta(seconds=10))
        counter.add()  # +1
        counter.add(5) # +5
        speed = counter.speed()  # скорость за последние 10 секунд
    """

    def __init__(self, window: timedelta, resolution: float = 0.1):
        """
        Args:
            window: Оконный интервал
            resolution: Разрешение в секундах (размер одного сегмента)
                       Чем меньше, тем точнее, но больше памяти
        """
        self.window_seconds = window.total_seconds()
        self.resolution = resolution

        # Размер буфера (количество сегментов)
        self.buffer_size = int(self.window_seconds / resolution) + 1

        # Кольцевой буфер - используем массив целых чисел
        self._buffer = array.array('L', [0]) * self.buffer_size  # 'L' для unsigned long
        self._index = 0
        self._total = 0

        # Временные метки в секундах с плавающей точкой
        self._last_update = time.monotonic()

        # Для высокой производительности - без блокировок,
        # используем атомарные операции где возможно
        self._lock = threading.Lock()

        # Кэш скорости для быстрого доступа
        self._cached_speed = 0.0
        self._last_speed_update = 0.0

    def _update_index(self, now: float) -> int:
        """
        Обновить текущий индекс на основе времени
        
        Args:
            now: текущее время (монотонное)
            
        Returns:
            int: текущий индекс
        """
        delta = now - self._last_update
        steps = int(delta / self.resolution)

        if steps <= 0:
            return self._index

        # Оптимизация: если много шагов, обновляем буфер
        max_steps = min(steps, self.buffer_size)

        for _ in range(max_steps):
            self._index = (self._index + 1) % self.buffer_size
            self._total -= self._buffer[self._index]
            self._buffer[self._index] = 0

        self._last_update = now + (steps - max_steps) * self.resolution

        return self._index

    def add(self, count: int = 1) -> None:
        """
        Добавить значение к счетчику
        
        Args:
            count: количество (по умолчанию 1)
        """
        now = time.monotonic()

        # Максимально быстрый путь без блокировки
        with self._lock:
            idx = self._update_index(now)
            self._buffer[idx] += count
            self._total += count
            self._cached_speed = 0.0  # Инвалидируем кэш

    def add_batch(self, counts: List[int]) -> None:
        """
        Добавить несколько значений за раз (оптимизировано)
        
        Args:
            counts: список значений для добавления
        """
        now = time.monotonic()

        with self._lock:
            idx = self._update_index(now)
            total_batch = sum(counts)
            self._buffer[idx] += total_batch
            self._total += total_batch
            self._cached_speed = 0.0

    def add_many(self, count: int, times: int) -> None:
        """
        Добавить одно и то же значение много раз (оптимизировано)
        
        Args:
            count: значение
            times: количество повторений
        """
        self.add(count * times)

    def speed(self) -> float:
        """
        Получить скорость накопления за оконный интервал
        
        Returns:
            float: количество событий в секунду
        """
        now = time.monotonic()

        # Используем кэш если обновляли менее 0.1 секунды назад
        if self._cached_speed > 0 and now - self._last_speed_update < 0.1:
            return self._cached_speed

        with self._lock:
            self._update_index(now)

            if self.window_seconds <= 0:
                return 0.0

            self._cached_speed = self._total / self.window_seconds
            self._last_speed_update = now

            return self._cached_speed

    def count(self) -> int:
        """
        Получить общее количество событий в текущем окне
        
        Returns:
            int: количество событий
        """
        now = time.monotonic()

        with self._lock:
            self._update_index(now)
            return self._total

    def reset(self) -> None:
        """Сбросить счетчик"""
        with self._lock:
            self._buffer = array.array('L', [0]) * self.buffer_size
            self._index = 0
            self._total = 0
            self._last_update = time.monotonic()
            self._cached_speed = 0.0

    def get_stats(self) -> dict:
        """
        Получить статистику счетчика
        
        Returns:
            dict: словарь со статистикой
        """
        return {
            'count': self.count(),
            'speed': self.speed(),
            'window_seconds': self.window_seconds,
            'resolution': self.resolution,
            'buffer_size': self.buffer_size,
            'memory_bytes': self.buffer_size * 8,  # приблизительно
        }

    def __len__(self) -> int:
        """Количество активных сегментов"""
        return self.buffer_size

    def __repr__(self) -> str:
        return f"<CircularWindowCounter speed={self.speed():.2f}/s count={self.count()}>"


# Супер-быстрая версия с numpy (если доступен)
class NumpyCircularWindowCounter(CircularWindowCounter):
    """Версия с numpy для максимальной производительности"""

    def __init__(self, window: timedelta, resolution: float = 0.1):
        super().__init__(window, resolution)
        self._buffer = np.zeros(self.buffer_size, dtype=np.uint64)
        self._index = 0
        self._total = 0

    def _update_index(self, now: float) -> int:
        delta = now - self._last_update
        steps = int(delta / self.resolution)

        if steps <= 0:
            return self._index

        steps = min(steps, self.buffer_size)

        # Используем numpy для быстрого обновления
        if steps > 0:
            indices = [(self._index + i + 1) % self.buffer_size for i in range(steps)]
            self._total -= np.sum(self._buffer[indices])
            self._buffer[indices] = 0
            self._index = indices[-1] if indices else self._index

        self._last_update = now

        return self._index
