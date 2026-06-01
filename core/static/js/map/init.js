// Initialisation de la carte — relie tous les modules
(function () {
    'use strict';

    const params   = new URLSearchParams(window.location.search);
    const initLat  = parseFloat(params.get('lat'))  || 36.0;
    const initLng  = parseFloat(params.get('lng'))  || 14.0;
    const initZoom = parseInt (params.get('zoom')) || 5;

    const map            = L.map('map', { center: [initLat, initLng], zoom: initZoom });
    const canvasRenderer = L.canvas({ padding: 0.5 });

    // ── Fonds de carte ────────────────────────────────────────────────────────
    const tileDefs = {
        dark:  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
               { attribution: '© OSM © CARTO', subdomains: 'abcd', maxZoom: 19 }),
        osm:   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
               { attribution: '© OpenStreetMap contributors', maxZoom: 18 }),
        light: L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
               { attribution: '© OSM © CARTO', subdomains: 'abcd', maxZoom: 19 }),
    };
    let activeBasemap = tileDefs.dark;
    activeBasemap.addTo(map);

    // ── Ports ─────────────────────────────────────────────────────────────────
    const ports = createPortLayer(map, canvasRenderer);

    // ── Navires ───────────────────────────────────────────────────────────────
    const shipLayer      = new ShipCanvasLayer().addTo(map);
    const congestionLayer = L.layerGroup().addTo(map);
    const trackLayer      = L.layerGroup();
    const loadedBboxKeys  = new Set();

    // Navires d'exemple (visibles immédiatement, remplacés par les données AIS)
    shipLayer.upsert([
        { mmsi: '123456789', name: 'MSC Tunis',     lat: 36.8,  lng: 10.2,  speed: 12.3, course: 45,  ship_type: 71, status: 0 },
        { mmsi: '987654321', name: 'Atlantic Star',  lat: 35.9,  lng: 14.5,  speed: 0,    course: 180, ship_type: 71, status: 5 },
        { mmsi: '111222333', name: 'Arctic Pioneer', lat: 68.5,  lng: 15.2,  speed: 8.5,  course: 220, ship_type: 80, status: 0 },
        { mmsi: '444555666', name: 'Pacific Dream',  lat: 22.3,  lng: 114.1, speed: 14.1, course: 90,  ship_type: 70, status: 0 },
        { mmsi: '777888999', name: 'Queen Europa',   lat: 51.5,  lng: 1.2,   speed: 18.2, course: 135, ship_type: 60, status: 0 },
    ]);

    async function loadShips() {
        if (!shipLayer._visible) return;
        const b   = map.getBounds().pad(0.1);
        const key = `${b.getSouth().toFixed(1)},${b.getWest().toFixed(1)},${b.getNorth().toFixed(1)},${b.getEast().toFixed(1)}`;
        if (loadedBboxKeys.has(key)) return;
        loadedBboxKeys.add(key);
        try {
            const ships = await MapAPI.ships(
                `${b.getSouth()},${b.getWest()},${b.getNorth()},${b.getEast()}`
            );
            shipLayer.upsert(ships);
        } catch { loadedBboxKeys.delete(key); }
    }

    map.on('moveend', loadShips);
    map.on('zoomend', () => { loadedBboxKeys.clear(); loadShips(); });
    loadShips();

    // Recharge la DB toutes les 2 min pour récupérer les nouveaux navires
    setInterval(() => { loadedBboxKeys.clear(); loadShips(); }, 120_000);

    // ── WebSocket ─────────────────────────────────────────────────────────────
    connectShipWS(shipLayer, congestionLayer, canvasRenderer);

    // ── Fonctions globales pour Alpine ────────────────────────────────────────
    window.mapFlyTo       = (lat, lng) => map.flyTo([lat, lng], 12, { duration: 1.5 });
    window.mapSwitchLayer = (id) => {
        map.removeLayer(activeBasemap);
        activeBasemap = tileDefs[id] || tileDefs.dark;
        activeBasemap.addTo(map);
    };
    window.setShipFilters    = (f) => shipLayer.setFilter(f);
    window.mapShowPorts      = () => ports.show();
    window.mapHidePorts      = () => ports.hide();
    window.mapShowShips      = () => { shipLayer.show(); loadShips(); };
    window.mapHideShips      = () => shipLayer.hide();
    window.mapShowCongestion = () => map.addLayer(congestionLayer);
    window.mapHideCongestion = () => map.removeLayer(congestionLayer);

    window.mapDrawTrack = async (mmsi) => {
        trackLayer.clearLayers();
        map.removeLayer(trackLayer);
        try {
            const body = await MapAPI.shipTrack(mmsi);
            const pts  = body.positions;
            if (!pts || !pts.length) return 0;
            L.polyline(pts.map(p => [p.latitude, p.longitude]),
                       { color: '#60a5fa', weight: 2, opacity: 0.7 })
             .addTo(trackLayer);
            map.addLayer(trackLayer);
            return pts.length;
        } catch { return 0; }
    };

    window.mapClearTrack = () => {
        trackLayer.clearLayers();
        map.removeLayer(trackLayer);
    };

})();
