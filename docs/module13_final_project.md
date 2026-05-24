# Modul 13: Panduan Final Project

## Learning Objectives

- Memahami spesifikasi dan kriteria penilaian final project
- Merancang arsitektur backend yang tepat untuk proyek
- Mengintegrasikan semua komponen yang dipelajari selama semester
- Menyiapkan dokumentasi API yang lengkap
- Melakukan presentasi dan demo proyek dengan baik

## 1. Overview Proyek

### 1.1 Deskripsi
Final project ini merupakan kulminasi dari seluruh pembelajaran selama semester. Anda diminta untuk mengembangkan backend lengkap Simple LMS (Learning Management System) yang mengintegrasikan seluruh teknologi yang telah dipelajari dari Modul 01 hingga Modul 13.

Proyek ini bukan sekadar menggabungkan potongan kode dari modul-modul sebelumnya, melainkan membangun sebuah sistem yang kohesif, teruji, dan terdokumentasi — layaknya sebuah proyek backend siap produksi.

### 1.2 Tujuan

- Integrasi Teknologi — Menggabungkan Django, PostgreSQL, Redis, MongoDB, Celery, dan RabbitMQ dalam satu arsitektur yang utuh
- Best Practices — Menerapkan standar industri dalam hal code quality, testing, dokumentasi, dan security
- Problem Solving — Menghadapi dan menyelesaikan tantangan teknis saat mengintegrasikan multiple services
- Presentasi Teknis — Mendemonstrasikan pemahaman mendalam tentang arsitektur yang dibangun

### 1.3 Format Pengerjaan

Proyek dapat dikerjakan secara individu atau kelompok (maksimal 3 orang). Untuk pengerjaan kelompok, setiap anggota harus memiliki kontribusi yang jelas dan terdokumentasi melalui git commit history.

### 1.4 Arsitektur Lengkap Sistem

Komponen utama yang diharapkan dalam sistem:

- **Client**: Browser / Postman / Frontend
- **Reverse Proxy**: Nginx
- **Web Application**: Django + Django Ninja (REST API + JWT Auth)
- **Main Database**: PostgreSQL
- **Cache & Session**: Redis
- **Analytics & Logs**: MongoDB
- **Message Broker**: RabbitMQ
- **Background Worker**: Celery Worker
- **Periodic Task Scheduler**: Celery Beat

Arsitektur yang ideal menggambarkan alur request-response, cache lookup, asynchronous task publish/consume, dan storage read/write.

## 2. Arsitektur Sistem yang Diharapkan

### 2.1 Komponen dan Perannya

| Komponen | Teknologi | Peran dalam Sistem |
|---|---|---|
| Web Application | Django + Django Ninja | Menangani HTTP request, business logic, dan REST API |
| Main Database | PostgreSQL | Menyimpan data utama: users, courses, contents, comments, enrollments |
| Cache & Session | Redis | Menyimpan cache response API dan session management |
| Analytics Database | MongoDB | Menyimpan activity logs dan data analytics |
| Message Broker | RabbitMQ | Mengelola antrian pesan antara Django dan Celery workers |
| Async Worker | Celery Worker | Mengeksekusi background tasks (email, report generation) |
| Task Scheduler | Celery Beat | Menjadwalkan periodic tasks (daily stats, cleanup) |
| Reverse Proxy | Nginx | Meneruskan request ke Django dan melayani static files |

### 2.2 Alur Request dalam Sistem

Contoh alur untuk beberapa use case:

