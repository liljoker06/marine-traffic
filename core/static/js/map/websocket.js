// Connexion WebSocket AIS — reconnexion automatique + indicateur de statut
function connectShipWS(shipLayer, congestionLayer, canvasRenderer) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    let ws       = null;
    let delay    = 1000; // backoff exponentiel

    function setStatus(connected) {
        const dot  = document.getElementById('ws-dot');
        const text = document.getElementById('ws-text');
        if (!dot || !text) return;
        if (connected) {
            dot.className  = 'w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse';
            text.textContent = 'En direct';
            text.className = 'text-green-400';
        } else {
            dot.className  = 'w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse';
            text.textContent = 'Reconnexion...';
            text.className = 'text-red-400';
        }
    }

    function connect() {
        ws = new WebSocket(`${proto}://${location.host}/ws/ships/`);

        ws.onopen = () => {
            console.log('[WS] Connecté ✓');
            setStatus(true);
            delay = 1000;
        };

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
                        `${z.level === 'high' ? 'Congestion élevée' : 'Congestion modérée'} — ${z.count} navires`,
                        { sticky: true }
                    ).addTo(congestionLayer);
                });
            }
        };

        ws.onerror = (err) => {
            console.warn('[WS] Erreur :', err);
            setStatus(false);
        };

        ws.onclose = () => {
            console.log(`[WS] Déconnecté — reconnexion dans ${delay / 1000}s`);
            setStatus(false);
            setTimeout(connect, delay);
            delay = Math.min(delay * 2, 30000); // max 30s
        };
    }

    connect();
}
