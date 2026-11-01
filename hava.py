# hava.py — Şehrin şu anki hava durumu (Open-Meteo; anahtar gerektirmez, ücretsiz)

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

# WMO hava kodu → Türkçe açıklama
_KOD = [
    ((0,), "açık"), ((1,), "az bulutlu"), ((2,), "parçalı bulutlu"), ((3,), "kapalı"),
    ((45, 48), "sisli"), ((51, 53, 55, 56, 57), "çisenti"), ((61,), "hafif yağmur"),
    ((63,), "yağmur"), ((65, 66, 67), "kuvvetli yağmur"), ((71, 73, 75, 77), "kar"),
    ((80, 81, 82), "sağanak"), ((85, 86), "kar sağanağı"), ((95, 96, 99), "gök gürültülü fırtına"),
]


def aciklama(kod: int) -> str:
    return next((metin for kodlar, metin in _KOD if kod in kodlar), "değişken")


def simdiki_hava(lat: float, lon: float, timeout: float = 5.0) -> dict | None:
    """{"sicaklik": 12.9, "durum": "hafif yağmur"} — ağ yoksa ya da hata olursa None."""
    if os.getenv("SMARTTRAVEL_OFFLINE") == "1":
        return None
    params = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "current": "temperature_2m,weather_code"}
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelAI/2.0 (egitim projesi)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            simdi = json.loads(r.read())["current"]
        return {"sicaklik": round(float(simdi["temperature_2m"]), 1), "durum": aciklama(int(simdi["weather_code"]))}
    except Exception:
        return None
