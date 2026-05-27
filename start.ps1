# Script de lancement du projet Marine Traffic
Write-Host "Lancement du projet Marine Traffic..." -ForegroundColor Cyan

# Lancer Tailwind dans un terminal séparé
Write-Host "Démarrage de Tailwind CSS..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd 'd:\Cours\marine traffic'; `
    .\venv\Scripts\Activate.ps1; `
    Write-Host 'Tailwind CSS - Watch mode' -ForegroundColor Yellow; `
    python manage.py tailwind start"

# Petit délai pour laisser Tailwind démarrer
Start-Sleep -Seconds 2

# Lancer Django dans un terminal séparé (import des ports au démarrage si table vide)
Write-Host "Démarrage du serveur Django..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd 'd:\Cours\marine traffic'; `
    .\venv\Scripts\Activate.ps1; `
    Write-Host 'Import des ports...' -ForegroundColor Yellow; `
    python manage.py load_ports --if-empty; `
    Write-Host 'Django Server' -ForegroundColor Green; `
    python manage.py runserver"

Write-Host "Projet lancé !" -ForegroundColor Cyan
Write-Host "Django  → http://127.0.0.1:8000" -ForegroundColor White
