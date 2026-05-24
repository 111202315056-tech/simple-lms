import redis
import json
import time
import random

# Koneksi ke Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_weather_from_api(city):
    """Simulasi API call yang lambat"""
    time.sleep(2)  # Simulate slow API
    # Simulasi response (karena api.example.com tidak nyata)
    weather_data = {
        "city": city,
        "temperature": random.randint(25, 35),
        "humidity": random.randint(60, 90),
        "condition": random.choice(["Sunny", "Cloudy", "Rainy"]),
        "source": "API"
    }
    return weather_data

def get_weather(city):
    """Get weather dengan Redis caching"""
    cache_key = f"weather:{city.lower()}"

    # 1. Cek cache dulu
    cached = r.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["source"] = "CACHE"
        print(f"[CACHE HIT] Data untuk {city} ditemukan di cache")
        return data

    # 2. Cache miss - call API
    print(f"[CACHE MISS] Memanggil API untuk {city}...")
    data = get_weather_from_api(city)

    # 3. Simpan ke cache dengan expiry 300 detik (5 menit)
    r.set(cache_key, json.dumps(data), ex=300)
    print(f"[CACHE SET] Data {city} disimpan ke cache (TTL: 300s)")

    return data

if __name__ == "__main__":
    print("=== Weather API dengan Redis Cache ===\n")
    city = "Jakarta"

    # First call - slow
    print("--- Call 1 ---")
    start = time.time()
    result1 = get_weather(city)
    time1 = time.time() - start
    print(f"Result: {result1}")
    print(f"Time: {time1:.2f}s\n")

    # Second call - fast (from cache)
    print("--- Call 2 ---")
    start = time.time()
    result2 = get_weather(city)
    time2 = time.time() - start
    print(f"Result: {result2}")
    print(f"Time: {time2:.2f}s\n")

    print(f"Speedup: {time1/time2:.0f}x lebih cepat!")
