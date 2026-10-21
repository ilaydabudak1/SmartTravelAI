import json
import os

import db
import memory


def test_bulanik_yer_eslesmesi():
    assert memory.ayni_yer_mi("Ayasofya", "AYASOFYA")
    assert memory.ayni_yer_mi("Galata Kulesi", "Galata Kulesi (Galata Tower)")
    assert memory.ayni_yer_mi("Topkapı Sarayı", "Topkapi Sarayi")
    assert memory.ayni_yer_mi("Kariye Camii (Chora)", "Kariye Camii")
    assert not memory.ayni_yer_mi("Galata Kulesi", "Kız Kulesi")
    assert not memory.ayni_yer_mi("Dolmabahçe Sarayı", "Topkapı Sarayı")


def test_ziyaret_kaydi_ve_sorgu():
    memory.ziyaretleri_kaydet("ali", "İstanbul", [{"isim": "Ayasofya", "kategori": "tarih"}, "Galata Kulesi"], 1)
    memory.ziyaretleri_kaydet("ali", "Ankara", ["Anıtkabir"], 2)
    assert len(memory.ziyaret_edilenler("ali")) == 3
    assert {z["yer"] for z in memory.ziyaret_edilenler("ali", "istanbul")} == {"Ayasofya", "Galata Kulesi"}
    assert memory.daha_once_gidildi_mi("ali", "ayasofya", "İstanbul")
    assert not memory.daha_once_gidildi_mi("veli", "Ayasofya")


def test_plan_silinince_hafiza_temizlenir():
    memory.ziyaretleri_kaydet("ali", "İstanbul", ["Ayasofya"], 7)
    memory.not_ekle("ali", "harika", "geri_bildirim", "İstanbul", 7, 5)
    memory.plan_hafizasini_sil("ali", 7)
    assert memory.ziyaret_edilenler("ali") == []
    assert memory.notlar("ali") == []


def test_dort_depo_ve_json_anlik_goruntu(gecici_db):
    memory.profil_kaydet("ali", {"ilgi_alanlari": ["muze"]})
    memory.ziyaretleri_kaydet("ali", "İzmir", ["Kordon"], 3)
    memory.algoritma_kaydet("ali", "İzmir", 1, 4, "aco", {"aco": {"km": 3.1, "sapma_yuzde": 0, "sure_ms": 50, "tur": [0, 1]},
                                                        "nn": {"km": 3.5, "sapma_yuzde": 12.9, "sure_ms": 1, "tur": [0, 1]}}, 3)
    memory.maliyet_kaydi_ekle("ali", "İzmir", 2, 1, "orta", 10000, 12000, 9000, 25.0, True, 0, {"toplam": 9000}, 3)
    yol = memory.json_disa_aktar("ali")
    assert yol and os.path.exists(yol)
    veri = json.load(open(yol, encoding="utf-8"))
    assert veri["profil"]["ilgi_alanlari"] == ["muze"]
    assert veri["seyahat_gecmisi"]["ziyaret_edilen_yerler"][0]["yer"] == "Kordon"
    assert veri["algoritma_istatistikleri"][0]["kazanan"] == "aco"
    assert veri["maliyet_kayitlari"][0]["kisisel_tl"] == 9000
    ozet = memory.algoritma_ozeti("ali")
    assert ozet["aco"]["kazanma"] == 1 and ozet["nn"]["ort_sapma_yuzde"] == 12.9


def test_hafiza_baglami_geri_bildirimleri_icerir():
    pid = db.save_travel_history("ali", {"destination": "İstanbul", "duration_days": 2, "budget": "orta"})
    memory.ziyaretleri_kaydet("ali", "İstanbul", ["Ayasofya"], pid)
    memory.not_ekle("ali", "", "geri_bildirim", "İstanbul", pid, 2, "müzeler", "kalabalık çarşılar")
    b = memory.hafiza_baglami("ali", "İstanbul")
    assert b["seyahat_sayisi"] == 1
    assert b["hedef_sehirde_gidilenler"] == ["Ayasofya"]
    assert b["geri_bildirimler"][0]["begenilmeyen"] == "kalabalık çarşılar"
