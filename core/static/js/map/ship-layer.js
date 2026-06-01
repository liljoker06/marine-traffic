// Couche canvas custom — dessine tous les navires comme MarineTraffic
// Un seul <canvas> partagé, zéro élément DOM par navire
const ShipCanvasLayer = L.Layer.extend({

    initialize() {
        this._ships   = {};
        this._filters = { name: '', type: '', status: '' };
        this._visible = true;
        this._ctx     = null;
        this._canvas  = null;
        this._ro      = null;
    },

    onAdd(map) {
        this._map = map;

        const canvas = document.createElement('canvas');
        canvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:500;';
        map.getContainer().appendChild(canvas);
        this._canvas = canvas;
        this._ctx    = canvas.getContext('2d');

        map.on('move zoomend viewreset', this._redraw, this);
        map.on('resize',                 this._resize,  this);
        map.on('click',                  this._onClick, this);

        // ResizeObserver — le plus fiable pour détecter les vraies dimensions
        if (window.ResizeObserver) {
            this._ro = new ResizeObserver(() => { this._resize(); this._redraw(); });
            this._ro.observe(map.getContainer());
        }

        // Fallbacks progressifs (cas où ResizeObserver n'est pas dispo ou trop lent)
        this._resize(); this._redraw();
        setTimeout(() => { this._resize(); this._redraw(); }, 0);
        setTimeout(() => { this._resize(); this._redraw(); }, 100);
        setTimeout(() => { this._resize(); this._redraw(); }, 500);
    },

    onRemove(map) {
        if (this._canvas) this._canvas.remove();
        if (this._ro)     this._ro.disconnect();
        map.off('move zoomend viewreset', this._redraw, this);
        map.off('resize',                 this._resize,  this);
        map.off('click',                  this._onClick, this);
    },

    _resize() {
        if (!this._canvas || !this._map) return;
        const c = this._map.getContainer();
        const w = c.offsetWidth  || c.clientWidth  || 800;
        const h = c.offsetHeight || c.clientHeight || 600;
        if (w > 0 && h > 0 && (this._canvas.width !== w || this._canvas.height !== h)) {
            this._canvas.width  = w;
            this._canvas.height = h;
        }
    },

    // Couleurs par type AIS — identiques à MarineTraffic
    _color(type, status) {
        if (status === 1 || status === 5) return '#94a3b8'; // mouillage/quai
        if (!type) return '#64748b';
        if (type >= 70 && type < 80) return '#22c55e'; // cargo      vert
        if (type >= 80 && type < 90) return '#ef4444'; // tanker     rouge
        if (type >= 60 && type < 70) return '#a855f7'; // passagers  violet
        if (type >= 30 && type < 36) return '#f97316'; // pêche      orange
        if (type >= 36 && type < 38) return '#06b6d4'; // voilier    cyan
        if (type === 35)             return '#475569'; // militaire  gris
        if (type >= 40 && type < 50) return '#eab308'; // rapide     jaune
        if (type >= 50 && type < 60) return '#ec4899'; // remorqueur rose
        return '#64748b';
    },

    _passesFilter(s) {
        const f = this._filters;
        if (f.name && !(s.name || '').toLowerCase().includes(f.name.toLowerCase())) return false;
        if (f.status && String(s.status) !== f.status) return false;
        if (f.type) {
            const t   = s.ship_type ?? s.type;
            const cat = !t ? 'other'
                : t >= 70 && t < 80 ? 'cargo'
                : t >= 80 && t < 90 ? 'tanker'
                : t >= 60 && t < 70 ? 'passenger'
                : t >= 30 && t < 36 ? 'fishing' : 'other';
            if (cat !== f.type) return false;
        }
        return true;
    },

    _redraw() {
        if (!this._visible || !this._ctx || !this._canvas) return;

        // Si le canvas n'est pas encore dimensionné, on force le resize et on réessaie
        if (!this._canvas.width || !this._canvas.height) {
            this._resize();
            if (!this._canvas.width || !this._canvas.height) return;
        }

        const ctx  = this._ctx;
        const w    = this._canvas.width;
        const h    = this._canvas.height;

        ctx.clearRect(0, 0, w, h);

        const zoom = this._map.getZoom();
        const a    = zoom >= 14 ? 14 : zoom >= 12 ? 11 : zoom >= 10 ? 9 : zoom >= 8 ? 8 : 7;

        let drawn = 0;
        for (const s of Object.values(this._ships)) {
            if (!this._passesFilter(s)) continue;
            const lat = s.lat ?? s.latitude;
            const lng = s.lng ?? s.longitude;
            if (lat == null || lng == null) continue;

            const p = this._map.latLngToContainerPoint([lat, lng]);
            if (p.x < -a * 3 || p.x > w + a * 3 || p.y < -a * 3 || p.y > h + a * 3) continue;

            const color = this._color(s.ship_type ?? s.type, s.status);
            const angle = ((s.course ?? s.heading ?? 0) * Math.PI) / 180;

            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate(angle);
            ctx.beginPath();
            ctx.moveTo(0, -a);
            ctx.lineTo(a * 0.65,  a * 0.85);
            ctx.lineTo(0,         a * 0.3);
            ctx.lineTo(-a * 0.65, a * 0.85);
            ctx.closePath();
            ctx.fillStyle   = color;
            ctx.strokeStyle = 'rgba(0,0,0,0.4)';
            ctx.lineWidth   = 0.7;
            ctx.fill();
            ctx.stroke();
            ctx.restore();
            drawn++;
        }

        if (window._alpineShipCount) window._alpineShipCount(drawn);
    },

    _onClick(e) {
        if (!this._visible) return;
        const click = this._map.latLngToContainerPoint(e.latlng);
        let nearest = null, minD = 14;
        for (const s of Object.values(this._ships)) {
            const lat = s.lat ?? s.latitude;
            const lng = s.lng ?? s.longitude;
            if (lat == null || lng == null) continue;
            const p = this._map.latLngToContainerPoint([lat, lng]);
            const d = Math.hypot(p.x - click.x, p.y - click.y);
            if (d < minD) { minD = d; nearest = s; }
        }
        if (nearest) window.dispatchEvent(new CustomEvent('open-ship-detail', { detail: nearest }));
    },

    upsert(ships) {
        ships.forEach(s => { this._ships[s.mmsi] = s; });
        this._redraw();
    },

    setFilter(f)   { this._filters = f; this._redraw(); },
    show()         { this._visible = true;  if (this._canvas) this._canvas.style.display = '';       this._redraw(); },
    hide()         { this._visible = false; if (this._canvas) this._canvas.style.display = 'none'; },
    shipCount()    { return Object.keys(this._ships || {}).length; },
});
