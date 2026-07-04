# Simple LMS - Advanced Features & Integration

## Architecture Diagram

```mermaid
graph TB
    Client([Client / Browser])

    subgraph Docker Compose
        NGINX[Nginx :80]
        WEB[Django App :8000]
        WORKER[Celery Worker]
        BEAT[Celery Beat]
        FLOWER[Flower :5555]

        subgraph Databases
            PG[(PostgreSQL :5432)]
            REDIS[(Redis :6379)]
            MONGO[(MongoDB :27017)]
        end

        subgraph Message Broker
            RMQ[RabbitMQ :5672]
            RMQUI[RabbitMQ UI :15672]
        end
    end

    Client --> NGINX
    NGINX --> WEB
    WEB --> PG
    WEB --> REDIS
    WEB --> MONGO
    WEB --> RMQ
    RMQ --> WORKER
    WORKER --> PG
    WORKER --> MONGO
    BEAT --> RMQ
    FLOWER --> WORKER
```

## Caching Strategy

### Overview
Redis digunakan sebagai cache layer antara Django dan PostgreSQL untuk mengurangi database queries dan mempercepat response time.

### Cache Keys
| Key Pattern | TTL | Keterangan |
|---|---|---|
| `course_list:{page}:{per_page}:{search}:{ordering}` | 300s | Cache hasil list courses |
| `course_detail:{id}` | 300s | Cache detail satu course |

### Flow: Cache-Aside Pattern
Request GET /courses
│
▼
Cek Redis cache
│
├── HIT  → Return cached data (< 1ms)
│
└── MISS → Query PostgreSQL
│
▼
Simpan ke Redis (TTL 300s)
│
▼
Return data ke client

### Cache Invalidation
Cache dihapus otomatis saat:
- Course dibuat (`POST /courses`) → hapus semua `course_list:*`
- Course diupdate (`PATCH /courses/{id}`) → hapus `course_detail:{id}` + `course_list:*`
- Course dihapus (`DELETE /courses/{id}`) → hapus `course_detail:{id}` + `course_list:*`
- Course image diupdate → hapus `course_detail:{id}` + `course_list:*`

### Redis CLI Commands
```bash
# Masuk Redis CLI
docker exec -it redis_cache redis-cli

# Lihat semua cache keys
KEYS *

# Lihat cache course list
KEYS course_list:*

# Lihat cache course detail
KEYS course_detail:*

# Baca nilai cache
GET course_detail:1

# Cek TTL sebuah key (dalam detik)
TTL course_detail:1

# Hapus cache tertentu
DEL course_detail:1

# Hapus semua cache
FLUSHALL

# Statistik Redis
INFO stats
INFO memory

# Monitor real-time commands
MONITOR
```

## Celery Task Flow

### Task 1: send_enrollment_email
POST /enrollments?course_id=X
│
▼
CourseMember dibuat di PostgreSQL
│
▼
send_enrollment_email.delay(user_id, course_id)
│
▼ (async via RabbitMQ)
Celery Worker menerima task
│
▼
Kirim email ke user (simulasi print)
│
▼
Log ke MongoDB: activity_logs { action: "enrollment_email_sent" }
│
▼
Return { status: "success" }

### Task 2: generate_certificate
Dipanggil saat course selesai
│
▼ (async via RabbitMQ)
Celery Worker generate certificate data
│
├── certificate_id: CERT-{user_id}-{course_id}-{date}
├── user: nama lengkap
├── course: nama course
└── issued_at: timestamp
│
▼
Log ke MongoDB: activity_logs { action: "certificate_generated" }

### Task 3: update_course_statistics (Scheduled)
Celery Beat (scheduler)
│
▼ Setiap interval terjadwal
Ambil semua Course dari PostgreSQL
│
▼
Hitung enrollment_count per course
│
▼
Hapus data lama di MongoDB: course_statistics
│
▼
Insert data baru ke MongoDB: course_statistics

### Task 4: export_course_report
POST /reports/export
│
▼
export_course_report.delay(course_id)
│
▼ Return langsung ke client:
{ task_id: "...", status: "processing" }
│
▼ (async via RabbitMQ)
Celery Worker generate CSV
│
▼
Log ke MongoDB: activity_logs { action: "report_generated" }
│
▼
Return CSV content + row count

