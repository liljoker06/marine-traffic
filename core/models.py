from django.db import models


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