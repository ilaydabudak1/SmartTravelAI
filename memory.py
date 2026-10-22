# memory.py — Kalıcı veri / hafıza katmanı (JSON + SQLite)
#
# "Sistem öğrenmiyor, hatırlıyor." Dört depo:
#   1) Kullanıcı profilleri       → kullanici_profilleri
#   2) Seyahat geçmişi            → travel_plans (db.py) + ziyaret_edilen_yerler + seyahat_notlari
#   3) Algoritma istatistikleri   → algoritma_istatistikleri
#   4) Maliyet kayıtları          → maliyet_kayitlari (+ eski maliyet_gecmisi)
#
# Kaynak gerçek SQLite'tır; her yazımdan sonra kullanıcının tüm hafızası
# data/hafiza/<kullanici>.json dosyasına okunabilir bir anlık görüntü olarak da yazılır.
# Hafıza, bir sonraki planda Profil Ajanı'na bağlam (in-context) olarak verilir;
# model ağırlıkları değişmez.

from __future__ import annotations

import difflib
import json
import os
import re
import unicodedata
from datetime import datetime

import db

_TR = str.maketrans("ıİğĞüÜşŞöÖçÇâÂîÎûÛ", "iIgGuUsSoOcCaAiIuU")
_GENEL_KELIMELER = {
    "the", "of", "muzesi", "museum", "camii", "mosque", "sarayi", "palace", "kulesi",
    "tower", "parki", "park", "meydani", "square", "kalesi", "castle", "carsisi",
}


def _simdi() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def normalize(metin: str) -> str:
    """Yer adlarını karşılaştırılabilir hale getirir: küçük harf, Türkçe karakter,
    noktalama ve parantez içi açıklamalar temizlenir."""
    if not metin:
        return ""
    s = str(metin).translate(_TR).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ayni_yer_mi(a: str, b: str) -> bool:
    """Bulanık eşleştirme: 'Ayasofya' ~ 'Ayasofya-i Kebir Camii', 'Galata Kulesi' ~ 'Galata Tower'."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ka = [w for w in na.split() if w not in _GENEL_KELIMELER]
    kb = [w for w in nb.split() if w not in _GENEL_KELIMELER]
    ca, cb = " ".join(ka), " ".join(kb)
    if ca and cb:
        if ca == cb:
            return True
        kisa, uzun = sorted((ca, cb), key=len)
        if len(kisa) >= 5 and re.search(rf"\b{re.escape(kisa)}\b", uzun):
            return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.88


# ---------------------------------------------------------------------------
# ŞEMA
# ---------------------------------------------------------------------------

def init_memory():
    db.init_db()
    with db._conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS kullanici_profilleri (
                username TEXT PRIMARY KEY,
                profil_json TEXT NOT NULL,
                guncelleme TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS ziyaret_edilen_yerler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                plan_id INTEGER,
                sehir TEXT, yer TEXT NOT NULL, yer_norm TEXT NOT NULL,
                kategori TEXT, lat REAL, lon REAL,
                tarih TEXT NOT NULL
            )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ziyaret_user ON ziyaret_edilen_yerler(username, sehir)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS algoritma_istatistikleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT, plan_id INTEGER, sehir TEXT, gun INTEGER,
                durak_sayisi INTEGER, kazanan TEXT,
                sonuc_json TEXT NOT NULL, tarih TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS maliyet_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL, plan_id INTEGER, sehir TEXT, gun INTEGER,
                kisi INTEGER, kategori TEXT,
                butce_limiti REAL, standart_tl REAL, kisisel_tl REAL, tasarruf_yuzde REAL,
                butce_icinde INTEGER, muzakere_turu INTEGER,
                kalemler_json TEXT, tarih TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS seyahat_notlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL, plan_id INTEGER, sehir TEXT,
                tur TEXT NOT NULL,          -- serbest_not | seyahat_notu | geri_bildirim
                metin TEXT, puan INTEGER,
                begenilen TEXT, begenilmeyen TEXT,
                tarih TEXT NOT NULL
            )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_notlar_user ON seyahat_notlari(username)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS hazirlik_durumu (
                username TEXT NOT NULL, plan_anahtari TEXT NOT NULL,
                isaretli_json TEXT NOT NULL, guncelleme TEXT NOT NULL,
                PRIMARY KEY (username, plan_anahtari)
            )""")


