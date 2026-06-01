// Tous les appels HTTP de la carte
const MapAPI = {
    async ports(bbox, zoom) {
        const res = await axios.get('/api/ports/', { params: { bbox, zoom } });
        return res.data.ports;
    },
    async searchPorts(q) {
        const res = await fetch(`/api/ports/search/?q=${encodeURIComponent(q)}`);
        return (await res.json()).ports;
    },
    async ships(bbox) {
        const res = await axios.get('/api/ships/', { params: { bbox } });
        return res.data.ships;
    },
    async shipTrack(mmsi) {
        const res = await fetch(`/api/ships/${mmsi}/track/`);
        return res.json();
    },
    async wiki(term, lang = 'fr') {
        const res = await fetch(
            `/api/wikipedia/?term=${encodeURIComponent(term)}&lang=${lang}`
        );
        if (!res.ok) return null;
        const d = await res.json();
        return d.extract ? d : null;
    },

    async shipPhoto(name) {
        if (!name || name.trim().length < 2) return null;
        const res = await fetch(`/api/ship-photo/?name=${encodeURIComponent(name)}`);
        if (!res.ok) return null;
        return res.json();
    },
};
