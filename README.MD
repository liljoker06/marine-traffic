# 🚢 Marine Traffic — Suivi maritime en temps réel

> Plateforme de visualisation du trafic maritime mondial en temps réel : positions AIS live, carte interactive, détection de congestion.

---

## 🏗️ Stack technique

| Composant         | Technologie                                      |
|-------------------|--------------------------------------------------|
| Backend           | Django 6 + Django Channels (ASGI/WebSocket)      |
| Frontend          | Tailwind CSS v4 + Alpine.js + Leaflet.js 1.9     |
| Cartographie      | Canvas Layer custom (rendu type MarineTraffic)   |
| Base de données   | PostgreSQL                                       |
| Message broker    | Apache Kafka (KRaft, confluentinc/cp-kafka:7.6)  |
| Stream processing | Apache Spark Structured Streaming (PySpark 3.5) |
| WebSocket         | Redis + Django Channels channel layer            |
| Source AIS        | aisstream.io (WebSocket, mondial)                |
| Photos navires    | DuckDuckGo Images JSON                           |
| Info ports        | Wikipedia REST API (proxy Django)                |
| Métriques         | Prometheus + django-prometheus                   |
| Dashboards        | Grafana (PostgreSQL + Prometheus)                |
| Conteneurisation  | Docker Compose                                   |
| Kafka UI          | AKHQ (localhost:8090)                            |

---

## 📂 Structure du projet

```
marine traffic/
├── core/
│   ├── management/commands/
│   │   ├── produce_ais.py        ← aisstream.io → Kafka ais-raw
│   │   ├── consume_ais.py        ← Kafka ais-positions → DB + WebSocket
│   │   └── load_ports.py         ← import CSV ports mondiaux
│   ├── static/js/map/
│   │   ├── ship-layer.js         ← canvas custom (flèches navires)
│   │   ├── port-layer.js         ← marqueurs ports
│   │   ├── websocket.js          ← connexion WebSocket AIS
│   │   ├── panels.js             ← composants Alpine (panneau gauche/droit)
│   │   ├── api.js                ← appels HTTP (ports, navires, wiki, photos)
│   │   ├── cache.js              ← cache localStorage ports
│   │   └── init.js               ← initialisation carte Leaflet
│   ├── models.py                 ← Ship, ShipPosition, Port
│   ├── consumers.py              ← ShipConsumer (WebSocket Django Channels)
│   └── views.py                  ← API REST + proxies Wikipedia/DDG photos
├── marine_traffic/
│   ├── asgi.py                   ← routing HTTP + WebSocket
│   └── settings.py
├── monitoring/
│   ├── prometheus.yml            ← config scrape Django + Redis
│   └── grafana/provisioning/
│       └── datasources/
│           └── datasources.yml   ← auto-provision Prometheus + PostgreSQL
├── theme/templates/
│   ├── base.html
│   ├── components/
│   │   ├── navbar.html
│   │   ├── map_panel_left.html   ← panneau paramètres + recherche port
│   │   └── map_panel_right.html  ← détail port (Wikipedia) + navire (AIS + photo)
│   └── core/map.html             ← page carte
├── spark_processor.py            ← PySpark : ais-raw → filtre → ais-positions
├── Dockerfile.spark              ← image Spark Linux (eclipse-temurin:17)
├── docker-compose.yml            ← Kafka, Redis, Spark, AKHQ, Prometheus, Grafana
├── requirements.txt
└── start.ps1                     ← script de lancement Windows
```

---

## ⚡ Installation

### Prérequis

