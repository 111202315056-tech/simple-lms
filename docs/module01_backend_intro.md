# Modul 1: Pengenalan Backend Development

## Learning Objectives

- Memahami peran backend dalam aplikasi web modern
- Menjelaskan arsitektur client-server dan request-response cycle
- Memahami konsep HTTP dan REST API
- Mengenal tech stack yang digunakan: Django, Docker, PostgreSQL
- Menyiapkan development environment dengan Docker

## 1. Pengantar Backend Development

Backend development adalah pengembangan bagian server-side dari aplikasi. Backend bertanggung jawab untuk:

- Memproses HTTP request dari client
- Menjalankan logika bisnis
- Mengakses dan memanipulasi data pada database
- Mengelola authentication dan authorization
- Menyediakan API layanan untuk client

Backend berinteraksi dengan client melalui pola request-response. Client dapat berupa browser, mobile app, atau service lain.

## 2. Frontend vs Backend vs Fullstack

- Frontend: antarmuka pengguna, UI/UX, HTML/CSS/JavaScript
- Backend: server logic, database, keamanan, API
- Fullstack: menguasai kedua sisi

## 3. Arsitektur Aplikasi Web

### 3.1 Model Client-Server

Client mengirim request ke server. Server memproses request, berinteraksi dengan database atau service lain, lalu mengembalikan response.

### 3.2 HTTP Protocol

HTTP adalah protokol komunikasi untuk client-server. Contoh request:

```http
POST /api/courses HTTP/1.1
Host: api.example.com
Content-Type: application/json
Authorization: Bearer token123

{
  "name": "Django for Beginners",
  "price": 100000
}
```

Contoh response:

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": 1,
  "name": "Django for Beginners",
  "price": 100000,
  "created_at": "2025-02-14T10:00:00Z"
}
```

### 3.3 HTTP Methods

- GET: ambil data
- POST: buat data baru
- PUT: update seluruh data
- PATCH: update sebagian data
- DELETE: hapus data

### 3.4 HTTP Status Codes

- 2xx: sukses
- 3xx: redirection
- 4xx: client error
- 5xx: server error

## 4. REST API Fundamentals

REST adalah gaya arsitektur web service yang:

- Stateles
- Memisahkan client dan server
- Mendukung caching
- Memiliki antarmuka uniform
- Dapat dibangun dalam layer

Contoh desain RESTful:

- `GET /api/courses`
- `GET /api/courses/1`
- `POST /api/courses`
- `PUT /api/courses/1`
- `DELETE /api/courses/1`

Hindari URL dengan kata kerja, seperti `/api/getCourses` atau `/api/createCourse`.

## 5. Tech Stack Simple LMS

Teknologi yang digunakan dalam proyek Simple LMS:

- Python
- Django
- Django Ninja
- PostgreSQL
- Redis
- MongoDB
- Docker
- Docker Compose

### Mengapa stack ini?

- Python: mudah dipelajari dan populer
- Django: framework web lengkap dengan ORM dan admin
- Django Ninja: API modern dan type-safe
- PostgreSQL: database relasional kuat
- Redis: cache in-memory
- MongoDB: document store untuk data fleksibel
- Docker: environment konsisten dan portable

## 6. Containerization dan Docker

Docker memudahkan pengemasan aplikasi dan dependensi dalam container. Keuntungan Docker:

- Konsistensi lingkungan
- Isolasi aplikasi
- Portabilitas
- Efisiensi sumber daya

Perbedaan dengan VM:

- Container boot lebih cepat
- Container lebih ringan
- Container berbagi kernel OS

## 7. Setup Development Environment

### 7.1 Prasyarat

Pastikan sudah terinstall:

- Python 3.9+
- Git
- Docker Desktop
- VS Code (opsional)

### 7.2 Verifikasi Docker

```powershell
docker --version
docker-compose --version
docker run hello-world
```

### 7.3 Menjalankan Proyek Simple LMS

1. Masuk ke folder proyek:

```powershell
cd /d d:\simple-lms
```

2. Aktifkan virtual environment jika ada:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Jalankan service yang diperlukan:

```powershell
docker compose up -d db redis mongodb
```

4. Jalankan server Django:

```powershell
python manage.py runserver
```

5. Buka `http://127.0.0.1:8000` untuk melihat aplikasi atau `http://127.0.0.1:8000/docs` untuk dokumentasi API jika tersedia.

## 8. Studi Kasus Simple LMS

Simple LMS adalah aplikasi Learning Management System yang mencakup:

- Manajemen user
- Manajemen course
- Enrollment
- Content delivery
- Tracking progress
- Komentar dan diskusi

## 9. Quick Start Simple LMS

Jika Anda ingin mulai langsung dengan proyek:

```powershell
cd /d d:\simple-lms
docker compose up -d
docker compose exec web python manage.py migrate
```

## 10. Menjelajahi Kode Backend Simple LMS

Proyek Simple LMS telah menyediakan struktur backend dengan Django dan Django Ninja.

### 10.1 File penting

- `manage.py` — entry point untuk menjalankan server dan command Django
- `config/settings.py` — konfigurasi Django, database, cache, dan middleware
- `config/urls.py` — routing utama untuk aplikasi dan API
- `courses/apiv1.py` — definisi API endpoint menggunakan Django Ninja
- `courses/models.py` — definisi model database untuk course, user, enrollment, content, comment
- `courses/mongo.py` — helper MongoDB untuk analytics
- `courses/cache.py` — helper Redis untuk caching dan cache invalidation

### 10.2 Contoh request API

Beberapa endpoint yang sudah tersedia di Simple LMS:

- `POST /api/v1/auth/register` — registrasi user
- `POST /api/v1/auth/login` — login dan dapatkan JWT token
- `GET /api/v1/courses` — daftar course
- `GET /api/v1/courses/{id}` — detail course
- `POST /api/v1/enrollments` — daftar course (authenticated)
- `GET /api/v1/enrollments/my-courses` — lihat course yang diikuti
- `POST /api/v1/analytics/log/` — catat kegiatan user ke MongoDB
- `GET /api/v1/analytics/popular-courses/` — ambil course terpopuler
- `GET /api/v1/analytics/my-activity/` — ringkasan aktivitas user sendiri
- `GET /api/v1/analytics/daily-summary/` — ringkasan aktivitas harian

### 10.3 Contoh CURL

Login untuk mendapatkan token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo", "password":"demo123"}'
```

Mengambil daftar course:

```bash
curl http://127.0.0.1:8000/api/v1/courses
```

Mencatat aktivitas user:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analytics/log/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"action":"view_course", "course_name":"Django Basics"}'
```

## 11. Latihan Modul 1

1. Buat environment project dengan Docker Compose.
2. Jalankan server Django dan buka API docs di `http://127.0.0.1:8000/docs`.
3. Coba registrasi user via API dan login.
4. Coba ambil daftar course menggunakan endpoint `GET /api/v1/courses`.
5. Coba tambahkan endpoint baru di `courses/apiv1.py` untuk latihan.

## 12. Referensi

- Django Documentation
- Django Ninja Documentation
- Docker Documentation
- PostgreSQL Documentation
- MDN Web Docs - HTTP
- RESTful API Design
