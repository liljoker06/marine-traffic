// Connexion WebSocket — reçoit ship_update et congestion_update
function connectShipWS(shipLayer, congestionLayer, canvasRenderer) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';

    function connect() {
        const ws = new WebSocket(`${proto}://${location.host}/ws/ships/`);

        ws.onopen = () => console.log('WebSocket AIS connecté ✓');

        ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);

            if (msg.type === 'ship_update') {
                shipLayer.upsert(msg.ships);
            }

            if (msg.type === 'congestion_update') {
                congestionLayer.clearLayers();
                msg.zones.forEach(z => {
                    const color = z.level === 'high' ? '#ef4444' : '#f97316';
                    L.circle([z.lat, z.lng], {
                        radius:      z.level === 'high' ? 40000 : 25000,
                        color, fillColor: color,
                        fillOpacity: 0.12, weight: 1, opacity: 0.4,
                        renderer:    canvasRenderer,
                    }).bindTooltip(
                        `🔴 ${z.level === 'high' ? 'Congestion élevée' : 'Congestion modérée'} — ${z.count} navires`,
                        { sticky: true }
                    ).addTo(congestionLayer);
                });
            }
        };

        ws.onclose = () => setTimeout(connect, 3000);
    }

    connect();
}
