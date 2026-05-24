import time
import sys
sys.path.insert(0, '.')
from weather_api import get_weather
import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print("=" * 50)
print("TEST REDIS CACHING - WEATHER API")
print("=" * 50)

# First call - should be slow (2 seconds)
print("\n[TEST 1] First call - ekspektasi: ~2 detik")
start = time.time()
result1 = get_weather("Jakarta")
time1 = time.time() - start
print(f"First call: {time1:.2f}s -> {result1}")

# Second call - should be fast
print("\n[TEST 2] Second call (cached) - ekspektasi: < 0.1 detik")
start = time.time()
result2 = get_weather("Jakarta")
time2 = time.time() - start
print(f"Second call (cached): {time2:.2f}s -> {result2}")

# Different city - should be slow
print("\n[TEST 3] Different city (Bandung) - ekspektasi: ~2 detik")
start = time.time()
result3 = get_weather("Bandung")
time3 = time.time() - start
print(f"Bandung first call: {time3:.2f}s -> {result3}")

# Check Redis directly
print("\n[REDIS INFO]")
print(f"Keys in cache: {r.keys('weather:*')}")
print(f"TTL weather:jakarta = {r.ttl('weather:jakarta')} detik")
print(f"TTL weather:bandung = {r.ttl('weather:bandung')} detik")

print("\n[SUMMARY]")
print(f"First call:  {time1:.2f}s  (API call)")
print(f"Cached call: {time2:.4f}s (from Redis)")
print(f"Speedup:     {time1/time2:.0f}x lebih cepat")
print(f"\nNote: Cache expire dalam 300 detik.")
print(f"Setelah 5 menit, call berikutnya akan lambat lagi (cache expired).")
