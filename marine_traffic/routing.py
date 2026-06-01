from django.urls import path
from core.consumers import ShipConsumer

websocket_urlpatterns = [
    path('ws/ships/', ShipConsumer.as_asgi()),
]