- Python 3.11+
- PostgreSQL (en local)
- Docker Desktop (en cours d'exécution)
- Node.js (pour Tailwind)

### 1. Cloner et créer l'environnement virtuel

```powershell
git clone https://github.com/votre-org/marine-traffic.git
cd "marine traffic"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurer la base de données

Créer la base PostgreSQL :

```powershell
psql -U postgres -c "CREATE DATABASE marine_traffic;"
```

Créer un fichier `.env` à la racine du projet :

```env
SECRET_KEY=django-insecure-change-me
DEBUG=True

DB_NAME=marine_traffic
DB_USER=postgres
DB_PASSWORD=ton_mot_de_passe
DB_HOST=localhost
DB_PORT=5432

AISSTREAM_API_KEY=ta_clé_aisstream
```

### 3. Installer Tailwind

```powershell
python manage.py tailwind install
```

### 4. Lancer le projet

```powershell
.\start.ps1
```

Le script démarre automatiquement dans l'ordre :

| Étape | Service | Description |
|-------|---------|-------------|
| 1 | Docker | Kafka + Redis + Spark + AKHQ + Prometheus + Grafana |
| 2 | Tailwind | Compilation CSS en watch mode |
| 3 | Daphne | migrate + load_ports + serveur ASGI (HTTP + WebSocket) |
| 4 | Producer AIS | aisstream.io → Kafka `ais-raw` |
| 5 | Consumer Kafka | `ais-positions` → DB + WebSocket |

> Spark (dans Docker) lit `ais-raw`, filtre/enrichit, écrit dans `ais-positions`.  
> `daphne` est requis à la place de `runserver` pour les WebSockets avec Channels v4.

---

## 🌐 URLs

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000` | Application |
| `http://127.0.0.1:8000/map/` | Carte AIS temps réel |
| `http://127.0.0.1:8000/ports/` | Liste des ports mondiaux |
| `http://127.0.0.1:8000/admin/` | Interface d'administration |
| `http://127.0.0.1:8000/metrics` | Métriques Prometheus (Django) |
| `http://localhost:8090` | AKHQ — Kafka UI |
| `http://localhost:9090` | Prometheus |
| `http://localhost:3000` | Grafana (admin / admin) |

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/ports/?bbox=&zoom=` | Ports dans la bbox (filtrés par zoom) |
| `GET /api/ports/search/?q=` | Recherche de ports |
| `GET /api/ships/?bbox=` | Navires actifs dans la bbox (6h) |
| `GET /api/ships/<mmsi>/track/` | Route des 50 dernières positions |
| `GET /api/wikipedia/?term=&lang=` | Proxy Wikipedia (info + photo port) |
| `GET /api/ship-photo/?name=` | Photo navire via DuckDuckGo Images |
| `WS /ws/ships/` | WebSocket — positions AIS live |

---

## 🗺️ Pipeline AIS

```
aisstream.io (WebSocket mondial)
       │
       ▼
produce_ais  →  Kafka [ais-raw]
                       │
                       ▼
              Spark Docker
              (filtre coords/vitesse,
               enrichit type_category,
               déduplique 30s)
                       │
                       ▼
              Kafka [ais-positions]
                       │
                       ▼
              consume_ais
              (bulk DB + WebSocket broadcast /10s)
                       │
              ┌────────┴────────┐
              ▼                 ▼
          PostgreSQL         WebSocket
          (Ship,             → navigateurs
          ShipPosition)      → canvas Leaflet
```

---

## 📊 Monitoring (Grafana + Prometheus)

Grafana est disponible sur `http://localhost:3000` (admin / admin).  
Deux datasources sont provisionnées automatiquement au démarrage :

| Datasource | Usage |
|------------|-------|
| **Prometheus** | Métriques Django (requêtes, latence, erreurs), Redis |
| **PostgreSQL** | Requêtes directes sur les données AIS (navires, positions) |

Le Redis exporter expose les métriques Redis sur `:9121` et Prometheus scrape Django sur `/metrics`.

### Requêtes Prometheus utiles

**Trafic HTTP Django**
```promql
# Requêtes par seconde
rate(django_http_requests_total[1m])

# Latence moyenne
rate(django_http_request_duration_seconds_sum[1m]) / rate(django_http_request_duration_seconds_count[1m])

# Erreurs 4xx/5xx
rate(django_http_requests_total{status=~"4..|5.."}[1m])
```

**Base de données**
```promql
# Requêtes SQL par seconde
rate(django_db_execute_total[1m])
```

**Redis**
```promql
redis_connected_clients
redis_memory_used_bytes
rate(redis_commands_processed_total[1m])
rate(redis_keyspace_hits_total[1m])
rate(redis_keyspace_misses_total[1m])
```

**Endpoints AIS**
```promql
# Trafic sur l'API navires
rate(django_http_requests_total{view="ships_api"}[1m])
```

---

## 🖥️ Fonctionnalités carte

- **Navires** — flèches colorées par type (cargo vert, tanker rouge, passagers violet…) rendues sur canvas, zéro DOM par navire
- **Ports** — marqueurs par taille de port (grand/moyen/petit), filtrés par zoom
- **Panneau gauche** — recherche port, filtres navires (nom/type/statut), fond de carte, couches
- **Panneau droit** — détail port avec photo Wikipedia + info navire AIS + photo + route tracée
- **Congestion** — zones de densité calculées en temps réel
- **WebSocket** — positions mises à jour toutes les 10 secondes
- **Rechargement DB** — toutes les 2 minutes pour les nouveaux navires

---

## 📦 Commandes utiles

```powershell
# Migrations
python manage.py migrate

# Importer les ports (une seule fois)
python manage.py load_ports --if-empty

# Lancer uniquement le producteur AIS
python manage.py produce_ais

# Lancer uniquement le consumer
python manage.py consume_ais

# Rebuild Spark si besoin
docker compose build spark
docker compose up -d

# Vider le cache Redis
docker exec marinetraffic-redis-1 redis-cli FLUSHDB
```

---

## 📄 Licence

MIT License
