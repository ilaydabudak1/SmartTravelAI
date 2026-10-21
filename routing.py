# routing.py — Rota Ajanı'nın algoritma çekirdeği (dil modeli yok, tamamen algoritma)
#
# Sunumdaki dört adım:
#   1) Mesafe   : Haversine (kuş uçuşu) mesafe matrisi
#   2) Yarış    : NN, NN + 2-opt, KKO (Karınca Koloni) ve GA (Genetik Algoritma)
#   3) Gerçek yol: OSRM / Google Maps ile yürüyüş mesafesi (ağ yoksa atlanır)
#   4) Saatler  : VRPTW benzeri — açılış/kapanış saatine göre yeniden sıralama
#
# Tüm turlar KAPALI turdur (başladığın yere dön) ve 0. düğüm başlangıç noktasıdır
# (otel / şehir merkezi). Rastgelelik `seed` ile tekrarlanabilir.

from __future__ import annotations

import itertools
import json
import math
import os
import random
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# PARAMETRELER (Sunum, Tablo 1)
# ---------------------------------------------------------------------------

ACO_VARSAYILAN = {"karinca": 20, "iterasyon": 100, "rho": 0.5, "alpha": 1.0, "beta": 2.0}
GA_VARSAYILAN = {"populasyon": 50, "nesil": 100, "turnuva": 3, "mutasyon": 0.1, "elit": 5}

ALGORITMA_ADLARI = {
    "nn": "En Yakın Komşu (NN)",
    "nn_2opt": "NN + 2-opt",
    "aco": "Karınca Koloni (KKO)",
    "ga": "Genetik Algoritma (GA)",
}


# ---------------------------------------------------------------------------
# 1) MESAFE
# ---------------------------------------------------------------------------

def haversine(a: dict, b: dict) -> float:
    """İki nokta arası kuş uçuşu mesafe (km). Noktalar {"lat":..,"lon":..}."""
    dlat = math.radians(b["lat"] - a["lat"])
    dlon = math.radians(b["lon"] - a["lon"])
    x = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"]))
         * math.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(x)))


def mesafe_matrisi(noktalar: list) -> list:
    n = len(noktalar)
    return [[0.0 if i == j else haversine(noktalar[i], noktalar[j]) for j in range(n)]
            for i in range(n)]


def tur_uzunlugu(tur: list, D: list) -> float:
    if len(tur) < 2:
        return 0.0
    return sum(D[tur[i]][tur[(i + 1) % len(tur)]] for i in range(len(tur)))


def _normalize(tur: list) -> list:
    """Turu 0. düğümden başlayacak şekilde döndürür (kapalı tur eşdeğeri)."""
    if 0 in tur:
        k = tur.index(0)
        return tur[k:] + tur[:k]
    return tur


# ---------------------------------------------------------------------------
# 2) ALGORİTMALAR
# ---------------------------------------------------------------------------

def en_yakin_komsu(D: list, baslangic: int = 0) -> list:
    """Açgözlü: her adımda en yakın ziyaret edilmemiş düğüme git."""
    n = len(D)
    if n == 0:
        return []
    tur = [baslangic]
    kalan = set(range(n)) - {baslangic}
    while kalan:
        son = tur[-1]
        sonraki = min(kalan, key=lambda j: D[son][j])
        tur.append(sonraki)
        kalan.remove(sonraki)
    return tur


def iki_opt(tur: list, D: list) -> list:
    """Kesişen iki kenarı ters çevirerek düzeltir; iyileşme kalmayana dek sürer."""
    n = len(tur)
    if n < 4:
        return list(tur)
    t = list(tur)
    iyilesti = True
    while iyilesti:
        iyilesti = False
        for i in range(1, n - 1):
            for k in range(i + 1, n):
                a, b = t[i - 1], t[i]
                c, d = t[k], t[(k + 1) % n]
                delta = (D[a][c] + D[b][d]) - (D[a][b] + D[c][d])
                if delta < -1e-12:
                    t[i:k + 1] = reversed(t[i:k + 1])
                    iyilesti = True
    return t


