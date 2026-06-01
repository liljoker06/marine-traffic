// Composants Alpine.js — panneau gauche (paramètres) et panneau droit (détail)

function mapPanel() {
    return {
        open: true,
        activeLayer: 'dark',
        searchQuery: '', searchResults: [], searching: false,
        shipFilter: { name: '', type: '', status: '' },
        shipCount: 0,
        layers: [
            { id: 'dark',  label: 'Sombre',   desc: 'CartoDB Dark Matter', color: '#1a1a2e' },
            { id: 'osm',   label: 'Standard', desc: 'OpenStreetMap',       color: '#d4c9a8' },
            { id: 'light', label: 'Clair',    desc: 'CartoDB Positron',    color: '#efefef' },
        ],

        init() {
            window._alpineShipCount = (n) => { this.shipCount = n; };
        },

        async searchPorts() {
            const q = this.searchQuery.trim();
            if (q.length < 2) { this.searchResults = []; return; }
            this.searching = true;
            try { this.searchResults = await MapAPI.searchPorts(q); }
            catch { this.searchResults = []; }
            this.searching = false;
        },

        flyToPort(port) {
            window.mapFlyTo(port.latitude, port.longitude);
            window.dispatchEvent(new CustomEvent('open-port-detail', { detail: port }));
            this.searchQuery = ''; this.searchResults = [];
        },

        applyShipFilters() { window.setShipFilters({ ...this.shipFilter }); },
        switchLayer(id)    { window.mapSwitchLayer(id); },
        showPorts()        { window.mapShowPorts(); },
        hidePorts()        { window.mapHidePorts(); },
        showShips()        { window.mapShowShips(); },
        hideShips()        { window.mapHideShips(); },
        showCongestion()   { window.mapShowCongestion(); },
        hideCongestion()   { window.mapHideCongestion(); },
    };
}

function detailPanel() {
    return {
        open: false,
        type: null,   // 'port' | 'ship'
        data: null,
        title: '', subtitle: '',
        wikiLoading: false, wikiData: null, wikiSearched: false,
        trackLoading: false, trackPoints: 0,
        shipPhoto: null, shipPhotoLoading: false,

        openPort(port) {
            this.type = 'port'; this.data = port; this.open = true;
            this.title    = '⚓ ' + port.name;
            this.subtitle = [port.country, port.region].filter(Boolean).join(' · ');
            this.wikiData = null; this.wikiSearched = false;
            window.mapClearTrack();
            this._fetchWiki(port.name);
        },

        async openShip(ship) {
            this.type = 'ship'; this.data = ship; this.open = true;
            this.title    = '🚢 ' + (ship.name || ship.mmsi || 'Navire inconnu');
            this.subtitle = 'MMSI : ' + (ship.mmsi || '—');
            this.trackLoading = true; this.trackPoints = 0;
            this.shipPhoto = null; this.shipPhotoLoading = false;

            // Route AIS — bloque l'affichage le temps du chargement
            try {
                const body = await MapAPI.shipTrack(ship.mmsi);
                if (body.ship) this.data = { ...ship, ...body.ship };
                this.trackPoints = await window.mapDrawTrack(ship.mmsi);
            } catch {}
            this.trackLoading = false;

            // Photo — en arrière-plan, n'attend pas l'affichage du panneau
            this._fetchShipPhoto(ship.name || '');
        },

        close() {
            this.open = false;
            this.shipPhoto = null;
            window.mapClearTrack();
        },

        async _fetchShipPhoto(name) {
            if (!name || name.trim().length < 2) return;
            this.shipPhotoLoading = true;
            const d = await MapAPI.shipPhoto(name);
            this.shipPhoto = d?.thumb || null;
            this.shipPhotoLoading = false;
        },

        async _fetchWiki(portName) {
            this.wikiLoading = true;
            this.wikiData = null;
            this.wikiSearched = false;

            // Essai en français puis en anglais — le proxy gère le fallback recherche
            for (const lang of ['fr', 'en']) {
                const d = await MapAPI.wiki(portName, lang);
                if (d) {
                    this.wikiData = d;
                    break;
                }
            }

            this.wikiLoading = false;
            this.wikiSearched = true;
        },
    };
}
