// Couche canvas custom — navires animés en temps réel (interpolation fluide)
const ShipCanvasLayer = L.Layer.extend({

    initialize() {
        this._ships    = {};
        this._filters  = { name: '', type: '', status: '' };
        this._selected = null;   // mmsi du navire sélectionné
        this._visible  = true;
        this._ctx      = null;
        this._canvas   = null;
        this._ro       = null;
        this._animId   = null;
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

        if (window.ResizeObserver) {
            this._ro = new ResizeObserver(() => { this._resize(); this._redraw(); });
            this._ro.observe(map.getContainer());
        }

        this._resize(); this._redraw();
        setTimeout(() => { this._resize(); this._redraw(); }, 0);
        setTimeout(() => { this._resize(); this._redraw(); }, 100);
        setTimeout(() => { this._resize(); this._redraw(); }, 500);

        // Boucle d'animation continue (~30 fps)
        this._startAnimation();
    },

    onRemove(map) {
        if (this._canvas)  this._canvas.remove();
        if (this._ro)      this._ro.disconnect();
        if (this._animId)  cancelAnimationFrame(this._animId);
        map.off('move zoomend viewreset', this._redraw, this);
        map.off('resize',                 this._resize,  this);
        map.off('click',                  this._onClick, this);
    },

    _startAnimation() {
        let last = 0;
        const FPS = 30;
        const INTERVAL = 1000 / FPS;

        const tick = (ts) => {
            this._animId = requestAnimationFrame(tick);
            if (ts - last < INTERVAL) return;
            last = ts;
            if (!this._visible) return;
            this._deadReckon();
            this._redraw();
        };
        this._animId = requestAnimationFrame(tick);
    },

    // Dead reckoning : projette la position en fonction de la vitesse + cap
    // → les navires bougent en continu même sans nouvel update AIS
    _deadReckon() {
        const nowS = Date.now() / 1000;
        for (const s of Object.values(this._ships)) {
            const baseLat = s.lat ?? s.latitude;
            const baseLng = s.lng ?? s.longitude;
            if (!isFinite(baseLat) || !isFinite(baseLng)) continue;

            const speed  = parseFloat(s.speed)  || 0; // nœuds
            const course = parseFloat(s.course ?? s.heading) || 0; // degrés
            const elapsed = nowS - (s._updateTime || nowS); // secondes depuis dernier update

            // Navire à quai ou au mouillage → on ne bouge pas
            if (speed < 0.3 || s.status === 1 || s.status === 5 || elapsed > 1800) {
                s._lat = baseLat;
                s._lng = baseLng;
                continue;
            }

            // distance parcourue en mètres depuis le dernier update AIS connu
            const distM      = speed * 0.514444 * elapsed;
            const courseRad  = (course * Math.PI) / 180;
            const latRad     = (baseLat * Math.PI) / 180;

            s._lat = baseLat + (distM * Math.cos(courseRad)) / 111320;
            s._lng = baseLng + (distM * Math.sin(courseRad)) / (111320 * Math.cos(latRad));
        }
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

    _color(type, status) {
        if (status === 1 || status === 5) return '#94a3b8';
        if (!type) return '#64748b';
        if (type >= 70 && type < 80) return '#22c55e';
        if (type >= 80 && type < 90) return '#ef4444';
        if (type >= 60 && type < 70) return '#a855f7';
        if (type >= 30 && type < 36) return '#f97316';
        if (type >= 36 && type < 38) return '#06b6d4';
        if (type === 35)             return '#475569';
        if (type >= 40 && type < 50) return '#eab308';
        if (type >= 50 && type < 60) return '#ec4899';
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
        let selectedShip = null;

        for (const s of Object.values(this._ships)) {
            if (!this._passesFilter(s)) continue;

            const lat = s._lat ?? s.lat ?? s.latitude;
            const lng = s._lng ?? s.lng ?? s.longitude;
            if (!isFinite(lat) || !isFinite(lng)) continue;

            const p = this._map.latLngToContainerPoint([lat, lng]);
            if (p.x < -a * 3 || p.x > w + a * 3 || p.y < -a * 3 || p.y > h + a * 3) continue;

            // Le navire sélectionné est dessiné en dernier (au-dessus de tous)
            if (s.mmsi === this._selected) { selectedShip = { s, p }; drawn++; continue; }

            this._drawShip(ctx, s, p, a, false);
            drawn++;
        }

        // Navire sélectionné — dessiné en dernier avec surbrillance
        if (selectedShip) this._drawShip(ctx, selectedShip.s, selectedShip.p, a, true);

        if (window._alpineShipCount) window._alpineShipCount(drawn);
    },

    _drawShip(ctx, s, p, a, selected) {
        const color = this._color(s.ship_type ?? s.type, s.status);
        const angle = ((s.course ?? s.heading ?? 0) * Math.PI) / 180;
        const size  = selected ? a * 1.6 : a;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(angle);

        if (selected) {
            // Halo blanc pulsant autour du navire sélectionné
            ctx.beginPath();
            ctx.arc(0, 0, size * 1.5, 0, Math.PI * 2);
            ctx.fillStyle   = 'rgba(255,255,255,0.15)';
            ctx.fill();

            // Anneau coloré
            ctx.beginPath();
            ctx.arc(0, 0, size * 1.3, 0, Math.PI * 2);
            ctx.strokeStyle = color;
            ctx.lineWidth   = 2;
            ctx.stroke();
        }

        // Flèche
        ctx.beginPath();
        ctx.moveTo(0, -size);
        ctx.lineTo(size * 0.65,  size * 0.85);
        ctx.lineTo(0,            size * 0.3);
        ctx.lineTo(-size * 0.65, size * 0.85);
        ctx.closePath();
        ctx.fillStyle   = selected ? '#ffffff' : color;
        ctx.strokeStyle = selected ? color : 'rgba(0,0,0,0.4)';
        ctx.lineWidth   = selected ? 1.5 : 0.7;
        ctx.fill();
        ctx.stroke();

        ctx.restore();
    },

    _onClick(e) {
        if (!this._visible) return;
        const click = this._map.latLngToContainerPoint(e.latlng);
        let nearest = null, minD = 18;
        for (const s of Object.values(this._ships)) {
            const lat = s._lat ?? s.lat ?? s.latitude;
            const lng = s._lng ?? s.lng ?? s.longitude;
            if (!isFinite(lat) || !isFinite(lng)) continue;
            const p = this._map.latLngToContainerPoint([lat, lng]);
            const d = Math.hypot(p.x - click.x, p.y - click.y);
            if (d < minD) { minD = d; nearest = s; }
        }
        if (nearest) {
            this._selected = nearest.mmsi;
            window.dispatchEvent(new CustomEvent('open-ship-detail', { detail: nearest }));
        }
    },

    upsert(ships) {
        const nowS = Date.now() / 1000;
        ships.forEach(s => {
            // Timestamp du dernier update AIS réel → base pour le dead reckoning
            s._updateTime = nowS;
            this._ships[s.mmsi] = s;
        });
        // La boucle RAF appelle _deadReckon() + _redraw() en continu
    },

    setFilter(f) { this._filters = f; },
    show()       { this._visible = true;  if (this._canvas) this._canvas.style.display = ''; },
    hide()       { this._visible = false; if (this._canvas) this._canvas.style.display = 'none'; },
    shipCount()  { return Object.keys(this._ships || {}).length; },
});