def karinca_koloni(D: list, karinca: int = 20, iterasyon: int = 100, rho: float = 0.5,
                   alpha: float = 1.0, beta: float = 2.0, seed: int | None = None,
                   q: float = 1.0) -> list:
    """Ant System (Dorigo vd., 1996).

    - Her karınca 0'dan başlar, olasılık ~ tau^alpha * (1/d)^beta ile ilerler.
    - Turdan sonra feromon (1-rho) oranında buharlaşır, her karınca Q/L bırakır.
    """
    n = len(D)
    if n <= 3:
        return list(range(n))
    rng = random.Random(seed)
    nn_len = tur_uzunlugu(en_yakin_komsu(D), D) or 1.0
    tau0 = karinca / nn_len
    tau = [[tau0] * n for _ in range(n)]
    eta = [[0.0 if i == j else 1.0 / max(D[i][j], 1e-9) for j in range(n)] for i in range(n)]

    en_iyi, en_iyi_L = None, float("inf")
    for _ in range(iterasyon):
        turlar = []
        for _ in range(karinca):
            tur = [0]
            ziyaret = [False] * n
            ziyaret[0] = True
            for _ in range(n - 1):
                i = tur[-1]
                adaylar, agirliklar = [], []
                for j in range(n):
                    if not ziyaret[j]:
                        adaylar.append(j)
                        agirliklar.append((tau[i][j] ** alpha) * (eta[i][j] ** beta))
                toplam = sum(agirliklar)
                if toplam <= 0:
                    j = rng.choice(adaylar)
                else:
                    r = rng.random() * toplam
                    birikim, j = 0.0, adaylar[-1]
                    for aday, w in zip(adaylar, agirliklar):
                        birikim += w
                        if birikim >= r:
                            j = aday
                            break
                tur.append(j)
                ziyaret[j] = True
            L = tur_uzunlugu(tur, D)
            turlar.append((tur, L))
            if L < en_iyi_L:
                en_iyi, en_iyi_L = tur, L
        # buharlaşma + birikim
        for i in range(n):
            for j in range(n):
                tau[i][j] *= (1.0 - rho)
        for tur, L in turlar:
            dep = q / max(L, 1e-9)
            for k in range(n):
                a, b = tur[k], tur[(k + 1) % n]
                tau[a][b] += dep
                tau[b][a] += dep
    return en_iyi


def _sirali_caprazlama(p1: list, p2: list, rng: random.Random) -> list:
    """Order Crossover (OX): 1. ebeveynden bir dilim + 2. ebeveynin sırasıyla kalanlar.
    0. düğüm (başlangıç) her zaman başta sabit tutulur."""
    g1, g2 = p1[1:], p2[1:]
    m = len(g1)
    if m < 2:
        return list(p1)
    a, b = sorted(rng.sample(range(m), 2))
    dilim = g1[a:b + 1]
    kalan = [g for g in g2 if g not in dilim]
    cocuk = kalan[:a] + dilim + kalan[a:]
    return [0] + cocuk


def genetik_algoritma(D: list, populasyon: int = 50, nesil: int = 100, turnuva: int = 3,
                      mutasyon: float = 0.1, elit: int = 5, seed: int | None = None) -> list:
    """Her rota bir birey; iyi rotalar çocuk yapar, kötüler elenir.
    Seçim: k'lı turnuva · Çaprazlama: OX · Mutasyon: iki durağın yer değiştirmesi · Seçkinlik."""
    n = len(D)
    if n <= 3:
        return list(range(n))
    rng = random.Random(seed)
    govde = list(range(1, n))

    def rastgele():
        g = govde[:]
        rng.shuffle(g)
        return [0] + g

    pop = [rastgele() for _ in range(populasyon)]
    for _ in range(nesil):
        pop.sort(key=lambda t: tur_uzunlugu(t, D))
        yeni = [list(t) for t in pop[:elit]]
        while len(yeni) < populasyon:
            e1 = min(rng.sample(pop, turnuva), key=lambda t: tur_uzunlugu(t, D))
            e2 = min(rng.sample(pop, turnuva), key=lambda t: tur_uzunlugu(t, D))
            cocuk = _sirali_caprazlama(e1, e2, rng)
            if rng.random() < mutasyon and n > 3:
                i, j = rng.sample(range(1, n), 2)
                cocuk[i], cocuk[j] = cocuk[j], cocuk[i]
            yeni.append(cocuk)
        pop = yeni
    return min(pop, key=lambda t: tur_uzunlugu(t, D))


