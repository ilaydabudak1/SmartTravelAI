# plan_render.py — Çok ajanlı planın arayüz parçaları (HTML)
#
# gunluk_html() çıktısı app.py'deki "gun-baslik" bölücüsüyle uyumludur: her gün bir
# <div class="gun-baslik"> ile başlar, kartlar data-type="gezi|yemek|genel" taşır.
# Kullanıcıdan ya da LLM'den gelen her metin html.escape ile kaçırılır.

from __future__ import annotations

import html

import google_maps
from routing import ALGORITMA_ADLARI

_E = html.escape

KATEGORI_ETIKET = {
    "tarih": "🏛️ Tarih", "muze": "🖼️ Müze", "sanat": "🎨 Sanat", "ibadet": "🕌 İbadet",
    "doga": "🌿 Doğa", "manzara": "🌄 Manzara", "alisveris": "🛍️ Alışveriş", "yemek": "🍽️ Yemek",
    "gece": "🌙 Gece", "sahil": "🌊 Sahil", "mahalle": "🏘️ Mahalle", "bilim": "🔭 Bilim",
    "macera": "🧗 Macera",
}
ETIKET_ADLARI = {"kalabalik": "👥 Kalabalık", "sakin": "🍃 Sakin", "yuruyus": "🥾 Uzun yürüyüş",
                 "gece": "🌙 Gece", "ikonik": "⭐ İkonik", "fotograf": "📷 Fotoğraf", "yerel": "🧺 Yerel"}
GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

CSS = """<style>
.plan-wrap { font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif; max-width: 820px; margin: 0 auto; }
.gun-baslik { font-size: 15px; font-weight: 800; color: #2c2416; padding: 18px 0 8px;
              border-bottom: 2px solid #c4b5a0; margin-bottom: 6px; }
.gun-ozet { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 4px; }
.chip { font-size:11px; font-weight:600; padding:3px 10px; border-radius:20px;
        background:#f2ede6; color:#7a6a5a; border:1px solid #e8dfd4; }
.chip.yesil { background:#eef0eb; color:#4f6b4f; border-color:#c0d0b8; }
.chip.turuncu { background:#fbeee4; color:#b0643a; border-color:#ecc9ae; }
.aktivite-kart { display:flex; margin:12px 0; border-radius:14px; overflow:hidden;
                 background:#fffefb; border:1px solid #e8dfd4; box-shadow:0 1px 6px rgba(44,36,22,.06); }
.aktivite-kart[data-type=gezi] { border-left:4px solid #8b7355; }
.aktivite-kart[data-type=yemek] { border-left:4px solid #d4976a; }
.aktivite-kart[data-type=genel] { border-left:4px solid #b5a99a; }
.saat-col { min-width:78px; max-width:78px; display:flex; flex-direction:column; align-items:center;
            padding:16px 6px; background:#f2ede6; border-right:1px solid #e8dfd4; }
.saat-txt { font-size:14px; font-weight:800; color:#2c2416; }
.saat-alt { font-size:10px; color:#9a8a7a; margin-top:3px; }
.sira-no { margin-top:8px; width:24px; height:24px; border-radius:50%; background:#8b7355; color:#fff;
           font-size:11px; font-weight:800; display:flex; align-items:center; justify-content:center; }
.icerik-col { flex:1; padding:14px 18px; }
.mekan-adi { font-size:14px; font-weight:700; color:#2c2416; margin:0 0 6px; display:flex;
             align-items:center; gap:8px; flex-wrap:wrap; }
.harita-btn { font-size:11px; font-weight:700; color:#fff !important; background:#8b7355; padding:3px 10px;
              border-radius:20px; text-decoration:none; }
.neden { font-size:12.5px; color:#4a3f35; line-height:1.7; margin:0; }
.yol-notu { font-size:11.5px; color:#7a6a5a; margin-top:6px; }
.uyari { font-size:11.5px; color:#b0643a; margin-top:6px; font-weight:600; }
</style>"""


def _harita_linki(p: dict, sehir: str = "") -> str:
    return p.get("google_uri") or google_maps.harita_linki(p, sehir)


