import random

import pytest

import routing


def rastgele_noktalar(n, seed):
    rng = random.Random(seed)
    return [{"lat": 41.0 + rng.uniform(-0.05, 0.05), "lon": 29.0 + rng.uniform(-0.05, 0.05)} for _ in range(n)]


def gecerli_tur(tur, n):
    return sorted(tur) == list(range(n)) and tur[0] == 0


def test_haversine_bilinen_mesafe():
    # İstanbul – Ankara kuş uçuşu ≈ 350 km
    km = routing.haversine({"lat": 41.0082, "lon": 28.9784}, {"lat": 39.9334, "lon": 32.8597})
    assert 345 < km < 355


@pytest.mark.parametrize("n", [5, 8, 12])
def test_tum_algoritmalar_gecerli_permutasyon(n):
    D = routing.mesafe_matrisi(rastgele_noktalar(n, n))
    assert gecerli_tur(routing.en_yakin_komsu(D), n)
    assert gecerli_tur(routing._normalize(routing.iki_opt(routing.en_yakin_komsu(D), D)), n)
    assert gecerli_tur(routing.karinca_koloni(D, karinca=10, iterasyon=20, seed=1), n)
    assert gecerli_tur(routing.genetik_algoritma(D, populasyon=20, nesil=20, seed=1), n)


@pytest.mark.parametrize("seed", range(5))
def test_iki_opt_nn_den_kotu_olamaz(seed):
    D = routing.mesafe_matrisi(rastgele_noktalar(15, seed))
    nn = routing.en_yakin_komsu(D)
    assert routing.tur_uzunlugu(routing.iki_opt(nn, D), D) <= routing.tur_uzunlugu(nn, D) + 1e-9


def test_kko_kucuk_problemlerde_en_iyiye_yakin():
    # Saf Ant System her örnekte kesin en iyiyi garanti etmez (sunumda %77);
    # küçük problemlerde çoğunlukla bulmalı ve hiçbirinde %3'ten fazla sapmamalı.
    tam, sapmalar = 0, []
    for seed in range(10):
        D = routing.mesafe_matrisi(rastgele_noktalar(7, seed))
        en_iyi = routing.tur_uzunlugu(routing.kaba_kuvvet(D), D)
        aco = routing.tur_uzunlugu(routing.karinca_koloni(D, seed=seed), D)
        sapmalar.append((aco - en_iyi) / en_iyi)
        tam += aco <= en_iyi + 1e-9
    assert tam >= 7
    assert max(sapmalar) < 0.03


def test_yaris_kazanani_en_kisa_tur():
    D = routing.mesafe_matrisi(rastgele_noktalar(10, 42))
    y = routing.yaris(D, seed=3)
    assert y.kazanan in routing.ALGORITMA_ADLARI
    assert y.uzunluk_km == min(s["km"] for s in y.sonuclar.values())
    assert all(s["sapma_yuzde"] >= 0 for s in y.sonuclar.values())


def test_yaris_kaba_kuvvet_referansi_kucuk_n():
    D = routing.mesafe_matrisi(rastgele_noktalar(6, 9))
    y = routing.yaris(D, seed=1)
    assert all(s["referans"] == "kaba_kuvvet" for s in y.sonuclar.values())


def test_gunlere_bol_dengeli_ve_eksiksiz():
    nok = rastgele_noktalar(11, 5)
    gunler = routing.gunlere_bol(nok, 3)
    assert len(gunler) == 3
    assert sorted(i for g in gunler for i in g) == list(range(11))
    assert max(map(len, gunler)) - min(map(len, gunler)) <= 1


def test_zaman_penceresi_ihlali_duzeltilir():
    # 2. durak sadece sabah açık; mesafe-optimal sıra onu öğleden sonraya koyuyor
    merkez = {"lat": 41.0, "lon": 29.0}
    duraklar = [
        {"lat": 41.001, "lon": 29.001, "acilis": "09:00", "kapanis": "20:00", "sure_dk": 120},
        {"lat": 41.030, "lon": 29.030, "acilis": "09:00", "kapanis": "11:00", "sure_dk": 60},
        {"lat": 41.002, "lon": 29.002, "acilis": "09:00", "kapanis": "20:00", "sure_dk": 120},
    ]
    D = routing.mesafe_matrisi([merkez] + duraklar)
    kotu_sira = [0, 1, 3, 2]
    assert routing.zaman_cizelgesi(kotu_sira, D, duraklar, 9 * 60)["ihlal"] >= 1
    sonuc = routing.zaman_pencereli_sirala(kotu_sira, D, duraklar, 9 * 60)
    assert sonuc["cizelge"]["ihlal"] == 0
    assert sonuc["sira"][1] == 2      # sabah kapanan yer öne alındı


def test_ogle_molasi_eklenir():
    merkez = {"lat": 41.0, "lon": 29.0}
    duraklar = [{"lat": 41.0 + i / 1000, "lon": 29.0, "acilis": "08:00", "kapanis": "22:00", "sure_dk": 120}
                for i in range(1, 4)]
    D = routing.mesafe_matrisi([merkez] + duraklar)
    c = routing.zaman_cizelgesi([0, 1, 2, 3], D, duraklar, 9 * 60)
    assert sum(1 for p in c["plan"] if p.get("ogle")) == 1


def test_gercek_yol_cevrimdisi_none():
    assert routing.gercek_yol([{"lat": 41, "lon": 29}, {"lat": 41.01, "lon": 29.01}]) is None
