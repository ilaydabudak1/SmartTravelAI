# multiagent.py — MBTI tabanlı çok ajanlı seyahat planlama sistemi
#
# Dört katmanlı mimari (sunum, slayt 15):
#   1 · Veri girdi   : kişilik testi, serbest not, şehir/gün/bütçe, geçmiş seyahatler
#   2 · Ajan katmanı : ① Kullanıcı Profili (Claude Opus) → ② Plan (Claude Sonnet)
#                      ⇄ Eleştirmen (Claude Sonnet) → ③ Rota (algoritma) → ④ Maliyet (Gemini Flash)
#   3 · Hafıza       : memory.py (JSON + SQLite) — geçmiş ajanlara geri beslenir
#   4 · Çıktı        : kişisel rota, algoritma raporu, bütçe karşılaştırması, seyahat notu
#
# Ajanlar "aktif"tir: ortak panoya mesaj bırakır ve birbirlerine iş geri gönderir.
#   • Eleştirmen, uygunsuz/tekrar/halüsinasyon yerleri reddeder → Plan Ajanı yeniden üretir.
#   • Rota Ajanı, saatlere sığmayan durakları çıkarır ve gerekçesini panoya yazar.
#   • Maliyet Ajanı bütçe aşımında müzakere başlatır: Plan Ajanı'ndan ücretsiz alternatif ister,
#     ulaşım/konaklama/yemek seviyesini düşürür; her tur kayıt altına alınır.

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime

import memory
import poi_data
import routing
from llm import LLMYonlendirici
from memory import ayni_yer_mi, normalize


# ---------------------------------------------------------------------------
# ORTAK PANO (blackboard) — ajanlar arası mesajlaşma
# ---------------------------------------------------------------------------

@dataclass
class Mesaj:
    gonderen: str
    alici: str
    tur: str           # bilgi | istek | ret | karar | uyari
    icerik: str
    veri: dict = field(default_factory=dict)
    zaman: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class Pano:
    def __init__(self, dinleyici=None):
        self.mesajlar: list[Mesaj] = []
        self._dinleyici = dinleyici

    def yaz(self, gonderen: str, alici: str, tur: str, icerik: str, veri: dict | None = None) -> Mesaj:
        m = Mesaj(gonderen, alici, tur, icerik, veri or {})
        self.mesajlar.append(m)
        if self._dinleyici:
            try:
                self._dinleyici(m)
            except Exception:
                pass
        return m

    def to_list(self) -> list:
        return [asdict(m) for m in self.mesajlar]


class Ajan:
    ad = "ajan"

    def __init__(self, pano: Pano, llm: LLMYonlendirici):
        self.pano = pano
        self.llm = llm

    def soyle(self, alici: str, tur: str, icerik: str, veri: dict | None = None):
        return self.pano.yaz(self.ad, alici, tur, icerik, veri)


# ---------------------------------------------------------------------------
# ① KULLANICI PROFİLİ AJANI — "Seyahat psikoloğu"
# ---------------------------------------------------------------------------

MBTI_KATEGORI = {
    "E": ["gece", "alisveris", "sahil", "mahalle"], "I": ["muze", "doga", "sanat"],
    "S": ["tarih", "yemek", "manzara"], "N": ["sanat", "mahalle", "manzara"],
    "T": ["bilim", "muze", "tarih"], "F": ["mahalle", "yemek", "sanat"],
    "J": ["tarih", "muze"], "P": ["mahalle", "sahil", "doga"],
}

# (anahtar kelime kökleri, kategori, etiket)
NOT_SOZLUGU = [
    (["müze", "muze", "museum"], "muze", None),
    (["tarih", "antik", "arkeoloji", "kale", "saray"], "tarih", None),
    (["sanat", "galeri", "sergi", "resim"], "sanat", None),
    (["doğa", "doga", "yürüyüş", "yuruyus", "park", "orman", "vadi", "trekking"], "doga", None),
    (["deniz", "plaj", "sahil", "kumsal"], "sahil", None),
    (["gece", "bar", "eğlence", "eglence", "parti", "konser"], "gece", None),
    (["alışveriş", "alisveris", "çarşı", "carsi", "pazar"], "alisveris", None),
    (["manzara", "seyir", "gün batımı", "gunbatimi"], "manzara", "manzara"),
    (["fotoğraf", "fotograf"], None, "fotograf"),
    (["yemek", "lezzet", "gastronomi", "mutfak", "sokak lezzet"], "yemek", None),
    (["cami", "kilise", "ibadet", "manevi"], "ibadet", None),
    (["bilim", "teknoloji", "uzay"], "bilim", None),
    (["macera", "adrenalin", "balon", "rafting"], "macera", None),
    (["yerel", "otantik", "mahalle"], "mahalle", "yerel"),
]
OLUMSUZ = r"(sevmem|sevmiyorum|istemem|istemiyorum|hoşlanmam|hoslanmam|olmasın|olmasin|sıkıl|sikil|nefret|uzak dur|kaçın|kacin|yorul|bunal|yok|değil|degil|hayır)"
BESLENME = {"vejetaryen": "vejetaryen", "vegan": "vegan", "glüten": "glütensiz", "gluten": "glütensiz",
            "helal": "helal", "laktoz": "laktozsuz", "alkol": "alkolsüz mekân", "deniz ürün": "deniz ürünü yok"}


_KATEGORI_ESANLAM = {
    "muze": "muze", "museum": "muze", "sanat": "sanat", "art": "sanat", "galeri": "sanat", "gallery": "sanat",
    "tarih": "tarih", "tarihi": "tarih", "history": "tarih", "historic": "tarih", "kale": "tarih",
    "doga": "doga", "nature": "doga", "park": "doga", "bahce": "doga", "manzara": "manzara", "viewpoint": "manzara",
    "seyir": "manzara", "alisveris": "alisveris", "shopping": "alisveris", "carsi": "alisveris", "pazar": "alisveris",
    "yemek": "yemek", "food": "yemek", "gastronomi": "yemek", "gece": "gece", "nightlife": "gece", "sahil": "sahil",
    "beach": "sahil", "plaj": "sahil", "bilim": "bilim", "science": "bilim", "ibadet": "ibadet", "cami": "ibadet",
    "kilise": "ibadet", "religious": "ibadet", "mahalle": "mahalle", "semt": "mahalle", "macera": "macera",
}
KATEGORI_ADI = {"tarih": "tarih", "muze": "müze", "sanat": "sanat", "ibadet": "ibadet yerleri", "doga": "doğa",
                "manzara": "manzara", "alisveris": "alışveriş", "yemek": "yemek", "gece": "gece hayatı",
                "sahil": "sahil", "mahalle": "mahalle gezisi", "bilim": "bilim", "macera": "macera"}


def _kategori_coz(ham, isim: str = "") -> str:
    """LLM'in yazdığı 'Müze', 'Tarih/Müze', 'museum' gibi değerleri iç kategoriye çevirir;
    çözülemezse yer adından tahmin eder (… Müzesi → muze)."""
    # Yer adındaki güçlü ipucu ("… Müzesi", "… Parkı", "… Camii") modelin genel etiketinden önce gelir
    for kelime in normalize(isim).split():
        for kok in ("muze", "museum", "galeri", "gallery", "park", "cami", "kilise", "plaj", "carsi", "pazar"):
            if kelime.startswith(kok):
                return _KATEGORI_ESANLAM[kok]
    for kaynak in (str(ham or ""), str(isim or "")):
        for kelime in normalize(kaynak).replace("/", " ").split():
            if kelime in poi_data.KATEGORILER:
                return kelime
            for kok, kat in _KATEGORI_ESANLAM.items():
                if kelime.startswith(kok):
                    return kat
    return "tarih"


