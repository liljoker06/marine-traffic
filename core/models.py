from django.db import models
from django.utils import timezone


# ── Types de navires AIS ──────────────────────────────────────────────────────
SHIP_TYPE_LABELS = {
    **{i: 'Pêche'       for i in range(30, 33)},
    **{i: 'Voilier'     for i in range(36, 38)},
    **{i: 'Passagers'   for i in range(60, 70)},
    **{i: 'Cargo'       for i in range(70, 80)},
    **{i: 'Tanker'      for i in range(80, 90)},
}

NAV_STATUS_LABELS = {
    0: 'En route (moteur)',
    1: 'Au mouillage',
    2: 'Hors de contrôle',
    3: 'Manœuvrabilité restreinte',
    5: 'À quai',
    7: 'En pêche',
    15: 'Indéfini',
}


class Ship(models.Model):
    mmsi        = models.CharField(max_length=20, unique=True, db_index=True)
    name        = models.CharField(max_length=200, blank=True)
    ship_type   = models.IntegerField(null=True, blank=True)
    flag        = models.CharField(max_length=10, blank=True)
    latitude    = models.FloatField(null=True)
    longitude   = models.FloatField(null=True)
    speed       = models.FloatField(null=True, blank=True)   # nœuds
    course      = models.FloatField(null=True, blank=True)   # degrés
    heading     = models.FloatField(null=True, blank=True)   # cap vrai
    status      = models.IntegerField(null=True, blank=True) # statut AIS
    last_update = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-last_update']
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='ship_latlon_idx'),
            models.Index(fields=['last_update'],           name='ship_update_idx'),
        ]

    def __str__(self):
        return f"{self.name or 'Inconnu'} ({self.mmsi})"

    @property
    def type_label(self):
        return SHIP_TYPE_LABELS.get(self.ship_type, 'Autre')

    @property
    def status_label(self):
        return NAV_STATUS_LABELS.get(self.status, 'Indéfini')


class ShipPosition(models.Model):
    ship      = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name='positions')
    latitude  = models.FloatField()
    longitude = models.FloatField()
    speed     = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['ship', '-timestamp'])]


class Port(models.Model):
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    wpi_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    harbor_size = models.CharField(
        max_length=1, blank=True, default='',
        help_text='L=Large, M=Medium, S=Small, V=Very Small',
        db_index=True,
    )
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='port_latlon_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.country})"