# hazirlik.py — "Gezi Hazırlığı" sekmesi: plana ve profile göre tatil listesi ve
# günlük harcama planı. Saf fonksiyonlar; arayüz app.py'de.

from __future__ import annotations

from datetime import date, datetime

import poi_data


def kalan_gun(baslangic: str, bugun: date | None = None) -> int | None:
    try:
        d = datetime.strptime(baslangic, "%Y-%m-%d").date()
    except Exception:
        return None
    return (d - (bugun or date.today())).days


def _mevsim(baslangic: str) -> str:
    try:
        ay = datetime.strptime(baslangic, "%Y-%m-%d").month
    except Exception:
        ay = date.today().month
    return {12: "kis", 1: "kis", 2: "kis", 3: "ilkbahar", 4: "ilkbahar", 5: "ilkbahar",
            6: "yaz", 7: "yaz", 8: "yaz"}.get(ay, "sonbahar")


TATIL_KATEGORILERI = {
    # anahtar: (başlık, ikon, ikon zemini — uygulamanın kahve/bej paletinden)
    "belgeler":   ("Belgeler & biletler", "🎫", "#f5ede6"),
    "gunes":      ("Güneş & plaj",        "☀️", "#f6efe0"),
    "bakim":      ("Kişisel bakım",       "🧴", "#eef0eb"),
    "kiyafet":    ("Kıyafet & ayakkabı",  "👕", "#ede8e0"),
    "saglik":     ("Sağlık & ilaç",       "🩺", "#f5e6e1"),
    "elektronik": ("Elektronik",          "🔌", "#f2ede6"),
    "diger":      ("Diğer",               "⭐", "#efebe4"),
    "ekipman":    ("Seyahat ekipmanları", "🧳", "#f3eadf"),
}


def tatil_listesi(sonuc: dict) -> list:
    """Fotoğraftaki 'Tatil Listesi' düzeninde kategoriler: [(anahtar, [madde, ...]), ...].
    Yapılacaklar (bilet, rezervasyon) ve bavul maddeleri plana, mevsime ve profile göre tek listede."""
    istek, profil = sonuc["istek"], sonuc["profil"]
    duraklar = [p for g in sonuc["rota"]["gunler"] for p in g["duraklar"]]
    kategoriler = {p.get("kategori") for p in duraklar}
    etiketler = {e for p in duraklar for e in (p.get("etiketler") or [])}
    sehir, gun, kisi = istek["sehir"], istek["gun"], istek["kisi"]
    mevsim = _mevsim(istek.get("baslangic", ""))
    yurtdisi = poi_data.yurtdisi_mi(sehir)
    k: dict = {a: [] for a in TATIL_KATEGORILERI}

    # Belgeler & biletler (yapılacaklar)
    if yurtdisi:
        k["belgeler"] += ["Pasaport (en az 6 ay geçerli)", f"{sehir} vize / giriş şartları", "Seyahat sağlık sigortası",
                          "Yerel para / yurt dışına açık kart"]
    else:
        k["belgeler"].append("Kimlik kartı")
    k["belgeler"].append(f"{istek.get('ulasim') or 'Ulaşım'} bileti ({kisi} kişi)")
    if gun > 1:
        k["belgeler"].append(f"Konaklama rezervasyonu ({gun - 1} gece)")
    for p in sorted((d for d in duraklar if d.get("ucret_tl")), key=lambda d: -float(d["ucret_tl"]))[:4]:
        k["belgeler"].append(f"{p['isim']} bileti")
    if istek.get("butce_kategorisi") == "luks":
        k["belgeler"].append("Akşam yemeği rezervasyonları")

    # Güneş & plaj — yalnızca yaz ya da planda sahil varsa
    if mevsim == "yaz" or "sahil" in kategoriler:
        k["gunes"] += ["Güneş kremi", "Şapka", "Güneş gözlüğü"]
        if "sahil" in kategoriler:
            k["gunes"] += ["Mayo", "Plaj havlusu", "Güneş sonrası krem"]

    # Kişisel bakım
    k["bakim"] += ["Diş fırçası ve macun", "Deodorant / parfüm", "Şampuan ve nemlendirici", "Tarak / fırça",
                   "Islak mendil"]

    # Kıyafet & ayakkabı
    k["kiyafet"] += [f"{min(gun, 7)} günlük kıyafet", "Pijama", "Çamaşır ve çorap", "Rahat yürüyüş ayakkabısı"]
    k["kiyafet"] += {"kis": ["Mont, bere ve eldiven", "Su geçirmez bot"],
                     "yaz": ["Terlik / sandalet", "İnce, nefes alan kıyafetler"],
                     "ilkbahar": ["İnce ceket"], "sonbahar": ["Hırka / ince mont"]}[mevsim]
    if "ibadet" in kategoriler:
        k["kiyafet"].append("Omuz/diz örten kıyafet, eşarp")
    if "gece" in kategoriler or istek.get("butce_kategorisi") == "luks":
        k["kiyafet"].append("Akşam için şık kıyafet")

    # Sağlık & ilaç
    k["saglik"] += ["Kişisel ilaçlar", "Ağrı kesici", "Yara bandı / küçük ilk yardım"]
    if profil.get("hareket_kisitli"):
        k["saglik"].append("Gerekli destek ekipmanları")

    # Elektronik
    k["elektronik"] += ["Telefon şarj aleti", "Powerbank", "Kulaklık", f"{sehir} çevrimdışı haritası",
                        "Planın PDF'i (Plan Sonucu → Planı İndir)"]
    if "fotograf" in etiketler or "manzara" in kategoriler:
        k["elektronik"].append("Fotoğraf makinesi / boş hafıza kartı")
    if sonuc["maliyet"]["kisisel"]["detay"].get("binis", 0) >= 3:
        k["elektronik"].append("Şehir ulaşım kartı / uygulaması")

    # Diğer
    if mevsim in ("ilkbahar", "sonbahar", "kis"):
        k["diger"].append("Katlanır şemsiye")
    k["diger"] += ["Su şişesi / matara", "Yolda okumak için kitap"]
    if profil.get("beslenme"):
        k["diger"].append(f"{', '.join(profil['beslenme']).capitalize()} atıştırmalık")
    if profil.get("aile"):
        k["diger"].append("Çocuk için oyuncak, yedek kıyafet")

    # Seyahat ekipmanları
    k["ekipman"].append("Bavul ve bavul kilidi")
    if "doga" in kategoriler or "yuruyus" in etiketler or gun > 1:
        k["ekipman"].append("Gün için küçük sırt çantası")
    if yurtdisi:
        k["ekipman"].append("Priz dönüştürücü")

    return [(a, maddeler) for a, maddeler in k.items() if maddeler]


def gunluk_harcama(sonuc: dict) -> list:
    """Gün başına kişi başı tahmini harcama: yemek + şehir içi ulaşım + o günün giriş ücretleri."""
    istek = sonuc["istek"]
    k = sonuc["maliyet"]["kisisel"]["kalemler"]
    kisi, gun = istek["kisi"], istek["gun"]
    yemek = k["yemek"] / kisi / gun
    ulasim = k["sehir_ici_ulasim"] / kisi / gun
    out = []
    for g in sonuc["rota"]["gunler"]:
        giris = sum(float(p.get("ucret_tl") or 0) for p in g["duraklar"])
        out.append({"Gün": f"Gün {g['gun']}", "Yemek": round(yemek), "Ulaşım": round(ulasim),
                    "Girişler": round(giris), "Toplam": round(yemek + ulasim + giris)})
    return out
