"""
Интеграционные тесты RedisService / KVMap.

Требуется Redis на localhost:6379 (см. materials/redis/docker-compose.yml).
"""
from __future__ import annotations

import time
import unittest
from dataclasses import dataclass

import redis

from src.mybootstrap_core_itskovichanton.redis_service import KVMap, RedisConfig, RedisService


@dataclass
class Item:
    name: str = ""
    score: int = 0


class _Cfg:
    def app_name(self) -> str:
        return "redis_test"


def _service() -> RedisService:
    svc = RedisService.__new__(RedisService)
    svc.config = RedisConfig(host="localhost", port=6379, password=None)
    svc.config_service = _Cfg()
    return svc


def _redis_up() -> bool:
    try:
        redis.Redis(host="localhost", port=6379).ping()
        return True
    except Exception:
        return False


@unittest.skipUnless(_redis_up(), "Redis не запущен (docker compose -f materials/redis/docker-compose.yml up -d)")
class RedisServiceIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.svc = _service()
        self.svc.check_availability()
        self.map_name = f"unittest_{int(time.time() * 1000)}"
        self.kv: KVMap[Item] = self.svc.make_map(Item, hname=self.map_name)

    def tearDown(self):
        self.kv.clear()

    def test_set_get_delete(self):
        self.kv.set("a", Item("one", 1))
        self.kv.set("b", Item("two", 2))
        self.assertEqual(self.kv.get("a").name, "one")
        self.assertEqual(self.kv.get("missing"), None)
        self.assertEqual(sorted(self.kv.get_keys()), ["a", "b"])
        self.assertEqual(len(self.kv.get_all()), 2)
        self.kv.delete("a")
        self.assertIsNone(self.kv.get("a"))
        self.assertEqual(self.kv.get_keys(), ["b"])

    def test_update(self):
        self.kv.set("x", Item("init", 0))
        updated = self.kv.update("x", lambda v: setattr(v, "score", v.score + 10))
        self.assertEqual(updated.score, 10)
        self.assertEqual(self.kv.get("x").score, 10)

        created = self.kv.update("new", lambda v: setattr(v, "name", "created"))
        self.assertEqual(created.name, "created")

    def test_find(self):
        self.kv.set("k1", Item("a", 1))
        self.kv.set("k2", Item("b", 2))
        found = self.kv.find(lambda k, v: v.score == 2)
        self.assertEqual(found, ("k2", Item("b", 2)))
        self.assertIsNone(self.kv.find(lambda _k, _v: False))

    def test_ttl_entry(self):
        self.kv.set("temp", Item("ttl", 99), ttl=2)
        self.assertEqual(self.kv.get("temp").score, 99)
        self.assertIn("temp", self.kv.get_keys())
        time.sleep(2.2)
        self.assertIsNone(self.kv.get("temp"))
        self.assertNotIn("temp", self.kv.get_keys())

    def test_clear(self):
        self.kv.set("z", Item("z", 0))
        self.kv.set("t", Item("t", 0), ttl=60)
        self.kv.clear()
        self.assertEqual(self.kv.get_keys(), [])
        self.assertIsNone(self.kv.get("z"))


if __name__ == "__main__":
    unittest.main()