# ---------------------------------------------------------------------------
# 1) PROFİL
# ---------------------------------------------------------------------------

def profil_kaydet(username: str, profil: dict):
    with db._conn() as c:
        c.execute("INSERT OR REPLACE INTO kullanici_profilleri VALUES (?, ?, ?)",
                  (username, json.dumps(profil, ensure_ascii=False, default=str), _simdi()))
    json_disa_aktar(username)


def profil_oku(username: str) -> dict:
    with db._conn() as c:
        r = c.execute("SELECT profil_json FROM kullanici_profilleri WHERE username=?",
                      (username,)).fetchone()
    try:
        return json.loads(r["profil_json"]) if r else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 2) SEYAHAT GEÇMİŞİ — ziyaret edilen yerler + notlar
# ---------------------------------------------------------------------------

def ziyaretleri_kaydet(username: str, sehir: str, yerler: list, plan_id: int | None = None):
    zaman = _simdi()
    with db._conn() as c:
        for y in yerler:
            ad = y.get("isim") or y.get("name") if isinstance(y, dict) else str(y)
            if not ad:
                continue
            c.execute(
                "INSERT INTO ziyaret_edilen_yerler (username, plan_id, sehir, yer, yer_norm, kategori, lat, lon, tarih) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (username, plan_id, sehir, ad, normalize(ad),
                 (y.get("kategori") if isinstance(y, dict) else None),
                 (y.get("lat") if isinstance(y, dict) else None),
                 (y.get("lon") if isinstance(y, dict) else None), zaman))
    json_disa_aktar(username)


def ziyaret_edilenler(username: str, sehir: str | None = None) -> list:
    q = "SELECT sehir, yer, kategori, plan_id, tarih FROM ziyaret_edilen_yerler WHERE username=?"
    args = [username]
    rows = []
    with db._conn() as c:
        rows = [dict(r) for r in c.execute(q + " ORDER BY id DESC", args).fetchall()]
    if sehir:
        ns = normalize(sehir)
        rows = [r for r in rows if ns and (ns in normalize(r["sehir"]) or normalize(r["sehir"]) in ns)]
    return rows


def plan_hafizasini_sil(username: str, plan_id: int):
    """Bir plan silindiğinde ona bağlı ziyaret/maliyet/algoritma/not kayıtlarını da siler."""
    with db._conn() as c:
        for tablo in ("ziyaret_edilen_yerler", "maliyet_kayitlari",
                      "algoritma_istatistikleri", "seyahat_notlari"):
            c.execute(f"DELETE FROM {tablo} WHERE username=? AND plan_id=?", (username, plan_id))
    json_disa_aktar(username)


def not_ekle(username: str, metin: str, tur: str = "serbest_not", sehir: str | None = None,
             plan_id: int | None = None, puan: int | None = None,
             begenilen: str = "", begenilmeyen: str = ""):
    if not (metin or "").strip() and not begenilen and not begenilmeyen and puan is None:
        return
    with db._conn() as c:
        c.execute(
            "INSERT INTO seyahat_notlari (username, plan_id, sehir, tur, metin, puan, begenilen, begenilmeyen, tarih) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (username, plan_id, sehir, tur, (metin or "").strip(), puan,
             begenilen.strip(), begenilmeyen.strip(), _simdi()))
    json_disa_aktar(username)


