import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ShipConsumer(AsyncWebsocketConsumer):
    """
    WebSocket côté serveur.
    Chaque onglet navigateur qui ouvre la carte se connecte ici.
    Le consumer est ajouté au groupe 'ships' pour recevoir les broadcasts
    émis par la commande consume_ais.
    """
    GROUP = 'ships'

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

    # Le navigateur n'envoie rien → on ignore les messages entrants
    async def receive(self, text_data=None, bytes_data=None):
        pass

    # ── handlers appelés par group_send depuis consume_ais ───────────────────

    async def ship_update(self, event):
        """Relaie les positions des navires au navigateur."""
        await self.send(text_data=json.dumps({
            'type': 'ship_update',
            'ships': event['ships'],
        }))

    async def congestion_update(self, event):
        """Relaie les zones de congestion au navigateur."""
        await self.send(text_data=json.dumps({
            'type': 'congestion_update',
            'zones': event['zones'],
        }))