def _gun_etiketi(baslangic: str, g: int) -> str:
    from datetime import datetime, timedelta
    try:
        d = datetime.strptime(baslangic, "%Y-%m-%d") + timedelta(days=g - 1)
        return f"Gün {g} · {d.day:02d}.{d.month:02d} {GUN_ADLARI[d.weekday()]}"
    except Exception:
        return f"Gün {g}"


def _restoran_karti(saat: str, etiket: str, r: dict | None, beslenme_notu: str, sehir: str = "") -> str:
    if not r:
        return (f'<div class="aktivite-kart" data-type="yemek"><div class="saat-col">'
                f'<div class="saat-txt">{saat}</div><div class="saat-alt">{etiket}</div></div>'
                f'<div class="icerik-col"><div class="mekan-adi">{etiket} molası</div>'
                f'<p class="neden">Yakındaki yerel bir lokanta önerilir.{(" " + _E(beslenme_notu)) if beslenme_notu else ""}</p>'
                f'</div></div>')
    fiyat = {"ekonomik": "₺", "orta": "₺₺", "luks": "₺₺₺"}.get(r.get("fiyat"), "")
    return (f'<div class="aktivite-kart" data-type="yemek"><div class="saat-col">'
            f'<div class="saat-txt">{saat}</div><div class="saat-alt">{etiket}</div></div>'
            f'<div class="icerik-col"><div class="mekan-adi">🍽️ {_E(r["isim"])} '
            f'<a class="harita-btn" href="{_harita_linki(r, sehir)}" target="_blank">Harita</a></div>'
            f'<p class="neden">{_E(r.get("mutfak", ""))} {fiyat} · son duraktan {r.get("mesafe_km", 0)} km'
            f'{(" · " + _E(beslenme_notu)) if beslenme_notu else ""}</p></div></div>')


def gunluk_html(sonuc: dict) -> str:
    rota, istek = sonuc["rota"], sonuc["istek"]
    sehir = istek.get("sehir", "")
    restoran = {r["gun"]: r for r in sonuc.get("restoran_plani", [])}
    parcalar = [CSS, '<div class="plan-wrap">']
    for g in rota["gunler"]:
        duraklar = g["duraklar"]
        yaris = g["yaris"]
        gy = g.get("gercek_yol")
        parcalar.append(f'<div class="gun-baslik">{_E(_gun_etiketi(istek.get("baslangic", ""), g["gun"]))}</div>')
        chipler = [f'<span class="chip">📍 {len(duraklar)} durak</span>',
                   f'<span class="chip">📏 {g["km"]:.1f} km kuş uçuşu</span>']
        if gy:
            chipler.append(f'<span class="chip yesil">🚶 {gy["km"]} km gerçek yol · {gy["dakika"]:.0f} dk</span>')
        chipler.append(f'<span class="chip turuncu">🏆 {ALGORITMA_ADLARI[yaris["kazanan"]]}</span>')
        if g.get("vrptw_duzeltme"):
            chipler.append(f'<span class="chip">🕒 saatlere göre {g["vrptw_duzeltme"]} düzeltme</span>')
        chipler.append(f'<span class="chip">🏁 bitiş {g["cizelge"]["bitis"]}</span>')
        chipler.append(f'<a class="harita-btn" href="{_E(google_maps.rota_linki(rota["merkez"], duraklar))}" '
                       f'target="_blank">🗺️ Günün rotasını Google Maps’te aç</a>')
        parcalar.append(f'<div class="gun-ozet">{"".join(chipler)}</div>')

        r = restoran.get(g["gun"], {})
        bes = r.get("not", "")
        sira = 0
        for olay in g["cizelge"]["plan"]:
            if olay.get("ogle"):
                parcalar.append(_restoran_karti(olay["varis"], "Öğle", r.get("ogle"), bes, sehir))
                continue
            p = duraklar[sira]
            sira += 1
            ucret = float(p.get("ucret_tl") or 0)
            ucret_txt = "Ücretsiz" if not ucret else f"~{ucret:,.0f} TL / kişi"
            yol = (f'<div class="yol-notu">↪ önceki noktadan ~{olay["yol_dk"]} dk · kalış {p.get("sure_dk", 60)} dk · '
                   f'açık {_E(p.get("acilis", ""))}–{_E(p.get("kapanis", ""))} · {ucret_txt}</div>')
            uyari = ('<div class="uyari">⚠️ Kapanış saatine yakın — erken gitmeyi düşünün.</div>'
                     if olay.get("ihlal") else "")
            parcalar.append(
                f'<div class="aktivite-kart" data-type="gezi"><div class="saat-col">'
                f'<div class="saat-txt">{olay["varis"]}</div><div class="saat-alt">→ {olay["ayrilis"]}</div>'
                f'<div class="sira-no">{sira}</div></div>'
                f'<div class="icerik-col"><div class="mekan-adi">{_E(p["isim"])} '
                f'<span class="chip">{KATEGORI_ETIKET.get(p.get("kategori"), _E(str(p.get("kategori"))))}</span>'
                f'<a class="harita-btn" href="{_harita_linki(p, sehir)}" target="_blank">Harita</a></div>'
                f'<p class="neden">{_E(p.get("neden") or "")}</p>{yol}{uyari}</div></div>')
        # Akşam yemeği en erken 19:00; gün daha geç biterse bitişte
        aksam_saat = max(g["cizelge"]["bitis"], "19:00")
        parcalar.append(_restoran_karti(aksam_saat, "Akşam", r.get("aksam"), bes, sehir))
    parcalar.append("</div>")
    return "".join(parcalar)


