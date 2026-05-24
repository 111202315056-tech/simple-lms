# Cache Report - Redis Weather API

## Hasil Test
First call:  2.01s  (API call langsung)
Cached call: 0.0007s (dari Redis cache)
Speedup:     2981x lebih cepat

## Screenshot Hasil Test
==================================================
TEST REDIS CACHING - WEATHER API
[TEST 1] First call - ekspektasi: ~2 detik
[CACHE MISS] Memanggil API untuk Jakarta...
[CACHE SET] Data Jakarta disimpan ke cache (TTL: 300s)
First call: 2.01s -> {'city': 'Jakarta', 'temperature': 27, 'humidity': 71, 'condition': 'Rainy', 'source': 'API'}
[TEST 2] Second call (cached) - ekspektasi: < 0.1 detik
[CACHE HIT] Data untuk Jakarta ditemukan di cache
Second call (cached): 0.00s -> {'city': 'Jakarta', 'temperature': 27, 'humidity': 71, 'condition': 'Rainy', 'source': 'CACHE'}
[TEST 3] Different city (Bandung) - ekspektasi: ~2 detik
[CACHE MISS] Memanggil API untuk Bandung...
[CACHE SET] Data Bandung disimpan ke cache (TTL: 300s)
Bandung first call: 2.00s -> {'city': 'Bandung', 'temperature': 31, 'humidity': 88, 'condition': 'Sunny', 'source': 'API'}
[REDIS INFO]
Keys in cache: ['weather:bandung', 'weather:jakarta']
TTL weather:jakarta = 298 detik
TTL weather:bandung = 300 detik
[SUMMARY]
First call:  2.01s  (API call)
Cached call: 0.0007s (from Redis)
Speedup:     2981x lebih cepat

## Kode yang Dimodifikasi

```python
import redis
import json
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_weather(city):
    cache_key = f"weather:{city.lower()}"

    # 1. Cek cache dulu (GET)
    cached = r.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["source"] = "CACHE"
        return data

    # 2. Cache miss - call API
    data = get_weather_from_api(city)

    # 3. Simpan ke cache dengan expiry 300 detik (SET + EXPIRE)
    r.set(cache_key, json.dumps(data), ex=300)

    return data
```

## Redis Commands yang Digunakan

| Command | Contoh | Fungsi |
|---|---|---|
| SET | `SET weather:jakarta '{"temp":27}' EX 300` | Simpan data ke cache dengan TTL |
| GET | `GET weather:jakarta` | Ambil data dari cache |
| EXPIRE | `EXPIRE weather:jakarta 300` | Set waktu expired (detik) |
| TTL | `TTL weather:jakarta` | Cek sisa waktu cache (detik) |
| KEYS | `KEYS weather:*` | Lihat semua cache keys |
| DEL | `DEL weather:jakarta` | Hapus cache manual |

### Contoh di Redis CLI:
```bash
# Set cache manual
SET weather:jakarta '{"city":"Jakarta","temperature":27}' EX 300

# Get cache
GET weather:jakarta

# Cek TTL
TTL weather:jakarta

# Lihat semua keys
KEYS *

# Hapus cache
DEL weather:jakarta
```

## Jawaban Pertanyaan

### 1. Kenapa response time berbeda?

First call (2.01s) harus memanggil API eksternal yang disimulasikan dengan
`time.sleep(2)` untuk menggambarkan latency jaringan dan pemrosesan server.
Second call (0.0007s) langsung mengambil data dari Redis yang tersimpan
di memory (RAM), sehingga tidak ada network request sama sekali.
Redis beroperasi di RAM yang aksesnya jauh lebih cepat dibanding
disk atau jaringan.

### 2. Apa keuntungan caching?

- **Performa**: Response time turun dari 2 detik menjadi 0.0007 detik (2981x lebih cepat)
- **Hemat biaya**: Mengurangi jumlah API call ke third-party yang berbayar
- **Mengurangi beban server**: Database/API tidak dipanggil berulang untuk data yang sama
- **Availability**: Jika API eksternal down, cache masih bisa melayani request
- **Skalabilitas**: Sistem bisa handle lebih banyak user dengan resource yang sama

### 3. Kapan sebaiknya TIDAK menggunakan cache?

- **Data real-time**: Harga saham, posisi GPS, data sensor IoT yang harus selalu terbaru
- **Data sensitif**: Password, token, data keuangan yang tidak boleh tersimpan di cache
- **Data yang sering berubah**: Stok barang, jumlah seat tersedia, notifikasi
- **Data unik per user**: Informasi personal yang berbeda tiap user (bisa menyebabkan data leak antar user)
- **Operasi write-heavy**: Jika data lebih sering ditulis daripada dibaca, overhead invalidasi cache lebih besar dari manfaatnya