# Script hỗ trợ Deploy VPS bằng PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "   TỰ ĐỘNG DEPLOY MARKETING MANAGEMENT LÊN VPS (45.117.177.80)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

$PyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PyCmd) {
    $PyCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $PyCmd) {
    Write-Host "[ERROR] Không tìm thấy Python trên máy local." -ForegroundColor Red
    Write-Host "Vui lòng cài đặt Python hoặc chạy deploy.sh trực tiếp trên VPS qua SSH." -ForegroundColor Red
    Read-Host "Nhấn Enter để thoát..."
    exit 1
}

& $PyCmd.Path deploy_vps.py