# ---------------------------------------------------------------------------
# Kartlar
# ---------------------------------------------------------------------------

def seyahat_notu_karti(sonuc: dict) -> str:
    p = sonuc["profil"]
    ilgi = "".join(f'<span style="background:#eef0eb;color:#4f6b4f;border-radius:20px;padding:3px 10px;'
                   f'font-size:11px;font-weight:600">{KATEGORI_ETIKET.get(k, _E(k))}</span>'
                   for k in p.get("ilgi_alanlari", [])[:6])
    kacin = "".join(f'<span style="background:#fbeee4;color:#b0643a;border-radius:20px;padding:3px 10px;'
                    f'font-size:11px;font-weight:600">✕ {KATEGORI_ETIKET.get(k) or ETIKET_ADLARI.get(k) or _E(k)}</span>'
                    for k in p.get("kacinilacaklar", []) + p.get("kacinilacak_etiketler", []))
    oruntu = "".join(f"<li>{_E(o)}</li>" for o in p.get("gecmis_oruntuler", []))
    return f"""
<div style="background:linear-gradient(135deg,#fffaf3,#f6efe4);border:1px solid #e3d5c2;border-radius:16px;
            padding:18px 22px;margin-bottom:16px;font-family:'Inter',sans-serif">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <div style="font-size:11px;font-weight:800;color:#8b7355;text-transform:uppercase;letter-spacing:.6px">
      📝 Kişisel Seyahat Notun</div>
  </div>
  <div style="font-size:13.5px;color:#3a2f24;line-height:1.8">{_E(p.get('seyahat_notu', ''))}</div>
  <div style="font-size:12px;color:#6b5a48;margin-top:10px"><b>Seyahat tarzın:</b> {_E(p.get('seyahat_tarzi', ''))}</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">{ilgi}{kacin}</div>
  {f'<ul style="font-size:12px;color:#6b5a48;margin:10px 0 0;padding-left:18px">{oruntu}</ul>' if oruntu else ''}
</div>"""


KALEM_ADLARI = [("konaklama", "Konaklama"), ("yemek", "Yemek"), ("sehir_ici_ulasim", "Şehir içi ulaşım"),
                ("aktivite", "Aktivite / giriş"), ("sehirlerarasi", "Şehirlerarası")]


# ---------------------------------------------------------------------------
# Plan sekmesi — kullanıcıya dönük zengin bölümler
# ---------------------------------------------------------------------------

_KART = ("background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:16px 18px;"
         "margin-bottom:16px;font-family:Inter,sans-serif")
_BASLIK = ("font-size:11px;font-weight:800;color:#8b7355;text-transform:uppercase;"
           "letter-spacing:.6px;margin-bottom:10px")
_FIYAT = {"ekonomik": "₺", "orta": "₺₺", "luks": "₺₺₺"}


def tum_duraklar(sonuc: dict) -> list:
    return [p for g in sonuc["rota"]["gunler"] for p in g["duraklar"]]


def _ilk_varis(g: dict) -> str:
    return next((o["varis"] for o in g["cizelge"]["plan"] if not o.get("ogle")), "-")


