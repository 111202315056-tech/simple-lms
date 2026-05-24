# Modul 14: Arsitektur Integrasi Asynchronous Task

## Tujuan

Dokumen ini menjelaskan bagaimana `Simple LMS` mengintegrasikan:

- Redis untuk caching dan Celery result backend
- RabbitMQ sebagai message broker Celery
- MongoDB untuk activity log dan analytics
- Celery worker dan scheduler untuk menjalankan task asynchronous
- Flower untuk monitoring task queue

## Komponen Utama

1. `web`
   - Aplikasi Django utama
   - Menjalankan API dan endpoint
   - Mengirim task ke Celery
   - Menggunakan Redis sebagai cache dan session backend

2. `redis`
   - Menyimpan data cache course list dan detail course
   - Menyimpan hasil task Celery jika `CELERY_RESULT_BACKEND` di-set ke Redis

3. `rabbitmq`
   - Message brokernya Celery
   - Menyimpan antrean task dan mengirimnya ke worker

4. `celery-worker`
   - Menjalankan worker yang memproses task asynchronous
   - Mengambil task dari RabbitMQ

5. `celery-beat`
   - Scheduler Celery untuk task berkala
   - Menjalankan task `update_course_statistics` secara terjadwal

6. `flower`
   - Dasbor monitoring Celery
   - Menyediakan informasi tentang task, worker, dan antrean

7. `mongodb`
   - Menyimpan log aktivitas user
   - Menyimpan analytics user dan event
   - Menyimpan reports dan certificate history

## Alur Kerja Async di Simple LMS

1. User mendaftar pada endpoint `POST /api/enrollments`.
2. API menulis data enrollment ke database utama (PostgreSQL).
3. API memanggil task Celery:
   - `send_enrollment_email.delay(user_id, course_id)`
4. Task dikirim ke RabbitMQ.
5. Worker Celery yang aktif mengambil task dari antrean.
6. Worker memproses task dan menulis hasil/log ke MongoDB.
7. Jika task berhasil selesai, hasil juga dapat disimpan di Redis melalui result backend.

## Contoh Endpoint Task

- `POST /api/courses/{id}/request-certificate`
  - Menyimpan task `generate_certificate` ke antrean
- `POST /api/courses/{id}/export-report`
  - Menyimpan task `export_course_report` ke antrean
- `POST /api/analytics/schedule-statistics`
  - Menyimpan task `update_course_statistics` ke antrean
- `GET /api/tasks/{task_id}`
  - Mengambil status task Celery (queued, started, success, failed)

## Arsitektur Data

### Redis

Redis digunakan untuk:

- Menyimpan hasil cache endpoint `courses` dan `courses/{id}`
- Menyimpan leaderboard popular course melalui sorted set
- Menyimpan task results Celery di backend Redis
- Session backend Django untuk mempercepat session store

### MongoDB

MongoDB menyediakan document store untuk:

- `activity_logs`: setiap event user, seperti view course, enrollment, dan export report
- `learning_analytics`: event analytic seperti `course_view`, `enrollment`, dan `certificate_generated`
- `certificates`: metadata sertifikat yang dihasilkan
- `reports`: summary atau report task yang dihasilkan oleh Celery

## Docker Compose

File `docker-compose.yml` sudah berisi service:

- `db`
- `redis`
- `rabbitmq`
- `mongodb`
- `web`
- `celery-worker`
- `celery-beat`
- `flower`

## Cara Menjalankan

1. Buat file environment `.env` dari `.env.example`.
2. Jalankan layanan utama:

```bash
docker compose up --build db redis rabbitmq mongodb web
```

3. Jalankan migrasi:

```bash
docker compose run web python manage.py migrate
```

4. Jalankan worker dan scheduler:

```bash
docker compose up -d celery-worker celery-beat flower
```

5. Buka Flower:

```text
http://localhost:5555
```

## Monitoring dan Debugging

- Gunakan `docker compose logs celery-worker` untuk melihat error worker
- Gunakan `docker compose logs celery-beat` untuk melihat scheduler
- Jika task gagal, gunakan Flower untuk melihat traceback
- Pastikan `rabbitmq` dan `redis` tersedia sebelum memulai worker

## Tips Pengembangan

- Pastikan `CELERY_BROKER_URL` mengarah ke `rabbitmq`
- Pastikan `CELERY_RESULT_BACKEND` mengarah ke Redis
- Gunakan `async_result.status` untuk memeriksa state task
- Simpan event analytics di MongoDB agar query reporting lebih cepat dan fleksibel
