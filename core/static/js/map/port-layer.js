// Chargement et rendu des ports avec cache et arrondi de bbox par zoom
function createPortLayer(map, canvasRenderer) {
    const layer       = L.layerGroup().addTo(map);
    let   visible     = true;
    let   currBucket  = -1;
    const loadedKeys  = new Set();

    function zoomBucket(z) { return z <= 3 ? 3 : z <= 5 ? 5 : z <= 8 ? 8 : 10; }
    function bboxStep(z)   { return z <= 3 ? 20 : z <= 5 ? 10 : z <= 8 ? 5 : 2; }

    function roundedBbox(bounds, step) {
        return {
            south: Math.floor(bounds.getSouth() / step) * step,
            west:  Math.floor(bounds.getWest()  / step) * step,
            north: Math.ceil (bounds.getNorth() / step) * step,
            east:  Math.ceil (bounds.getEast()  / step) * step,
        };
    }

    function portStyle(s) {
        switch (s) {
            case 'L': return { radius: 9, fillColor: '#facc15', color: '#a16207', weight: 1.5 };
            case 'M': return { radius: 7, fillColor: '#fb923c', color: '#c2410c', weight: 1 };
            case 'S': return { radius: 5, fillColor: '#60a5fa', color: '#1d4ed8', weight: 1 };
            default:  return { radius: 3, fillColor: '#94a3b8', color: '#475569', weight: 1 };
        }
    }

    function addMarkers(ports) {
        ports.forEach(port => {
            const m = L.circleMarker([port.latitude, port.longitude], {
                ...portStyle(port.harbor_size),
                opacity: 0.9, fillOpacity: 0.8, renderer: canvasRenderer,
            });
            m.on('click', () =>
                window.dispatchEvent(new CustomEvent('open-port-detail', { detail: port }))
            );
            layer.addLayer(m);
        });
    }

    async function load() {
        if (!visible) return;
        const zoom   = map.getZoom();
        const bucket = zoomBucket(zoom);
        if (bucket !== currBucket) { layer.clearLayers(); loadedKeys.clear(); currBucket = bucket; }
        const step = bboxStep(zoom);
        const bbox = roundedBbox(map.getBounds(), step);
        const key  = `${PortCache.PFX}${bucket}_${bbox.south}_${bbox.west}_${bbox.north}_${bbox.east}`;
        if (loadedKeys.has(key)) return;
        loadedKeys.add(key);
        const cached = PortCache.get(key);
        if (cached) { addMarkers(cached); return; }
        try {
            const ports = await MapAPI.ports(
                `${bbox.south},${bbox.west},${bbox.north},${bbox.east}`, zoom
            );
            PortCache.set(key, ports);
            addMarkers(ports);
        } catch (e) { console.error('Ports:', e.message); loadedKeys.delete(key); }
    }

    map.on('moveend', load);
    map.on('zoomend', load);
    load();

    return {
        show() { visible = true;  map.addLayer(layer);    load(); },
        hide() { visible = false; map.removeLayer(layer); },
    };
}