def _kisalt(metin: str, n: int) -> str:
    """Metni kelime sınırında kısaltır."""
    metin = " ".join(str(metin).split())
    if len(metin) <= n:
        return metin
    return metin[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def bulunma_eki(ad: str) -> str:
    """Türkçe bulunma hâli: İstanbul'da, Eskişehir'de, Paris'te, Roma'da."""
    if not ad:
        return ad
    kucuk = ad.lower()
    unluler = [ch for ch in kucuk if ch in "aeıioöuü"]
    son_unlu = unluler[-1] if unluler else "e"
    kalin = son_unlu in "aıou"
    sert = kucuk[-1] in "çfhkpsşt"
    return f"{ad}'{'t' if sert else 'd'}{'a' if kalin else 'e'}"


def _cumleler(metin: str) -> list:
    return [c.strip() for c in re.split(r"[.,;!?\n]| ama | fakat | ancak ", metin.lower()) if c.strip()]


def notu_cozumle(metin: str) -> dict:
    """Serbest metin notundan ilgi/kaçınma/beslenme/tempo sinyallerini çıkarır (kural tabanlı)."""
    sonuc = {"ilgi": [], "kacin": [], "etiket_ilgi": [], "etiket_kacin": [], "beslenme": [],
             "tempo": None, "butce_hassas": False, "hareket_kisitli": False, "aile": False}
    if not metin:
        return sonuc
    for c in _cumleler(metin):
        olumsuz = re.search(OLUMSUZ, c) is not None
        for kokler, kat, etiket in NOT_SOZLUGU:
            if any(k in c for k in kokler):
                if kat:
                    (sonuc["kacin"] if olumsuz else sonuc["ilgi"]).append(kat)
                if etiket:
                    (sonuc["etiket_kacin"] if olumsuz else sonuc["etiket_ilgi"]).append(etiket)
        if "kalabalık" in c or "kalabalik" in c:
            (sonuc["etiket_ilgi"] if not olumsuz and "sev" in c and "sevm" not in c else sonuc["etiket_kacin"]).append("kalabalik")
        if any(k in c for k in ("sakin", "dinlen", "yavaş", "yavas", "huzur", "rahat")):
            sonuc["tempo"] = "sakin"
            sonuc["etiket_ilgi"].append("sakin")
        if any(k in c for k in ("yoğun", "yogun", "çok yer", "cok yer", "dolu dolu", "hızlı", "hizli")):
            sonuc["tempo"] = "yogun"
        if any(k in c for k in ("öğrenci", "ogrenci", "ucuz", "bütçe", "butce", "ekonomik", "tasarruf")):
            sonuc["butce_hassas"] = True
        if any(k in c for k in ("tekerlekli", "engelli", "yürüyemem", "yuruyemem", "dizim", "hamile")):
            sonuc["hareket_kisitli"] = True
            sonuc["tempo"] = "sakin"
        if any(k in c for k in ("çocuk", "cocuk", "aile", "bebek")):
            sonuc["aile"] = True
            sonuc["etiket_ilgi"].append("aile")
        for k, v in BESLENME.items():
            if k in c:
                sonuc["beslenme"].append(v)
    for k in sonuc:
        if isinstance(sonuc[k], list):
            sonuc[k] = list(dict.fromkeys(sonuc[k]))
    # Aynı kategori hem ilgi hem kaçınma ise kaçınma kazanır (daha güvenli)
    sonuc["ilgi"] = [k for k in sonuc["ilgi"] if k not in sonuc["kacin"]]
    return sonuc


class ProfilAjani(Ajan):
    ad = "profil"
    SISTEM = (
        "Sen bir seyahat psikoloğusun. Kullanıcının MBTI tipini, KENDİ CÜMLESİYLE yazdığı serbest notu "
        "ve hafızadaki geçmiş seyahatlerini birlikte yorumlarsın. Serbest not testten önceliklidir. "
        "Geçmişteki geri bildirimlerden örüntü çıkar. Türkçe yaz."
    )

    def calis(self, istek: dict, hafiza: dict) -> dict:
        mbti = (istek.get("mbti") or "ENFP").upper()
        self.soyle("hepsi", "bilgi", f"{mbti} tipi, serbest not ve {hafiza.get('seyahat_sayisi', 0)} geçmiş seyahat inceleniyor.")

        kural = self._kural_tabanli(istek, hafiza)
        llm_profil = None
        if self.llm.anthropic_var() or self.llm.gemini_var():
            llm_profil = self.llm.json("profil", self.SISTEM, self._istem(istek, hafiza, kural), 3000)
        profil = self._birlestir(kural, llm_profil)
        profil["model"] = self.llm.kullanilan_model("profil") if llm_profil else "kural tabanlı"

        ozet = (f"Profil hazır: ilgi → {', '.join(profil['ilgi_alanlari'][:5])}; "
                f"tempo {profil['tempo']} (günde {profil['gunluk_durak']} durak)"
                + (f"; kaçınılacak → {', '.join(profil['kacinilacaklar'])}" if profil["kacinilacaklar"] else ""))
        self.soyle("plan", "karar", ozet, {"profil": {k: v for k, v in profil.items() if k != "seyahat_notu"}})
        return profil

    # -- kural tabanlı çekirdek (LLM olmasa da her zaman çalışır) --------
    def _kural_tabanli(self, istek: dict, hafiza: dict) -> dict:
        mbti = (istek.get("mbti") or "ENFP").upper()
        puan: dict = {}
        for harf in mbti:
            for i, kat in enumerate(MBTI_KATEGORI.get(harf, [])):
                puan[kat] = puan.get(kat, 0) + (3 - min(i, 2))
        cozum = notu_cozumle(istek.get("serbest_not", ""))
        for kat in cozum["ilgi"]:
            puan[kat] = puan.get(kat, 0) + 8          # serbest not testten önceliklidir
        oruntuler = []
        for kat in hafiza.get("sik_kategoriler", [])[:3]:
            puan[kat] = puan.get(kat, 0) + 2
            oruntuler.append(f"Geçmiş gezilerinde en çok {KATEGORI_ADI.get(kat, kat)} türünde yerlere gittin")

        kacin = list(cozum["kacin"])
        etiket_kacin = list(cozum["etiket_kacin"])
        for g in hafiza.get("geri_bildirimler", []):
            gc = notu_cozumle(g.get("begenilmeyen") or "")
            gb = notu_cozumle(g.get("begenilen") or "")
            neg = gc["ilgi"] + gc["kacin"]
            for kat in neg:
                if kat not in kacin:
                    kacin.append(kat)
                    oruntuler.append(f"{g.get('sehir') or 'Önceki gezi'} gezinde {KATEGORI_ADI.get(kat, kat)} sevmediğini söylemiştin")
            etiket_kacin += [e for e in gc["etiket_ilgi"] + gc["etiket_kacin"] if e not in etiket_kacin]
            for kat in gb["ilgi"]:
                puan[kat] = puan.get(kat, 0) + 4
                oruntuler.append(f"{g.get('sehir') or 'Önceki gezi'} gezinde {KATEGORI_ADI.get(kat, kat)} sevdiğini söylemiştin")
        if "I" in mbti[:1] and "kalabalik" not in etiket_kacin and "kalabalik" not in cozum["etiket_ilgi"]:
            etiket_kacin.append("kalabalik")

        for kat in kacin:
            puan.pop(kat, None)
        ilgi = [k for k, _ in sorted(puan.items(), key=lambda kv: -kv[1])]

        tempo = cozum["tempo"] or ("yogun" if mbti.endswith("J") and mbti.startswith("E")
                                   else "sakin" if mbti.startswith("I") and mbti.endswith("P") else "dengeli")
        gunluk = {"sakin": 3, "dengeli": 4, "yogun": 5}[tempo]
        butce_hassas = cozum["butce_hassas"] or istek.get("butce_kategorisi") == "ekonomik"
        baslangic = "08:30" if mbti.endswith("J") else "10:00" if tempo == "sakin" else "09:00"

        return {
            "mbti": mbti,
            "ilgi_alanlari": ilgi[:7],
            "kacinilacaklar": kacin,
            "kacinilacak_etiketler": list(dict.fromkeys(etiket_kacin)),
            "tercih_etiketleri": cozum["etiket_ilgi"],
            "tempo": tempo, "gunluk_durak": gunluk, "baslangic_saati": baslangic,
            "beslenme": cozum["beslenme"],
            "butce_hassasiyeti": "yuksek" if butce_hassas else "orta",
            "hareket_kisitli": cozum["hareket_kisitli"], "aile": cozum["aile"],
            "seyahat_tarzi": self._tarz(mbti, tempo),
            "gecmis_oruntuler": oruntuler[:6],
            "daha_once_gidilenler": hafiza.get("hedef_sehirde_gidilenler", [])[:30],
            "seyahat_notu": self._not_sablonu(istek, hafiza, cozum, tempo, kacin),
        }

    @staticmethod
    def _tarz(mbti: str, tempo: str) -> str:
        enerji = "sosyal ve hareketli ortamlardan enerji alan" if mbti.startswith("E") else "sakin, kendi temposunda gezen"
        bilgi = "ünlü ve somut yerleri görmek isteyen" if "S" in mbti[1:2] else "atmosfer ve hikâye peşinde koşan"
        duzen = "saat saat hazır programı seven" if mbti.endswith("J") else "esnek ve anlık kararlara açık"
        return f"{enerji}, {bilgi}, {duzen} bir gezgin ({tempo} tempo)."

    @staticmethod
    def _not_sablonu(istek, hafiza, cozum, tempo, kacin) -> str:
        sehir = istek.get("sehir", "")
        parcalar = [f"{sehir} için {istek.get('gun', 1)} günlük planını senin için hazırladık."]
        serbest = (istek.get("serbest_not") or "").strip()
        if serbest:
            kisa = serbest if len(serbest) <= 120 else serbest[:117] + "…"
            parcalar.append(f"Notunda “{kisa}” yazdın; bu yüzden planı {tempo} tempoda kurduk"
                            + (f" ve {', '.join(cozum['ilgi'][:3])} ağırlıklı yerler seçtik." if cozum["ilgi"] else "."))
            if cozum["beslenme"]:
                parcalar.append(f"Beslenme tercihin ({', '.join(cozum['beslenme'])}) restoran seçiminde dikkate alındı.")
        gecmis = hafiza.get("gecmis_seyahatler", [])
        if gecmis:
            son = gecmis[-1]
            parcalar.append(f"Hafızamda {hafiza.get('seyahat_sayisi', len(gecmis))} geçmiş seyahatin kayıtlı; "
                            f"en son {son.get('sehir')} gezini birlikte planlamıştık.")
        for g in hafiza.get("geri_bildirimler", [])[:2]:
            if g.get("begenilmeyen"):
                parcalar.append(f"{g.get('sehir')} gezinde “{g['begenilmeyen']}” beğenmediğini söylemiştin; benzerlerini bu kez öne çıkarmadık.")
            elif g.get("begenilen"):
                parcalar.append(f"{g.get('sehir')} gezinde “{g['begenilen']}” sevmiştin; benzer deneyimlere yer açtık.")
        gidilen = hafiza.get("hedef_sehirde_gidilenler", [])
        if gidilen:
            ornek = ", ".join(list(dict.fromkeys(gidilen))[:3])
            parcalar.append(f"{bulunma_eki(sehir)} daha önce gittiğin {len(set(gidilen))} yer (ör. {ornek}) bu planda tekrar önerilmedi.")
        if kacin:
            parcalar.append(f"Kaçınmak istediğin türler ({', '.join(kacin)}) listeye alınmadı.")
        if istek.get("butce_limiti"):
            parcalar.append(f"Toplam bütçe sınırın {istek['butce_limiti']:,.0f} TL; maliyet ajanı bu sınırı aşmamaya çalıştı.")
        return " ".join(parcalar)

    def _istem(self, istek: dict, hafiza: dict, kural: dict) -> str:
        hafiza_kisa = {k: hafiza.get(k) for k in ("gecmis_seyahatler", "ziyaret_edilen_yerler",
                                                  "geri_bildirimler", "onceki_serbest_notlar",
                                                  "sik_kategoriler", "gunluk_ortalama_harcama_tl",
                                                  "butce_asim_sayisi")}
        return (
            f"MBTI: {istek.get('mbti')}\nHedef: {istek.get('sehir')} · {istek.get('gun')} gün · "
            f"{istek.get('kisi')} kişi · bütçe kategorisi {istek.get('butce_kategorisi')} · "
            f"toplam bütçe sınırı {istek.get('butce_limiti') or 'yok'} TL\n"
            f"Serbest not (testten önceliklidir): \"{istek.get('serbest_not') or '-'}\"\n"
            f"Hafıza (geçmiş seyahatler): {json.dumps(hafiza_kisa, ensure_ascii=False)}\n"
            f"Kural tabanlı ön profil: {json.dumps({k: v for k, v in kural.items() if k != 'seyahat_notu'}, ensure_ascii=False)}\n\n"
            "Şu alanlarla bir JSON nesnesi döndür:\n"
            f"- ilgi_alanlari: öncelik sırasıyla şu kategorilerden 4-7 tanesi: {poi_data.KATEGORILER}\n"
            "- kacinilacaklar: aynı kategori listesinden kaçınılacaklar\n"
            "- kacinilacak_etiketler: ör. ['kalabalik']\n"
            "- tempo: 'sakin' | 'dengeli' | 'yogun'\n- gunluk_durak: 2-6 arası tam sayı\n"
            "- baslangic_saati: 'HH:MM'\n- beslenme: liste\n- butce_hassasiyeti: 'dusuk'|'orta'|'yuksek'\n"
            "- seyahat_tarzi: tek cümle\n- gecmis_oruntuler: geçmişten çıkardığın en fazla 5 madde\n"
            "- seyahat_notu: kullanıcıya hitaben 4-6 cümlelik kişisel seyahat notu; serbest notuna ve "
            "geçmiş seyahatlerine (varsa) somut atıf yap, daha önce gidilen yerlerin tekrar önerilmeyeceğini belirt."
        )

    @staticmethod
    def _birlestir(kural: dict, llm: dict | None) -> dict:
        if not isinstance(llm, dict):
            return kural
        p = dict(kural)
        gecerli = set(poi_data.KATEGORILER)
        ilgi = [k for k in (llm.get("ilgi_alanlari") or []) if k in gecerli]
        kacin = [k for k in (llm.get("kacinilacaklar") or []) if k in gecerli]
        # Kullanıcının açıkça yazdığı kaçınmalar asla geri alınmaz
        kacin = list(dict.fromkeys(kural["kacinilacaklar"] + kacin))
        if ilgi:
            p["ilgi_alanlari"] = [k for k in ilgi if k not in kacin][:7]
        p["kacinilacaklar"] = kacin
        p["kacinilacak_etiketler"] = list(dict.fromkeys(kural["kacinilacak_etiketler"]
                                                        + [str(e) for e in (llm.get("kacinilacak_etiketler") or [])]))
        if llm.get("tempo") in ("sakin", "dengeli", "yogun"):
            p["tempo"] = llm["tempo"]
        try:
            p["gunluk_durak"] = max(2, min(6, int(llm.get("gunluk_durak", p["gunluk_durak"]))))
        except (TypeError, ValueError):
            pass
        if re.fullmatch(r"\d{2}:\d{2}", str(llm.get("baslangic_saati", ""))):
            p["baslangic_saati"] = llm["baslangic_saati"]
        for alan in ("seyahat_tarzi", "seyahat_notu"):
            if isinstance(llm.get(alan), str) and len(llm[alan]) > 20:
                p[alan] = llm[alan].strip()
        if isinstance(llm.get("gecmis_oruntuler"), list) and llm["gecmis_oruntuler"]:
            p["gecmis_oruntuler"] = [str(x) for x in llm["gecmis_oruntuler"]][:6]
        p["beslenme"] = list(dict.fromkeys(kural["beslenme"] + [str(x) for x in (llm.get("beslenme") or [])]))
        if llm.get("butce_hassasiyeti") in ("dusuk", "orta", "yuksek") and kural["butce_hassasiyeti"] != "yuksek":
            p["butce_hassasiyeti"] = llm["butce_hassasiyeti"]
        return p


# ---------------------------------------------------------------------------
# ② PLAN AJANI — "Gezi rehberi"
# ---------------------------------------------------------------------------

def poi_puani(p: dict, profil: dict) -> float:
    """Bir gezi noktasının profile uygunluk puanı (yüksek = daha uygun)."""
    ilgi = profil.get("ilgi_alanlari", [])
    s = 0.0
    if p.get("kategori") in ilgi:
        s += 6 - min(ilgi.index(p["kategori"]), 5)
    if p.get("kategori") in profil.get("kacinilacaklar", []):
        s -= 12
    etiketler = set(p.get("etiketler") or [])
    s += 1.5 * len(etiketler & set(profil.get("tercih_etiketleri", [])))
    s -= 3.0 * len(etiketler & set(profil.get("kacinilacak_etiketler", [])))
    if "ikonik" in etiketler and "S" in profil.get("mbti", "")[1:2]:
        s += 1.5
    if profil.get("butce_hassasiyeti") == "yuksek":
        s -= float(p.get("ucret_tl") or 0) / 400
    if profil.get("hareket_kisitli") and ("yuruyus" in etiketler or p.get("kategori") == "macera"):
        s -= 8
    return round(s, 2)


class PlanAjani(Ajan):
    ad = "plan"
    SISTEM = ("Sen deneyimli bir gezi rehberisin. Verilen kullanıcı profiline uygun, GERÇEKTE VAR OLAN "
              "gezi noktaları önerirsin. Koordinatlar gerçek olmalı. Uydurma yer önerme. Türkçe yaz.")

    def __init__(self, pano, llm):
        super().__init__(pano, llm)
        self._havuz_cache: dict = {}

    def havuz(self, sehir: str) -> tuple[list, str]:
        """Yerel bilgi tabanı → OpenStreetMap sırasıyla aday havuzu."""
        if sehir not in self._havuz_cache:
            yerel = poi_data.yerel_poi(sehir)
            if yerel:
                self._havuz_cache[sehir] = (yerel, "yerel bilgi tabanı")
            else:
                osm = poi_data.osm_poi(sehir)
                self._havuz_cache[sehir] = (osm, "OpenStreetMap") if osm else ([], "yok")
        return self._havuz_cache[sehir]

    def calis(self, istek: dict, profil: dict, haric: list, adet: int,
              geri_bildirim: dict | None = None) -> dict:
        sehir = istek["sehir"]
        if geri_bildirim:
            self.soyle("elestirmen" if geri_bildirim.get("kaynak") == "elestirmen" else "maliyet", "bilgi",
                       f"Geri bildirim alındı ({geri_bildirim.get('ozet', '')}); liste yeniden üretiliyor.")
        yerler, restoranlar, kaynak, baz_sehir = [], [], "", None
        if self.llm.anthropic_var() or self.llm.gemini_var():
            cevap = self.llm.json("plan", self.SISTEM, self._istem(istek, profil, haric, adet, geri_bildirim), 8000)
            if isinstance(cevap, dict):
                yerler = [self._temizle(y) for y in (cevap.get("yerler") or []) if isinstance(y, dict)]
                yerler = [y for y in yerler if y]
                restoranlar = [r for r in (cevap.get("restoranlar") or []) if isinstance(r, dict) and r.get("isim")]
                kaynak = self.llm.kullanilan_model("plan")
                if istek.get("_ulke") and isinstance(cevap.get("baz_sehir"), str) and cevap["baz_sehir"].strip():
                    baz_sehir = cevap["baz_sehir"].strip()
        havuz, havuz_kaynak = self.havuz(sehir)
        if len(yerler) < adet:
            ek = self._havuzdan_sec(havuz, profil, haric + [y["isim"] for y in yerler],
                                    adet - len(yerler) + 3, geri_bildirim)
            if ek:
                kaynak = (kaynak + " + " if kaynak else "") + havuz_kaynak
            yerler += ek
        # LLM restoranları + yerel bilgi tabanı tek havuzda; en yakını atanırken ikisi de aday
        restoranlar = restoranlar + poi_data.yerel_restoran(sehir)
        self.soyle("elestirmen", "istek",
                   f"{len(yerler)} aday gezi noktası hazırlandı (kaynak: {kaynak or 'yok'}). Denetim isteniyor.",
                   {"adaylar": [y["isim"] for y in yerler]})
        return {"yerler": yerler, "restoranlar": restoranlar, "kaynak": kaynak or "yok", "baz_sehir": baz_sehir}

    def alternatif_bul(self, istek: dict, profil: dict, haric: list, adet: int, ucretsiz: bool = True) -> list:
        """Maliyet müzakeresi için: kullanılmamış, (tercihen) ücretsiz yerler."""
        havuz, _ = self.havuz(istek["sehir"])
        aday = [p for p in havuz if not any(ayni_yer_mi(p["isim"], h) for h in haric)]
        if ucretsiz:
            aday = [p for p in aday if not p.get("ucret_tl")]
        # Profile ters düşen (kaçınılan tür/etiket) alternatifler önerilmez
        aday = [p for p in aday if poi_puani(p, profil) > 0]
        aday.sort(key=lambda p: -poi_puani(p, profil))
        return [dict(p) for p in aday[:adet]]

    @staticmethod
    def _havuzdan_sec(havuz: list, profil: dict, haric: list, adet: int, geri: dict | None) -> list:
        aday = [p for p in havuz if not any(ayni_yer_mi(p["isim"], h) for h in haric)]
        if geri and geri.get("ucretsiz_tercih"):
            aday.sort(key=lambda p: (bool(p.get("ucret_tl")), -poi_puani(p, profil)))
        else:
            aday.sort(key=lambda p: -poi_puani(p, profil))
        # çeşitlilik: tek bir kategori seçimin %40'ını geçmesin
        secim, sayac = [], {}
        limit = max(2, math.ceil(adet * 0.4))
        for p in aday:
            if len(secim) >= adet:
                break
            if sayac.get(p["kategori"], 0) >= limit:
                continue
            sayac[p["kategori"]] = sayac.get(p["kategori"], 0) + 1
            secim.append(dict(p))
        for p in aday:                                 # hâlâ eksikse sınırı gevşet
            if len(secim) >= adet:
                break
            if p not in secim:
                secim.append(dict(p))
        for p in secim:
            p.setdefault("neden", PlanAjani._neden(p, profil))
        return secim

    @staticmethod
    def _neden(p: dict, profil: dict) -> str:
        parca = []
        if p.get("kategori") in profil.get("ilgi_alanlari", [])[:4]:
            parca.append(f"'{p['kategori']}' ilgi alanına uygun")
        ortak = set(p.get("etiketler") or []) & set(profil.get("tercih_etiketleri", []))
        if ortak:
            parca.append(f"{', '.join(ortak)} tercihinle örtüşüyor")
        if not p.get("ucret_tl"):
            parca.append("ücretsiz")
        return "; ".join(parca).capitalize() or "Şehrin öne çıkan noktalarından"

    @staticmethod
    def _temizle(y: dict) -> dict | None:
        try:
            ad = str(y.get("isim") or y.get("name") or "").strip()
            lat, lon = float(y.get("lat") or y.get("enlem")), float(y.get("lon") or y.get("boylam"))
        except (TypeError, ValueError):
            return {"isim": str(y.get("isim") or y.get("name") or "?"), "lat": None, "lon": None,
                    "kategori": "tarih", "sure_dk": 60, "acilis": "09:00", "kapanis": "18:00",
                    "ucret_tl": 0, "etiketler": [], "neden": ""}
        kat = _kategori_coz(y.get("kategori"), ad)
        try:
            sure = int(y.get("sure_dk") or 60)
            ucret = float(y.get("ucret_tl") or 0)
        except (TypeError, ValueError):
            sure, ucret = 60, 0.0
        return {"isim": ad, "lat": lat, "lon": lon, "kategori": kat, "sure_dk": max(15, min(240, sure)),
                "acilis": str(y.get("acilis") or "09:00")[:5], "kapanis": str(y.get("kapanis") or "18:00")[:5],
                "ucret_tl": max(0.0, ucret), "etiketler": [str(e) for e in (y.get("etiketler") or [])][:5],
                "neden": str(y.get("neden") or "")[:240]}

    def _istem(self, istek, profil, haric, adet, geri) -> str:
        ek = ""
        if geri:
            if geri.get("reddedilen"):
                ek += f"\nÖnceki listeden REDDEDİLENLER (bunları ve benzerlerini önerme): {json.dumps(geri['reddedilen'], ensure_ascii=False)}"
            if geri.get("ucretsiz_tercih"):
                ek += "\nBütçe aşıldı: mümkün olduğunca ÜCRETSİZ ya da düşük ücretli yerler öner."
        if istek.get("_ulke"):
            ek += ("\nHEDEF BİR ÜLKE/BÖLGE: Profile en uygun TEK bir şehir seç; bütün yerler o şehirde (merkeze en fazla "
                   "25 km) olsun. Seçtiğin şehri JSON'a \"baz_sehir\" alanı olarak ekle.")
        return (
            f"Şehir: {istek['sehir']} · {istek['gun']} gün · {istek['kisi']} kişi · bütçe: {istek['butce_kategorisi']}\n"
            f"Kullanıcı profili: {json.dumps({k: profil.get(k) for k in ('mbti', 'ilgi_alanlari', 'kacinilacaklar', 'kacinilacak_etiketler', 'tempo', 'beslenme', 'butce_hassasiyeti', 'hareket_kisitli', 'aile')}, ensure_ascii=False)}\n"
            f"DAHA ÖNCE GİDİLMİŞ — KESİNLİKLE ÖNERME: {json.dumps(haric[:60], ensure_ascii=False)}{ek}\n\n"
            f"{adet + 3} gezi noktası ve {istek['gun'] * 2} restoran öner. JSON şeması:\n"
            '{"yerler":[{"isim":"...","lat":0.0,"lon":0.0,"kategori":"' + "|".join(poi_data.KATEGORILER) + '",'
            '"sure_dk":60,"acilis":"09:00","kapanis":"18:00","ucret_tl":0,"etiketler":["kalabalik|sakin|ikonik|fotograf|yerel"],'
            '"neden":"bu kullanıcıya neden uygun (1 cümle)"}],'
            '"restoranlar":[{"isim":"...","lat":0.0,"lon":0.0,"fiyat":"ekonomik|orta|luks","mutfak":"..."}]}\n'
            "ucret_tl: yetişkin giriş ücreti (TL, tahmini; ücretsizse 0). Kaçınılacak kategorilerden yer önerme."
        )


# ---------------------------------------------------------------------------
# ELEŞTİRMEN AJAN — halüsinasyon / tekrar / profil uyumu denetimi
# ---------------------------------------------------------------------------

class ElestirmenAjani(Ajan):
    ad = "elestirmen"
    SISTEM = ("Sen titiz bir seyahat planı denetçisisin. Bir gezi listesinin kullanıcı profiline uygunluğunu "
              "eleştirirsin. Sadece gerçekten uygunsuz olanları işaretle.")

    def calis(self, istek: dict, profil: dict, adaylar: list, haric: list, merkez: dict | None) -> dict:
        onay, red = [], []
        sehir = istek["sehir"]
        yerel = poi_data.yerel_poi(sehir)
        max_km = 45 if poi_data.sehir_anahtari(sehir) in ("kapadokya", "antalya") else 30
        for y in adaylar:
            neden = None
            if y.get("lat") is None or y.get("lon") is None or not (-90 <= y["lat"] <= 90 and -180 <= y["lon"] <= 180):
                neden = "koordinat yok/geçersiz"
            elif any(ayni_yer_mi(y["isim"], h) for h in haric):
                neden = "daha önce gidildi (hafıza)"
            elif any(ayni_yer_mi(y["isim"], o["isim"]) for o in onay):
                neden = "listede tekrar"
            elif y.get("kategori") in profil.get("kacinilacaklar", []):
                neden = f"profilde kaçınılan tür: {y['kategori']}"
            else:
                ref = next((p for p in yerel if ayni_yer_mi(p["isim"], y["isim"])), None)
                if ref and routing.haversine(ref, y) > 1.5:
                    self.soyle("plan", "uyari", f"'{y['isim']}' koordinatı bilgi tabanına göre "
                               f"{routing.haversine(ref, y):.1f} km sapmış — düzeltildi.")
                    y["lat"], y["lon"] = ref["lat"], ref["lon"]
                if merkez and routing.haversine(merkez, y) > max_km:
                    uzak = routing.haversine(merkez, y)
                    neden = (f"seçilen şehrin dışında ({uzak:.0f} km)" if uzak < 400
                             else f"merkeze {uzak:.0f} km — konum hatalı olabilir")
            if neden:
                red.append({"isim": y["isim"], "neden": neden})
            else:
                onay.append(y)

        # Profil uyumu için ikinci görüş (LLM) — en fazla listenin %30'unu eleyebilir
        if onay and (self.llm.anthropic_var() or self.llm.gemini_var()):
            cevap = self.llm.json("elestirmen", self.SISTEM, (
                f"Profil: {json.dumps({k: profil.get(k) for k in ('mbti', 'ilgi_alanlari', 'kacinilacaklar', 'kacinilacak_etiketler', 'tempo', 'hareket_kisitli', 'aile')}, ensure_ascii=False)}\n"
                f"Serbest not: \"{istek.get('serbest_not') or '-'}\"\nŞehir: {sehir}\n"
                f"Liste: {json.dumps([{'isim': o['isim'], 'kategori': o['kategori']} for o in onay], ensure_ascii=False)}\n"
                'Uygunsuz olanları {"uygunsuz":[{"isim":"...","neden":"..."}],"yorum":"tek cümle"} olarak döndür.'), 1500)
            if isinstance(cevap, dict):
                sinir = max(0, int(len(onay) * 0.3))
                for u in (cevap.get("uygunsuz") or [])[:sinir]:
                    hedef = next((o for o in onay if ayni_yer_mi(o["isim"], str(u.get("isim", "")))), None)
                    if hedef:
                        onay.remove(hedef)
                        red.append({"isim": hedef["isim"], "neden": _kisalt(f"profil uyumu: {u.get('neden', '')}", 220)})
                if cevap.get("yorum"):
                    self.soyle("plan", "bilgi", f"Eleştirmen yorumu: {cevap['yorum']}")

        if red:
            self.soyle("plan", "ret", f"{len(red)} yer reddedildi: " +
                       "; ".join(f"{r['isim']} ({r['neden']})" for r in red[:6]), {"reddedilen": red})
        else:
            self.soyle("plan", "karar", f"Listenin tamamı ({len(onay)} yer) onaylandı.")
        return {"onaylanan": onay, "reddedilen": red}


# ---------------------------------------------------------------------------
# ③ ROTA AJANI — dil modeli yok, tamamen algoritma
# ---------------------------------------------------------------------------

def _dk(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


class RotaAjani(Ajan):
    ad = "rota"
    GUN_SONU_LIMIT = 21 * 60 + 30

    def calis(self, istek: dict, profil: dict, yerler: list, gercek_yol_kullan: bool = True) -> dict:
        gun = istek["gun"]
        merkez = {"isim": "Konaklama bölgesi",
                  "lat": sum(p["lat"] for p in yerler) / len(yerler),
                  "lon": sum(p["lon"] for p in yerler) / len(yerler)}
        gun_gruplari = routing.gunlere_bol(yerler, gun)
        baslangic = _dk(profil.get("baslangic_saati", "09:00"))
        hiz = 3.5 if profil.get("hareket_kisitli") else 4.5
        gunler, cikarilan = [], []
        kazanan_sayac: dict = {}
        for g, indeksler in enumerate(gun_gruplari, start=1):
            duraklar = [yerler[i] for i in indeksler]
            gun_sonucu = self._gunu_coz(g, merkez, duraklar, baslangic, hiz)
            # Gün çok uzarsa en düşük puanlı durağı çıkar (ajan kararı)
            while (_dk(gun_sonucu["cizelge"]["bitis"]) > self.GUN_SONU_LIMIT and len(duraklar) > 2):
                dusuk = min(duraklar, key=lambda p: poi_puani(p, profil))
                duraklar.remove(dusuk)
                cikarilan.append(dusuk)
                self.soyle("plan", "uyari", f"Gün {g} {gun_sonucu['cizelge']['bitis']}'de bitiyordu; "
                           f"'{dusuk['isim']}' çıkarıldı (profile en az uyan durak).")
                gun_sonucu = self._gunu_coz(g, merkez, duraklar, baslangic, hiz)
            # Yeniden sıralamaya rağmen kapanış saatine sığmayan durak varsa çıkar (kapalı yere gidilmez)
            while gun_sonucu["cizelge"]["ihlal"] and len(duraklar) > 1:
                ihlalli = [gun_sonucu["duraklar"][i] for i, olay in
                           enumerate(o for o in gun_sonucu["cizelge"]["plan"] if not o.get("ogle")) if olay.get("ihlal")]
                dusuk = min(ihlalli, key=lambda p: poi_puani(p, profil))
                duraklar.remove(dusuk)
                cikarilan.append(dusuk)
                self.soyle("plan", "uyari", f"Gün {g}: '{dusuk['isim']}' kapanış saatinden ({dusuk.get('kapanis')}) "
                           "önce ziyaret edilemiyor; saatlere uyan bir rota için çıkarıldı.")
                gun_sonucu = self._gunu_coz(g, merkez, duraklar, baslangic, hiz)
            kazanan_sayac[gun_sonucu["yaris"]["kazanan"]] = kazanan_sayac.get(gun_sonucu["yaris"]["kazanan"], 0) + 1
            gunler.append(gun_sonucu)

        if gercek_yol_kullan:
            for gs in gunler:
                # Kuş uçuşu ile aynı kapalı tur: konaklama → duraklar → konaklama
                noktalar = [merkez] + gs["duraklar"] + [merkez]
                gs["gercek_yol"] = routing.gercek_yol(noktalar, "foot")
        toplam_kus = round(sum(g["km"] for g in gunler), 2)
        gercek = [g.get("gercek_yol") for g in gunler]
        toplam_gercek = round(sum(x["km"] for x in gercek if x), 2) if all(gercek) and gercek else None

        ozet = ", ".join(f"{routing.ALGORITMA_ADLARI[k]} ×{v}" for k, v in kazanan_sayac.items())
        self.soyle("maliyet", "karar",
                   f"{gun} günlük rota hazır: toplam {toplam_kus} km kuş uçuşu"
                   + (f", {toplam_gercek} km gerçek yürüyüş" if toplam_gercek else "")
                   + f". Kazanan algoritma(lar): {ozet}.",
                   {"toplam_km": toplam_kus, "kazananlar": kazanan_sayac})
        return {"merkez": merkez, "gunler": gunler, "toplam_km": toplam_kus,
                "toplam_gercek_km": toplam_gercek, "kazananlar": kazanan_sayac, "cikarilan": cikarilan}

    def _gunu_coz(self, g: int, merkez: dict, duraklar: list, baslangic: int, hiz: float) -> dict:
        noktalar = [merkez] + duraklar
        D = routing.mesafe_matrisi(noktalar)
        yaris = routing.yaris(D, seed=1000 + g)
        vrptw = routing.zaman_pencereli_sirala(yaris.tur, D, duraklar, baslangic)
        cizelge = routing.zaman_cizelgesi(vrptw["sira"], D, duraklar, baslangic, hiz_kmh=hiz, ogle_molasi=True)
        sirali = [duraklar[i - 1] for i in vrptw["sira"] if i != 0]
        return {
            "gun": g, "duraklar": sirali, "km": routing.tur_uzunlugu(vrptw["sira"], D),
            "yaris": yaris.to_dict(), "cizelge": cizelge,
            "vrptw_duzeltme": vrptw["duzeltme_sayisi"],
            "sira_degisti": vrptw["sira"] != yaris.tur,
        }


# ---------------------------------------------------------------------------
# ④ MALİYET TAHMİN AJANI
# ---------------------------------------------------------------------------

SEVIYELER = ["ekonomik", "orta", "luks"]
CAPA = {   # Ankara tabanı (çarpan 1.0), 2026 tahmini
    "konaklama_oda_gece": {"ekonomik": 1800, "orta": 4000, "luks": 11000},
    "yemek_kisi_gun":     {"ekonomik": 700,  "orta": 1600, "luks": 4500},
    "toplu_tasima_binis": 35,
    "taksi_acilis": 60, "taksi_km": 35,
}
YURUME_ESIGI_KM = 1.5


class MaliyetAjani(Ajan):
    ad = "maliyet"

    def capalar(self, istek: dict) -> dict:
        """Kural çıpaları × şehir çarpanı; varsa Gemini tahminiyle (makul aralıktaysa) harmanlanır."""
        carpan = poi_data.sehir_carpani(istek["sehir"])
        kat = istek["butce_kategorisi"]
        kural = {
            "konaklama_oda_gece": CAPA["konaklama_oda_gece"][kat] * carpan,
            "yemek_kisi_gun": CAPA["yemek_kisi_gun"][kat] * carpan,
            "toplu_tasima_binis": CAPA["toplu_tasima_binis"] * carpan,
            "taksi_km": CAPA["taksi_km"] * carpan,
        }
        kaynak = f"kural çıpası × {carpan:.2f} şehir çarpanı"
        if self.llm.gemini_var() or self.llm.anthropic_var():
            cevap = self.llm.json("maliyet", "Sen bir seyahat maliyet analistisin. Sayısal ve gerçekçi ol.", (
                f"{istek['sehir']} için 2026 yılı, '{kat}' seviyesinde ortalama fiyatları Türk Lirası olarak tahmin et. "
                'JSON: {"konaklama_oda_gece":0,"yemek_kisi_gun":0,"toplu_tasima_binis":0,"taksi_km":0}'), 600)
            if isinstance(cevap, dict):
                kabul = 0
                for k, v in kural.items():
                    try:
                        llm_v = float(cevap.get(k))
                    except (TypeError, ValueError):
                        continue
                    if 0.4 <= llm_v / v <= 2.5:     # akıl dışı tahminleri reddet
                        kural[k] = math.sqrt(llm_v * v)
                        kabul += 1
                if kabul:
                    kaynak += f" + {self.llm.kullanilan_model('maliyet')} tahmini ({kabul}/4 kalem, geometrik ortalama)"
        return {k: round(v, 2) for k, v in kural.items()} | {"kaynak": kaynak}

    def hesapla(self, istek: dict, gun_duraklari: list, capa: dict, ayar: dict) -> dict:
        """Kalem kalem maliyet. ayar: konaklama/yemek seviyesi, ulasim_modu ('toplu'|'taksi'), sehirlerarasi."""
        kisi, gun = istek["kisi"], istek["gun"]
        oda = math.ceil(kisi / 2)
        gece = max(1, gun - 1)
        kat = istek["butce_kategorisi"]
        oran_k = CAPA["konaklama_oda_gece"][ayar["konaklama"]] / CAPA["konaklama_oda_gece"][kat]
        oran_y = CAPA["yemek_kisi_gun"][ayar["yemek"]] / CAPA["yemek_kisi_gun"][kat]
        konaklama = capa["konaklama_oda_gece"] * oran_k * oda * gece
        yemek = capa["yemek_kisi_gun"] * oran_y * kisi * gun

        binis, taksi_km, yuruyus_km = 0, 0.0, 0.0
        for bacaklar in gun_duraklari:
            for km in bacaklar:
                if km <= YURUME_ESIGI_KM:
                    yuruyus_km += km
                elif ayar["ulasim_modu"] == "taksi":
                    taksi_km += km
                else:
                    binis += 1
        arac = math.ceil(kisi / 4)
        sehir_ici = (binis * capa["toplu_tasima_binis"] * kisi
                     + arac * (taksi_km * capa["taksi_km"] + (CAPA["taksi_acilis"] if taksi_km else 0)))

        aktivite = sum(float(p.get("ucret_tl") or 0) for gd in istek.get("_plan_duraklari", []) for p in gd) * kisi
        sehirlerarasi = self._sehirlerarasi(istek, ayar["sehirlerarasi"])
        kalemler = {
            "konaklama": round(konaklama), "yemek": round(yemek), "sehir_ici_ulasim": round(sehir_ici),
            "aktivite": round(aktivite), "sehirlerarasi": round(sehirlerarasi),
        }
        kalemler["toplam"] = sum(kalemler.values())
        return {"kalemler": kalemler, "detay": {"oda": oda, "gece": gece, "binis": binis,
                                                "taksi_km": round(taksi_km, 1), "yuruyus_km": round(yuruyus_km, 1)},
                "ayar": dict(ayar)}

    @staticmethod
    def _sehirlerarasi(istek: dict, mod: str) -> float:
        kisi = istek["kisi"]
        yurtdisi = poi_data.yurtdisi_mi(istek["sehir"])
        lux = 1.8 if istek["butce_kategorisi"] == "luks" else 1.0
        if mod == "ucak":
            return (12000 if yurtdisi else 3500) * kisi * lux
        if mod == "tren":
            return 1200 * kisi
        if mod == "araba":
            return 2500 * math.ceil(kisi / 5)
        return (6000 if yurtdisi else 1600) * kisi      # otobüs

    def calis(self, istek: dict, rota: dict, standart_duraklar: list) -> dict:
        capa = self.capalar(istek)
        kat = istek["butce_kategorisi"]
        mod = _ulasim_kodu(istek.get("ulasim", "otobus"))
        ayar = {"konaklama": kat, "yemek": kat, "ulasim_modu": "taksi" if kat == "luks" else "toplu",
                "sehirlerarasi": mod}

        istek["_plan_duraklari"] = [g["duraklar"] for g in rota["gunler"]]
        bacak = [_bacaklar(rota["merkez"], g["duraklar"]) for g in rota["gunler"]]
        kisisel = self.hesapla(istek, bacak, capa, ayar)

        # Standart plan: popüler liste, verildiği sırayla (rota optimizasyonu yok), taksiyle
        std_istek = dict(istek, _plan_duraklari=standart_duraklar)
        std_bacak = [_bacaklar(rota["merkez"], g) for g in standart_duraklar]
        standart = self.hesapla(std_istek, std_bacak, capa, {**ayar, "ulasim_modu": "taksi"})
        self.soyle("orkestrator", "bilgi",
                   f"Kişisel plan {kisisel['kalemler']['toplam']:,.0f} TL, standart plan "
                   f"{standart['kalemler']['toplam']:,.0f} TL (çıpa: {capa['kaynak']}).")
        return {"capa": capa, "kisisel": kisisel, "standart": standart, "bacaklar": bacak}


def _ulasim_kodu(s: str) -> str:
    n = normalize(s)
    if "ucak" in n:
        return "ucak"
    if "tren" in n:
        return "tren"
    if "araba" in n or "arac" in n:
        return "araba"
    return "otobus"


def _bacaklar(merkez: dict, duraklar: list) -> list:
    nok = [merkez] + list(duraklar) + [merkez]
    return [routing.haversine(nok[i], nok[i + 1]) for i in range(len(nok) - 1)]


def tasarruf(standart: dict, kisisel: dict) -> tuple[float, float]:
    s, k = standart["kalemler"]["toplam"], kisisel["kalemler"]["toplam"]
    return s - k, (round((s - k) / s * 100, 1) if s > 0 else 0.0)


# ---------------------------------------------------------------------------
# ORKESTRATÖR
# ---------------------------------------------------------------------------

class Orkestrator:
    MAKS_PLAN_TURU = 3
    MAKS_MUZAKERE_TURU = 6

    def __init__(self, dinleyici=None, gercek_yol: bool = True):
        self.pano = Pano(dinleyici)
        self.llm = LLMYonlendirici()
        self.profil_ajani = ProfilAjani(self.pano, self.llm)
        self.plan_ajani = PlanAjani(self.pano, self.llm)
        self.elestirmen = ElestirmenAjani(self.pano, self.llm)
        self.rota_ajani = RotaAjani(self.pano, self.llm)
        self.maliyet_ajani = MaliyetAjani(self.pano, self.llm)
        self.gercek_yol = gercek_yol

    def _yaz(self, tur, icerik, veri=None):
        self.pano.yaz("orkestrator", "hepsi", tur, icerik, veri)

    def planla(self, istek: dict, username: str) -> dict:
        t0 = time.perf_counter()
        istek = _istek_dogrula(istek)
        self._yaz("bilgi", f"Model ataması: " + ", ".join(f"{r}→{m}" for r, m in self.llm.durum().items()))

        # Hedef bir ülke/bölge ise birkaç günlük plan tek bir üs şehirde kurulur
        hedef_notu = None
        cozum = poi_data.hedef_coz(istek["sehir"])
        if cozum["tur"] == "sehir":
            istek["sehir"] = cozum["sehir"]
        if cozum["tur"] == "ulke":
            istek["hedef_girdi"] = istek["sehir"]
            if cozum["sehir"]:
                hedef_notu = (f"“{istek['sehir']}” bir ülke/bölge; {istek['gun']} günlük bir gezi için planı "
                              f"{bulunma_eki(cozum['sehir'])} kurduk. Başka bir şehir istersen hedefe şehir adını yaz.")
                istek["sehir"] = cozum["sehir"]
            else:
                istek["_ulke"] = True        # şehri Plan Ajanı seçecek
            self._yaz("karar", hedef_notu or f"“{istek['sehir']}” bir ülke/bölge; üs şehri Plan Ajanı seçecek.")

        # 0) Hafıza
        hafiza = memory.hafiza_baglami(username, istek["sehir"])
        haric = list(dict.fromkeys(hafiza.get("hedef_sehirde_gidilenler", [])))
        self.pano.yaz("hafiza", "profil", "bilgi",
                      f"{hafiza['seyahat_sayisi']} geçmiş seyahat, {len(haric)} daha önce gidilmiş yer "
                      f"({istek['sehir']}), {len(hafiza['geri_bildirimler'])} geri bildirim yüklendi.")

        # 1) Profil
        profil = self.profil_ajani.calis(istek, hafiza)
        hedef = max(2, profil["gunluk_durak"] * istek["gun"])

        # 2) Plan ⇄ Eleştirmen
        merkez = None if istek.get("_ulke") else poi_data.sehir_koordinati(istek["sehir"])
        onaylanan, tum_red, restoranlar, kaynak = [], [], [], ""
        geri = None
        for tur in range(1, self.MAKS_PLAN_TURU + 1):
            haric_tur = haric + [o["isim"] for o in onaylanan] + [r["isim"] for r in tum_red]
            cikti = self.plan_ajani.calis(istek, profil, haric_tur, hedef - len(onaylanan), geri)
            restoranlar = restoranlar or cikti["restoranlar"]
            kaynak = cikti["kaynak"]
            if istek.get("_ulke") and cikti.get("baz_sehir"):
                hedef_notu = (f"“{istek['hedef_girdi']}” bir ülke/bölge; planı Plan Ajanı'nın seçtiği "
                              f"{bulunma_eki(cikti['baz_sehir'])} kurduk.")
                istek["sehir"] = cikti["baz_sehir"]
                istek.pop("_ulke", None)
            if merkez is None and cikti["yerler"]:
                # Merkez: önerilerin en yoğun kümesi (dağınık öneriler tek bir şehre toplanır)
                merkez = _yogun_merkez([y for y in cikti["yerler"] if y.get("lat") is not None])
            denetim = self.elestirmen.calis(istek, profil, cikti["yerler"], haric + [o["isim"] for o in onaylanan], merkez)
            onaylanan += denetim["onaylanan"]
            tum_red += denetim["reddedilen"]
            if len(onaylanan) >= hedef or not cikti["yerler"]:
                break
            geri = {"kaynak": "elestirmen", "reddedilen": denetim["reddedilen"],
                    "ozet": f"{len(denetim['reddedilen'])} ret, {hedef - len(onaylanan)} yer eksik"}
            self._yaz("istek", f"Tur {tur}: {len(onaylanan)}/{hedef} yer onaylı — Plan Ajanı'ndan ek öneri istendi.")

        if not onaylanan:
            raise RuntimeError(f"“{istek.get('hedef_girdi') or istek['sehir']}” için uygun gezi noktası bulunamadı. "
                               "Yazımı kontrol et ya da pilot destinasyonlardan birini dene: "
                               + ", ".join(poi_data.PILOT_DESTINASYONLAR) + ".")
        onaylanan.sort(key=lambda p: -poi_puani(p, profil))
        secilen = onaylanan[:hedef]

        # 3) Rota
        rota = self.rota_ajani.calis(istek, profil, secilen, self.gercek_yol)

        # 4) Maliyet + bütçe müzakeresi
        standart = self._standart_liste(istek, secilen, rota)
        maliyet = self.maliyet_ajani.calis(istek, rota, standart)
        muzakere, rota, maliyet = self._muzakere(istek, profil, rota, maliyet, standart, haric, tum_red)

        restoran_plani = _restoran_ata(rota, restoranlar, istek, profil)
        tl, yuzde = tasarruf(maliyet["standart"], maliyet["kisisel"])
        limit = istek.get("butce_limiti")
        toplam = maliyet["kisisel"]["kalemler"]["toplam"]
        sonuc = {
            "istek": {k: v for k, v in istek.items() if not k.startswith("_")},
            "profil": profil, "hafiza_ozeti": {k: hafiza[k] for k in ("seyahat_sayisi", "hedef_sehirde_gidilenler",
                                                                     "sik_kategoriler", "geri_bildirimler")},
            "haric_tutulan": haric, "reddedilenler": tum_red, "plan_kaynagi": kaynak,
            "hedef_notu": hedef_notu,
            # Onaylanıp plana sığmayan ya da saat/süre yüzünden çıkarılan yerler: "vaktin kalırsa" listesi
            "yedek_yerler": _yedekler(onaylanan[hedef:] + rota.get("cikarilan", []), rota),
            "rota": rota, "maliyet": maliyet, "muzakere": muzakere, "restoran_plani": restoran_plani,
            "tasarruf_tl": tl, "tasarruf_yuzde": yuzde,
            "butce_icinde": (toplam <= limit) if limit else True,
            "butce_farki_tl": (limit - toplam) if limit else None,
            "mesajlar": self.pano.to_list(),
            "model_kullanimi": [asdict(k) for k in self.llm.kayitlar],
            "sure_sn": round(time.perf_counter() - t0, 2),
        }
        durum = ("bütçe içinde ✅" if sonuc["butce_icinde"] else
                 f"bütçe {-sonuc['butce_farki_tl']:,.0f} TL aşıldı ⚠️")
        self._yaz("karar", f"Plan tamamlandı ({sonuc['sure_sn']} sn): {toplam:,.0f} TL, {durum}")
        return sonuc

    # -- standart (popüler) plan ----------------------------------------
    def _standart_liste(self, istek: dict, secilen: list, rota: dict) -> list:
        yerel = poi_data.yerel_poi(istek["sehir"])
        n = len(secilen)
        if yerel:
            populer = sorted(yerel, key=lambda p: (0 if "ikonik" in p.get("etiketler", []) else 1))[:n]
        else:
            populer = list(secilen)        # bilgi tabanı yoksa aynı yerler, optimizasyonsuz sırada
        gun = istek["gun"]
        boy = math.ceil(len(populer) / gun) if gun else len(populer)
        return [populer[i * boy:(i + 1) * boy] for i in range(gun)]

    # -- bütçe müzakeresi -------------------------------------------------
    def _muzakere(self, istek, profil, rota, maliyet, standart, haric, tum_red):
        limit = istek.get("butce_limiti")
        turlar = []
        if not limit:
            return turlar, rota, maliyet
        kisisel = maliyet["kisisel"]
        ayar = dict(kisisel["ayar"])
        capa = maliyet["capa"]
        bacak = maliyet["bacaklar"]

        def hesapla():
            istek["_plan_duraklari"] = [g["duraklar"] for g in rota["gunler"]]
            return self.maliyet_ajani.hesapla(istek, bacak, capa, ayar)

        # Deneyime en az dokunan adım önce: ulaşım → yemek → konaklama → (profile en az uyan)
        # ücretli duraklar → şehirlerarası → ikinci kademe düşüşler
        stratejiler = ["ulasim", "yemek", "konaklama", "aktivite", "sehirlerarasi", "yemek", "konaklama"]
        for adim in stratejiler:
            toplam = kisisel["kalemler"]["toplam"]
            if toplam <= limit or len(turlar) >= self.MAKS_MUZAKERE_TURU:
                break
            asim = toplam - limit
            onceki = toplam
            aciklama = None
            if adim == "ulasim" and ayar["ulasim_modu"] == "taksi":
                ayar["ulasim_modu"] = "toplu"
                aciklama = "Şehir içi ulaşım taksiden toplu taşımaya çevrildi"
            elif adim == "aktivite" and kisisel["kalemler"]["aktivite"] > 0:
                self.maliyet_ajani.soyle("plan", "istek",
                                         f"Bütçe {asim:,.0f} TL aşılıyor; ücretli durakların yerine ücretsiz alternatif öner.")
                kullanilan = [p["isim"] for g in rota["gunler"] for p in g["duraklar"]]
                yeni_rota, degisen = self._ucretsize_cevir(istek, profil, rota, haric + kullanilan + [r["isim"] for r in tum_red], asim)
                if degisen:
                    rota = yeni_rota
                    bacak = [_bacaklar(rota["merkez"], g["duraklar"]) for g in rota["gunler"]]
                    aciklama = "Ücretli yerler ücretsiz alternatiflerle değiştirildi: " + "; ".join(degisen)
                    self.plan_ajani.soyle("maliyet", "karar", aciklama)
                else:
                    self.plan_ajani.soyle("maliyet", "ret", "Profile yeterince uyan ücretsiz alternatif yok; "
                                          "kişiselleştirmeyi korumak için duraklar değiştirilmedi.")
            elif adim in ("yemek", "konaklama") and SEVIYELER.index(ayar[adim]) > 0:
                eski = ayar[adim]
                ayar[adim] = SEVIYELER[SEVIYELER.index(eski) - 1]
                aciklama = f"{adim.capitalize()} seviyesi {eski} → {ayar[adim]} düşürüldü"
            elif adim == "sehirlerarasi" and ayar["sehirlerarasi"] == "ucak" and not poi_data.yurtdisi_mi(istek["sehir"]):
                ayar["sehirlerarasi"] = "otobus"
                aciklama = "Şehirlerarası ulaşım uçaktan otobüse çevrildi (öneri)"
            if not aciklama:
                continue
            kisisel = hesapla()
            yeni = kisisel["kalemler"]["toplam"]
            turlar.append({"tur": len(turlar) + 1, "adim": adim, "aciklama": aciklama,
                           "onceki_tl": onceki, "yeni_tl": yeni, "kazanc_tl": onceki - yeni,
                           "butce_icinde": yeni <= limit})
            self.maliyet_ajani.soyle("orkestrator", "karar",
                                     f"Müzakere turu {len(turlar)}: {aciklama} → {yeni:,.0f} TL "
                                     f"({'bütçe içinde' if yeni <= limit else f'{yeni - limit:,.0f} TL fazla'})")
        if kisisel["kalemler"]["toplam"] > limit:
            self.maliyet_ajani.soyle("orkestrator", "uyari",
                                     f"Tüm stratejiler denendi; plan bütçeyi {kisisel['kalemler']['toplam'] - limit:,.0f} TL aşıyor. "
                                     "Gün sayısını azaltmayı ya da bütçeyi artırmayı düşünebilirsin.")
        maliyet = {**maliyet, "kisisel": kisisel, "bacaklar": bacak}
        if turlar and any(t["adim"] == "aktivite" for t in turlar):
            maliyet["standart"] = self.maliyet_ajani.hesapla(
                dict(istek, _plan_duraklari=standart), [_bacaklar(rota["merkez"], g) for g in standart],
                capa, {**maliyet["standart"]["ayar"]})
        return turlar, rota, maliyet

    def _ucretsize_cevir(self, istek, profil, rota, haric, asim):
        ucretli = sorted([(p, g) for g in rota["gunler"] for p in g["duraklar"] if p.get("ucret_tl")],
                         key=lambda pg: poi_puani(pg[0], profil))            # profile en az uyan önce
        if not ucretli:
            return rota, []
        alternatifler = self.plan_ajani.alternatif_bul(istek, profil, haric, len(ucretli), ucretsiz=True)
        degisen, kazanc = [], 0.0
        yerler = [p for g in rota["gunler"] for p in g["duraklar"]]
        for p, _ in ucretli:
            if kazanc >= asim or not alternatifler:
                break
            # Profile çok daha az uyan bir alternatifle değiştirmek kişiselleştirmeyi bozar
            alt = next((a for a in alternatifler if poi_puani(a, profil) >= poi_puani(p, profil) - 2), None)
            if alt is None:
                continue
            alternatifler.remove(alt)
            yerler[yerler.index(p)] = alt
            kazanc += float(p["ucret_tl"]) * istek["kisi"]
            degisen.append(f"{p['isim']} → {alt['isim']}")
        if not degisen:
            return rota, []
        return self.rota_ajani.calis(istek, profil, yerler, self.gercek_yol), degisen


def _yogun_merkez(yerler: list, yaricap_km: float = 20) -> dict | None:
    """En çok komşusu olan noktanın çevresindeki yerlerin ortalaması."""
    if not yerler:
        return None
    en_iyi = max(yerler, key=lambda a: sum(1 for b in yerler if routing.haversine(a, b) <= yaricap_km))
    kume = [b for b in yerler if routing.haversine(en_iyi, b) <= yaricap_km]
    return {"lat": sum(p["lat"] for p in kume) / len(kume), "lon": sum(p["lon"] for p in kume) / len(kume)}


def _yedekler(adaylar: list, rota: dict) -> list:
    planda = [p["isim"] for g in rota["gunler"] for p in g["duraklar"]]
    out = []
    for p in adaylar:
        if any(ayni_yer_mi(p["isim"], x) for x in planda + [o["isim"] for o in out]):
            continue
        out.append(p)
    return out[:8]


def _istek_dogrula(istek: dict) -> dict:
    i = dict(istek)
    i["sehir"] = str(i.get("sehir") or "").strip()
    if not i["sehir"]:
        raise ValueError("Şehir boş olamaz.")
    i["gun"] = max(1, min(14, int(i.get("gun") or 1)))
    i["kisi"] = max(1, min(20, int(i.get("kisi") or 1)))
    i["butce_kategorisi"] = i.get("butce_kategorisi") if i.get("butce_kategorisi") in SEVIYELER else "orta"
    try:
        lim = float(i.get("butce_limiti") or 0)
    except (TypeError, ValueError):
        lim = 0
    i["butce_limiti"] = lim if lim > 0 else None
    i["mbti"] = (i.get("mbti") or "ENFP").upper()[:4]
    i["serbest_not"] = str(i.get("serbest_not") or "")[:2000]
    return i


def _restoran_ata(rota: dict, restoranlar: list, istek: dict, profil: dict) -> list:
    """Her gün için öğle (öğle molasından önceki durağa) ve akşam (son durağa) en yakın restoran."""
    kat = istek["butce_kategorisi"]
    havuz = []
    for r in restoranlar:
        try:
            r = {**r, "lat": float(r["lat"]), "lon": float(r["lon"])}
        except (KeyError, TypeError, ValueError):
            continue
        # Merkezden çok uzak restoran koordinatı büyük olasılıkla hatalıdır (halüsinasyon)
        if routing.haversine(rota["merkez"], r) <= 25 and not any(ayni_yer_mi(r["isim"], h["isim"]) for h in havuz):
            havuz.append(r)
    kullanilan: set = set()
    bitkisel = any(b in ("vejetaryen", "vegan") for b in profil.get("beslenme", []))
    plan = []

    def sec(nokta):
        if not havuz or nokta is None:
            return None
        def skor(r):
            fiyat_uyum = 0 if r.get("fiyat") == kat else 1.5
            tekrar = 3 if r["isim"] in kullanilan else 0
            metin = normalize(f"{r['isim']} {r.get('mutfak', '')}")
            diyet = 0.0
            if bitkisel:
                if any(k in metin for k in ("vejetaryen", "vegan", "vegetarian")):
                    diyet -= 0.5
                elif any(k in metin for k in ("kofte", "kebap", "kebab", "et ", "balik", "iskender", "mangal", "steak")):
                    diyet += 4
            return routing.haversine(nokta, r) + fiyat_uyum + tekrar + diyet
        r = min(havuz, key=skor)
        kullanilan.add(r["isim"])
        return {**r, "mesafe_km": round(routing.haversine(nokta, r), 2)}

    for g in rota["gunler"]:
        d = g["duraklar"]
        ogle_oncesi = None
        sira_no = 0
        for olay in g["cizelge"]["plan"]:
            if olay.get("ogle"):
                ogle_oncesi = d[sira_no - 1] if sira_no > 0 else (d[0] if d else None)
                break
            sira_no += 1
        if ogle_oncesi is None and d:
            ogle_oncesi = d[min(1, len(d) - 1)]
        ogle = sec(ogle_oncesi)
        aksam = sec(d[-1] if d else None)
        plan.append({"gun": g["gun"], "ogle": ogle, "aksam": aksam,
                     "not": (f"Beslenme: {', '.join(profil['beslenme'])}" if profil.get("beslenme") else "")})
    return plan


# ---------------------------------------------------------------------------
# HAFIZAYA KAYIT
# ---------------------------------------------------------------------------

def hafizaya_kaydet(username: str, sonuc: dict, plan_id: int | None):
    istek = sonuc["istek"]
    yerler = [p for g in sonuc["rota"]["gunler"] for p in g["duraklar"]]
    memory.ziyaretleri_kaydet(username, istek["sehir"], yerler, plan_id)
    for g in sonuc["rota"]["gunler"]:
        memory.algoritma_kaydet(username, istek["sehir"], g["gun"], len(g["duraklar"]),
                                g["yaris"]["kazanan"], g["yaris"]["sonuclar"], plan_id)
    k = sonuc["maliyet"]["kisisel"]["kalemler"]
    s = sonuc["maliyet"]["standart"]["kalemler"]
    memory.maliyet_kaydi_ekle(username, istek["sehir"], istek["gun"], istek["kisi"], istek["butce_kategorisi"],
                              istek.get("butce_limiti"), s["toplam"], k["toplam"], sonuc["tasarruf_yuzde"],
                              sonuc["butce_icinde"], len(sonuc["muzakere"]), k, plan_id)
    if istek.get("serbest_not"):
        memory.not_ekle(username, istek["serbest_not"], "serbest_not", istek["sehir"], plan_id)
    memory.not_ekle(username, sonuc["profil"].get("seyahat_notu", ""), "seyahat_notu", istek["sehir"], plan_id)
    memory.profil_kaydet(username, {k: v for k, v in sonuc["profil"].items()
                                    if k not in ("seyahat_notu", "daha_once_gidilenler")})
