import db
import memory
import pytest
from multiagent import (Orkestrator, ProfilAjani, Pano, hafizaya_kaydet, notu_cozumle, bulunma_eki,
                        _istek_dogrula)
from llm import LLMYonlendirici, json_ayikla


def _istek(**kw):
    i = {"sehir": "İstanbul", "gun": 2, "kisi": 1, "butce_kategorisi": "orta", "mbti": "ENFP",
         "serbest_not": "", "ulasim": "Otobüs", "baslangic": "2026-11-05"}
    i.update(kw)
    return i


# ── serbest not ────────────────────────────────────────────────────────────

def test_serbest_not_cozumleme():
    c = notu_cozumle("Kalabalık sevmem, müzelere bayılırım. Gece hayatı istemiyorum. Vejetaryenim, öğrenciyim.")
    assert "muze" in c["ilgi"]
    assert "gece" in c["kacin"] and "gece" not in c["ilgi"]
    assert "kalabalik" in c["etiket_kacin"]
    assert "vejetaryen" in c["beslenme"]
    assert c["butce_hassas"]


def test_serbest_not_testten_onceliklidir():
    pano = Pano()
    p = ProfilAjani(pano, LLMYonlendirici()).calis(
        _istek(mbti="ESTP", serbest_not="Doğa yürüyüşü ve sakin parklar istiyorum, alışveriş sevmem."),
        memory.hafiza_baglami("x"))
    assert p["ilgi_alanlari"][0] == "doga"
    assert "alisveris" in p["kacinilacaklar"] and "alisveris" not in p["ilgi_alanlari"]
    assert p["tempo"] == "sakin"
    assert pano.mesajlar, "ajan panoya mesaj bırakmalı"


def test_turkce_bulunma_eki():
    assert bulunma_eki("İstanbul") == "İstanbul'da"
    assert bulunma_eki("Eskişehir") == "Eskişehir'de"
    assert bulunma_eki("Paris") == "Paris'te"
    assert bulunma_eki("Roma") == "Roma'da"


def test_json_ayikla():
    assert json_ayikla('```json\n{"a": 1}\n```') == {"a": 1}
    assert json_ayikla('Tabii! İşte: {"yerler": []} umarım beğenirsin') == {"yerler": []}
    assert json_ayikla("json değil") is None


def test_llm_yoksa_kural_tabanli():
    assert set(LLMYonlendirici().durum().values()) == {"kural tabanlı (LLM yok)"}


# ── uçtan uca ──────────────────────────────────────────────────────────────

def test_uctan_uca_plan_ve_mesajlasma():
    s = Orkestrator(gercek_yol=False).planla(_istek(), "ayse")
    yerler = [p for g in s["rota"]["gunler"] for p in g["duraklar"]]
    assert len(s["rota"]["gunler"]) == 2 and len(yerler) >= 4
    gonderenler = {m["gonderen"] for m in s["mesajlar"]}
    assert {"profil", "plan", "elestirmen", "rota", "maliyet"} <= gonderenler
    assert s["maliyet"]["kisisel"]["kalemler"]["toplam"] > 0
    assert len(s["restoran_plani"]) == 2


def test_gecmis_yerler_tekrar_onerilmez():
    s1 = Orkestrator(gercek_yol=False).planla(_istek(), "ayse")
    pid = db.save_travel_history("ayse", {"destination": "İstanbul"})
    hafizaya_kaydet("ayse", s1, pid)
    s2 = Orkestrator(gercek_yol=False).planla(_istek(), "ayse")
    ilk = [p["isim"] for g in s1["rota"]["gunler"] for p in g["duraklar"]]
    ikinci = [p["isim"] for g in s2["rota"]["gunler"] for p in g["duraklar"]]
    assert ikinci, "ikinci plan boş olmamalı"
    assert not any(memory.ayni_yer_mi(a, b) for a in ilk for b in ikinci)
    assert "tekrar önerilmedi" in s2["profil"]["seyahat_notu"]


def test_elle_eklenen_gecmis_de_haric_tutulur():
    memory.ziyaretleri_kaydet("can", "İstanbul", ["Ayasofya", "Topkapı Sarayı", "Galata Kulesi"], None)
    s = Orkestrator(gercek_yol=False).planla(_istek(gun=3), "can")
    yerler = [p["isim"] for g in s["rota"]["gunler"] for p in g["duraklar"]]
    assert not {"Ayasofya", "Topkapı Sarayı", "Galata Kulesi"} & set(yerler)


def test_geri_bildirim_sonraki_profile_yansir():
    pid = db.save_travel_history("deniz", {"destination": "İzmir"})
    memory.not_ekle("deniz", "", "geri_bildirim", "İzmir", pid, 2, "", "gece hayatı ve barlar")
    s = Orkestrator(gercek_yol=False).planla(_istek(mbti="ESFP"), "deniz")
    assert "gece" in s["profil"]["kacinilacaklar"]
    assert all(p["kategori"] != "gece" for g in s["rota"]["gunler"] for p in g["duraklar"])


def test_butce_kisiti_muzakere_ile_saglanir():
    s = Orkestrator(gercek_yol=False).planla(
        _istek(butce_kategorisi="luks", butce_limiti=40000, kisi=2, ulasim="Uçak"), "zeynep")
    assert s["muzakere"], "bütçe aşıldığında maliyet ajanı müzakere etmeli"
    assert s["butce_icinde"]
    assert s["maliyet"]["kisisel"]["kalemler"]["toplam"] <= 40000
    assert any(m["gonderen"] == "maliyet" and m["tur"] == "karar" for m in s["mesajlar"])


