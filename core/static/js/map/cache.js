// Cache localStorage pour les tuiles de ports (TTL 10 min, max 80 entrées)
const PortCache = {
    TTL: 10 * 60 * 1000,
    PFX: 'mt_ports_',
    MAX: 80,

    get(key) {
        try {
            const raw = localStorage.getItem(key);
            if (!raw) return null;
            const { ts, ports } = JSON.parse(raw);
            if (Date.now() - ts > this.TTL) { localStorage.removeItem(key); return null; }
            return ports;
        } catch { return null; }
    },

    set(key, ports) {
        try {
            const keys = Object.keys(localStorage).filter(k => k.startsWith(this.PFX));
            if (keys.length >= this.MAX) {
                keys.map(k => ({ k, ts: (() => { try { return JSON.parse(localStorage.getItem(k)).ts; } catch { return 0; } })() }))
                    .sort((a, b) => a.ts - b.ts).slice(0, 20)
                    .forEach(e => localStorage.removeItem(e.k));
            }
            localStorage.setItem(key, JSON.stringify({ ts: Date.now(), ports }));
        } catch {
            Object.keys(localStorage).filter(k => k.startsWith(this.PFX))
                .forEach(k => localStorage.removeItem(k));
        }
    },
};
