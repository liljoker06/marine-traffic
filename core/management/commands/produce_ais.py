"""
Commande Django : connecte à aisstream.io via WebSocket et publie
chaque position AIS reçue dans le topic Kafka 'ais-positions'.

Usage : python manage.py produce_ais
"""

import asyncio
import json
import websockets
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from django.core.management.base import BaseCommand
from django.conf import settings


AISSTREAM_URL = 'wss://stream.aisstream.io/v0/stream'


class Command(BaseCommand):
    help = 'Collecte les positions AIS depuis aisstream.io et les publie dans Kafka'

    def handle(self, *args, **options):
        asyncio.run(self._run())

    async def _run(self):
        # Connexion Kafka (retry au démarrage)
        producer = None
        for attempt in range(10):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                )
                self.stdout.write(self.style.SUCCESS('Kafka connecté'))
                break
            except NoBrokersAvailable:
                self.stdout.write(f'Kafka indisponible, tentative {attempt + 1}/10...')
                await asyncio.sleep(3)

        if producer is None:
            self.stderr.write(self.style.ERROR('Impossible de se connecter à Kafka'))
            return

        # Boucle de reconnexion aisstream.io
        while True:
            try:
                async with websockets.connect(AISSTREAM_URL) as ws:
                    # Abonnement : tous les navires dans le monde entier
                    await ws.send(json.dumps({
                        'APIKey': settings.AISSTREAM_API_KEY,
                        'BoundingBoxes': [[[-90, -180], [90, 180]]],
                        'FilterMessageTypes': ['PositionReport'],
                    }))
                    # Les messages bruts vont dans ais-raw
                    # Spark les lit, les filtre, et les écrit dans ais-positions
                    self.stdout.write(self.style.SUCCESS('Connecté à aisstream.io — flux AIS actif'))

                    async for raw in ws:
                        msg = json.loads(raw)

                        # On ne traite que les rapports de position
                        if msg.get('MessageType') != 'PositionReport':
                            continue

                        meta = msg.get('MetaData', {})
                        pos  = msg['Message']['PositionReport']

                        # Latitude/longitude : d'abord dans MetaData, puis dans PositionReport
                        lat = meta.get('latitude') or pos.get('Latitude')
                        lng = meta.get('longitude') or pos.get('Longitude')

                        if lat is None or lng is None:
                            continue

                        record = {
                            'mmsi':      str(meta.get('MMSI', '')),
                            'name':      meta.get('ShipName', '').strip(),
                            'lat':       float(lat),
                            'lng':       float(lng),
                            'speed':     float(pos.get('Sog', 0)),
                            'course':    float(pos.get('Cog', 0)),
                            'heading':   int(pos.get('TrueHeading', 511)),
                            'status':    int(pos.get('NavigationalStatus', 15)),
                            'ship_type': int(pos.get('Type', 0)) if pos.get('Type') else None,
                            'timestamp': meta.get('time_utc', ''),
                        }

                        producer.send(settings.KAFKA_RAW_TOPIC, record)

            except Exception as exc:
                self.stderr.write(f'Déconnexion aisstream.io : {exc} — reconnexion dans 5 s...')
                await asyncio.sleep(5)
