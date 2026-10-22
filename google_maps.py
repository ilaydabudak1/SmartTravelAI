# google_maps.py — Google Maps entegrasyonu
#
# Anahtar gerektirmeyen (her zaman kullanılır):
#   harita_linki / rota_linki  → Google Maps URL'leri (yer kartı, yürüyüş yol tarifi)
# GOOGLE_MAPS_API_KEY gerektiren (Google Cloud'da açılması gereken API'ler):
#   yol_tarifi   → Routes API (computeRoutes, yürüyüş)       — gerçek mesafe/süre
#   yer_ara      → Places API (New) Text Search               — gerçek gezi noktaları
# SMARTTRAVEL_OFFLINE=1 iken hiçbir ağ çağrısı yapılmaz.

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

_ZAMAN_ASIMI = 8


def anahtar() -> str:
    if os.getenv("SMARTTRAVEL_OFFLINE") == "1":
        return ""
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()


def _ll(p: dict) -> str:
    return f"{p['lat']:.6f},{p['lon']:.6f}"


# ---------------------------------------------------------------------------
# Anahtarsız URL'ler
# ---------------------------------------------------------------------------

def harita_linki(p: dict, sehir: str = "") -> str:
    """Yerin Google Maps kartı: ad + şehirle arar (gerçek yer kartı açılır); ad yoksa koordinat."""
    if p.get("isim"):
        sorgu = f"{p['isim']}, {sehir}" if sehir else p["isim"]
    elif p.get("lat") is not None:
        sorgu = _ll(p)
    else:
        sorgu = sehir
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(sorgu)


def rota_linki(merkez: dict, duraklar: list, mod: str = "walking") -> str:
    """Konaklama → duraklar → konaklama yürüyüş tarifi (Google Maps uygulamasında açılır)."""
    gecerli = [d for d in duraklar if d.get("lat") is not None]
    params = {"api": "1", "origin": _ll(merkez), "destination": _ll(merkez), "travelmode": mod}
    if gecerli:
        params["waypoints"] = "|".join(_ll(d) for d in gecerli)
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params, safe="|,")


# ---------------------------------------------------------------------------
# Anahtarlı servisler
# ---------------------------------------------------------------------------

def _post(url: str, govde: dict, alan_maskesi: str) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(govde).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": anahtar(),
                 "X-Goog-FieldMask": alan_maskesi})
    with urllib.request.urlopen(req, timeout=_ZAMAN_ASIMI) as r:
        return json.loads(r.read())


def yol_tarifi(noktalar: list) -> dict | None:
    """Routes API ile sıralı noktalar arasında yürüyüş mesafesi ve süresi."""
    if not anahtar() or len(noktalar) < 2:
        return None

    def konum(p):
        return {"location": {"latLng": {"latitude": p["lat"], "longitude": p["lon"]}}}

    govde = {"origin": konum(noktalar[0]), "destination": konum(noktalar[-1]),
             "intermediates": [konum(p) for p in noktalar[1:-1]],
             "travelMode": "WALK", "languageCode": "tr", "units": "METRIC"}
    try:
        data = _post("https://routes.googleapis.com/directions/v2:computeRoutes", govde,
                     "routes.distanceMeters,routes.duration,routes.legs.distanceMeters,routes.legs.duration")
        rota = data["routes"][0]
    except Exception:
        return None

    def dk(s):
        return round(float(str(s or "0s").rstrip("s")) / 60, 1)

    return {
        "kaynak": "Google Maps",
        "km": round(rota.get("distanceMeters", 0) / 1000, 2),
        "dakika": dk(rota.get("duration")),
        "bacaklar": [{"km": round(l.get("distanceMeters", 0) / 1000, 2), "dakika": dk(l.get("duration"))}
                     for l in rota.get("legs", [])],
    }


# Google yer türü → sistemin kategorisi
_TUR_KATEGORI = {
    "museum": "muze", "art_gallery": "sanat", "tourist_attraction": "tarih", "historical_landmark": "tarih",
    "monument": "tarih", "church": "ibadet", "mosque": "ibadet", "synagogue": "ibadet", "hindu_temple": "ibadet",
    "park": "doga", "national_park": "doga", "garden": "doga", "beach": "sahil", "zoo": "doga",
    "aquarium": "bilim", "observation_deck": "manzara", "shopping_mall": "alisveris", "market": "alisveris",
    "night_club": "gece", "bar": "gece", "amusement_park": "macera", "science_museum": "bilim",
}


def yer_ara(sehir: str, merkez: dict | None = None, sorgu: str | None = None, adet: int = 20) -> list:
    """Places API (New) Text Search ile şehrin gerçek gezi noktaları (sistemin POI biçiminde)."""
    if not anahtar():
        return []
    govde = {"textQuery": sorgu or f"{sehir} gezilecek yerler", "languageCode": "tr", "pageSize": min(adet, 20)}
    if merkez:
        govde["locationBias"] = {"circle": {"center": {"latitude": merkez["lat"], "longitude": merkez["lon"]},
                                            "radius": 15000.0}}
    try:
        data = _post("https://places.googleapis.com/v1/places:searchText", govde,
                     "places.displayName,places.location,places.primaryType,places.types,places.googleMapsUri")
    except Exception:
        return []
    out = []
    for p in data.get("places", []):
        ad = (p.get("displayName") or {}).get("text")
        loc = p.get("location") or {}
        if not ad or "latitude" not in loc:
            continue
        turler = [p.get("primaryType")] + list(p.get("types") or [])
        kategori = next((_TUR_KATEGORI[t] for t in turler if t in _TUR_KATEGORI), "tarih")
        out.append({"isim": ad, "lat": loc["latitude"], "lon": loc["longitude"], "kategori": kategori,
                    "sure_dk": 60, "acilis": "09:00", "kapanis": "18:00", "ucret_tl": 0,
                    "etiketler": ["google"], "google_uri": p.get("googleMapsUri")})
    return out
