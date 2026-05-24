import os
import time

import redis
from weather_api import get_weather


if __name__ == "__main__":
    city = "Jakarta"
    cache_key = f"weather:{city.strip().lower()}"
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    client = redis.from_url(redis_url, decode_responses=True)
    client.delete(cache_key)

    start = time.time()
    result1 = get_weather(city)
    time1 = time.time() - start
    print(f"First call: {time1:.2f}s")
    print(f"Result 1: {result1}\n")

    start = time.time()
    result2 = get_weather(city)
    time2 = time.time() - start
    print(f"Second call (cached): {time2:.2f}s")
    print(f"Result 2: {result2}\n")

    print("Note: To test cache expiry, wait 5 minutes or reset the key in Redis.")