## MongoDB Collections

### activity_logs
Menyimpan semua aktivitas user untuk audit trail dan analytics.
```json
{
  "user_id": 1,
  "action": "enrollment",
  "details": {
    "course_id": 5,
    "course_name": "Belajar Django"
  },
  "timestamp": "2026-05-24T08:00:00Z"
}
```
Actions yang di-log: `login`, `enrollment`, `enrollment_email_sent`, `certificate_generated`, `report_generated`, `course_view`

### course_statistics
Snapshot statistik enrollment per course, diupdate oleh scheduled task.
```json
{
  "course_id": 1,
  "course_name": "Belajar Django",
  "enrollment_count": 42,
  "updated_at": "2026-05-24T08:00:00Z"
}
```

## Monitoring

### Flower (Celery Monitoring)
URL: http://localhost:5555
- Monitor active/completed/failed tasks
- Lihat worker status dan task history
- Retry failed tasks secara manual

### RabbitMQ Management UI
URL: http://localhost:15672
- Username: lms_user / Password: lms_pass
- Monitor queues, messages, connections
- Lihat message rates dan consumer stats

## Docker Services Summary

| Service | Image | Port | Fungsi |
|---|---|---|---|
| web | python:3.11-slim | 8000 | Django REST API |
| db | postgres:15 | 5432 | Primary database |
| redis | redis:7-alpine | 6379 | Cache + Celery result backend |
| mongodb | mongo:7 | 27017 | Activity logs + analytics |
| rabbitmq | rabbitmq:3-management | 5672, 15672 | Message broker untuk Celery |
| celery-worker | python:3.11-slim | - | Async task processor |
| celery-beat | python:3.11-slim | - | Scheduled task scheduler |
| flower | python:3.11-slim | 5555 | Celery monitoring dashboard |

## Menjalankan Test

```bash
# Jalankan semua test
docker-compose exec web python manage.py test courses --settings=config.settings_test

# Jalankan test dengan coverage report
docker-compose exec web bash -c "coverage run --source=courses --omit=courses/lab_views.py,courses/tasks.py,courses/views.py manage.py test courses --settings=config.settings_test && coverage report"
```

**Hasil test:** 76 tests, 74 passed, 2 skipped, 0 failed  
**Coverage:** 90%

## Cara Menjalankan Project

```bash
# 1. Clone repository
git clone https://github.com/111202315056-tech/simple-lms
cd simple-lms

# 2. Salin file environment
cp .env.example .env

# 3. Jalankan semua service
docker-compose up -d

# 4. Jalankan migration
docker-compose exec web python manage.py migrate

# 5. Seed data demo
docker-compose exec web python seed.py

# 6. Akses aplikasi
# Swagger UI  : http://localhost:8000/api/v1/docs
# Django Admin: http://localhost:8000/admin/
# Silk        : http://localhost:8000/silk/
# Flower      : http://localhost:5555
# RabbitMQ    : http://localhost:15672 (lms_user/lms_pass)
```

## Akun Demo

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Instructor | dosen01 | pass123 |
| Student | siswa01 | testpass123 |

## Screenshot & Bukti Pengujian

Seluruh bukti visual pengujian tersimpan di folder [docs/screenshots/](docs/screenshots/). Berikut ringkasannya:

### 1. Swagger UI — Daftar Endpoint Lengkap
![Swagger UI](docs/screenshots/01-swagger-ui.png)

### 2. Flower — Celery Worker Status
![Flower Workers](docs/screenshots/02-flower-workers.png)

### 3. Flower — Riwayat Task Async (Email Enrollment)
![Flower Tasks](docs/screenshots/03-flower-tasks.png)

### 4. Django Silk — Perbandingan Query Baseline vs Optimized (N+1 Fixing)
![Silk N+1 Comparison](docs/screenshots/04-silk-nplus1-comparison.png)

Log lengkap hasil demo (semua fitur dijalankan berurutan) tersedia di [docs/demo-output.txt](docs/demo-output.txt).

Laporan lengkap dengan penjelasan tiap fitur ada di [FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md).
