Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Starting Simple LMS..." -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan

docker-compose up -d

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  Simple LMS sudah jalan!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API      : http://localhost:8000/api/v1" -ForegroundColor White
Write-Host "  Docs     : http://localhost:8000/api/v1/docs" -ForegroundColor White
Write-Host "  Flower   : http://localhost:5555" -ForegroundColor White
Write-Host "  RabbitMQ : http://localhost:15672" -ForegroundColor White
Write-Host ""
Write-Host "  Membuka browser..." -ForegroundColor Yellow
Start-Sleep 2
Start-Process "http://localhost:8000/api/v1/docs"
Write-Host "=========================================" -ForegroundColor Green
