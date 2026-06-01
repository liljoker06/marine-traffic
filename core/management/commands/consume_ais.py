"""
Commande Django : lit les positions AIS depuis Kafka, met à jour la base
de données et diffuse les données en temps réel aux navigateurs.

Optimisations :
- bulk_create + bulk_update  → 3 requêtes DB par flush (au lieu de N×5)
- ShipPosition sauvegardée toutes les 5 min par navire (pas à chaque message)
- Purge positions lancée toutes les 30 min (pas à chaque flush)
- BROADCAST_EVERY = 10 s pour réduire la charge WebSocket
"""

import time
import json
from collections import defaultdict

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from core.models import Ship, ShipPosition

CONGESTION_MEDIUM  = 5
CONGESTION_HIGH    = 15
BROADCAST_EVERY    = 10   # secondes entre deux broadcasts WebSocket
POSITION_SAVE_MIN  = 300  # secondes entre deux sauvegardes de position par navire
PURGE_EVERY        = 1800 # secondes entre deux purges de l'historique (30 min)
MAX_POSITIONS      = 50


def _flush(batch: dict, channel_layer, last_position_save: dict):
    if not batch:
        return

    now    = timezone.now()
    mmsis  = list(batch.keys())

    # ── 1 requête : récupère tous les navires connus ──────────────────────────
    existing = {s.mmsi: s for s in Ship.objects.filter(mmsi__in=mmsis)}

    to_create  = []
    to_update  = []
    need_track = []   # mmsis qui ont besoin d'une position historique

    for mmsi, data in batch.items():
        lat, lng = data['lat'], data['lng']

        # Décide si on sauvegarde un point de route
        last_saved = last_position_save.get(mmsi, 0)
        if now.timestamp() - last_saved >= POSITION_SAVE_MIN:
            need_track.append(mmsi)
            last_position_save[mmsi] = now.timestamp()

        if mmsi in existing:
            s = existing[mmsi]
            s.latitude    = lat
            s.longitude   = lng
            s.speed       = data.get('speed')
            s.course      = data.get('course')
            s.heading     = data.get('heading')
            s.status      = data.get('status')
            s.last_update = now
            if data.get('name'):      s.name      = data['name']
            if data.get('ship_type'): s.ship_type = data['ship_type']
            to_update.append(s)
        else:
            to_create.append(Ship(
                mmsi=mmsi,
                name=data.get('name', ''),
                latitude=lat, longitude=lng,
                speed=data.get('speed'),
                course=data.get('course'),
                heading=data.get('heading'),
                status=data.get('status'),
                ship_type=data.get('ship_type'),
                last_update=now,
            ))

    # ── 1 requête bulk_create + 1 requête bulk_update ─────────────────────────
    with transaction.atomic():
        if to_create:
            Ship.objects.bulk_create(to_create, ignore_conflicts=True)
        if to_update:
            Ship.objects.bulk_update(
                to_update,
                ['name', 'latitude', 'longitude', 'speed', 'course',
                 'heading', 'status', 'ship_type', 'last_update'],
            )

    # ── Sauvegarde positions historiques (1 requête bulk_create) ─────────────
    if need_track:
        ship_map = {s.mmsi: s for s in Ship.objects.filter(mmsi__in=need_track)}
        positions = [
            ShipPosition(
                ship=ship_map[mmsi],
                latitude=batch[mmsi]['lat'],
                longitude=batch[mmsi]['lng'],
                speed=batch[mmsi].get('speed'),
                timestamp=now,
            )
            for mmsi in need_track if mmsi in ship_map
        ]
        if positions:
            ShipPosition.objects.bulk_create(positions)

    # ── Broadcast WebSocket ───────────────────────────────────────────────────
    ships_payload = [
        {
            'mmsi':    mmsi,
            'name':    data.get('name', ''),
            'lat':     data['lat'],
            'lng':     data['lng'],
            'speed':   round(data.get('speed') or 0, 1),
            'course':  round(data.get('course') or 0, 1),
            'heading': data.get('heading', 511),
            'status':  data.get('status', 15),
            'type':    data.get('ship_type'),
        }
        for mmsi, data in batch.items()
    ]

    async_to_sync(channel_layer.group_send)('ships', {
        'type': 'ship_update', 'ships': ships_payload,
    })

    # ── Zones de congestion ───────────────────────────────────────────────────
    grid = defaultdict(int)
    for data in batch.values():
        cell = (round(data['lat'] * 2) / 2, round(data['lng'] * 2) / 2)
        grid[cell] += 1

    zones = [
        {'lat': lat, 'lng': lng, 'count': c,
         'level': 'high' if c >= CONGESTION_HIGH else 'medium'}
        for (lat, lng), c in grid.items() if c >= CONGESTION_MEDIUM
    ]
    if zones:
        async_to_sync(channel_layer.group_send)('ships', {
            'type': 'congestion_update', 'zones': zones,
        })


def _purge_old_positions():
    """Supprime les positions > MAX_POSITIONS par navire. 1 requête par navire concerné."""
    for ship in Ship.objects.only('id'):
        old_ids = list(
            ShipPosition.objects.filter(ship=ship)
            .order_by('-timestamp')
            .values_list('id', flat=True)[MAX_POSITIONS:]
        )
        if old_ids:
            ShipPosition.objects.filter(id__in=old_ids).delete()


class Command(BaseCommand):
    help = 'Consomme les positions AIS depuis Kafka et les diffuse en temps réel'

    def handle(self, *args, **options):
        consumer = None
        for attempt in range(10):
            try:
                consumer = KafkaConsumer(
                    settings.KAFKA_TOPIC,
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    auto_offset_reset='latest',
                    group_id='marine-traffic-consumer',
                )
                self.stdout.write(self.style.SUCCESS('Consumer Kafka connecté'))
                break
            except NoBrokersAvailable:
                self.stdout.write(f'Kafka indisponible, tentative {attempt + 1}/10...')
                time.sleep(3)

        if consumer is None:
            self.stderr.write(self.style.ERROR('Impossible de se connecter à Kafka'))
            return

        channel_layer      = get_channel_layer()
        batch              = {}   # mmsi → dernière position
        last_position_save = {}   # mmsi → timestamp dernière sauvegarde route
        last_flush         = time.time()
        last_purge         = time.time()

        self.stdout.write('En attente de messages AIS...')

        while True:
            records = consumer.poll(timeout_ms=1000)

            for tp, messages in records.items():
                for msg in messages:
                    data = msg.value
                    mmsi = data.get('mmsi')
                    if mmsi and data.get('lat') is not None and data.get('lng') is not None:
                        batch[mmsi] = data

            now = time.time()

            if now - last_flush >= BROADCAST_EVERY:
                if batch:
                    self.stdout.write(f'Flush {len(batch)} navires → DB + WebSocket')
                    _flush(batch, channel_layer, last_position_save)
                    batch.clear()
                last_flush = now

            if now - last_purge >= PURGE_EVERY:
                self.stdout.write('Purge historique positions...')
                _purge_old_positions()
                last_purge = now
