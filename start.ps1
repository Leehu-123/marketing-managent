# Script khởi chạy ứng dụng Marketing Management trên Windows PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "   DAFA GLASS MARKETING MANAGEMENT - CHẠY APP TRÊN LOCAL (TESTING)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

$BackendDir = Join-Path $PSScriptRoot "backend"
Set-Location $BackendDir

# 1. Kiểm tra file .env
$EnvFile = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"

if (-not (Test-Path $EnvFile)) {
    Write-Host "[INFO] Chưa thấy file .env, đang khởi tạo từ .env.example..." -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
    Write-Host "[OK] Đã tạo file .env thành công." -ForegroundColor Green
}

# 2. Tìm lệnh Python
$CommonPyPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "C:\Python313\python.exe",
    "C:\Program Files\Python313\python.exe"
)

$PyCmdPath = $null
foreach ($path in $CommonPyPaths) {
    if (Test-Path $path) {
        $PyCmdPath = $path
        break
    }
}

if (-not $PyCmdPath) {
    $foundCmd = Get-Command py -ErrorAction SilentlyContinue
    if (-not $foundCmd) { $foundCmd = Get-Command python -ErrorAction SilentlyContinue }
    if ($foundCmd -and $foundCmd.Source -notlike "*WindowsApps*") {
        $PyCmdPath = $foundCmd.Source
    }
}

if (-not $PyCmdPath) {
    Write-Host "[ERROR] Không tìm thấy Python thực thi trên hệ thống!" -ForegroundColor Red
    Write-Host "Vui lòng tải và cài đặt Python từ https://www.python.org/" -ForegroundColor Red
    Read-Host "Nhấn Enter để thoát..."
    exit 1
}

$PyCmd = $PyCmdPath

Write-Host "[INFO] Đã tìm thấy Python tại: $PyCmd" -ForegroundColor Green

# 3. Tạo virtualenv nếu chưa có
$VenvDir = Join-Path $BackendDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "[INFO] Đang tạo môi trường ảo Python (venv)..." -ForegroundColor Yellow
    & $PyCmd -m venv $VenvDir
}

# 4. Kích hoạt venv
$ActivatePs1 = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivatePs1) {
    try {
        & $ActivatePs1
    } catch {
        $env:PATH = "$(Join-Path $VenvDir 'Scripts');$env:PATH"
    }
} else {
    $env:PATH = "$(Join-Path $VenvDir 'Scripts');$env:PATH"
}

# 5. Cài đặt thưa viện
Write-Host "[INFO] Đang cài đặt / cập nhật các gói thư viện Python..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host "  🚀 SERVER ĐÃ SẴN SÀNG CHẠY TẠI: http://localhost:8000" -ForegroundColor Green
Write-Host "  🔑 TÀI KHOẢN MẶC ĐỊNH: admin / dafa123" -ForegroundColor Green
Write-Host "  📌 Nhấn Ctrl+C để dừng server khi test xong." -ForegroundColor Yellow
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host ""

# Mở web browser
Start-Process "http://localhost:8000"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
