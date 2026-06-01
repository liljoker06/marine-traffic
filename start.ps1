# Script de lancement du projet Marine Traffic
# Prérequis : Docker en cours d'exécution

$projectPath = $PSScriptRoot

Write-Host ""
Write-Host "Marine Traffic — Lancement" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor DarkGray

# ── Docker (Kafka + Redis + Spark + AKHQ + Prometheus + Grafana) ──────────────
Write-Host ""
Write-Host "[1/4] Docker — Kafka, Redis, Spark, AKHQ, Prometheus, Grafana..." -ForegroundColor Yellow
Set-Location $projectPath
docker compose up -d
Write-Host "      AKHQ       : http://localhost:8090" -ForegroundColor DarkGray
Write-Host "      Prometheus : http://localhost:9090" -ForegroundColor DarkGray
Write-Host "      Grafana    : http://localhost:3000  (admin/admin)" -ForegroundColor DarkGray
Start-Sleep -Seconds 5

# ── Tailwind CSS ───────────────────────────────────────────────────────────────
Write-Host "[2/4] Tailwind CSS (watch mode)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$projectPath'; `
    .\venv\Scripts\Activate.ps1; `
    Write-Host '>>> Tailwind watch' -ForegroundColor Yellow; `
    python manage.py tailwind start"

Start-Sleep -Seconds 2

# ── Django ASGI via Daphne (HTTP + WebSocket + static files) ──────────────────
Write-Host "[3/4] Django (migrate + daphne)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$projectPath'; `
    .\venv\Scripts\Activate.ps1; `
    python manage.py migrate; `
    python manage.py load_ports --if-empty; `
    Write-Host '>>> Daphne ASGI http://127.0.0.1:8000' -ForegroundColor Green; `
    daphne -b 127.0.0.1 -p 8000 marine_traffic.asgi:application"

Start-Sleep -Seconds 4

# ── Producteur AIS  (aisstream.io → Kafka ais-raw) ────────────────────────────
Write-Host "[4/4] Producteur AIS + Consumer Kafka..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$projectPath'; `
    .\venv\Scripts\Activate.ps1; `
    Write-Host '>>> Producer : aisstream.io -> ais-raw' -ForegroundColor Magenta; `
    python manage.py produce_ais"

Start-Sleep -Seconds 2

# ── Consumer Kafka  (ais-positions → DB → WebSocket) ─────────────────────────
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$projectPath'; `
    .\venv\Scripts\Activate.ps1; `
    Write-Host '>>> Consumer : ais-positions -> DB + WebSocket' -ForegroundColor Blue; `
    python manage.py consume_ais"

# ── Résumé ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "==========================================" -ForegroundColor DarkGray
Write-Host "Tout est lance !" -ForegroundColor Cyan
Write-Host ""
Write-Host "  App         : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  AKHQ        : http://localhost:8090" -ForegroundColor White
Write-Host "  Prometheus  : http://localhost:9090" -ForegroundColor White
Write-Host "  Grafana     : http://localhost:3000  (admin/admin)" -ForegroundColor White
Write-Host ""
Write-Host "  Pipeline AIS :" -ForegroundColor DarkGray
Write-Host "  aisstream.io -> ais-raw -> [Spark Docker] -> ais-positions -> DB -> WebSocket" -ForegroundColor DarkGray
Write-Host ""
