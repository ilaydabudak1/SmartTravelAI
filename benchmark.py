# benchmark.py — Rota algoritmalarının adil yarışı (sunum, slayt 21)
#
#   • 5, 10 ve 20 duraklı problemler × 30 rastgele örnek = 90 problem
#   • Algoritmalar: NN, NN + 2-opt, KKO, GA (Tablo 1 parametreleri) → 360 ölçüm (+ eşit bütçe)
#   • Referans: 5 durakta kaba kuvvet; 10–20 durakta OR-Tools (kuruluysa), yoksa
#     "en iyi bilinen" (tüm algoritmalar + 30 rastgele başlangıçlı 2-opt'un en iyisi)
#   • Sapma (%) = (L − L_ref) / L_ref × 100
#   • Eşleştirilmiş Wilcoxon işaretli sıralar testi, Holm düzeltmesi, Cohen d (eşleştirilmiş)
#   • Eşit bütçe koşulu: KKO 20×100 = 2.000 tur; GA 20×100 = 2.000 tur
#
# Kullanım:  python benchmark.py [--ornek 30] [--seed 2026] [--cikti data/benchmark]

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import time
from datetime import datetime

import routing

try:
    from scipy.stats import wilcoxon
except Exception:            # scipy yoksa test atlanır, betimsel istatistik yine üretilir
    wilcoxon = None


def problem_uret(n: int, rng: random.Random) -> list:
    """Bir şehir merkezi çevresinde (~6 km) rastgele n durak."""
    return [{"lat": 41.0 + rng.uniform(-0.03, 0.03), "lon": 29.0 + rng.uniform(-0.04, 0.04)} for _ in range(n)]


def ortools_referans(D: list) -> list | None:
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except Exception:
        return None
    n = len(D)
    yonetici = pywrapcp.RoutingIndexManager(n, 1, 0)
    model = pywrapcp.RoutingModel(yonetici)
    cb = model.RegisterTransitCallback(
        lambda i, j: int(D[yonetici.IndexToNode(i)][yonetici.IndexToNode(j)] * 1_000_000))
    model.SetArcCostEvaluatorOfAllVehicles(cb)
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.seconds = 2
    cozum = model.SolveWithParameters(p)
    if not cozum:
        return None
    tur, i = [], model.Start(0)
    while not model.IsEnd(i):
        tur.append(yonetici.IndexToNode(i))
        i = cozum.Value(model.NextVar(i))
    return tur


def en_iyi_bilinen(D: list, adaylar: list, rng: random.Random, baslangic: int = 30) -> list:
    en_iyi = min(adaylar, key=lambda t: routing.tur_uzunlugu(t, D))
    n = len(D)
    for _ in range(baslangic):
        g = list(range(1, n))
        rng.shuffle(g)
        t = routing.iki_opt([0] + g, D)
        if routing.tur_uzunlugu(t, D) < routing.tur_uzunlugu(en_iyi, D):
            en_iyi = t
    return en_iyi


def holm(p_degerleri: dict) -> dict:
    sirali = sorted(p_degerleri.items(), key=lambda kv: kv[1])
    m, onceki, sonuc = len(sirali), 0.0, {}
    for i, (k, p) in enumerate(sirali):
        duz = min(1.0, max(onceki, (m - i) * p))
        sonuc[k] = duz
        onceki = duz
    return sonuc


def cohen_d_eslesmis(a: list, b: list) -> float:
    fark = [x - y for x, y in zip(a, b)]
    sd = statistics.stdev(fark) if len(fark) > 1 else 0.0
    return statistics.mean(fark) / sd if sd > 0 else 0.0


def calistir(ornek: int, seed: int) -> dict:
    rng = random.Random(seed)
    algolar = {
        "nn": lambda D, s: routing.en_yakin_komsu(D),
        "nn_2opt": lambda D, s: routing.iki_opt(routing.en_yakin_komsu(D), D),
        "aco": lambda D, s: routing.karinca_koloni(D, seed=s),                       # 20 × 100 = 2.000 tur
        "ga": lambda D, s: routing.genetik_algoritma(D, seed=s),                     # 50 × 100 = 5.000 tur
        "ga_esit_butce": lambda D, s: routing.genetik_algoritma(D, populasyon=20, nesil=100, elit=2, seed=s),
    }
    olcumler = []
    for n in (5, 10, 20):
        for k in range(ornek):
            nok = problem_uret(n, rng)
            D = routing.mesafe_matrisi(nok)
            turlar = {}
            for ad, f in algolar.items():
                t0 = time.perf_counter()
                tur = routing._normalize(f(D, seed * 1000 + n * 100 + k))
                sure = time.perf_counter() - t0
                turlar[ad] = (tur, sure)
            if n <= 8:
                ref, ref_ad = routing.kaba_kuvvet(D), "kaba_kuvvet"
            else:
                ref = ortools_referans(D)
                ref_ad = "or_tools"
                if ref is None:
                    ref, ref_ad = en_iyi_bilinen(D, [t for t, _ in turlar.values()], rng), "en_iyi_bilinen"
            L_ref = routing.tur_uzunlugu(ref, D)
            for ad, (tur, sure) in turlar.items():
                L = routing.tur_uzunlugu(tur, D)
                olcumler.append({"n": n, "ornek": k, "algoritma": ad, "km": round(L, 4),
                                 "sapma_yuzde": round(max(0.0, (L - L_ref) / L_ref * 100), 4),
                                 "sure_sn": round(sure, 5), "referans": ref_ad})
        print(f"  n={n:>2}: {ornek} örnek tamam")
    return {"olcumler": olcumler}


