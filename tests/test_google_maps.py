import urllib.parse

import google_maps
import routing


def test_anahtarsiz_linkler_google():
    p = {"isim": "Galata Kulesi", "lat": 41.0256, "lon": 28.9741}
    url = google_maps.harita_linki(p, "İstanbul")
    assert url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Galata Kulesi, İstanbul" == urllib.parse.unquote(url.split("query=")[1])

    merkez = {"lat": 41.0, "lon": 29.0}
    rota = google_maps.rota_linki(merkez, [p, {"isim": "X", "lat": 41.01, "lon": 28.98}])
    q = urllib.parse.parse_qs(urllib.parse.urlparse(rota).query)
    assert rota.startswith("https://www.google.com/maps/dir/?")
    assert q["travelmode"] == ["walking"] and q["origin"] == q["destination"]
    assert q["waypoints"][0].count("|") == 1


def test_cevrimdisi_anahtarli_servisler_cagrilmaz(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-anahtari")      # offline bayrağı anahtarı devre dışı bırakır
    assert google_maps.anahtar() == ""
    assert google_maps.yol_tarifi([{"lat": 41, "lon": 29}, {"lat": 41.01, "lon": 29.01}]) is None
    assert google_maps.yer_ara("İstanbul") == []
    assert routing.gercek_yol([{"lat": 41, "lon": 29}, {"lat": 41.01, "lon": 29.01}]) is None


def test_routes_api_yaniti_cozulur(monkeypatch):
    monkeypatch.delenv("SMARTTRAVEL_OFFLINE", raising=False)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-anahtari")
    yakalanan = {}

    def sahte_post(url, govde, maske):
        yakalanan.update(url=url, govde=govde, maske=maske)
        return {"routes": [{"distanceMeters": 2500, "duration": "1800s",
                            "legs": [{"distanceMeters": 1000, "duration": "720s"},
                                     {"distanceMeters": 1500, "duration": "1080s"}]}]}

    monkeypatch.setattr(google_maps, "_post", sahte_post)
    r = google_maps.yol_tarifi([{"lat": 41, "lon": 29}, {"lat": 41.01, "lon": 29.01}, {"lat": 41, "lon": 29}])
    assert r == {"kaynak": "Google Maps", "km": 2.5, "dakika": 30.0,
                 "bacaklar": [{"km": 1.0, "dakika": 12.0}, {"km": 1.5, "dakika": 18.0}]}
    assert yakalanan["url"].endswith("directions/v2:computeRoutes")
    assert yakalanan["govde"]["travelMode"] == "WALK" and len(yakalanan["govde"]["intermediates"]) == 1


def test_places_yaniti_poi_bicimine_cevrilir(monkeypatch):
    monkeypatch.delenv("SMARTTRAVEL_OFFLINE", raising=False)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-anahtari")
    monkeypatch.setattr(google_maps, "_post", lambda url, g, m: {"places": [
        {"displayName": {"text": "Pera Müzesi"}, "location": {"latitude": 41.03, "longitude": 28.97},
         "primaryType": "museum", "googleMapsUri": "https://maps.google.com/?cid=1"},
        {"displayName": {"text": "Eksik konum"}}]})
    yerler = google_maps.yer_ara("İstanbul")
    assert len(yerler) == 1 and yerler[0]["kategori"] == "muze" and yerler[0]["google_uri"]