def kaba_kuvvet(D: list) -> list:
    """Tüm (n-1)! turu dener — yalnızca küçük n (<=9) için referans."""
    n = len(D)
    if n <= 3:
        return list(range(n))
    en_iyi, en_iyi_L = None, float("inf")
    for perm in itertools.permutations(range(1, n)):
        if perm[0] > perm[-1]:          # ters yönlü eşleri atla: (n-1)!/2
            continue
        tur = [0, *perm]
        L = tur_uzunlugu(tur, D)
        if L < en_iyi_L:
            en_iyi, en_iyi_L = tur, L
    return en_iyi


# ---------------------------------------------------------------------------
# YARIŞ
# ---------------------------------------------------------------------------

@dataclass
class YarisSonucu:
    kazanan: str
    tur: list
    uzunluk_km: float
    sonuclar: dict = field(default_factory=dict)   # algo -> {km, sure_ms, sapma_yuzde, tur}

    def to_dict(self) -> dict:
        return {"kazanan": self.kazanan, "tur": self.tur,
                "uzunluk_km": self.uzunluk_km, "sonuclar": self.sonuclar}


def yaris(D: list, seed: int | None = 42, aco_param: dict | None = None,
          ga_param: dict | None = None) -> YarisSonucu:
    """Dört algoritmayı aynı problemde koşturur; en kısa turu kazanan seçer.
    Sapma (%) yarıştaki en iyi tura göre hesaplanır (n<=8 ise kaba kuvvet referansı)."""
    aco_p = {**ACO_VARSAYILAN, **(aco_param or {})}
    ga_p = {**GA_VARSAYILAN, **(ga_param or {})}
    kosucular = {
        "nn": lambda: en_yakin_komsu(D),
        "nn_2opt": lambda: iki_opt(en_yakin_komsu(D), D),
        "aco": lambda: karinca_koloni(D, aco_p["karinca"], aco_p["iterasyon"], aco_p["rho"],
                                      aco_p["alpha"], aco_p["beta"], seed=seed),
        "ga": lambda: genetik_algoritma(D, ga_p["populasyon"], ga_p["nesil"], ga_p["turnuva"],
                                        ga_p["mutasyon"], ga_p["elit"], seed=seed),
    }
    sonuclar = {}
    for ad, f in kosucular.items():
        t0 = time.perf_counter()
        tur = _normalize(f())
        sure = (time.perf_counter() - t0) * 1000
        sonuclar[ad] = {"km": round(tur_uzunlugu(tur, D), 3), "sure_ms": round(sure, 2), "tur": tur}

    referans = min(s["km"] for s in sonuclar.values())
    referans_kaynagi = "yaris_en_iyisi"
    if 3 < len(D) <= 8:
        referans = round(tur_uzunlugu(kaba_kuvvet(D), D), 3)
        referans_kaynagi = "kaba_kuvvet"
    for s in sonuclar.values():
        s["sapma_yuzde"] = round((s["km"] - referans) / referans * 100, 2) if referans > 0 else 0.0
        s["referans"] = referans_kaynagi

    # Eşitlikte daha hızlı olan kazanır
    kazanan = min(sonuclar, key=lambda k: (sonuclar[k]["km"], sonuclar[k]["sure_ms"]))
    return YarisSonucu(kazanan, sonuclar[kazanan]["tur"], sonuclar[kazanan]["km"], sonuclar)


# ---------------------------------------------------------------------------
# GÜNLERE BÖLME
# ---------------------------------------------------------------------------

def gunlere_bol(noktalar: list, gun_sayisi: int) -> list:
    """Noktaları coğrafi olarak yakın gruplara (gün) böler.

    Önce tüm noktalar için tek bir NN+2-opt turu çıkarılır, sonra tur ardışık ve
    dengeli parçalara kesilir — böylece her gün birbirine yakın yerlerden oluşur.
    Dönen liste: her gün için nokta indeksleri (0. düğüm = merkez hariç)."""
    if not noktalar:
        return [[] for _ in range(gun_sayisi)]
    merkez = {"lat": sum(p["lat"] for p in noktalar) / len(noktalar),
              "lon": sum(p["lon"] for p in noktalar) / len(noktalar)}
    tum = [merkez] + noktalar
    D = mesafe_matrisi(tum)
    tur = iki_opt(en_yakin_komsu(D), D)
    sira = [i - 1 for i in tur if i != 0]
    gun_sayisi = max(1, gun_sayisi)
    gunler, bas = [], 0
    for g in range(gun_sayisi):
        kalan_gun = gun_sayisi - g
        adet = math.ceil((len(sira) - bas) / kalan_gun) if kalan_gun else 0
        gunler.append(sira[bas:bas + adet])
        bas += adet
    return gunler


