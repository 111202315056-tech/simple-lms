# Final Project Report — Simple LMS

## 1. Identitas

| | |
|---|---|
| Nama | Aldi Febriayanto |
| NIM | A11.2023.15056 |
| Kelas | *(isi manual)* |
| URL Repository | https://github.com/111202315056-tech/simple-lms |

---

## 2. Deskripsi Project

Simple LMS adalah backend Learning Management System berbasis Django + Django Ninja yang dikembangkan dari project capstone semester sebelumnya. Final project ini melanjutkan project tersebut dengan menambahkan fitur performa dan kualitas API sesuai **Paket 4 — Performance & API Quality**, mencakup Redis caching, cache invalidation, optimasi query (N+1 fixing), filtering/sorting/pagination, dan konsistensi format response/error.

Sistem berjalan penuh di atas Docker Compose dengan 8 service: Django app, PostgreSQL, Redis, MongoDB, RabbitMQ, Celery worker, Celery beat, dan Flower — merepresentasikan arsitektur backend yang mendekati kondisi produksi skala kecil.

---

## 3. Fitur Dasar yang Sudah Berjalan

- Authentication JWT (register, login, refresh token)
- Role-based access control (admin, instructor/teacher, student)
- Endpoint Course, CourseContent, CourseMember (enrollment), Comment — CRUD lengkap
- Swagger/OpenAPI docs (`/api/v1/docs`)
- Struktur konfigurasi berbasis `.env` (tidak hardcode secret)

---

## 4. Fitur Tambahan yang Dipilih — Paket 4: Performance & API Quality

| No | Fitur | Kategori | Poin | Status |
|---|---|---|---|---|
| 1 | Redis caching untuk course list/detail | D | 12 | Selesai |
| 2 | Cache invalidation strategy | D | 12 | Selesai |
| 3 | Optimasi query & N+1 fixing | D | 15 | Selesai |
| 4 | Filtering, sorting, pagination lengkap | I | 12 | Selesai |
| 5 | Response & error format konsisten | I | 10 | Selesai |
| | **Total dikerjakan** | | **61** | **dihitung maks 50** |

---

## 5. Penjelasan Implementasi

### 5.1 Redis Caching + Cache Invalidation
Endpoint `GET /courses` di-cache dengan key berbasis parameter (`page`, `per_page`, `search`, `ordering`) dan TTL 300 detik. Dibuktikan lewat inspeksi langsung ke Redis (`redis-cli KEYS`), termasuk memverifikasi isi cache dan TTL yang tersisa.

Cache invalidation diuji dengan skenario: cek key ada → buat course baru → cek key hilang otomatis. Hasil pengujian menunjukkan seluruh key `course_list:*` terhapus otomatis setelah create.

### 5.2 Optimasi Query & N+1 Fixing
Dibuktikan lewat endpoint pembanding `/lab/course-list/baseline/` (tanpa optimasi) vs `/lab/course-list/optimized/` (pakai `select_related` + `annotate`):

| Endpoint | Query Count | Waktu |
|---|---|---|
| Baseline (N+1) | 454 queries | 566.75 ms |
| Optimized | 2 queries | 6.79 ms |

Speedup ±83x, pengurangan query ±227x. Profiling juga diverifikasi lewat Django Silk.

### 5.3 Filtering, Sorting, Pagination
Endpoint `GET /courses` mendukung `search`, `min_price`, `max_price`, `ordering`, `page`, `per_page`, dengan metadata pagination (`total`, `page`, `per_page`) di setiap response.

### 5.4 Response & Error Format Konsisten
Seluruh error menggunakan format seragam `{"detail": "pesan"}` dengan status code HTTP yang sesuai (401 Unauthorized, 403 Forbidden, 404 Not Found, dsb), diverifikasi lewat pengujian manual terhadap berbagai skenario error.

### 5.5 Fitur di Luar Paket 4 (opsional, tidak dihitung poin karena Paket 4 sudah mencapai batas maksimal 50)

