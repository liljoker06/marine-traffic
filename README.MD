# 🚢 Suivi du trafic maritime en temps réel — Django + Kafka

## 📌 Présentation du projet

Cette application permet de suivre le trafic maritime en temps réel à partir d’une API de données AIS (Automatic Identification System).

Le système collecte les positions des navires commerciaux en continu, diffuse les événements via Apache Kafka, puis traite les flux pour détecter les ralentissements, suivre des navires spécifiques et afficher les mouvements sur une carte interactive.

Le projet est construit autour de :

* Backend : Django + Django REST Framework
* Streaming : Apache Kafka
* Traitement temps réel : Kafka Consumers
* Base de données : PostgreSQL + PostGIS
* Frontend : Django Templates ou React (optionnel)
* Cartographie : Leaflet.js / OpenStreetMap
* Conteneurisation : Docker & Docker Compose

---

# 🎯 Objectifs du projet

## Fonctionnalités principales

### ✅ Collecte temps réel

* Récupération des données AIS via une API externe
* Synchronisation automatique toutes les minutes
* Gestion des erreurs réseau et des quotas API

### ✅ Streaming Kafka

* Publication des positions des navires dans Kafka
* Architecture orientée événements
* Découplage entre ingestion et traitement

### ✅ Analyse du trafic maritime

* Détection des ralentissements
* Détection des zones de congestion
* Suivi d’un navire spécifique
* Analyse régionale ou mondiale

### ✅ Visualisation

* Carte interactive en temps réel
* Filtres :

  * Nom du navire
  * Type
  * Pays
  * Zone géographique
* Affichage des trajectoires
* Heatmap de densité maritime

---

# 🏗️ Architecture du projet

```text
                    +-------------------+
                    | API Maritime AIS |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Django Producer   |
                    | (Collecte API)    |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Apache Kafka      |
                    | Topic: ships      |
                    +---------+---------+
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
+--------------------------+     +--------------------------+
| Consumer Analyse         |     | Consumer Tracking        |
| Congestion / anomalies   |     | Suivi temps réel         |
+-------------+------------+     +-------------+------------+
              |                                |
              v                                v
       +-------------+                 +---------------+
       | PostgreSQL  |                 | WebSocket API |
       | + PostGIS   |                 +-------+-------+
       +------+------+                         |
              |                                v
              +----------------------> Frontend
                                      (Carte live)
```

---

# ⚙️ Stack technique

| Composant             | Technologie           |
| --------------------- | --------------------- |
| Backend API           | Django                |
| API REST              | Django REST Framework |
| Streaming             | Apache Kafka          |
| Broker Kafka          | Confluent / Bitnami   |
| Base de données       | PostgreSQL            |
| Données géographiques | PostGIS               |
| Scheduler             | Celery Beat / Cron    |
| WebSocket             | Django Channels       |
| Cartographie          | Leaflet.js            |
| Conteneurisation      | Docker                |
| Monitoring            | Prometheus + Grafana  |

---

# 📂 Structure du projet

```text
maritime-tracking/
│
├── backend/
│   ├── config/
│   ├── ships/
│   ├── tracking/
│   ├── analytics/
│   ├── consumers/
│   ├── producers/
│   ├── websocket/
│   └── manage.py
│
├── frontend/
│   ├── templates/
│   ├── static/
│   └── map/
│
├── kafka/
│   ├── producer.py
│   ├── consumer.py
│   └── topics/
│
├── docker/
│
├── docker-compose.yml
│
├── requirements.txt
│
└── README.md
```

---

# 🌍 API maritime utilisée

Plusieurs APIs peuvent être utilisées.

## Option 1 — MarineTraffic

👉 API professionnelle AIS.

Fonctionnalités :

* Position temps réel
* Type des navires
* Vitesse
* Destination
* Historique des trajets

Documentation :

