# Redis CLI Commands

Gunakan Redis CLI pada host Redis untuk memeriksa cache dan nilai populer.

```bash
redis-cli -h 127.0.0.1 -p 6379
```

Perintah umum:

- `KEYS *` - daftar semua key cache
- `GET <key>` - tampilkan nilai dari key sederhana
- `HGETALL <hash>` - tampilkan semua field pada hash
- `DEL <key>` - hapus key secara manual
- `FLUSHDB` - bersihkan semua data pada database Redis aktif

Cache khusus aplikasi:

- `KEYS courses_list:*` - kunci cache daftar kursus
- `GET course_detail:<id>` - kunci cache detail kursus
- `GET simple_lms:session:<session_key>` - sesi yang disimpan di cache jika menggunakan session cache
``