def plan_ozet_html(sonuc: dict) -> str:
    istek, rota = sonuc["istek"], sonuc["rota"]
    duraklar = tum_duraklar(sonuc)
    kisi, gun = istek["kisi"], istek["gun"]
    toplam = sonuc["maliyet"]["kisisel"]["kalemler"]["toplam"]
    giris = sum(float(p.get("ucret_tl") or 0) for p in duraklar)
    ucretsiz = sum(1 for p in duraklar if not p.get("ucret_tl"))
    km = rota.get("toplam_gercek_km") or rota["toplam_km"]
    km_etiket = "gerçek yol" if rota.get("toplam_gercek_km") else "kuş uçuşu"

    def kutu(deger, etiket, alt=""):
        alt_html = f'<div style="font-size:10.5px;color:#a89580">{alt}</div>' if alt else ""
        return (f'<div style="background:#f6f1ea;border:1px solid #e8dfd4;border-radius:12px;padding:12px 10px;text-align:center">'
                f'<div style="font-size:22px;font-weight:900;color:#2c2416;line-height:1.1">{deger}</div>'
                f'<div style="font-size:11px;color:#7a6a5a;margin-top:4px">{etiket}</div>{alt_html}</div>')

    kutular = "".join([
        kutu(len(duraklar), "gezi noktası", f"{ucretsiz} tanesi ücretsiz"),
        kutu(f"{km:.1f} km", "toplam rota", km_etiket),
        kutu(f"{giris:,.0f} TL", "giriş ücretleri", "kişi başı"),
        kutu(f"{toplam / kisi:,.0f} TL", "kişi başı toplam", f"günde ~{toplam / kisi / gun:,.0f} TL"),
    ])

    gunler = ""
    for g in rota["gunler"]:
        zincir = " → ".join(_E(p["isim"]) for p in g["duraklar"]) or "Serbest gün"
        kats = sorted({KATEGORI_ETIKET.get(p.get("kategori"), "") for p in g["duraklar"]} - {""})
        gunler += (
            f'<div style="display:flex;gap:14px;padding:11px 0;border-bottom:1px solid #f0ebe4">'
            f'<div style="min-width:92px"><div style="font-size:13px;font-weight:800;color:#2c2416">Gün {g["gun"]}</div>'
            f'<div style="font-size:11px;color:#9a8a7a">{_ilk_varis(g)} – {g["cizelge"]["bitis"]}</div></div>'
            f'<div style="flex:1"><div style="font-size:12.5px;color:#3a2f24;line-height:1.6">{zincir}</div>'
            f'<div style="font-size:11px;color:#9a8a7a;margin-top:3px">{" · ".join(kats)} · {g["km"]:.1f} km</div></div></div>')
    return (f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;'
            f'font-family:Inter,sans-serif">{kutular}</div>'
            f'<div style="{_KART}"><div style="{_BASLIK}">🗓️ Günlere genel bakış</div>{gunler}</div>')


def butce_dokum_html(sonuc: dict) -> str:
    k = sonuc["maliyet"]["kisisel"]["kalemler"]
    istek = sonuc["istek"]
    kisi, gun, toplam = istek["kisi"], istek["gun"], k["toplam"] or 1
    renk = {"konaklama": "#8b7355", "yemek": "#d4976a", "sehir_ici_ulasim": "#9eaa8f",
            "aktivite": "#c4a882", "sehirlerarasi": "#b5a99a"}
    satir = ""
    for anahtar, ad in KALEM_ADLARI:
        v = k[anahtar]
        satir += (f'<div style="padding:8px 0;border-bottom:1px solid #f3efe9">'
                  f'<div style="display:flex;justify-content:space-between;font-size:12.5px;color:#3a2f24">'
                  f'<span>{ad}</span><span><b>{v:,.0f} TL</b>'
                  f'<span style="color:#a89580;font-size:11px"> · %{v / toplam * 100:.0f}</span></span></div>'
                  f'<div style="background:#efe8de;border-radius:4px;height:6px;margin-top:5px">'
                  f'<div style="background:{renk[anahtar]};height:6px;border-radius:4px;width:{max(2, v / toplam * 100):.0f}%"></div></div></div>')
    limit = istek.get("butce_limiti")
    limit_satir = (f'<div style="font-size:12px;color:#6b5a48;margin-top:4px">Belirlediğin bütçe: {limit:,.0f} TL · '
                   f'kalan: {limit - toplam:,.0f} TL</div>') if limit and limit >= toplam else ""
    return (f'<div style="{_KART}"><div style="{_BASLIK}">💰 Bütçe dökümü</div>{satir}'
            f'<div style="display:flex;justify-content:space-between;font-size:14px;font-weight:800;color:#2c2416;padding-top:10px">'
            f'<span>Toplam</span><span>{toplam:,.0f} TL</span></div>'
            f'<div style="font-size:12px;color:#6b5a48;margin-top:4px">Kişi başı {toplam / kisi:,.0f} TL · '
            f'günlük {toplam / gun:,.0f} TL</div>{limit_satir}'
            f'<div style="font-size:10.5px;color:#a89580;margin-top:8px">Rakamlar tahminidir; gerçek fiyatlar değişebilir.</div></div>')