def test_karsilanamayan_butce_raporlanir():
    s = Orkestrator(gercek_yol=False).planla(_istek(butce_limiti=1000, gun=4), "zeynep")
    assert not s["butce_icinde"]
    assert s["butce_farki_tl"] < 0
    assert any(m["tur"] == "uyari" and m["gonderen"] == "maliyet" for m in s["mesajlar"])


def test_tasarruf_kalemlerden_hesaplanir():
    s = Orkestrator(gercek_yol=False).planla(_istek(), "ayse")
    std = s["maliyet"]["standart"]["kalemler"]["toplam"]
    kis = s["maliyet"]["kisisel"]["kalemler"]["toplam"]
    assert s["tasarruf_yuzde"] == pytest.approx((std - kis) / std * 100, abs=0.06)


def test_bilinmeyen_sehir_cevrimdisi_anlamli_hata():
    with pytest.raises(RuntimeError):
        Orkestrator(gercek_yol=False).planla(_istek(sehir="Hiçbiryerabad"), "ayse")


def test_istek_dogrulama():
    i = _istek_dogrula({"sehir": "  Roma ", "gun": 99, "kisi": 0, "butce_kategorisi": "x", "butce_limiti": "-5"})
    assert (i["sehir"], i["gun"], i["kisi"], i["butce_kategorisi"], i["butce_limiti"]) == ("Roma", 14, 1, "orta", None)
    with pytest.raises(ValueError):
        _istek_dogrula({"sehir": " "})


def test_kapali_saatteki_durak_cikarilir():
    from multiagent import RotaAjani
    merkez_yakin = [{"isim": f"Müze {i}", "lat": 39.76 + i * 0.002, "lon": 30.52, "kategori": "muze",
                     "sure_dk": 120, "acilis": "09:00", "kapanis": "12:00", "ucret_tl": 0, "etiketler": []}
                    for i in range(4)]
    pano = Pano()
    profil = {"ilgi_alanlari": ["muze"], "baslangic_saati": "09:00"}
    r = RotaAjani(pano, LLMYonlendirici()).calis(_istek(sehir="Eskişehir", gun=1), profil, merkez_yakin, False)
    g = r["gunler"][0]
    assert g["cizelge"]["ihlal"] == 0
    assert r["cikarilan"], "sığmayan durak çıkarılmalı"
    assert any("kapanış" in m.icerik for m in pano.mesajlar)


def test_vejetaryene_et_restorani_onerilmez():
    from multiagent import _restoran_ata
    rota = {"merkez": {"lat": 41.0, "lon": 29.0},
            "gunler": [{"gun": 1, "duraklar": [{"isim": "A", "lat": 41.0, "lon": 29.0}],
                        "cizelge": {"plan": [{"indeks": 1}, {"ogle": True}]}}]}
    restoranlar = [{"isim": "Köfteci Ali", "lat": 41.0001, "lon": 29.0, "fiyat": "orta", "mutfak": "köfte"},
                   {"isim": "Yeşil Tabak", "lat": 41.004, "lon": 29.0, "fiyat": "orta", "mutfak": "vejetaryen"}]
    plan = _restoran_ata(rota, restoranlar, {"butce_kategorisi": "orta"}, {"beslenme": ["vejetaryen"]})
    assert plan[0]["ogle"]["isim"] == "Yeşil Tabak"


def test_kategori_cozumleme():
    from multiagent import _kategori_coz
    assert _kategori_coz("Tarih", "Pera Müzesi") == "muze"
    assert _kategori_coz("Müze / Sanat", "X") == "muze"
    assert _kategori_coz("museum", "Louvre") == "muze"
    assert _kategori_coz("tarih", "Gülhane Parkı") == "doga"
    assert _kategori_coz("bilinmiyor", "Galata Kulesi") == "tarih"


def test_on_pilot_destinasyon_ve_istanbul_pilot():
    import poi_data
    assert len(poi_data.PILOT_DESTINASYONLAR) == 10
    assert poi_data.PILOT_DESTINASYONLAR[0] == "İstanbul"
    assert all(len(poi_data.yerel_poi(d)) >= 9 for d in poi_data.PILOT_DESTINASYONLAR)


def test_ulke_ve_sehir_algilama():
    import poi_data
    beklenen = {"ispanya": "Barcelona", "İspanya": "Barcelona", "Hollanda": "Amsterdam", "türkiye": "İstanbul",
                "Ege": "İzmir", "istanbul": "İstanbul", "Barselona": "Barcelona", "ROMA": "Roma"}
    for girdi, sehir in beklenen.items():
        assert poi_data.hedef_coz(girdi)["sehir"] == sehir, girdi


def test_ulke_girilince_plan_pilot_sehirde_kurulur():
    s = Orkestrator(gercek_yol=False).planla(_istek(sehir="ispanya"), "ulke")
    assert s["istek"]["sehir"] == "Barcelona"
    assert s["hedef_notu"] and "Barcelona" in s["hedef_notu"]
    assert not s["reddedilenler"] or all("halüsinasyon" not in r["neden"] for r in s["reddedilenler"])


def test_daginik_onerilerde_merkez_en_yogun_kume():
    from multiagent import _yogun_merkez
    yerler = [{"lat": 41.40, "lon": 2.17}, {"lat": 41.39, "lon": 2.16}, {"lat": 41.38, "lon": 2.18},
              {"lat": 40.42, "lon": -3.70}]                       # 3 Barcelona + 1 Madrid
    m = _yogun_merkez(yerler)
    assert abs(m["lat"] - 41.39) < 0.05