- **GET /api/v1/courses/**
  - Nginx menerima request
  - Django memeriksa Redis cache
  - Jika cache miss, Django membaca dari PostgreSQL dan menulis kembali ke Redis
  - Response dikembalikan ke client
  - Aktivitas dapat dicatat ke MongoDB secara asynchronous

- **POST /api/v1/courses/1/enroll/**
  - Nginx meneruskan request ke Django
  - Django menulis enrollment ke PostgreSQL
  - Django mem-publish task ke RabbitMQ untuk mengirim email notifikasi
  - Response 201 Created dikembalikan segera
  - Celery worker memproses task email secara background

### 2.3 Docker Compose Services

Semua layanan harus didefinisikan dalam `docker-compose.yml` sehingga sistem dapat dijalankan dengan satu perintah:

```bash
docker compose up --build
```

## 3. Functional Requirements

Setiap fitur harus mengikuti konvensi RESTful dan mengembalikan response JSON yang konsisten.

### 3.1 User Management

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| POST | `/api/v1/register` | Registrasi user baru | Tidak |
| POST | `/api/v1/auth/sign-in` | Login dan mendapatkan JWT token | Tidak |
| POST | `/api/v1/auth/token-refresh` | Refresh access token | Tidak |

- Registrasi harus memvalidasi email unik dan password minimal 8 karakter
- Login mengembalikan `access_token` dan `refresh_token`

### 3.2 Course Management (CRUD)

| Method | Endpoint | Deskripsi | Auth | Authorization |
|---|---|---|---|---|
| GET | `/api/v1/courses/` | List courses | Tidak | Public |
| GET | `/api/v1/courses/{id}/` | Detail course | Tidak | Public |
| POST | `/api/v1/courses/` | Buat course baru | Ya | User jadi teacher |
| PUT | `/api/v1/courses/{id}/` | Update course | Ya | Owner only |
| PATCH | `/api/v1/courses/{id}/` | Partial update course | Ya | Owner only |
| DELETE | `/api/v1/courses/{id}/` | Hapus course | Ya | Owner + Admin |

- List harus mendukung filtering (nama, teacher), sorting (nama, tanggal, harga), dan pagination
- User yang membuat course otomatis menjadi teacher
- Delete hanya bisa dilakukan oleh owner atau admin

### 3.3 Content Management

| Method | Endpoint | Deskripsi | Auth | Authorization |
|---|---|---|---|---|
| GET | `/api/v1/courses/{id}/contents/` | List contents | Ya | Enrolled + Owner |
| POST | `/api/v1/contents/` | Buat content baru | Ya | Course owner only |
| PUT | `/api/v1/contents/{id}/` | Update content | Ya | Course owner only |
| DELETE | `/api/v1/contents/{id}/` | Hapus content | Ya | Course owner only |
| POST | `/api/v1/contents/{id}/upload/` | Upload attachment | Ya | Course owner only |

- Content mendukung hierarki melalui `parent_id` (section > subsection > materi)
- Upload attachment mendukung file PDF, gambar, dan dokumen

### 3.4 Enrollment

| Method | Endpoint | Deskripsi | Auth | Authorization |
|---|---|---|---|---|
| POST | `/api/v1/courses/{id}/enroll/` | Mendaftar ke course | Ya | Authenticated user |
| GET | `/api/v1/mycourses/` | List course yang diikuti | Ya | Authenticated user |

- User tidak boleh enroll dua kali pada course yang sama
- Enrollment memicu async task untuk mengirim email notifikasi
- Activity dicatat di MongoDB

### 3.5 Comments

| Method | Endpoint | Deskripsi | Auth | Authorization |
|---|---|---|---|---|
| POST | `/api/v1/comments/` | Posting komentar | Ya | Enrolled member only |
| PUT | `/api/v1/comments/{id}/` | Update komentar | Ya | Comment owner only |
| DELETE | `/api/v1/comments/{id}/` | Hapus komentar | Ya | Comment owner + Course owner |

### 3.6 Caching (Redis)

- Cache `GET /api/v1/courses/` dengan TTL 5 menit
- Cache `GET /api/v1/courses/{id}/` dengan TTL 10 menit
- Cache invalidation otomatis saat create/update/delete course
- Session management pengguna disimpan di Redis
- Gunakan key pattern yang konsisten seperti `course:list:page:{n}` dan `course:detail:{id}`
- Cached endpoint harus memiliki response time di bawah 50ms

### 3.7 Analytics (MongoDB)

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/v1/analytics/popular-courses/` | Top courses berdasarkan views | Ya (Admin) |
| GET | `/api/v1/analytics/user-activity/` | Ringkasan aktivitas user | Ya (Admin) |

Format dokumen MongoDB:

```json
{
  "user_id": 1,
  "action": "view_course",
  "target_type": "course",
  "target_id": 5,
  "metadata": {
    "course_name": "Python Basics",
    "ip_address": "192.168.1.1"
  },
  "timestamp": "2025-02-10T14:30:00Z"
}
```

### 3.8 Async Tasks (Celery + RabbitMQ)

| Task | Jenis | Deskripsi |
|---|---|---|
| Email notifikasi enrollment | Async | Kirim email konfirmasi saat user enroll ke course |
| Report generation | Async | Generate laporan course statistics di background |
| Daily stats | Periodic | Task harian menghitung statistik (total users, courses, enrollments) |

- Semua task harus memiliki error handling dan retry mechanism

## 4. Non-Functional Requirements

### 4.1 Containerization

- Seluruh sistem bisa dijalankan dengan `docker compose up --build`
- Environment variables dikonfigurasi melalui file `.env`
- Data persisten menggunakan Docker volumes

### 4.2 API Documentation

- OpenAPI/Swagger accessible di `/api/v1/docs`
- Setiap endpoint memiliki deskripsi, request/response schema, dan contoh

### 4.3 Testing

- Minimal 80% test coverage
- Unit tests untuk model dan business logic
- Integration tests untuk API endpoint
- Dijalankan dengan:

```bash
docker compose exec django pytest --cov
```

### 4.4 Performance

- Response time endpoint biasa: < 500ms
- Response time cached endpoint: < 50ms

### 4.5 Security

- JWT authentication pada semua protected endpoint
- Authorization checks pada setiap operasi yang membutuhkan permission
- Tidak ada sensitive data (password, token) terekspos di response
- Input validation pada semua endpoint yang menerima data

## 5. Milestone Breakdown

Proyek dikerjakan selama dua minggu sebelum UAS.

### 5.1 Timeline

| Milestone | Minggu | Deliverable | Bobot |
|---|---|---|---|
| M1: Setup & Models | Minggu 14 (hari 1-2) | Docker Compose + Django models + migrations | 10% |
| M2: REST API | Minggu 14 (hari 3-4) | CRUD endpoints + schemas + error handling | 20% |
| M3: Auth & Authorization | Minggu 14 (hari 5-7) | JWT + RBAC + protected endpoints | 15% |
| M4: Advanced Features | Minggu 15 (hari 1-2) | Filtering + sorting + pagination + file upload | 10% |
| M5: NoSQL Integration | Minggu 15 (hari 3-4) | Redis caching + MongoDB analytics | 15% |
| M6: Async Tasks | Minggu 15 (hari 5) | Celery + RabbitMQ + email notification | 10% |
| M7: Testing & Docs | Minggu 15 (hari 6-7) | Unit + integration tests + API docs + README | 10% |
| M8: Presentation | Minggu 15 | Demo langsung + Q&A session | 10% |

### 5.2 Milestone Detail

- **M1**: Buat `docker-compose.yml` dengan semua services. Pastikan semua services berjalan dan bisa berkomunikasi. Definisikan models (`Course`, `CourseMember`, `CourseContent`, `Comment`). Jalankan migrations.
- **M2**: Implementasikan seluruh CRUD endpoint menggunakan Django Ninja. Definisikan request/response schemas. Implementasikan error handling konsisten.
- **M3**: Implementasikan registrasi, login (JWT), dan token refresh. Terapkan authorization checks (owner only, enrolled only, admin only).
- **M4**: Tambahkan filtering, sorting, dan pagination pada list endpoints. Implementasikan file upload untuk course content attachment.
- **M5**: Konfigurasi Redis caching dan cache invalidation. Konfigurasi MongoDB connection, activity logging, dan analytics endpoints.
- **M6**: Konfigurasi Celery dengan RabbitMQ. Implementasikan async email notification, report generation, dan periodic daily stats task.
- **M7**: Tulis unit tests dan integration tests (coverage >= 80%). Lengkapi API documentation dan README.
- **M8**: Demo live dari `docker compose up`, tunjukkan seluruh fitur dan kemampuan menjawab Q&A.

## 6. Kriteria Penilaian

### 6.1 Bobot Penilaian

| Komponen | Bobot | Deskripsi |
|---|---|---|
| Functionality | 20% | Kelengkapan dan kebenaran fitur |
| Code Quality | 5% | Struktur kode, penamaan, konsistensi, best practices |
| Documentation | 5% | API docs, README, dan komentar kode |
| Presentation | 5% | Demo, penjelasan arsitektur, kemampuan menjawab Q&A |

### 6.2 Rubrik Penilaian Detail

| Kriteria | Excellent (90-100) | Good (80-89) | Satisfactory (70-79) | Needs Improvement (<70) |
|---|---|---|---|---|
| Functionality | Semua fitur berfungsi sempurna, tidak ada bug | Fitur utama berfungsi, minor bugs | Beberapa fitur belum lengkap, core features berfungsi | Banyak fitur tidak berfungsi, major bugs |
| Code Quality | Kode bersih, terstruktur rapi, best practices | Struktur baik, minor issues penamaan/organisasi | Kualitas cukup, ada inkonsistensi | Organisasi buruk, banyak code smell |
| Documentation | API docs lengkap, README komprehensif | Dokumentasi baik, beberapa bagian kurang detail | Dokumentasi dasar ada, banyak bagian kosong | Dokumentasi sangat minim atau tidak ada |
| Testing | Coverage > 90%, semua pass, edge cases |
| Architecture | Semua komponen terintegrasi sempurna | Sebagian besar terintegrasi, minor issues | Integrasi parsial | Integrasi buruk |

### 6.3 Penilaian Presentasi

Aspek penilaian:

- Demo: sistem berjalan dari `docker compose up`, semua fitur didemonstrasikan
- Penjelasan Arsitektur: mampu jelaskan peran setiap komponen dan alur data
- Q&A: mampu jawab pertanyaan teknis implementasi dan keputusan desain
- Waktu: presentasi selesai dalam 15-20 menit per kelompok

### 6.4 Checklist Self-Assessment

#### Infrastructure & Setup

- Docker Compose berjalan dengan semua services
- Semua services bisa berkomunikasi satu sama lain
- Environment variables dikonfigurasi melalui `.env`
- Migrasi database berjalan otomatis saat startup

#### API Endpoints

- Semua CRUD endpoint untuk courses berfungsi
- CRUD endpoint untuk contents berfungsi
- CRUD endpoint untuk comments berfungsi
- Endpoint enrollment berfungsi
- Endpoint analytics berfungsi
- File upload berfungsi

#### Authentication & Authorization

- JWT authentication aktif pada semua protected endpoints
- Registrasi dan login berfungsi
- Token refresh berfungsi
- Authorization checks benar
- Tidak ada sensitive data terekspos di response

#### Advanced Features

- Filtering pada list courses berfungsi
- Sorting berfungsi
- Pagination berfungsi

#### Redis Caching

- Cache aktif pada `GET /api/v1/courses`
- Cache aktif pada `GET /api/v1/courses/{id}`
- Cache invalidation berfungsi
- Session management menggunakan Redis

#### MongoDB Analytics

- Activity logging berfungsi
- Endpoint popular courses menampilkan data
- Endpoint user activity menampilkan ringkasan aktivitas

#### Celery Async Tasks

- Email notification async terkirim saat enrollment
- Report generation berjalan background
- Periodic daily stats task berjalan otomatis

#### Testing & Documentation

- Test coverage >= 80%
- Semua test pass
- API docs accessible di `/api/v1/docs`
- README lengkap dengan instruksi setup
- `.gitignore` sudah dikonfigurasi benar

## 7. Panduan Submission

### 7.1 Format Submission

- Platform: Git repository (GitHub atau GitLab)
- Branch: `main` atau `master`
- Deadline: sebelum jadwal UAS
- Akses: repository harus bisa diakses oleh dosen (public atau invite collaborator)

### 7.2 Yang Harus Ada di Repository

- Source code lengkap aplikasi Django
- `docker-compose.yml`
- `Dockerfile`
- `README.md`
- Dokumentasi API (`/api/v1/docs`)
- Test files
- `.env.example`
- `.gitignore`

### 7.3 Yang Tidak Boleh Ada di Repository

- File `.env` dengan secrets
- Folder `venv/` atau virtual environment
- Folder `__pycache__/` dan file `.pyc`
- File database SQLite (`db.sqlite3`)
- File media upload besar

## 8. Contoh Struktur Proyek

```
simple-lms/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── .gitignore
├── .env.example
├── code/
│   ├── manage.py
│   ├── requirements.txt
│   ├── lms/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── core/
│   │   │   ├── models.py
│   │   │   ├── api.py
│   │   │   ├── schemas.py
│   │   │   ├── services.py
│   │   │   ├── tasks.py
│   │   │   ├── cache.py
│   │   │   └── tests/
│   │   └── analytics/
│   │       ├── mongo_service.py
│   │       ├── api.py
│   │       └── tests/
│   └── fixtures/
└── conf/
    └── nginx.conf
```

## 9. Contoh `docker-compose.yml`

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - '80:80'
    volumes:
      - ./conf/nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/app/static
      - media_volume:/app/media
    depends_on:
      - django
    restart: unless-stopped

  django:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn lms.wsgi:application --bind 0.0.0.0:8000 --workers 3"
    volumes:
      - ./code:/app
      - static_volume:/app/static
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - mongodb
      - rabbitmq
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-lms_db}
      POSTGRES_USER: ${POSTGRES_USER:-lms_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-lms_password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - '5432:5432'
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - '6379:6379'
    restart: unless-stopped

  mongodb:
    image: mongo:7
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-mongo_user}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-mongo_password}
      MONGO_INITDB_DATABASE: ${MONGO_DB:-lms_analytics}
    volumes:
      - mongo_data:/data/db
    ports:
      - '27017:27017'
    restart: unless-stopped

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-rabbit_user}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-rabbit_password}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - '5672:5672'
      - '15672:15672'
    restart: unless-stopped

  celery_worker:
    build: .
    command: celery -A lms worker --loglevel=info --concurrency=2
    volumes:
      - ./code:/app
    env_file:
      - .env
    depends_on:
      - django
      - rabbitmq
      - redis
    restart: unless-stopped

  celery_beat:
    build: .
    command: celery -A lms beat --loglevel=info
    volumes:
      - ./code:/app
    env_file:
      - .env
    depends_on:
      - django
      - rabbitmq
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  mongo_data:
  rabbitmq_data:
  static_volume:
  media_volume:
```

## 10. Contoh `.env.example`

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
POSTGRES_DB=lms_db
POSTGRES_USER=lms_user
POSTGRES_PASSWORD=lms_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_REDIS_URL=redis://redis:6379/1
SESSION_REDIS_URL=redis://redis:6379/2

# MongoDB
MONGO_USER=mongo_user
MONGO_PASSWORD=mongo_password
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DB=lms_analytics

# RabbitMQ / Celery
CELERY_BROKER_URL=amqp://rabbit_user:rabbit_password@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/3

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## 11. Tips dan Best Practices

- Mulai lebih awal, jangan menunda.
- Ikuti milestone secara berurutan.
- Test saat development.
- Commit sering dengan pesan deskriptif.
- Gunakan Docker logs untuk debugging.
- Manfaatkan OpenAPI docs untuk testing.
- Jalankan fresh test sebelum submission.
- Minta peer review bila memungkinkan.

## 12. Referensi

- Django Documentation
- Django Ninja Documentation
- Celery Documentation
- Docker Documentation
- PostgreSQL Documentation
- Redis Documentation
- MongoDB Documentation
- RabbitMQ Documentation
- pytest Documentation
