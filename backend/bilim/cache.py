from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.redis import RedisCache
from redis.exceptions import RedisError


class ResilientRedisCache(RedisCache):
    def get(self, key, default=None, version=None):
        try:
            return super().get(key, default, version)
        except RedisError:
            return default

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            return super().set(key, value, timeout, version)
        except RedisError:
            return None