def notlar(username: str, tur: str | None = None, limit: int = 50) -> list:
    q = "SELECT * FROM seyahat_notlari WHERE username=?"
    args: list = [username]
    if tur:
        q += " AND tur=?"
        args.append(tur)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with db._conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


# ---------------------------------------------------------------------------
# 3) ALGORİTMA İSTATİSTİKLERİ
# ---------------------------------------------------------------------------

def algoritma_kaydet(username: str, sehir: str, gun: int, durak_sayisi: int,
                     kazanan: str, sonuclar: dict, plan_id: int | None = None):
    sade = {k: {kk: vv for kk, vv in v.items() if kk != "tur"} for k, v in sonuclar.items()}
    with db._conn() as c:
        c.execute(
            "INSERT INTO algoritma_istatistikleri (username, plan_id, sehir, gun, durak_sayisi, kazanan, sonuc_json, tarih) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, plan_id, sehir, gun, durak_sayisi, kazanan,
             json.dumps(sade, ensure_ascii=False), _simdi()))


# ---------------------------------------------------------------------------
# 4) MALİYET KAYITLARI
# ---------------------------------------------------------------------------

def maliyet_kaydi_ekle(username: str, sehir: str, gun: int, kisi: int, kategori: str,
                       butce_limiti: float | None, standart_tl: float, kisisel_tl: float,
                       tasarruf_yuzde: float, butce_icinde: bool, muzakere_turu: int,
                       kalemler: dict, plan_id: int | None = None):
    with db._conn() as c:
        c.execute(
            "INSERT INTO maliyet_kayitlari (username, plan_id, sehir, gun, kisi, kategori, butce_limiti, "
            "standart_tl, kisisel_tl, tasarruf_yuzde, butce_icinde, muzakere_turu, kalemler_json, tarih) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (username, plan_id, sehir, gun, kisi, kategori, butce_limiti, standart_tl, kisisel_tl,
             tasarruf_yuzde, int(bool(butce_icinde)), muzakere_turu,
             json.dumps(kalemler, ensure_ascii=False), _simdi()))
    # Eski rapor ekranı için eski tabloya da yaz
    try:
        db.maliyet_kaydet(username, sehir, gun, kategori, standart_tl, kisisel_tl, tasarruf_yuzde)
    except Exception:
        pass
    json_disa_aktar(username)