* [https://servicedocs.marinetraffic.com/](https://servicedocs.marinetraffic.com/)

## Option 2 — OpenAIS

👉 Alternative open-source ou gratuite selon disponibilité.

* [https://open-ais.org/](https://open-ais.org/)

---

# 🔄 Pipeline temps réel

## Étape 1 — Collecte des données

Le producer Django interroge l’API toutes les minutes.

Exemple de payload AIS :

```json
{
  "mmsi": "235009271",
  "ship_name": "EVER GIVEN",
  "latitude": 48.8566,
  "longitude": 2.3522,
  "speed": 14.5,
  "course": 120,
  "country": "Panama",
  "timestamp": "2026-05-27T10:00:00Z"
}
```

---

## Étape 2 — Publication Kafka

Les données sont publiées dans le topic :

```text
ships.positions
```

Exemple de producer Kafka :

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('ships.positions', payload)
```

---

## Étape 3 — Traitement temps réel

Les consumers Kafka permettent de :

### 🚨 Détection de congestion

Détection automatique si plusieurs navires :

* restent dans une même zone
* avancent à vitesse réduite
* provoquent un embouteillage maritime

### 🚢 Suivi d’un navire

Suivi par :

* MMSI
* Nom
* IMO

### 📊 Détection d’anomalies

Exemples :

* Arrêt inhabituel
* Changement brutal de trajectoire
* Sortie de route commerciale
* Retard important

---

# 🗺️ Visualisation cartographique

## Carte interactive

Utilisation de :

* Leaflet.js
* OpenStreetMap

Fonctionnalités :

* Affichage temps réel
* Zoom régional / mondial
* Clustering des navires
* Heatmap de trafic
* Trajectoires dynamiques

---

# 🔌 WebSocket temps réel

Les mises à jour sont poussées au frontend avec Django Channels.

Exemple :

```python
class ShipConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def ship_update(self, event):
        await self.send(text_data=json.dumps(event))
```

---

# 🐳 Déploiement Docker

## Lancer le projet

```bash
docker-compose up --build
```

---

# 📦 Services Docker

| Service    | Port |
| ---------- | ---- |
| Django     | 8000 |
| PostgreSQL | 5432 |
| Kafka      | 9092 |
| Zookeeper  | 2181 |
| Grafana    | 3000 |
| Prometheus | 9090 |

---

# 🧠 Détection de congestion

## Exemple de logique métier

Un ralentissement est détecté si :

```text
- plus de 10 navires
- dans un rayon de 5 km
- vitesse moyenne < 3 noeuds
```

---

# 📊 Monitoring

Le système peut intégrer :

## Prometheus

Collecte des métriques :

* nombre de navires
* latence Kafka
* erreurs API
* fréquence des événements

## Grafana

Dashboards :

* trafic mondial
* densité maritime
* alertes congestion
* activité par zone

---

# 🔐 Sécurité

## Recommandations

* Variables d’environnement (.env)
* Rotation des clés API
* Auth JWT
* Rate limiting
* HTTPS
* Validation des données AIS

---

# 🚀 Installation locale

## 1. Cloner le projet

```bash
git clone https://github.com/votre-org/maritime-tracking.git
cd maritime-tracking
```

---

## 2. Créer le fichier .env

```env
DEBUG=True
SECRET_KEY=your_secret_key
POSTGRES_DB=maritime
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
MARINE_API_KEY=your_api_key
```

---

## 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## 4. Lancer les migrations

```bash
python manage.py migrate
```

---

## 5. Lancer le serveur

```bash
python manage.py runserver
```

---

# 📜 Exemple requirements.txt

```txt
Django
 djangorestframework
psycopg2-binary
kafka-python
channels
channels-redis
celery
redis
requests
geopy
shapely
python-dotenv
```

---

# 🧪 Tests

## Lancer les tests

```bash
pytest
```

---

# 📈 Évolutions possibles

## Intelligence artificielle

* Prévision des retards
* Détection comportementale
* Prévision de congestion
* Classification des anomalies

## Big Data

* Apache Spark Streaming
* Flink
* Data Lake

## Notifications

* Alertes Slack
* Email
* SMS
* Discord

---

# 👨‍💻 Équipe projet

| Rôle              | Mission                 |
| ----------------- | ----------------------- |
| Backend Engineer  | APIs Django             |
| Data Engineer     | Kafka + Streaming       |
| DevOps            | Docker + Monitoring     |
| Frontend Engineer | Cartographie temps réel |
| Data Analyst      | Analyse maritime        |

---

# 📚 Ressources utiles

## Kafka

* [https://kafka.apache.org/](https://kafka.apache.org/)

## Django

* [https://www.djangoproject.com/](https://www.djangoproject.com/)

## Django Channels

* [https://channels.readthedocs.io/](https://channels.readthedocs.io/)

## Leaflet

* [https://leafletjs.com/](https://leafletjs.com/)

## PostGIS

* [https://postgis.net/](https://postgis.net/)

---

# ✅ Résultat attendu

L’application permettra :

* d’observer le trafic maritime mondial en direct
* de détecter automatiquement les congestions
* de suivre des navires spécifiques
* d’analyser les flux maritimes
* d’avoir une plateforme scalable temps réel basée sur Kafka

---

# 🛳️ Exemple de cas d’usage

## Cas réel

Un port européen souhaite :

* anticiper les retards
* surveiller l’arrivée des cargos
* détecter les bouchons maritimes
* optimiser les opérations logistiques

Le système fournit alors :

* une carte live
* des alertes congestion
* un suivi des navires critiques
* des statistiques temps réel

---

# 📄 Licence

MIT License