def restoran_listesi_html(sonuc: dict) -> str:
    satir = ""
    for r in sonuc.get("restoran_plani", []):
        for etiket, ogun in (("Öğle", r.get("ogle")), ("Akşam", r.get("aksam"))):
            if not ogun:
                continue
            satir += (f'<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f3efe9;font-size:12.5px">'
                      f'<span style="min-width:96px;color:#9a8a7a">Gün {r["gun"]} · {etiket}</span>'
                      f'<span style="flex:1;color:#2c2416"><b>{_E(ogun["isim"])}</b> '
                      f'<span style="color:#9a8a7a">{_E(ogun.get("mutfak", ""))} {_FIYAT.get(ogun.get("fiyat"), "")}</span></span>'
                      f'<a href="{_harita_linki(ogun, sonuc["istek"].get("sehir", ""))}" target="_blank" style="color:#8b7355;font-size:11.5px">harita</a></div>')
    if not satir:
        return ""
    return f'<div style="{_KART}"><div style="{_BASLIK}">🍽️ Yeme-içme önerileri</div>{satir}</div>'


def yedek_yerler_html(sonuc: dict) -> str:
    yedek = sonuc.get("yedek_yerler") or []
    if not yedek:
        return ""
    kart = ""
    for p in yedek[:6]:
        ucret = "Ücretsiz" if not p.get("ucret_tl") else f"~{float(p['ucret_tl']):,.0f} TL"
        kart += (f'<div style="background:#f8f4ee;border:1px solid #ece3d7;border-radius:12px;padding:12px 14px">'
                 f'<div style="font-size:13px;font-weight:700;color:#2c2416">{_E(p["isim"])}</div>'
                 f'<div style="font-size:11px;color:#9a8a7a;margin:3px 0 6px">{KATEGORI_ETIKET.get(p.get("kategori"), "")} · '
                 f'{ucret} · ~{p.get("sure_dk", 60)} dk</div>'
                 f'<div style="font-size:12px;color:#4a3f35;line-height:1.55">{_E(p.get("neden") or "")}</div>'
                 f'<a href="{_harita_linki(p, sonuc["istek"].get("sehir", ""))}" target="_blank" style="font-size:11.5px;color:#8b7355">haritada gör</a></div>')
    return (f'<div style="{_KART}"><div style="{_BASLIK}">✨ Vaktin kalırsa</div>'
            f'<div style="font-size:12px;color:#6b5a48;margin-bottom:10px">Profiline uyan ama programa sığmayan yerler.</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px">{kart}</div></div>')


