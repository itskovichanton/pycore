import functools
import inspect
from typing import Callable, Any

from src.mybootstrap_ioc_itskovichanton.config import ConfigService
from src.mybootstrap_ioc_itskovichanton.ioc import bean
from src.mybootstrap_ioc_itskovichanton.utils import omittable_parentheses
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException, ERR_REASON_TOO_MANY_REQUESTS

from src.mybootstrap_core_itskovichanton.redis_service import RedisService

_ACQUIRE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if tonumber(current) == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


@bean
class RateLimiter:
    redis_service: RedisService
    config_service: ConfigService

    def init(self, **kwargs):
        self._acquire_script = self.redis_service.get().register_script(_ACQUIRE_SCRIPT)

    def _make_redis_key(self, bucket: str, key: str) -> str:
        return f"{self.config_service.app_name()}:rate_limit:{bucket}:{key}"

    def _resolve_key(self, key: str | Callable[..., Any] | None, func: Callable, args, kwargs) -> str:
        if key is None:
            return func.__qualname__
        if callable(key):
            return str(key(*args, **kwargs))
        return key

    def acquire(self, bucket: str, limit: int, window_sec: int, key: str):
        if limit <= 0 or window_sec <= 0:
            raise CoreException(message=f"Invalid rate limit config: limit={limit}, window_sec={window_sec}")

        redis_key = self._make_redis_key(bucket, key)
        current = int(self._acquire_script(keys=[redis_key], args=[window_sec]))
        if current > limit:
            raise CoreException(message='Слишком много запросов', reason=ERR_REASON_TOO_MANY_REQUESTS)
            #     message=(
            #         f"Rate limit exceeded: bucket={bucket}, key={key}, "
            #         f"limit={limit}/{window_sec}s, current={current}"
            #     ),
            # )

    @omittable_parentheses(allow_partial=True)
    def rate_limit(self,
                   bucket: str,
                   limit: int | None = None,
                   window_sec: int | None = None,
                   key: str | Callable[..., Any] | None = None,
                   _func: Callable | None = None):
        def decorator(func: Callable):
            is_async = inspect.iscoroutinefunction(func)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if limit is not None and window_sec is not None:
                    resolved_key = self._resolve_key(key, func, args, kwargs)
                    self.acquire(bucket, limit, window_sec, resolved_key)
                return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if limit is not None and window_sec is not None:
                    resolved_key = self._resolve_key(key, func, args, kwargs)
                    self.acquire(bucket, limit, window_sec, resolved_key)
                return func(*args, **kwargs)

            return async_wrapper if is_async else sync_wrapper

        if _func is None:
            return decorator
        return decorator(_func)


from src.mybootstrap_core_itskovichanton.di import injector

util = injector().inject(RateLimiter).rate_limit