def analiz(olcumler: list) -> dict:
    rapor = {}
    algolar = sorted({o["algoritma"] for o in olcumler})
    for n in sorted({o["n"] for o in olcumler}):
        tablo = {}
        for a in algolar:
            sat = sorted((o for o in olcumler if o["n"] == n and o["algoritma"] == a), key=lambda o: o["ornek"])
            sap = [o["sapma_yuzde"] for o in sat]
            tablo[a] = {
                "ortalama_sapma": round(statistics.mean(sap), 3),
                "ortanca_sapma": round(statistics.median(sap), 3),
                "referansi_bulma_orani": round(sum(1 for s in sap if s < 1e-6) / len(sap) * 100, 1),
                "ortalama_sure_sn": round(statistics.mean(o["sure_sn"] for o in sat), 4),
                "_sap": sap,
            }
        # KKO'yu diğerleriyle eşleştirilmiş karşılaştır
        p_ham, etkiler = {}, {}
        for diger in [a for a in algolar if a != "aco"]:
            a, b = tablo["aco"]["_sap"], tablo[diger]["_sap"]
            etkiler[diger] = round(cohen_d_eslesmis(b, a), 3)        # pozitif = KKO daha iyi
            if wilcoxon and any(x != y for x, y in zip(a, b)):
                try:
                    p_ham[diger] = float(wilcoxon(a, b, zero_method="wilcox").pvalue)
                except ValueError:
                    p_ham[diger] = 1.0
            else:
                p_ham[diger] = 1.0
        p_holm = holm(p_ham)
        karsilastirma = {d: {"p_ham": round(p_ham[d], 5), "p_holm": round(p_holm[d], 5),
                             "anlamli": p_holm[d] < 0.05, "cohen_d": etkiler[d]} for d in p_ham}
        ga_kotu = sum(1 for g, t in zip(tablo["ga"]["_sap"], tablo["nn_2opt"]["_sap"]) if g > t + 1e-9)
        for v in tablo.values():
            v.pop("_sap")
        rapor[n] = {"algoritmalar": tablo, "kko_karsilastirma": karsilastirma,
                    "ga_nn2opt_dan_kotu_ornek": ga_kotu}
    return rapor


def markdown(rapor: dict, ornek: int, seed: int) -> str:
    ad = {**routing.ALGORITMA_ADLARI, "ga_esit_butce": "GA (eşit bütçe, 2.000 tur)"}
    s = [f"# Rota algoritmaları deneyi\n\n{len(rapor) * ornek} problem ({ornek} örnek × {list(rapor)} durak), "
         f"seed={seed}, {datetime.now():%Y-%m-%d %H:%M}\n"]
    for n, r in rapor.items():
        s.append(f"\n## {n} durak\n\n| Algoritma | Ort. sapma % | Ortanca % | Referansı bulma % | Ort. süre (sn) |\n|---|---:|---:|---:|---:|")
        for a, v in sorted(r["algoritmalar"].items(), key=lambda kv: kv[1]["ortalama_sapma"]):
            s.append(f"| {ad.get(a, a)} | {v['ortalama_sapma']:.2f} | {v['ortanca_sapma']:.2f} | "
                     f"{v['referansi_bulma_orani']:.0f} | {v['ortalama_sure_sn']:.4f} |")
        s.append("\nKKO karşılaştırması (Wilcoxon, Holm düzeltmeli; Cohen d > 0 → KKO daha iyi):\n")
        s.append("| Karşı | p (ham) | p (Holm) | Anlamlı | Cohen d |\n|---|---:|---:|:---:|---:|")
        for d, v in r["kko_karsilastirma"].items():
            s.append(f"| {ad.get(d, d)} | {v['p_ham']:.4f} | {v['p_holm']:.4f} | {'✓' if v['anlamli'] else '–'} | {v['cohen_d']:.2f} |")
        s.append(f"\nGA'nın NN + 2-opt'tan kötü olduğu örnek sayısı: {r['ga_nn2opt_dan_kotu_ornek']}/{ornek}.")
    return "\n".join(s) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ornek", type=int, default=30)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--cikti", default=os.path.join("data", "benchmark"))
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    print(f"Deney başlıyor: {3 * a.ornek} problem…")
    t0 = time.perf_counter()
    veri = calistir(a.ornek, a.seed)
    rapor = analiz(veri["olcumler"])
    damga = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(a.cikti, f"olcumler_{damga}.json"), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.cikti, f"rapor_{damga}.json"), "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    md = markdown(rapor, a.ornek, a.seed)
    with open(os.path.join(a.cikti, f"rapor_{damga}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"Süre: {time.perf_counter() - t0:.1f} sn · çıktılar: {a.cikti}")


if __name__ == "__main__":
    main()
