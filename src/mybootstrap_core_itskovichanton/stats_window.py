from dataclasses import dataclass
from collections import deque
from statistics import mean, median, pstdev
from typing import List
import math


@dataclass
class Point:
    name: str
    duration: float  # миллисекунды


@dataclass
class StatsSummary:
    avg: float
    max: float
    min: float
    median: float
    stddev: float
    count: int
    total: float
    p95: float
    p99: float
    most_long_requests: List[Point]


class StatsWindow:
    def __init__(self, max_size=500):
        self.items = deque(maxlen=max_size)

    def add(self, p: Point):
        self.items.append(p)

    def _percentile(self, sorted_values, p):
        if not sorted_values:
            return 0
        k = (len(sorted_values) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_values[int(k)]
        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)

    def get_summary(self, top_n=5) -> StatsSummary:
        if not self.items:
            return StatsSummary(
                avg=0, max=0, min=0, median=0, stddev=0,
                count=0, total=0, p95=0, p99=0, most_long_requests=[]
            )

        durations = [x.duration for x in self.items]
        sorted_d = sorted(durations)

        avg_v = mean(durations)
        max_v = max(durations)
        min_v = min(durations)
        med_v = median(durations)
        std_v = pstdev(durations) if len(durations) > 1 else 0
        total_v = sum(durations)
        p95_v = self._percentile(sorted_d, 95)
        p99_v = self._percentile(sorted_d, 99)

        most_long_requests = sorted(self.items, key=lambda x: x.duration, reverse=True)[:top_n]

        return StatsSummary(
            avg=avg_v,
            max=max_v,
            min=min_v,
            median=med_v,
            stddev=std_v,
            count=len(durations),
            total=total_v,
            p95=p95_v,
            p99=p99_v,
            most_long_requests=most_long_requests
        )
