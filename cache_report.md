# Redis Cache Report

## File yang dimodifikasi

- `weather_api.py`
- `test_cache.py`

## Implementasi caching

Fungsi `get_weather(city)` sekarang melakukan:

1. Membuat kunci cache Redis: `weather:{city}`
2. Mencoba membaca data dari Redis dengan `GET`
3. Jika cache hit, mengembalikan data dari Redis tanpa memanggil API
4. Jika cache miss, melakukan panggilan API lambat (`time.sleep(2)`)
5. Menyimpan hasil di Redis dengan `SET` dan `EXPIRE` 300 detik

## Redis commands yang digunakan

- `GET weather:<city>`
- `SET weather:<city> <json_value> EX 300`
- `EXPIRE weather:<city> 300` (ekivalen melalui parameter `ex=300` di `SET`)

## Hasil pengujian

```bash
python test_cache.py
```

Expected output:

```text
First call: 2.00s
Result 1: {'city': 'jakarta', 'temperature': 30, 'condition': 'sunny', 'source': 'simulated-api'}
Second call (cached): 0.01s
Result 2: {'city': 'jakarta', 'temperature': 30, 'condition': 'sunny', 'source': 'simulated-api'}
Note: To test cache expiry, wait 5 minutes or reset the key in Redis.
```

> Jika Redis aktif dan data tersimpan, panggilan kedua akan sangat cepat karena data dibaca langsung dari cache.

## Jawaban pertanyaan

### 1. Kenapa response time berbeda?

Response time berbeda karena panggilan pertama selalu melakukan pemanggilan API lambat dan hanya menyimpan hasil ke cache setelah selesai. Pada panggilan kedua, data sudah tersedia di Redis, sehingga tidak perlu menunggu delay `time.sleep(2)` dan tidak perlu memanggil API lagi.

### 2. Apa keuntungan caching?

- Mengurangi waktu respons API untuk permintaan yang sama
- Mengurangi beban pada layanan eksternal atau backend
- Menghemat bandwith dan sumber daya komputasi
- Meningkatkan performa aplikasi dan pengalaman pengguna

### 3. Kapan sebaiknya tidak menggunakan cache?

- Ketika data harus selalu real-time dan tidak boleh stale
- Ketika frekuensi update sangat tinggi sehingga cache sering invalidasi
- Ketika kompleksitas invalidasi cache melebihi manfaatnya
- Saat permintaan jarang sehingga overhead cache tidak sebanding dengan penghematan
