# =========================================================
# Demo Script - Simple LMS Final Project
# Jalankan dari folder D:\simple-lms
# Cara pakai: powershell -ExecutionPolicy Bypass -File demo-simple-lms.ps1
# =========================================================

function Section($title) {
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Yellow
    Write-Host "=================================================================" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
}

function Pause-Demo($msg = "Tekan ENTER untuk lanjut ke langkah berikutnya...") {
    Write-Host ""
    Write-Host $msg -ForegroundColor Green
    Read-Host | Out-Null
}

# ---------------------------------------------------------
Section "0. START ALL SERVICES"
docker-compose up -d
Write-Host "Menunggu service siap..."
Start-Sleep -Seconds 10
docker-compose ps
Pause-Demo

# ---------------------------------------------------------
Section "1. BUKA DOKUMENTASI & MONITORING (Swagger, Silk, Flower)"
Start-Process "http://localhost:8000/api/v1/docs"
Start-Process "http://localhost:8000/silk/"
Start-Process "http://localhost:5555"
Write-Host "3 tab browser dibuka: Swagger UI, Silk Profiler, Flower."
Pause-Demo

# ---------------------------------------------------------
Section "2. AUTH: REGISTER USER BARU"
$registerBody = @{
    username   = "demo_student_$(Get-Random -Maximum 9999)"
    email      = "demo$(Get-Random -Maximum 9999)@mail.com"
    password   = "demopass123"
    first_name = "Demo"
    last_name  = "Student"
} | ConvertTo-Json

$registerResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
$registerResp | Format-List
$demoUsername = ($registerBody | ConvertFrom-Json).username
Pause-Demo

# ---------------------------------------------------------
Section "3. AUTH: LOGIN & DAPATKAN JWT TOKEN"
$loginBody = @{ username = $demoUsername; password = "demopass123" } | ConvertTo-Json
$loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
$token = $loginResp.access_token
$headers = @{ Authorization = "Bearer $token" }
Write-Host "Token diperoleh: $($token.Substring(0,40))..." -ForegroundColor Green
Pause-Demo

# ---------------------------------------------------------
Section "4. RBAC: STUDENT COBA BUAT COURSE (HARUS DITOLAK)"
$courseAttempt = @{ name = "Should Fail"; description = "test"; price = 1000 } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/courses" -Method Post -Body $courseAttempt -ContentType "application/json" -Headers $headers
} catch {
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Response   : $($_.ErrorDetails.Message)" -ForegroundColor Red
}
Pause-Demo

# ---------------------------------------------------------
Section "5. FILTERING, SORTING, PAGINATION"
$filtered = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/courses?search=Python&ordering=-price&page=1&per_page=5" -Headers $headers
$filtered | ConvertTo-Json -Depth 5
Pause-Demo

# ---------------------------------------------------------
Section "6. REDIS CACHE: CEK KEY SEBELUM"
Write-Host "Keys di Redis sebelum create course:"
docker exec redis_cache redis-cli KEYS "*course_list*"
Pause-Demo

Section "6b. REDIS CACHE INVALIDATION: LOGIN INSTRUCTOR & BUAT COURSE"
$loginInstr = @{ username = "dosen01"; password = "pass123" } | ConvertTo-Json
$instrResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -Body $loginInstr -ContentType "application/json"
$instrHeaders = @{ Authorization = "Bearer $($instrResp.access_token)" }

$newCourse = @{ name = "Demo Course $(Get-Random -Maximum 999)"; description = "Dibuat saat demo"; price = 25000 } | ConvertTo-Json
$createdCourse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/courses" -Method Post -Body $newCourse -ContentType "application/json" -Headers $instrHeaders
$createdCourse | Format-List

Write-Host "Keys di Redis SETELAH create course (harusnya kosong / berkurang):"
docker exec redis_cache redis-cli KEYS "*course_list*"
Pause-Demo

