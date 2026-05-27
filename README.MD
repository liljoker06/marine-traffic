# 🚢 Marine Traffic — Suivi maritime en temps réel

> Plateforme de visualisation et d'analyse du trafic maritime mondial basée sur Django, Kafka et Leaflet.js.

---

## 🏗️ Stack technique

| Composant        | Technologie                        |
|------------------|------------------------------------|
| Backend          | Django 6 + Django REST Framework   |
| Frontend         | Django Templates + Tailwind CSS v4 |
| Cartographie     | Leaflet.js + OpenStreetMap         |
| Base de données  | PostgreSQL                         |
| Streaming        | Apache Kafka                       |
| WebSocket        | Django Channels                    |
| Scheduler        | Celery Beat                        |
| Conteneurisation | Docker & Docker Compose            |
| Monitoring       | Prometheus + Grafana               |

---

## 📂 Structure du projet

```
marine traffic/
├── core/                  ← App principale (vues, modèles, URLs)
├── marine_traffic/        ← Configuration Django (settings, urls, wsgi)
├── theme/                 ← App Tailwind CSS
│   └── templates/
│       ├── base.html      ← Layout principal
│       ├── components/    ← Navbar, footer, etc.
│       └── core/          ← Pages de l'app
├── venv/                  ← Environnement virtuel (non versionné)
├── .env                   ← Variables d'environnement (non versionné)
├── .gitignore
├── manage.py
├── requirements.txt
└── start.ps1              ← Script de lancement (Windows)
```

---

## ⚡ Installation locale

### 1. Cloner le projet

```bash
git clone https://github.com/votre-org/marine-traffic.git
cd marine-traffic
```

### 2. Créer et activer l'environnement virtuel

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances Python

```powershell
pip install -r requirements.txt
```

### 4. Créer le fichier `.env`

Copier le fichier d'exemple et remplir les valeurs :

```powershell
copy .env.example .env
```

Contenu minimal du `.env` :

```env
SECRET_KEY=django-insecure-change-me-in-production
DEBUG=True

DB_NAME=marine_traffic
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Créer la base de données PostgreSQL

```powershell
psql -U postgres -c "CREATE DATABASE marine_traffic;"
```

### 6. Installer Tailwind CSS

```powershell
python manage.py tailwind install
```

### 7. Appliquer les migrations

```powershell
python manage.py migrate
```

### 8. Créer un superutilisateur

```powershell
python manage.py createsuperuser
```

### 9. Lancer le projet

```powershell
.\start.ps1
```

> Ce script ouvre automatiquement deux terminaux :
> - 🎨 **Tailwind** en mode watch (live reload CSS)
> - 🌐 **Django** sur http://127.0.0.1:8000

---

## 🌐 URLs disponibles

| URL            | Description              |
|----------------|--------------------------|
| `/`            | Page d'accueil           |
| `/map/`        | Carte maritime Leaflet   |
| `/ports/`      | Liste des ports mondiaux (filtres, pagination) |
| `/api/ports/`  | API JSON — données de tous les ports |
| `/admin/`      | Interface d'administration |
| `/__reload__/` | Live reload (dev)        |

---

## 📦 Générer le fichier requirements.txt

```powershell
pip freeze > requirements.txt
```

---

## 🧪 Lancer les tests

```powershell
python manage.py test
```

---

## 🏗️ Architecture temps réel (cible)

```
  API AIS externe
       │
       ▼
  Django Producer
  (collecte toutes les minutes)
       │
       ▼
  Apache Kafka
  Topic: ships.positions
       │
  ┌────┴────┐
  ▼         ▼
Consumer   Consumer
Analyse    Tracking
Congestion Temps réel
  │              │
  ▼              ▼
PostgreSQL   WebSocket
             (Django Channels)
                  │
                  ▼
            Frontend
            (Carte Leaflet live)
```

---

## 👨‍💻 Équipe projet

| Rôle              | Mission                          |
|-------------------|----------------------------------|
| Backend Engineer  | APIs Django + modèles            |
| Data Engineer     | Kafka + pipeline streaming       |
| DevOps            | Docker + monitoring              |
| Frontend Engineer | Templates + Tailwind + Leaflet   |
| Data Analyst      | Analyse et détection d'anomalies |

---

## 📚 Ressources

- [Django](https://www.djangoproject.com/)
- [Tailwind CSS v4](https://tailwindcss.com/)
- [Leaflet.js](https://leafletjs.com/)
- [OpenStreetMap](https://www.openstreetmap.org/)
- [Apache Kafka](https://kafka.apache.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [MarineTraffic API](https://servicedocs.marinetraffic.com/)

---

## 📄 Licence

MIT License
