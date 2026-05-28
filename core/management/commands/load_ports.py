import csv
import io
import urllib.request
from django.core.management.base import BaseCommand
from core.models import Port
from django.db.models import Count

#url WPI (World Port Index) pour télécharger le csv
WPI_CSV_URL = (
    "https://msi.nga.mil/api/publications/download"
    "?type=view&key=16920959/SFH00000/UpdatedPub150.csv"
)

# dictionnaires porur détecter les colonnes dans le csv (varianntes possibles)
COL_CANDIDATES = {
    "lat": ["latitude", "lat", "latitude_deg", "lat_deg", "y"],
    "lon": ["longitude", "lon", "lng", "longitude_deg", "lon_deg", "x"],
    "name": ["main_port_name", "main port name", "port_name", "port name", "portname"],
    "country": ["country_code", "country code", "country", "cty_code"],
    "region": ["region_name", "region name", "region"],
    "wpi": ["world_port_index_number", "world port index number", "wpi_number", "index_number"],
    "harbor_size": ["harbor size", "harbor_size", "harbour size", "harborsize", "harbour_size"],
}

# normlaise une chaîne pour comparaison 
def _normalize(s: str) -> str:
    """Minuscule + strip BOM/espaces + remplace _ par espace pour comparaison uniforme."""
    return s.strip().lstrip("﻿￾\x00").lower().replace("_", " ")


# exécute la commande : python manage.py load_ports pour importer les ports depuis le WPI
class Command(BaseCommand):
    help = "importe les ports mondiaux depuis le WPI"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Vider la table avant import")
        parser.add_argument("--debug", action="store_true", help="Afficher les colonnes détectées")
        parser.add_argument("--if-empty", action="store_true", help="Importer uniquement si la table est vide (utile au démarrage)")

    def handle(self, *args, **options):
        # --if-empty : on saute si des ports existent déjà
        if options["if_empty"]:
            count = Port.objects.count()
            if count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"  {count} ports déjà en base — import ignoré.")
                )
                return

        if options["clear"]:
            deleted, _ = Port.objects.all().delete()
            self.stdout.write(f"  {deleted} ports supprimés.")

        self.stdout.write("Téléchargement du WPI")
        try:
            req = urllib.request.Request(
                WPI_CSV_URL,
                headers={"User-Agent": "Mozilla/5.0 MarineTrafficApp/1.0"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8-sig")  # supprime le BOM si présent
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Erreur de téléchargement : {exc}"))
            return
        
        # lecture csv
        reader = csv.DictReader(io.StringIO(raw))

        cols = self._detect_columns(reader.fieldnames)

        if options["debug"]:
            self.stdout.write(f"\nToutes les colonnes ({len(reader.fieldnames)}) :")
            self.stdout.write("  " + ", ".join(reader.fieldnames))
            self.stdout.write(f"\nColonnes détectées : {cols}\n")

        if not cols["lat"] or not cols["lon"] or not cols["name"]:
            self.stderr.write(
                self.style.ERROR(
                    f"Colonnes manquantes — relance avec --debug.\n"
                    f"Détecté : {cols}"
                )
            )
            return

        self.stdout.write(
            f"Colonnes → nom: '{cols['name']}', lat: '{cols['lat']}', "
            f"lon: '{cols['lon']}', pays: '{cols['country']}', "
            f"harbor_size: '{cols['harbor_size']}'"  # None = colonne non trouvée
        )

        created = skipped = errors = 0
        batch = []

        # pour chaque ligne du csv, on tente de créer un objet Port
        for row in reader:
            try:
                lat = self._parse_coord(row.get(cols["lat"], ""))
                lon = self._parse_coord(row.get(cols["lon"], ""))
                if lat is None or lon is None:
                    skipped += 1
                    continue

                name = row.get(cols["name"], "").strip()
                if not name:
                    skipped += 1
                    continue

                # WPI number stocké comme "7950.0"
                wpi_raw = row.get(cols["wpi"] or "", "").strip() if cols["wpi"] else ""
                try:
                    wpi = str(int(float(wpi_raw))) if wpi_raw else None
                except ValueError:
                    wpi = wpi_raw or None

                # exemple région : "United States E Coast -- 6585" 
                region = row.get(cols["region"] or "", "").strip() if cols["region"] else ""

                harbor_size = (
                    row.get(cols["harbor_size"] or "", "").strip()[:1]
                    if cols["harbor_size"] else ""
                )

                batch.append(
                    Port(
                        name=name,
                        country=row.get(cols["country"] or "", "").strip() if cols["country"] else "",
                        region=region,
                        latitude=lat,
                        longitude=lon,
                        wpi_number=wpi,
                        harbor_size=harbor_size,
                    )
                )
                created += 1

                if len(batch) >= 200:
                    Port.objects.bulk_create(batch, ignore_conflicts=True)
                    batch = []
                    self.stdout.write(f"  {created} insérés…", ending="\r")

            except Exception as exc:
                errors += 1
                if errors <= 3:
                    self.stderr.write(f"Ligne ignorée : {exc}")

        if batch:
            Port.objects.bulk_create(batch, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTerminé : {created} ports insérés, {skipped} ignorés, {errors} erreurs."
            )
        )

        # vérif size
        stats = (
            Port.objects.values("harbor_size")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        dist = ", ".join(
            f"{s['harbor_size'] or '(vide)'}={s['n']}" for s in stats
        )
        self.stdout.write(f"  harbor_size : {dist}")
        if not Port.objects.exclude(harbor_size="").exists():
            self.stderr.write(self.style.WARNING("Tous les harbor_size sont vides !\n"))

    @classmethod
    def _detect_columns(cls, fieldnames: list) -> dict:
        """Détecte les colonnes en normalisant underscores : espaces, insensible à la casse"""
        clean_map = {_normalize(fn): fn for fn in fieldnames}

        result = {}
        # pour chaque champ du dictionnaire
        for key, candidates in COL_CANDIDATES.items():
            result[key] = None
            for c in candidates:
                normalized = _normalize(c)  # "main_port_name" devient "main port name"
                if normalized in clean_map:
                    result[key] = clean_map[normalized]
                    break
        return result

    @staticmethod
    def _parse_coord(value: str):
        """convertit une coordonnée en float, gère les formats DMS et les hémisphères N/S/E/W"""
        val = str(value).strip()
        if not val:
            return None

        try:
            f = float(val)
            return None if f == 0 else f
        except ValueError:
            pass

        # si la valeur se termine par N/S/E/W, on tente de parser
        if val and val[-1].upper() in "NSEW":
            hemi = val[-1].upper()
            body = val[:-1]
            try:
                parts = body.split("-")
                if len(parts) >= 2:
                    deg = float(parts[0])
                    min_ = float(parts[1])
                    sec = float(parts[2]) if len(parts) > 2 else 0.0
                    dec = deg + min_ / 60 + sec / 3600
                else:
                    num = float(body)
                    deg = int(num / 100)
                    dec = deg + (num - deg * 100) / 60
                return -dec if hemi in ("S", "W") else dec
            except (ValueError, IndexError):
                pass

        return None
