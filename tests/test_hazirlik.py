from datetime import date

import hazirlik
import plan_render
from multiagent import Orkestrator


def _plan(**kw):
    istek = {"sehir": "İstanbul", "gun": 2, "kisi": 2, "butce_kategorisi": "orta", "mbti": "INFJ",
             "serbest_not": "Kalabalık sevmem, vejetaryenim.", "ulasim": "Uçak", "baslangic": "2026-12-10"}
    istek.update(kw)
    return Orkestrator(gercek_yol=False).planla(istek, "hz")


def test_hazirlik_listeleri_plana_gore():
    s = _plan()
    liste = dict(hazirlik.tatil_listesi(s))
    assert any("Uçak" in m for m in liste["belgeler"])
    assert any("Konaklama" in m for m in liste["belgeler"])
    gh = hazirlik.gunluk_harcama(s)
    assert len(gh) == 2 and all(r["Toplam"] >= r["Yemek"] for r in gh)


def test_yurtdisi_belgeleri():
    s = _plan(sehir="Roma")
    liste = dict(hazirlik.tatil_listesi(s))
    assert any("Pasaport" in m for m in liste["belgeler"])
    assert any("Priz" in m for m in liste["ekipman"])


def test_kalan_gun():
    assert hazirlik.kalan_gun("2026-12-10", date(2026, 12, 1)) == 9
    assert hazirlik.kalan_gun("bozuk") is None


def test_plan_bolumleri_uretilir():
    s = _plan()
    for f in (plan_render.plan_ozet_html, plan_render.butce_dokum_html, plan_render.ipuclari_html):
        assert len(f(s)) > 100
    assert any("vejetaryen" in t for t in plan_render.ipuclari(s))


def test_tatil_listesi_kategorileri():
    s = _plan()                                   # Aralık, İstanbul, vejetaryen
    liste = dict(hazirlik.tatil_listesi(s))
    assert set(liste) <= set(hazirlik.TATIL_KATEGORILERI)
    assert any("Uçak" in m for m in liste["belgeler"])
    assert "gunes" not in liste, "kışın ve sahil yoksa güneş/plaj kartı çıkmamalı"
    assert any("Mont" in m for m in liste["kiyafet"])
    assert any("Vejetaryen" in m for m in liste["diger"])
    yaz = dict(hazirlik.tatil_listesi(_plan(sehir="Antalya", baslangic="2026-07-10")))
    assert "gunes" in yaz


def test_hazirlik_notu_saklanir():
    import memory
    memory.hazirlik_not_kaydet("ali", "k1", "Pasaport fotokopisi")
    assert memory.hazirlik_not_oku("ali", "k1") == "Pasaport fotokopisi"
    memory.hazirlik_not_kaydet("ali", "k1", "")
    assert memory.hazirlik_not_oku("ali", "k1") == ""