# ---------------------------------------------------------
Section "7. N+1 QUERY FIXING: BASELINE vs OPTIMIZED"
$baseline = Invoke-RestMethod -Uri "http://localhost:8000/lab/course-list/baseline/"
Write-Host "BASELINE  -> Queries: $($baseline.query_count) | Time: $($baseline.time_ms) ms" -ForegroundColor Red

$optimized = Invoke-RestMethod -Uri "http://localhost:8000/lab/course-list/optimized/"
Write-Host "OPTIMIZED -> Queries: $($optimized.query_count) | Time: $($optimized.time_ms) ms" -ForegroundColor Green
Write-Host ""
Write-Host "Lihat juga tab Silk Profiler di browser untuk detail query." -ForegroundColor Yellow
Pause-Demo

# ---------------------------------------------------------
Section "8. RESPONSE & ERROR FORMAT KONSISTEN"
Write-Host "Test 404:"
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/courses/99999" -Headers $headers
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__) | Body: $($_.ErrorDetails.Message)"
}

Write-Host ""
Write-Host "Test 401 (tanpa token):"
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/me"
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__) | Body: $($_.ErrorDetails.Message)"
}
Pause-Demo

# ---------------------------------------------------------
Section "9. MONGODB: ENROLL, VIEW LOG, POPULAR COURSES AGGREGATION"
$courseId = $createdCourse.id
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/courses/$courseId" -Headers $headers | Out-Null
try {
    $enroll = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/enrollments?course_id=$courseId" -Method Post -Headers $headers
    $enroll | Format-List
} catch {
    Write-Host "Enroll gagal/sudah terdaftar: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Popular Courses (dari MongoDB aggregation):"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/analytics/popular-courses" -Headers $headers | ConvertTo-Json
Pause-Demo

# ---------------------------------------------------------
Section "10. CELERY ASYNC: CEK LOG WORKER UNTUK EMAIL NOTIFICATION"
Write-Host "Lihat log celery-worker (task send_enrollment_email harus muncul SUCCESS):"
docker-compose logs celery-worker --tail=15
Write-Host ""
Write-Host "Cek juga dashboard Flower yang sudah terbuka di browser (tab ke-3)." -ForegroundColor Yellow
Pause-Demo

# ---------------------------------------------------------
Section "11. TESTING: JALANKAN FULL TEST SUITE + COVERAGE"
docker-compose exec web bash -c "coverage run --source=courses --omit=courses/lab_views.py,courses/tasks.py,courses/views.py manage.py test courses --settings=config.settings_test && coverage report"
Pause-Demo

# ---------------------------------------------------------
Section "12. CI/CD: BUKA GITHUB ACTIONS"
Start-Process "https://github.com/111202315056-tech/simple-lms/actions"
Write-Host "Tunjukkan riwayat run CI yang hijau/sukses."
Pause-Demo

# ---------------------------------------------------------
Section "13. DOKUMENTASI: BUKA README DI GITHUB"
Start-Process "https://github.com/111202315056-tech/simple-lms#readme"
Write-Host "Tunjukkan diagram arsitektur, cara menjalankan, akun demo."
Pause-Demo

# ---------------------------------------------------------
Section "DEMO SELESAI"
Write-Host "Semua fitur utama sudah didemokan:" -ForegroundColor Green
Write-Host "  1. Docker Compose (semua service)"
Write-Host "  2. Auth (register, login, JWT)"
Write-Host "  3. RBAC (403 untuk role tidak sesuai)"
Write-Host "  4. Filtering, sorting, pagination"
Write-Host "  5. Redis caching + cache invalidation"
Write-Host "  6. N+1 query fixing (Django Silk)"
Write-Host "  7. Response & error format konsisten"
Write-Host "  8. MongoDB activity log & aggregation"
Write-Host "  9. Celery async task + Flower monitoring"
Write-Host " 10. Testing + coverage report"
Write-Host " 11. CI/CD (GitHub Actions)"
Write-Host " 12. Dokumentasi (README + diagram)"