# ---------------------------------------------------------------------------
# 3) GERÇEK YOL (opsiyonel, ağ gerektirir)
# ---------------------------------------------------------------------------

def gercek_yol(noktalar: list, mod: str = "foot", timeout: float = 6.0) -> dict | None:
    """Sıralı noktalar için gerçek yürüyüş/araç mesafesi ve süresi.

    Öncelik: GOOGLE_MAPS_API_KEY varsa Google Directions, yoksa açık kaynak OSRM.
    Ağ yoksa ya da SMARTTRAVEL_OFFLINE=1 ise None döner (kuş uçuşu kullanılır)."""
    if os.getenv("SMARTTRAVEL_OFFLINE") == "1" or len(noktalar) < 2:
        return None
    gkey = os.getenv("GOOGLE_MAPS_API_KEY", "")
    try:
        if gkey:
            return _google_directions(noktalar, gkey, timeout)
        return _osrm(noktalar, mod, timeout)
    except Exception:
        return None


def _osrm(noktalar: list, mod: str, timeout: float) -> dict | None:
    profil = "foot" if mod == "foot" else "driving"
    sunucu = ("https://routing.openstreetmap.de/routed-foot" if profil == "foot"
              else "https://router.project-osrm.org")
    koord = ";".join(f"{p['lon']:.6f},{p['lat']:.6f}" for p in noktalar)
    url = f"{sunucu}/route/v1/{profil}/{koord}?overview=false&steps=false"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelAI/2.0 (edu)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    rota = data["routes"][0]
    return {
        "kaynak": "OSRM (OpenStreetMap)",
        "km": round(rota["distance"] / 1000, 2),
        "dakika": round(rota["duration"] / 60, 1),
        "bacaklar": [{"km": round(l["distance"] / 1000, 2), "dakika": round(l["duration"] / 60, 1)}
                     for l in rota.get("legs", [])],
    }


def _google_directions(noktalar: list, key: str, timeout: float) -> dict | None:
    params = {
        "origin": f"{noktalar[0]['lat']},{noktalar[0]['lon']}",
        "destination": f"{noktalar[-1]['lat']},{noktalar[-1]['lon']}",
        "mode": "walking", "key": key,
    }
    if len(noktalar) > 2:
        params["waypoints"] = "|".join(f"{p['lat']},{p['lon']}" for p in noktalar[1:-1])
    url = "https://maps.googleapis.com/maps/api/directions/json?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = json.loads(r.read())
    if data.get("status") != "OK":
        return None
    legs = data["routes"][0]["legs"]
    return {
        "kaynak": "Google Maps Directions",
        "km": round(sum(l["distance"]["value"] for l in legs) / 1000, 2),
        "dakika": round(sum(l["duration"]["value"] for l in legs) / 60, 1),
        "bacaklar": [{"km": round(l["distance"]["value"] / 1000, 2),
                      "dakika": round(l["duration"]["value"] / 60, 1)} for l in legs],
    }


# ---------------------------------------------------------------------------
# 4) SAATLER — VRPTW benzeri zaman penceresi kontrolü
# ---------------------------------------------------------------------------

def _dk(saat: str, varsayilan: int) -> int:
    try:
        h, m = str(saat).split(":")[:2]
        return int(h) * 60 + int(m)
    except Exception:
        return varsayilan


def _saat(dk: float) -> str:
    dk = int(round(dk))
    return f"{(dk // 60) % 24:02d}:{dk % 60:02d}"


