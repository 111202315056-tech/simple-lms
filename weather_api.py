import json
import os
import time

import redis
from redis.exceptions import RedisError

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_TTL_SECONDS = 300
CACHE_KEY_TEMPLATE = "weather:{city}"


def get_redis_client():
    return redis.from_url(REDIS_URL, decode_responses=True)


def _simulate_api_response(city):
    return {
        "city": city,
        "temperature": 30,
        "condition": "sunny",
        "source": "simulated-api",
    }


def get_weather(city):
    """Fetch weather data with Redis caching.

    1. Check Redis cache first
    2. If cache hit, return cached JSON
    3. If cache miss, simulate slow API call
    4. Store result in Redis with EXPIRE = 300 seconds
    """
    city_key = city.strip().lower()
    cache_key = CACHE_KEY_TEMPLATE.format(city=city_key)
    client = get_redis_client()

    try:
        cached = client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except RedisError:
        pass

    # Simulate a slow API call
    time.sleep(2)
    data = _simulate_api_response(city_key)

    try:
        client.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
    except RedisError:
        pass

    return data