def maliyet_kayitlari(username: str) -> list:
    with db._conn() as c:
        rows = c.execute("SELECT * FROM maliyet_kayitlari WHERE username=? ORDER BY id DESC",
                         (username,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["kalemler"] = json.loads(d.pop("kalemler_json") or "{}")
        except Exception:
            d["kalemler"] = {}
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# GEZİ HAZIRLIĞI — işaretlenen yapılacaklar / bavul maddeleri
# ---------------------------------------------------------------------------

def hazirlik_oku(username: str, plan_anahtari: str) -> set:
    with db._conn() as c:
        r = c.execute("SELECT isaretli_json FROM hazirlik_durumu WHERE username=? AND plan_anahtari=?",
                      (username, plan_anahtari)).fetchone()
    try:
        return set(json.loads(r["isaretli_json"])) if r else set()
    except Exception:
        return set()


def hazirlik_kaydet(username: str, plan_anahtari: str, isaretli: set):
    with db._conn() as c:
        c.execute("INSERT OR REPLACE INTO hazirlik_durumu VALUES (?, ?, ?, ?)",
                  (username, plan_anahtari, json.dumps(sorted(isaretli), ensure_ascii=False), _simdi()))


def hazirlik_not_oku(username: str, plan_anahtari: str) -> str:
    kayit = hazirlik_oku(username, plan_anahtari + "|not")
    return next(iter(kayit), "")


def hazirlik_not_kaydet(username: str, plan_anahtari: str, metin: str):
    hazirlik_kaydet(username, plan_anahtari + "|not", {metin.strip()} if metin.strip() else set())


# ---------------------------------------------------------------------------
# HAFIZA BAĞLAMI — Profil Ajanı'na verilen özet
# ---------------------------------------------------------------------------

def hafiza_baglami(username: str, hedef_sehir: str | None = None) -> dict:
    planlar = db.get_travel_plans(username)
    gecmis = [{
        "sehir": p.get("destination"), "baslangic": p.get("start_date"),
        "gun": p.get("duration_days"), "kategori": p.get("budget"),
        "maliyet_tl": p.get("estimated_cost"), "mbti": p.get("mbti_type"),
    } for p in planlar[-10:]]

    ziyaret = ziyaret_edilenler(username)
    sehre_gore: dict = {}
    for z in ziyaret:
        sehre_gore.setdefault(z["sehir"] or "?", []).append(z["yer"])
    kategori_sayac: dict = {}
    for z in ziyaret:
        if z.get("kategori"):
            kategori_sayac[z["kategori"]] = kategori_sayac.get(z["kategori"], 0) + 1

    tum_notlar = notlar(username, limit=30)
    geri = [n for n in tum_notlar if n["tur"] == "geri_bildirim"]
    serbest = [n for n in tum_notlar if n["tur"] == "serbest_not"]
    maliyetler = maliyet_kayitlari(username)
    ort_harcama = (round(sum(m["kisisel_tl"] / max(1, m["gun"] or 1) for m in maliyetler) / len(maliyetler))
                   if maliyetler else None)

    return {
        "gecmis_seyahatler": gecmis,
        "seyahat_sayisi": len(planlar),
        "ziyaret_edilen_yerler": sehre_gore,
        "hedef_sehirde_gidilenler": [z["yer"] for z in ziyaret_edilenler(username, hedef_sehir)] if hedef_sehir else [],
        "sik_kategoriler": sorted(kategori_sayac, key=kategori_sayac.get, reverse=True)[:5],
        "geri_bildirimler": [{"sehir": g["sehir"], "puan": g["puan"], "begenilen": g["begenilen"],
                              "begenilmeyen": g["begenilmeyen"], "not": g["metin"]} for g in geri[:8]],
        "onceki_serbest_notlar": [n["metin"] for n in serbest[:5] if n["metin"]],
        "gunluk_ortalama_harcama_tl": ort_harcama,
        "butce_asim_sayisi": sum(1 for m in maliyetler if not m["butce_icinde"]),
        "onceki_profil": profil_oku(username),
    }


# ---------------------------------------------------------------------------
# JSON ANLIK GÖRÜNTÜ
# ---------------------------------------------------------------------------

def _json_yolu(username: str) -> str:
    guvenli = re.sub(r"[^A-Za-z0-9_.-]+", "_", username) or "kullanici"
    return os.path.join(db.VERI_KLASORU, "hafiza", f"{guvenli}.json")


def json_disa_aktar(username: str) -> str | None:
    """Kullanıcının dört deposunu tek bir okunabilir JSON dosyasına yazar."""
    try:
        yol = _json_yolu(username)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with db._conn() as c:
            algo = [dict(r) for r in c.execute(
                "SELECT sehir, gun, durak_sayisi, kazanan, sonuc_json, tarih FROM algoritma_istatistikleri "
                "WHERE username=? ORDER BY id DESC LIMIT 50", (username,)).fetchall()]
        for a in algo:
            try:
                a["sonuclar"] = json.loads(a.pop("sonuc_json"))
            except Exception:
                pass
        veri = {
            "kullanici": username,
            "guncelleme": _simdi(),
            "profil": profil_oku(username),
            "seyahat_gecmisi": {
                "ziyaret_edilen_yerler": ziyaret_edilenler(username),
                "notlar": notlar(username, limit=200),
            },
            "algoritma_istatistikleri": algo,
            "maliyet_kayitlari": maliyet_kayitlari(username),
        }
        tmp = yol + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, yol)
        return yol
    except Exception:
        return None


init_memory()
