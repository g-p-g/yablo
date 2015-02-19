from . import redis_keys

QUERY_EXPIRE = 3600 * 24  # 1 day


class RedisStorage(object):

    def __init__(self, red):
        self.red = red

    def cached_query(self, query):
        key = redis_keys.QUERY_CACHE % query
        # Renew its ttl in case it is cached.
        self.red.expire(key, QUERY_EXPIRE)

        return self.red.get(key)

    def cache_query(self, query, result):
        self.red.setex(redis_keys.QUERY_CACHE % query, QUERY_EXPIRE, result)

    def cache_remove(self, query):
        key = redis_keys.QUERY_CACHE % query
        self.red.delete(key)