def zaman_cizelgesi(sira: list, D: list, duraklar: list, baslangic_dk: int = 9 * 60,
                    hiz_kmh: float = 4.5, ogle_molasi: bool = True,
                    yurume_esigi_km: float = 1.5) -> dict:
    """Verilen sırada gün planını simüle eder.

    sira: D indeksleri (0 = başlangıç noktası, duraklar[i-1] = i. düğüm).
    Her durak: acilis/kapanis ("HH:MM") ve sure_dk. Erken varılırsa beklenir,
    kapanıştan sonra varılırsa ya da ziyaret kapanışa sığmazsa ihlal sayılır.
    ogle_molasi: saat 12:30'u geçince bir sonraki durağa gitmeden 60 dk öğle yemeği."""
    t = float(baslangic_dk)
    plan, ihlal, bekleme = [], 0, 0.0
    ogle_alindi = not ogle_molasi
    onceki = sira[0] if sira else 0
    for dugum in sira[1:]:
        if dugum == 0:
            continue
        if not ogle_alindi and t >= 12 * 60 + 30:
            plan.append({"ogle": True, "varis": _saat(t), "ayrilis": _saat(t + 60)})
            t += 60
            ogle_alindi = True
        d = duraklar[dugum - 1]
        km = D[onceki][dugum]
        # Kısa bacak yürünür; uzun bacakta toplu taşıma (~20 km/sa + 10 dk bekleme) varsayılır
        yol_dk = km / hiz_kmh * 60 if km <= yurume_esigi_km else 10 + km / 20 * 60
        t += yol_dk
        acilis = _dk(d.get("acilis"), 0)
        kapanis = _dk(d.get("kapanis"), 24 * 60 - 1)
        sure = int(d.get("sure_dk") or 60)
        if t < acilis:
            bekleme += acilis - t
            t = acilis
        sorun = t + sure > kapanis
        if sorun:
            ihlal += 1
        plan.append({"indeks": dugum, "varis": _saat(t), "ayrilis": _saat(t + sure),
                     "yol_dk": round(yol_dk), "ihlal": sorun})
        t += sure
        onceki = dugum
    if not ogle_alindi and plan and t >= 12 * 60 + 30:
        plan.append({"ogle": True, "varis": _saat(t), "ayrilis": _saat(t + 60)})
        t += 60
    return {"plan": plan, "ihlal": ihlal, "bekleme_dk": round(bekleme), "bitis": _saat(t)}


def zaman_pencereli_sirala(tur: list, D: list, duraklar: list, baslangic_dk: int = 9 * 60) -> dict:
    """Mesafe-optimal turu, açılış/kapanış saatlerine uyacak şekilde düzeltir.

    Strateji: önce turun iki yönünü dener; ihlal varsa ihlalli durakları tek tek
    çıkarıp en az ihlal + en kısa mesafe veren konuma yeniden ekler (yerleştirme
    sezgiseli). Tamamen çözülemeyen ihlaller raporlanır."""
    yonler = [tur, [tur[0]] + list(reversed(tur[1:]))]
    en_iyi = min(yonler, key=lambda s: (zaman_cizelgesi(s, D, duraklar, baslangic_dk)["ihlal"],
                                         tur_uzunlugu(s, D)))
    cizelge = zaman_cizelgesi(en_iyi, D, duraklar, baslangic_dk)
    duzeltme = 0
    for _ in range(len(tur)):
        if cizelge["ihlal"] == 0:
            break
        ihlalli = [p["indeks"] for p in cizelge["plan"] if p.get("ihlal")]
        iyilesti = False
        for dugum in ihlalli:
            taban = [x for x in en_iyi if x != dugum]
            adaylar = [taban[:k] + [dugum] + taban[k:] for k in range(1, len(taban) + 1)]
            aday = min(adaylar, key=lambda s: (zaman_cizelgesi(s, D, duraklar, baslangic_dk)["ihlal"],
                                                tur_uzunlugu(s, D)))
            yeni = zaman_cizelgesi(aday, D, duraklar, baslangic_dk)
            if yeni["ihlal"] < cizelge["ihlal"]:
                en_iyi, cizelge, iyilesti = aday, yeni, True
                duzeltme += 1
                break
        if not iyilesti:
            break
    return {"sira": en_iyi, "cizelge": cizelge, "duzeltme_sayisi": duzeltme,
            "km": round(tur_uzunlugu(en_iyi, D), 3)}