def ipuclari(sonuc: dict) -> list:
    """Plana ve profile göre kişisel, uygulanabilir ipuçları."""
    p, rota = sonuc["profil"], sonuc["rota"]
    duraklar = tum_duraklar(sonuc)
    out = []
    ucretli = sorted((d for d in duraklar if d.get("ucret_tl")), key=lambda d: -float(d["ucret_tl"]))
    if ucretli:
        out.append("🎟️ Giriş ücretli yerler için biletleri önceden online almak kuyruğu kısaltır: "
                   + ", ".join(d["isim"] for d in ucretli[:4]) + ".")
    if "kalabalik" in p.get("kacinilacak_etiketler", []):
        populer = [d["isim"] for d in duraklar
                   if {"ikonik", "kalabalik"} & set(d.get("etiketler") or [])]
        if populer:
            out.append("👥 Kalabalıktan hoşlanmadığın için " + ", ".join(populer[:3])
                       + " gibi popüler yerlere açılış saatinde gitmeni öneririz.")
    for g in rota["gunler"]:
        for olay, d in zip([o for o in g["cizelge"]["plan"] if not o.get("ogle")], g["duraklar"]):
            if olay.get("ihlal"):
                out.append(f"⏰ Gün {g['gun']}: {d['isim']} {d.get('kapanis')} saatinde kapanıyor; gecikirsen sırayı değiştir.")
    if p.get("beslenme"):
        out.append(f"🥗 Beslenme tercihin ({', '.join(p['beslenme'])}) restoran seçiminde dikkate alındı; "
                   "yine de menüyü önceden kontrol et.")
    detay = sonuc["maliyet"]["kisisel"]["detay"]
    if detay.get("binis", 0) >= 3:
        out.append(f"🚇 Planda yaklaşık {detay['binis']} toplu taşıma binişi var; şehir kartı ya da günlük bilet daha ekonomik olur.")
    if detay.get("yuruyus_km", 0) >= 4:
        out.append(f"👟 Toplam ~{detay['yuruyus_km']:.0f} km yürüyeceksin; rahat bir ayakkabı şart.")
    en_uzun = max(rota["gunler"], key=lambda g: g["cizelge"]["bitis"])
    if en_uzun["cizelge"]["bitis"] >= "19:00":
        out.append(f"🔋 En yoğun gün Gün {en_uzun['gun']} (bitiş {en_uzun['cizelge']['bitis']}); yanına powerbank al.")
    if p.get("tempo") == "sakin":
        out.append("🍃 Sakin tempo istediğin için duraklar arasında mola payı bıraktık; acele etme.")
    return out


def ipuclari_html(sonuc: dict) -> str:
    liste = ipuclari(sonuc)
    if not liste:
        return ""
    li = "".join(f'<li style="margin-bottom:7px">{_E(t)}</li>' for t in liste)
    return (f'<div style="{_KART}"><div style="{_BASLIK}">💡 Sana özel ipuçları</div>'
            f'<ul style="margin:0;padding-left:18px;font-size:12.5px;color:#3a2f24;line-height:1.6">{li}</ul></div>')


# ---------------------------------------------------------------------------
# Plan oluşturulurken ajan ilerleme paneli
# ---------------------------------------------------------------------------

def ilerleme_paneli_html(yuzde: int, adim: str, kayit: list, durum: str = "calisiyor") -> str:
    """Başlık + ilerleme çubuğu + o anki adım + koyu kayıt kutusu (her satır bir ajan adımı)."""
    baslik = {"calisiyor": "Ajanlar çalışıyor…", "bitti": "Planın hazır ✓",
              "hata": "Plan oluşturulamadı"}.get(durum, "Ajanlar çalışıyor…")
    cubuk = "#dc2626" if durum == "hata" else "linear-gradient(90deg,#4f46e5,#7c3aed)"
    satirlar = "".join(
        f'<div style="margin-bottom:4px"><span style="color:#a5b4fc">•</span> {_E(s[0])}'
        + (f'<div style="padding-left:16px;color:#a5b4fc">{_E(s[1])}</div>' if len(s) > 1 and s[1] else "")
        + "</div>" for s in kayit)
    return f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:18px 20px;
            box-shadow:0 2px 10px rgba(44,36,22,.06);font-family:Inter,sans-serif;margin:8px 0 14px">
  <div style="font-size:17px;font-weight:800;color:#2c2416">{baslik}</div>
  <div style="background:#f2ede6;border-radius:6px;height:7px;margin:12px 0 10px;overflow:hidden">
    <div style="width:{max(3, min(100, yuzde))}%;height:7px;border-radius:6px;background:{cubuk};
                transition:width .4s ease"></div></div>
  <div style="font-size:12.5px;font-weight:600;color:#4338ca;margin-bottom:10px">{_E(adim)}</div>
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e 60%,#0f3460);color:#e5e7eb;border-radius:10px;padding:12px 14px;
              font-family:Consolas,'Courier New',monospace;font-size:12px;line-height:1.55">{satirlar}</div>
</div>"""