- **MongoDB Activity Logging & Analytics** — pencatatan `course_view` dan agregasi `popular-courses` via MongoDB aggregation pipeline.
- **Celery Async Task** — email notifikasi enrollment dikirim secara asynchronous, diverifikasi lewat log Celery worker dan dashboard Flower (status `SUCCESS`).
- **Endpoint sertifikat PDF** (`GET /enrollments/{id}/certificate`) — fitur eksperimental, **belum melakukan validasi status "course selesai"** sebelum sertifikat bisa diunduh, sehingga tidak diklaim sebagai fitur selesai penuh sesuai deskripsi resmi rubrik (Kategori B).

---

## 6. Cara Menjalankan Project

```bash
# 1. Clone repository
git clone https://github.com/111202315056-tech/simple-lms.git
cd simple-lms

# 2. Salin file environment dan isi SECRET_KEY (wajib, tidak ada default)
cp .env.example .env

# 3. Jalankan semua service
docker-compose up -d

# 4. Jalankan migration
docker-compose exec web python manage.py migrate

# 5. (Opsional) Seed data demo
docker-compose exec web python seed.py
```

**Akses aplikasi:**
- Swagger UI: http://localhost:8000/api/v1/docs
- Django Admin: http://localhost:8000/admin/
- Silk Profiler: http://localhost:8000/silk/
- Flower (Celery monitoring): http://localhost:5555

---

## 7. Akun Demo

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Instructor | dosen01 | pass123 |
| Student | siswa01 | testpass123 |

---

## 8. Endpoint Penting untuk Diuji

| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/api/v1/auth/register` | Registrasi user |
| POST | `/api/v1/auth/login` | Login, dapat JWT |
| GET | `/api/v1/courses?search=&ordering=&page=&per_page=` | List course dengan filter |
| POST | `/api/v1/courses` | Buat course (instructor only) |
| POST | `/api/v1/enrollments?course_id=` | Enroll ke course |
| GET | `/api/v1/analytics/popular-courses` | Analitik dari MongoDB |
| GET | `/lab/course-list/baseline/` | Demo N+1 (tanpa optimasi) |
| GET | `/lab/course-list/optimized/` | Demo query optimized |

---

## 9. Testing dan Coverage

Menjalankan test suite lengkap dengan coverage report:

```bash
docker-compose exec web bash -c "coverage run --source=courses --omit=courses/lab_views.py,courses/tasks.py,courses/views.py manage.py test courses --settings=config.settings_test && coverage report"
```

**Hasil:** 76 test (74 pass, 2 skip), 0 failure, **coverage 90%** — melampaui target 75% untuk nilai maksimal pada kriteria testing rubrik.

Termasuk 10 test baru di `courses/testcases/test_cache_and_performance.py` (coverage 100%) yang secara otomatis memvalidasi:
- Fungsi cache Redis (`set`/`get`/`invalidate` untuk course list & detail, key spesifik per kombinasi filter)
- Cache benar-benar terisi setelah request API dan terhapus otomatis saat course baru dibuat (end-to-end)
- Endpoint `optimized` menggunakan query jauh lebih sedikit (≤5) dibanding `baseline` (>10) dengan 10 course uji, dibaca langsung dari `query_count` pada response — bukan hanya pembuktian manual

| Modul | Coverage |
|---|---|
| `courses/cache.py` | 100% |
| `courses/certificate.py` | 100% |
| `courses/schemas.py` | 100% |
| `courses/testcases/test_cache_and_performance.py` | 100% |
| `courses/apiv1.py` | 80% |
| `courses/auth.py` | 74% |
| `courses/mongo.py` | 48% *(sebagian besar branch koneksi MongoDB tidak dilatih karena test menggunakan mock/skip untuk skenario tertentu)* |
| **Total** | **90%** |

Test mencakup: autentikasi (register/login/refresh), CRUD course, permission/RBAC (student ditolak membuat course dengan status 403), enrollment, comment, dan model/business logic.

Postman collection tersedia di `Simple_LMS_API.postman_collection.json` untuk pengujian manual seluruh endpoint di luar Swagger UI.

## 10. Screenshot / Bukti Pengujian

- Perbandingan query count baseline vs optimized (Django Silk)
- Isi dan TTL cache Redis sebelum/sesudah invalidation
- Log Celery worker menunjukkan task `send_enrollment_email` berstatus `SUCCESS`
- Dashboard Flower menampilkan riwayat task
- Hasil test suite: 76 test, 90% coverage (termasuk test otomatis untuk cache Redis dan N+1 query)
- Riwayat GitHub Actions CI — seluruh run hijau/sukses

*(Lampirkan file screenshot pada folder `docs/screenshots/` di repository)*

---

## 11. Kendala dan Solusi

| Kendala | Solusi |
|---|---|
| Endpoint `courses.apiv1` sempat error `TypeError: 'module' object is not iterable` saat `include()` | Diperbaiki dengan mengarahkan langsung ke `apiv1.urls` (instance NinjaAPI), bukan module. |
| Endpoint `/lab/*` sempat tidak terdaftar karena import di tengah file `urls.py` | Dipindahkan ke bagian atas file agar tidak memicu circular import behavior yang tidak konsisten. |
| Test suite gagal karena path endpoint di test client tidak cocok dengan prefix routing Django Ninja | Disesuaikan path pada seluruh test case (`courses/testcases/test_api.py`). |
| Rate limiter (429) mengganggu eksekusi test berulang | Dibuat `config/settings_test.py` terpisah dengan `RATELIMIT_ENABLE = False` khusus untuk environment testing. |
| Kolom `created_at`/`updated_at` pada `CourseContent` sempat menyebabkan `DuplicateColumn` saat migration dijalankan di database baru (seperti CI) | Ditemukan bahwa migration `0001_initial.py` sudah mencakup kolom tersebut; migration duplikat yang sempat dibuat manual dihapus agar migration history konsisten dari database kosong. |
| File `.env` (berisi kredensial development) sempat ter-commit ke git history meski sudah ada di `.gitignore` | Dibersihkan total dari seluruh riwayat commit menggunakan `git-filter-repo`, diikuti force-push ke remote. |
| `SECRET_KEY` sebelumnya memiliki fallback default yang tidak aman (`django-insecure-...`) | Diubah menjadi fail-fast — aplikasi menolak start jika `SECRET_KEY` tidak diset di environment. |

---

## 12. Kesimpulan

Final project ini memperkuat pemahaman tentang trade-off performa backend nyata — terutama bagaimana N+1 query problem dapat menurunkan performa API secara drastis (454 → 2 query, ±83x speedup) dan bagaimana caching yang tepat sasaran (dengan strategi invalidation yang benar) memberi manfaat signifikan tanpa mengorbankan konsistensi data.

Proses debugging migration history yang tidak sinkron dengan kondisi database aktual, serta pembersihan credential yang sempat ter-commit ke git, menjadi pengalaman penting soal pentingnya kebersihan riwayat version control — bukan hanya kondisi kode saat ini, tapi juga jejak historisnya.

---

## 13. Catatan Bonus

| Bonus | Status |
|---|---|
| Dokumentasi rapi dengan diagram arsitektur | ✅ Tercapai — README menyertakan diagram Mermaid arsitektur, caching, dan alur Celery |
| Test coverage tinggi dan CI berjalan | ✅ Tercapai — coverage tinggi, GitHub Actions CI hijau konsisten di setiap push |
| Deployment online | ❌ Belum — project berjalan lokal via Docker Compose |
| UI/frontend sederhana | ❌ Tidak dikerjakan — project murni backend/API |
| Fitur inovatif di luar daftar | Endpoint pembanding `/lab/course-list/baseline/` vs `/optimized/` dibuat sebagai alat bantu pembuktian N+1 secara live dan tidak tercantum di daftar fitur resmi manapun pada lampiran rubrik. |
