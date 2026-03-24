🎓 Simple LMS - Docker & Django

📦 Deskripsi

Project **Simple LMS (Learning Management System)** ini dibuat menggunakan **Django** dan **PostgreSQL** dengan pendekatan **containerization menggunakan Docker**.

Project ini bertujuan untuk memahami:

* Konsep Docker & container
* Multi-container dengan Docker Compose
* Integrasi Django dengan PostgreSQL
* Setup backend modern yang portable

🛠️ Teknologi yang Digunakan

* Python 3.11
* Django
* PostgreSQL
* Docker & Docker Compose



 📁 Struktur Project


simple-lms/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── README.md
 ⚙️ Environment Variables

Buat file `.env` berdasarkan `.env.example`

Contoh:


DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=postgres_db
DB_PORT=5432
 🐳 Docker Services

Project ini menggunakan 2 service utama:

1. Web (Django)

* Menjalankan aplikasi Django
* Port: `8000`

### 2. Database (PostgreSQL)

* Menyimpan data aplikasi
* Menggunakan volume agar data persistent


 🚀 Cara Menjalankan Project
 1. Clone Repository


git clone https://github.com/USERNAME/simple-lms.git
cd simple-lms
 2. Buat File Environment


cp .env.example .env


(Atau buat manual jika di Windows)

 3. Jalankan Docker

docker-compose up --build


4. Jalankan Migration

Buka terminal baru:


docker-compose run web python manage.py migrate


 5. Buat Superuser

docker-compose run web python manage.py createsuperuser
🌐 Akses Aplikasi

* Homepage Django:
  http://localhost:8000

* Admin Panel:
  http://localhost:8000/admin


📸 Screenshot

 Halaman Django

![Django](screenshot.png)

### Admin Panel (Opsional)

![Admin](admin.png)

✅ Fitur yang Berhasil Dibuat

* Docker multi-container (web + database)
* Django berjalan di container
* PostgreSQL terintegrasi
* Migration database berhasil
* Admin panel aktif

🎯 Hasil Pembelajaran

Dari project ini, saya memahami:

* Cara membuat Dockerfile dan docker-compose
* Cara menjalankan aplikasi Django di Docker
* Konfigurasi PostgreSQL dalam container
* Penggunaan environment variables
* Best practice struktur project backend

 👤 Author

Aldi Febriayanto
NIM: A11.2023.15056

 📌 Catatan

* Pastikan Docker Desktop sudah berjalan sebelum menjalankan project
* Gunakan `.env` untuk konfigurasi environment
* Data PostgreSQL disimpan menggunakan Docker Volume

🏁 Status

 Project selesai dan siap dijalankan
 Sesuai dengan kriteria penilaian tugas
