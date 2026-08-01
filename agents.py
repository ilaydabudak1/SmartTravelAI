# agents.py — tüm ajanlar tek dosyada, Gemini API + statik fallback

import os
import json
import math
import random
import base64
import hashlib
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    from google import genai as _genai
except Exception:
    _genai = None

def _gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if _genai and api_key:
        try:
            return _genai.Client(api_key=api_key)
        except Exception:
            pass
    return None

def _gemini_generate(prompt: str) -> str | None:
    client = _gemini_client()
    if not client:
        return None
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = resp.text or ""
        import re as _re
        # Kod bloğu sarmalını temizle: ```html ... ``` veya ``` ... ```
        text = _re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
        text = _re.sub(r"\s*```\s*$", "", text.strip())
        # <html><body> sarmalını temizle — sadece içeriği al
        body = _re.search(r"<body[^>]*>([\s\S]*?)</body>", text, _re.IGNORECASE)
        if body:
            text = body.group(1).strip()
        return text.strip() if text.strip() else None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# AJAN İLETİŞİM BUS'I — ajanlar birbirini doğrudan çağırmak yerine bu bus
# üzerinden mesaj yayınlar/okur. Tek-oturumluk, in-process, dağıtık değil.
# ---------------------------------------------------------------------------

@dataclass
class AgentMessage:
    sender: str    # "aco" | "ulasim" | "restoran" | "maliyet" | "plan"
    type: str      # "<gönderen>.<olay>", örn. "aco.route"
    payload: dict
    ts: float = field(default_factory=time.time)


class AgentBus:
    """Basit yayınla/oku (pub/sub) mesaj kütüğü — session_state içinde tek örnek tutulur."""

    def __init__(self):
        self._log: list[AgentMessage] = []

    def publish(self, sender: str, type: str, payload: dict) -> AgentMessage:
        msg = AgentMessage(sender, type, payload)
        self._log.append(msg)
        return msg

    def latest(self, type: str, default=None):
        for msg in reversed(self._log):
            if msg.type == type:
                return msg.payload
        return default

    def log(self) -> list:
        return list(self._log)


def _sig(data: dict, fields: list) -> str:
    """Bir ajanın karar üretirken kullandığı alanların kısa özeti — değişim algılama için."""
    snapshot = {k: data.get(k) for k in fields}
    raw = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def _llm_decide(prompt: str, fallback: str) -> str:
    """Narratif (JSON olmayan) ajan kararları için ortak Gemini-sonra-statik deseni."""
    text = _gemini_generate(prompt)
    return text if text else fallback


# ---------------------------------------------------------------------------
# MBTI AJAN
# ---------------------------------------------------------------------------

class MBTIAgent:
    ARKETIPLER = {
        "INTJ": "Stratejik Mimar",     "INTP": "Mantıkçı Düşünür",
        "ENTJ": "Komutan Lider",       "ENTP": "Yenilikçi Tartışmacı",
        "INFJ": "Savunucu Vizyoner",   "INFP": "Hayalperest Arabulucu",
        "ENFJ": "Karizmatik Öğretmen", "ENFP": "Özgür Ruhlu Kaşif",
        "ISTJ": "Güvenilir Denetçi",   "ISFJ": "Koruyucu Savunucu",
        "ESTJ": "Yönetici Organizatör","ESFJ": "Toplumcu Bakıcı",
        "ISTP": "Usta Teknisyen",      "ISFP": "Sanatçı Kâşif",
        "ESTP": "Girişken Girişimci",  "ESFP": "Eğlenceli Sunucu",
    }

    SEYAHAT_TERCIHLERI = {
        "INTJ": ["tarihi mekanlar", "müzeler", "kütüphaneler", "mimari yapılar"],
        "INTP": ["bilim müzeleri", "teknoloji merkezleri", "arkeolojik alanlar"],
        "ENTJ": ["iş merkezleri", "lüks oteller", "fine dining", "networking etkinlikleri"],
        "ENTP": ["startup hubs", "sanat galerileri", "alternatif mekanlar", "sokak sanatı"],
        "INFJ": ["manevi mekanlar", "doğa yürüyüşleri", "yerel kültür", "el sanatları"],
        "INFP": ["romantik köşeler", "kitap kafeleri", "doğa manzaraları", "yerel sanat"],
        "ENFJ": ["topluluk etkinlikleri", "yerel festivaller", "sosyal projeler", "kültürel turlar"],
        "ENFP": ["macera sporları", "gece hayatı", "street food", "spontane keşifler"],
        "ISTJ": ["organize turlar", "tarihi müzeler", "geleneksel restoranlar", "planlı rotalar"],
        "ISFJ": ["aile dostu mekanlar", "geleneksel kültür", "rahat oteller", "yerel mutfak"],
        "ESTJ": ["verimli turlar", "ünlü turistik yerler", "kaliteli restoranlar", "örgütlü aktiviteler"],
        "ESFJ": ["grup aktiviteleri", "sosyal mekanlar", "popüler turistik spotlar", "yerel pazarlar"],
        "ISTP": ["teknik müzeler", "endüstriyel alanlar", "bağımsız keşif", "macera sporları"],
        "ISFP": ["doğa yürüyüşleri", "fotoğraf mekanları", "sanat müzeleri", "sessiz köşeler"],
        "ESTP": ["aktif sporlar", "heyecanlı aktiviteler", "canlı barlar", "spontane maceralar"],
        "ESFP": ["plajlar", "gece hayatı", "alışveriş merkezleri", "eğlence parkları"],
    }

    STATIK_RAPORLAR = {
        "ENFP": """
<h2>🌟 ENFP — Özgür Ruhlu Kaşif</h2>
<p>Sen dünyanın en meraklı ve coşkulu gezginlerinden birisin! Her seyahat senin için yeni bir macera, yeni insanlar ve beklenmedik deneyimler demek.</p>
<h3>Seyahat Tarzın</h3>
<ul>
<li>Spontane kararlar vermekten korkmazsın</li>
<li>Yerel halkla kaynaşmak en büyük zevkin</li>
<li>Off-the-beaten-path mekanları tercih edersin</li>
<li>Her deneyimi hikayeye dönüştürürsün</li>
</ul>
<h3>Önerilen Destinasyonlar</h3>
<p>Bali, Porto, Buenos Aires, Marakeş, İstanbul</p>
<h3>Seyahat İpuçları</h3>
<p>Planlamaya fazla takılma — güzel anlar planlanmamış anlardadır. Ama temel rezervasyonları yap!</p>""",
        "INTJ": """
<h2>🏛️ INTJ — Stratejik Mimar</h2>
<p>Seyahatlerini titizlikle planlayan, her rotayı optimize eden stratejik bir gezginsin. Kalite ve derinlik senin için miktardan önemli.</p>
<h3>Seyahat Tarzın</h3>
<ul>
<li>Detaylı ön araştırma yaparsın</li>
<li>Turistik kalabalıklardan kaçınırsın</li>
<li>Tarihi ve kültürel derinliği tercih edersin</li>
<li>Sessiz, düşünceli rotalar seçersin</li>
</ul>
<h3>Önerilen Destinasyonlar</h3>
<p>Kyoto, Prag, Edinburgh, Kahire, Atina</p>
<h3>Seyahat İpuçları</h3>
<p>Her şeyi planlamak güzel ama bazen kendiliğinden gelişen anlara yer bırak.</p>""",
        "INFP": """
<h2>🌿 INFP — Hayalperest Arabulucu</h2>
<p>Seyahat senin için bir kaçış değil, derinleşme yolu. Doğanın içinde, sessiz köylerde ve sanatla dolu mekanlarda kendini bulursun.</p>
<h3>Seyahat Tarzın</h3>
<ul>
<li>Huzurlu, sakin destinasyonları tercih edersin</li>
<li>Yerel sanat ve el sanatlarına ilgi duyarsın</li>
<li>Yavaş seyahat (slow travel) sana göre</li>
<li>Anlamlı deneyimler arar, fotoğraf koleksiyonu yapmazsın</li>
</ul>
<h3>Önerilen Destinasyonlar</h3>
<p>Cappadocia, İzlanda, Toskana, Luang Prabang, Fethiye</p>""",
    }

    def _default_rapor(self, mbti: str, archetype: str, preferences: list) -> str:
        pref_str = ", ".join(preferences[:4])
        return f"""
<h2>{mbti} — {archetype}</h2>
<p>Seyahat kişiliğin analiz edildi. Tercihlerine göre özelleştirilmiş bir rota deneyimi seni bekliyor.</p>
<h3>Seyahat Tercihlerin</h3>
<p>{pref_str}</p>
<h3>Genel Profil</h3>
<p>{mbti} tipindeki gezginler genellikle kendine özgü ve tutarlı bir seyahat stili geliştirirler.
Senin için en iyi seyahat deneyimi kişisel değerlerinle örtüşen destinasyonlarda yaşanır.</p>
<h3>Öneri</h3>
<p>Tercihlerine göre oluşturulan rotanda {pref_str} gibi deneyimler seni bekliyor.</p>"""

    # Skor tablosu: q -> {harf -> {boyut: puan}}
    _SCORING = {
        "q1":  {"A": {"E":2}, "B": {"N":1,"E":1}, "C": {"I":1,"F":1}, "D": {"I":2}},
        "q2":  {"A": {"S":2}, "B": {"N":2},        "C": {"F":1,"S":1}, "D": {"N":1,"F":1}},
        "q3":  {"A": {"T":1,"J":1}, "B": {"T":2},  "C": {"P":1},       "D": {"F":2}},
        "q4":  {"A": {"J":2}, "B": {"J":1,"T":1},  "C": {"P":2},       "D": {"P":1,"I":1}},
        "q5":  {"A": {"E":2}, "B": {"E":1,"S":1},  "C": {"N":1,"I":1}, "D": {"I":2}},
        "q6":  {"A": {"E":2}, "B": {"S":1,"J":1},  "C": {"N":2},       "D": {"N":1,"F":1}},
        "q7":  {"A": {"T":2}, "B": {"T":1,"J":1},  "C": {"F":1,"P":1}, "D": {"F":2}},
        "q8":  {"A": {"J":2}, "B": {"J":1,"T":1},  "C": {"P":1},       "D": {"P":2}},
        "q9":  {"A": {"E":2}, "B": {"N":1,"T":1},  "C": {"N":1,"F":1}, "D": {"I":2}},
        "q10": {"A": {"J":2}, "B": {"J":1},         "C": {"P":1,"N":1}, "D": {"P":2,"I":1,"F":1}},
        "q11": {"A": {"E":2}, "B": {"E":1,"S":1},  "C": {"I":1,"N":1}, "D": {"I":2}},
        "q12": {"A": {"S":2}, "B": {"S":1,"F":1},  "C": {"N":2},       "D": {"N":1,"P":1}},
        "q13": {"A": {"T":2}, "B": {"T":1,"J":1},  "C": {"F":1},       "D": {"F":2}},
        "q14": {"A": {"J":2}, "B": {"J":1,"S":1},  "C": {"P":1},       "D": {"P":2}},
        "q15": {"A": {"E":2}, "B": {"E":1,"F":1},  "C": {"I":1},       "D": {"I":2}},
        "q16": {"A": {"S":2}, "B": {"S":1,"T":1},  "C": {"N":1,"P":1}, "D": {"N":2}},
        "q17": {"A": {"T":2}, "B": {"T":1,"J":1},  "C": {"F":1,"P":1}, "D": {"F":2}},
        "q18": {"A": {"J":2}, "B": {"J":1},         "C": {"P":1},       "D": {"P":2}},
        "q19": {"A": {"E":2}, "B": {"E":1},         "C": {"I":1,"F":1}, "D": {"I":2}},
        "q20": {"A": {"S":2}, "B": {"S":1,"E":1},  "C": {"N":1,"I":1}, "D": {"N":2}},
    }

    def _determine_mbti(self, answers: dict) -> str:
        scores = {"E": 0, "I": 0, "N": 0, "S": 0, "T": 0, "F": 0, "J": 0, "P": 0}
        for q, opt_scores in self._SCORING.items():
            raw = answers.get(q, "A")
            # "A) Metin..." formatından sadece ilk harfi al
            letter = raw[0].upper() if isinstance(raw, str) and raw else "A"
            if letter not in opt_scores:
                letter = "A"
            for dim, val in opt_scores[letter].items():
                scores[dim] += val
        ei = "E" if scores["E"] >= scores["I"] else "I"
        ns = "N" if scores["N"] >= scores["S"] else "S"
        tf = "T" if scores["T"] >= scores["F"] else "F"
        jp = "J" if scores["J"] >= scores["P"] else "P"
        return ei + ns + tf + jp

    # ── Genişletilmiş form: 70 madde, 5'li Likert (1=Kesinlikle Katılmıyorum … 5=Kesinlikle Katılıyorum)
    # Her madde bir kutba (dim) yönelik ifadedir; puan o kutba, (6-puan) karşıt kutba yazılır.
    _KARSIT = {"E": "I", "I": "E", "S": "N", "N": "S", "T": "F", "F": "T", "J": "P", "P": "J"}

    EXTENDED_ITEMS = [
        # ── E / I (18 madde) ──────────────────────────────────────────────
        {"dim": "E", "text": "Seyahatte yeni insanlarla tanışmak beni enerjilendirir."},
        {"dim": "I", "text": "Kalabalık turistik yerlerde uzun süre kalmak beni yorar."},
        {"dim": "E", "text": "Grup turlarında sosyalleşmek gezinin en keyifli yanıdır."},
        {"dim": "I", "text": "Tek başıma seyahat etmek bana özgürlük hissi verir."},
        {"dim": "E", "text": "Gittiğim yerde yerel halkla hemen sohbet başlatırım."},
        {"dim": "I", "text": "Gezi sonrası otelde sessiz vakit geçirerek şarj olurum."},
        {"dim": "E", "text": "Hostellerin ortak alanlarında vakit geçirmeyi severim."},
        {"dim": "I", "text": "Sakin ve az bilinen destinasyonları kalabalık şehirlere tercih ederim."},
        {"dim": "E", "text": "Seyahat anılarımı anında sosyal medyada paylaşırım."},
        {"dim": "I", "text": "Bir kafede tek başıma oturup şehri izlemek bana yeter."},
        {"dim": "E", "text": "Gece hayatı canlı olan şehirler beni cezbeder."},
        {"dim": "I", "text": "Seyahatte günlük tutmayı veya iç gözlem yapmayı severim."},
        {"dim": "E", "text": "Kalabalık festival ve etkinlikler gezimin vazgeçilmezidir."},
        {"dim": "I", "text": "Rehberli grup turları yerine kendi başıma gezmeyi yeğlerim."},
        {"dim": "E", "text": "Yol arkadaşlarımla sürekli sohbet etmek yolculuğu kısaltır."},
        {"dim": "I", "text": "Doğada yalnız yürüyüş yapmak şehir turundan daha çekicidir."},
        {"dim": "E", "text": "Yemekleri kalabalık ve hareketli mekânlarda yemeyi severim."},
        {"dim": "I", "text": "Müze ve galerileri sessizce, kendi hızımda gezmek isterim."},
        # ── S / N (18 madde) ──────────────────────────────────────────────
        {"dim": "S", "text": "Bir şehirde önce en ünlü somut yapıları (anıt, kule, saray) görmek isterim."},
        {"dim": "N", "text": "Bir destinasyonun hikâyesi ve atmosferi, görülecek yerler listesinden önemlidir."},
        {"dim": "S", "text": "Gezi planımı kanıtlanmış, popüler rotalar üzerine kurarım."},
        {"dim": "N", "text": "Haritada olmayan yerleri keşfetme fikri beni heyecanlandırır."},
        {"dim": "S", "text": "Yerel mutfağı denemek benim için gezinin en somut zevkidir."},
        {"dim": "N", "text": "Gezdiğim yerlerin efsaneleri ve sembolik anlamları ilgimi çeker."},
        {"dim": "S", "text": "Müzede eserlerin tarihî gerçekleri ve detayları beni cezbeder."},
        {"dim": "N", "text": "Bir sokakta yürürken oranın geçmişini hayal ederim."},
        {"dim": "S", "text": "Gördüğüm yerleri fotoğraflayıp belgelemek benim için önemlidir."},
        {"dim": "N", "text": "Seyahat benim için kendimi ve dünyayı yeniden yorumlama yoludur."},
        {"dim": "S", "text": "Gezi rehberlerindeki pratik bilgiler (saat, ücret, ulaşım) kararlarımı belirler."},
        {"dim": "N", "text": "Planladığım rotadan sapıp sezgilerimi takip etmeyi severim."},
        {"dim": "S", "text": "Bir yeri değerlendirirken orada ne yaptığıma ve ne gördüğüme bakarım."},
        {"dim": "N", "text": "Bir yeri değerlendirirken bana ne hissettirdiğine ve ne çağrıştırdığına bakarım."},
        {"dim": "S", "text": "Alışveriş yaparken yerel pazarların somut ürünlerini incelemeyi severim."},
        {"dim": "N", "text": "Sanat eserlerinin ardındaki soyut fikirler beni eserin kendisinden çok etkiler."},
        {"dim": "S", "text": "Tur programındaki her durağı sırasıyla ziyaret etmek bana güven verir."},
        {"dim": "N", "text": "Seyahatten döndüğümde en çok aklımda kalan, yaşadığım anların anlamıdır."},
        # ── T / F (17 madde) ──────────────────────────────────────────────
        {"dim": "T", "text": "Otel seçerken puan, fiyat ve konum verilerini sistematik karşılaştırırım."},
        {"dim": "F", "text": "Bir mekânın samimi atmosferi, puanlarından daha belirleyicidir."},
        {"dim": "T", "text": "Seyahat bütçem aşılırsa hangi kalemi keseceğime mantıkla karar veririm."},
        {"dim": "F", "text": "Yol arkadaşımın mutlu olması, rotanın verimli olmasından önemlidir."},
        {"dim": "T", "text": "Restoran seçerken yorumları analiz eder, duygusal pazarlamaya kanmam."},
        {"dim": "F", "text": "Yerel halkın hikâyelerini dinlemek beni derinden etkiler."},
        {"dim": "T", "text": "Gezide yaşanan bir aksaklıkta önce çözüm, sonra teselli gelir."},
        {"dim": "F", "text": "Gezide yaşanan bir aksaklıkta önce moral, sonra çözüm gelir."},
        {"dim": "T", "text": "Tur fiyatı pazarlığında rakamlarla ikna etmeyi bilirim."},
        {"dim": "F", "text": "Hediyelik eşya alırken alacağım kişinin duygusunu düşünerek seçerim."},
        {"dim": "T", "text": "Rota planında kişisel istekler değil, verimlilik öncelikli olmalıdır."},
        {"dim": "F", "text": "Grupta herkesin fikri alınmadan rota kesinleşmemelidir."},
        {"dim": "T", "text": "Seyahat değerlendirmelerimi objektif kriterlere göre yazarım."},
        {"dim": "F", "text": "Bir şehirle duygusal bağ kurarsam oraya tekrar tekrar giderim."},
        {"dim": "T", "text": "Gezi sırasında tartışmalı konularda net ve doğrudan konuşurum."},
        {"dim": "F", "text": "Yol arkadaşımın yüz ifadesinden yorulduğunu hemen anlar, planı esnetirim."},
        {"dim": "T", "text": "Kötü bir tur deneyimini şikâyet ederken kanıt ve madde sıralarım."},
        # ── J / P (17 madde) ──────────────────────────────────────────────
        {"dim": "J", "text": "Seyahat programımı gün gün, saat saat önceden planlarım."},
        {"dim": "P", "text": "En güzel geziler plansız ve kendiliğinden gelişenlerdir."},
        {"dim": "J", "text": "Bavulumu günler öncesinden liste yaparak hazırlarım."},
        {"dim": "P", "text": "Bavulumu genellikle son gece toplarım ve sorun yaşamam."},
        {"dim": "J", "text": "Rezervasyonlarımı aylar önceden garantiye alırım."},
        {"dim": "P", "text": "Konaklamayı vardığım yerde bulmak bana heyecan verir."},
        {"dim": "J", "text": "Uçuş saatinden çok önce havalimanında olmayı tercih ederim."},
        {"dim": "P", "text": "Gezide programın değişmesi beni strese sokmaz, keyiflendirir."},
        {"dim": "J", "text": "Günlük harcamalarımı seyahat sırasında düzenli kaydederim."},
        {"dim": "P", "text": "Gezi bütçemi esnek tutar, ana kalemler dışında akışına bırakırım."},
        {"dim": "J", "text": "Planladığım bir durağı atlamak zorunda kalmak beni rahatsız eder."},
        {"dim": "P", "text": "Yolda gördüğüm ilginç bir yer için tüm planı değiştirebilirim."},
        {"dim": "J", "text": "Dönüş gününe her şey tamamlanmış olarak girmek isterim."},
        {"dim": "P", "text": "Son dakika fırsatlarıyla seyahat planlamak bana göre ideal yoldur."},
        {"dim": "J", "text": "Gezi öncesi yapılacaklar listem olmadan kendimi hazır hissetmem."},
        {"dim": "P", "text": "Şehri haritasız, kaybolarak keşfetmek en sevdiğim yöntemdir."},
        {"dim": "J", "text": "Grup gezilerinde buluşma saatlerine herkesin uymasını beklerim."},
    ]

    def _determine_mbti_extended(self, likert_answers: list) -> str:
        """likert_answers: EXTENDED_ITEMS sırasıyla 1-5 arası puan listesi."""
        scores = {"E": 0, "I": 0, "N": 0, "S": 0, "T": 0, "F": 0, "J": 0, "P": 0}
        for item, val in zip(self.EXTENDED_ITEMS, likert_answers):
            try:
                v = int(val)
            except (TypeError, ValueError):
                v = 3
            v = max(1, min(5, v))
            scores[item["dim"]] += v
            scores[self._KARSIT[item["dim"]]] += 6 - v
        ei = "E" if scores["E"] >= scores["I"] else "I"
        ns = "N" if scores["N"] >= scores["S"] else "S"
        tf = "T" if scores["T"] >= scores["F"] else "F"
        jp = "J" if scores["J"] >= scores["P"] else "P"
        return ei + ns + tf + jp

    def analyze_extended(self, likert_answers: list) -> dict:
        mbti = self._determine_mbti_extended(likert_answers)
        archetype = self.ARKETIPLER.get(mbti, "Özgün Gezgin")
        preferences = self.SEYAHAT_TERCIHLERI.get(mbti, ["kültürel mekanlar", "doğa", "mutfak turu"])
        rapor = self._ai_rapor(mbti, archetype, preferences)
        return {
            "mbti_type": mbti,
            "archetype": archetype,
            "description": rapor,
            "travel_preferences": preferences,
            "form": "extended-70",
        }

    def analyze(self, answers: dict) -> dict:
        mbti = self._determine_mbti(answers)
        archetype = self.ARKETIPLER.get(mbti, "Özgün Gezgin")
        preferences = self.SEYAHAT_TERCIHLERI.get(mbti, ["kültürel mekanlar", "doğa", "mutfak turu"])
        rapor = self._ai_rapor(mbti, archetype, preferences)
        return {
            "mbti_type": mbti,
            "archetype": archetype,
            "description": rapor,
            "travel_preferences": preferences,
        }

    def _ai_rapor(self, mbti: str, archetype: str, preferences: list) -> str:
        pref_str = ", ".join(preferences[:4])
        prompt = (
            f"Sen bir seyahat kişilik uzmanısın. {mbti} ({archetype}) tipindeki bir gezgin için "
            f"Türkçe, samimi ve ilham verici bir seyahat kişilik raporu yaz. "
            f"Bu kişinin seyahat tercihleri: {pref_str}. "
            f"Rapor şunları içersin: kişilik özeti (2-3 cümle), seyahat tarzı (4 madde), "
            f"önerilen destinasyonlar (5 şehir), pratik seyahat ipuçları (2-3 cümle). "
            f"Yanıtı sade HTML olarak döndür (h2, h3, p, ul, li etiketleri kullan). "
            f"Inline CSS KULLANMA — yalnızca semantik HTML döndür, stil üst katmanda uygulanacak."
        )
        ai_text = _gemini_generate(prompt)
        if ai_text:
            return ai_text
        return self.STATIK_RAPORLAR.get(mbti) or self._default_rapor(mbti, archetype, preferences)


# ---------------------------------------------------------------------------
# ACO AJAN
# ---------------------------------------------------------------------------

class ACOAgent:
    POPULER_YERLER = {
        "istanbul": [
            {"name": "Sultanahmet Camii", "lat": 41.0054, "lon": 28.9768},
            {"name": "Ayasofya",          "lat": 41.0086, "lon": 28.9802},
            {"name": "Topkapı Sarayı",    "lat": 41.0115, "lon": 28.9833},
            {"name": "Kapalıçarşı",       "lat": 41.0106, "lon": 28.9681},
            {"name": "Galata Kulesi",     "lat": 41.0256, "lon": 28.9742},
            {"name": "Boğaz Köprüsü",     "lat": 41.0462, "lon": 29.0338},
            {"name": "Beylerbeyi Sarayı", "lat": 41.0416, "lon": 29.0453},
            {"name": "Dolmabahçe Sarayı", "lat": 41.0392, "lon": 29.0006},
        ],
        "ankara": [
            {"name": "Anıtkabir",          "lat": 39.9254, "lon": 32.8369},
            {"name": "Ankara Kalesi",      "lat": 39.9403, "lon": 32.8631},
            {"name": "Anadolu Medeniyetleri Müzesi", "lat": 39.9401, "lon": 32.8618},
            {"name": "Kızılay Meydanı",    "lat": 39.9208, "lon": 32.8541},
            {"name": "Hamamönü",           "lat": 39.9378, "lon": 32.8579},
            {"name": "Gençlik Parkı",      "lat": 39.9317, "lon": 32.8572},
        ],
        "izmir": [
            {"name": "Kemeraltı Çarşısı", "lat": 38.4192, "lon": 27.1287},
            {"name": "Saat Kulesi",       "lat": 38.4194, "lon": 27.1290},
            {"name": "Kordon",            "lat": 38.4231, "lon": 27.1377},
            {"name": "Kadifekale",        "lat": 38.4088, "lon": 27.1411},
            {"name": "Ephesus",           "lat": 37.9395, "lon": 27.3408},
            {"name": "Çeşme Kalesi",      "lat": 38.3228, "lon": 26.3053},
        ],
        "antalya": [
            {"name": "Kaleiçi",           "lat": 36.8864, "lon": 30.7044},
            {"name": "Düden Şelalesi",    "lat": 36.8923, "lon": 30.7601},
            {"name": "Antalya Müzesi",    "lat": 36.8888, "lon": 30.6969},
            {"name": "Konyaaltı Plajı",   "lat": 36.8755, "lon": 30.6672},
            {"name": "Aspendos",          "lat": 36.9371, "lon": 31.1706},
            {"name": "Perge Antik Kenti", "lat": 36.9609, "lon": 30.8553},
        ],
        "kapadokya": [
            {"name": "Göreme Açık Hava Müzesi", "lat": 38.6431, "lon": 34.8297},
            {"name": "Uçhisar Kalesi",     "lat": 38.6282, "lon": 34.7947},
            {"name": "Derinkuyu Yer Altı Şehri", "lat": 38.3731, "lon": 34.7344},
            {"name": "Paşabağı",           "lat": 38.6697, "lon": 34.8394},
            {"name": "Avanos",             "lat": 38.7172, "lon": 34.8494},
        ],
    }

    def _get_popular_locations(self, destination: str, mbti_type: str) -> list:
        key = destination.lower().strip()
        for k, locs in self.POPULER_YERLER.items():
            if k in key or key in k:
                return locs
        # generic fallback
        return [
            {"name": f"{destination} Merkezi",      "lat": 39.9, "lon": 32.8},
            {"name": f"{destination} Müzesi",        "lat": 39.91, "lon": 32.81},
            {"name": f"{destination} Tarihi Alan",   "lat": 39.92, "lon": 32.82},
            {"name": f"{destination} Pazar Yeri",    "lat": 39.89, "lon": 32.79},
            {"name": f"{destination} Park",          "lat": 39.88, "lon": 32.78},
        ]

    @staticmethod
    def _distance(a: dict, b: dict) -> float:
        dlat = math.radians(b["lat"] - a["lat"])
        dlon = math.radians(b["lon"] - a["lon"])
        x = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(a["lat"]))
             * math.cos(math.radians(b["lat"]))
             * math.sin(dlon / 2) ** 2)
        return 6371 * 2 * math.asin(math.sqrt(x))

    def _aco(self, locations: list, iterations: int = 30, ants: int = 10) -> list:
        n = len(locations)
        if n <= 2:
            return list(range(n))
        pheromone = [[1.0] * n for _ in range(n)]
        dist = [[self._distance(locations[i], locations[j]) for j in range(n)] for i in range(n)]
        best_path, best_dist = list(range(n)), float("inf")
        for _ in range(iterations):
            for _ in range(ants):
                path = [0]
                unvisited = set(range(1, n))
                while unvisited:
                    cur = path[-1]
                    probs = []
                    for nxt in unvisited:
                        d = dist[cur][nxt] or 0.001
                        probs.append((nxt, (pheromone[cur][nxt] ** 1.0) * ((1.0 / d) ** 2.0)))
                    total = sum(p for _, p in probs)
                    r = random.random() * total
                    cumul = 0.0
                    chosen = probs[0][0]
                    for nxt, p in probs:
                        cumul += p
                        if cumul >= r:
                            chosen = nxt
                            break
                    path.append(chosen)
                    unvisited.remove(chosen)
                total_d = sum(dist[path[i]][path[i + 1]] for i in range(n - 1))
                if total_d < best_dist:
                    best_dist = total_d
                    best_path = path[:]
                for i in range(n - 1):
                    pheromone[path[i]][path[i + 1]] += 1.0 / (total_d or 1)
            for i in range(n):
                for j in range(n):
                    pheromone[i][j] *= 0.9
        return best_path

    def optimize_route(self, travel_data: dict) -> dict:
        destination = travel_data.get("destination", "İstanbul")
        mbti = travel_data.get("mbti_type", "ENFP")
        locations = self._get_popular_locations(destination, mbti)
        duration = travel_data.get("duration_days", 3)
        max_loc = min(len(locations), max(4, duration * 2))
        locations = locations[:max_loc]
        path = self._aco(locations)
        optimized = [locations[i] for i in path]
        total_dist = sum(
            self._distance(optimized[i], optimized[i + 1])
            for i in range(len(optimized) - 1)
        ) if len(optimized) > 1 else 0
        score = min(100, max(60, 100 - int(total_dist / 2)))
        return {
            "optimized_route": [loc["name"] for loc in optimized],
            "locations": optimized,
            "optimized_path": path,
            "total_distance": round(total_dist, 2),
            "optimization_score": score,
            "destination": destination,
            "tahmini_toplam_mesafe_km": round(total_dist, 1),
            "rota_uyumluluk_skoru": score,
        }

    def act(self, bus: "AgentBus", travel_data: dict) -> dict:
        """Otonom giriş noktası: değişmemiş girdi varsa yeniden kullanır, yoksa
        rotayı hesaplar ve Gemini'den rota gerekçesi isteyip bus'a yayınlar."""
        sig = _sig(travel_data, ["destination", "mbti_type", "duration_days"])
        prev = bus.latest("aco.route")
        if prev and prev.get("sig") == sig:
            reused = {**prev, "reused": True}
            bus.publish("aco", "aco.route", reused)
            return reused

        result = self.optimize_route(travel_data)
        commentary = _llm_decide(
            f"Bir seyahat rotası için 1-2 cümlelik Türkçe, samimi bir gerekçe yaz. "
            f"Rota: {', '.join(result['optimized_route'])}. "
            f"Toplam mesafe: {result['tahmini_toplam_mesafe_km']} km. "
            f"Gezginin MBTI tipi: {travel_data.get('mbti_type', 'ENFP')}. "
            f"Sadece düz metin döndür, HTML veya madde işareti kullanma.",
            fallback="Rota, konumlar arası toplam mesafeyi en aza indirecek şekilde optimize edildi.",
        )
        result = {**result, "ai_commentary": commentary, "sig": sig, "reused": False}
        bus.publish("aco", "aco.route", result)
        return result


# ---------------------------------------------------------------------------
# ULAŞIM AJAN
# ---------------------------------------------------------------------------

class UlasimAgent:
    SEHIR_ULASIM = {
        "istanbul": {
            "metro": "M1-M11 hatları, Marmaray, Metrobüs",
            "vapur": "Şehir Hatları vapurları — Boğaz ve adalara",
            "tramvay": "T1 Kabataş-Bağcılar, T5 Eminönü-Alibeyköy",
            "taksi": "Başlangıç 25 TL + km başı ~18 TL",
        },
        "ankara": {
            "metro": "M1-M4 hatları, Ankaray",
            "otobus": "EGO otobüsleri geniş ağ",
            "taksi": "Başlangıç 20 TL + km başı ~15 TL",
        },
        "izmir": {
            "metro": "İZBAN banliyö treni, İzmir Metrosu",
            "vapur": "İzmir Körfezi feribot hatları",
            "otobus": "ESHOT otobüsleri",
            "taksi": "Başlangıç 22 TL + km başı ~16 TL",
        },
        "antalya": {
            "tramvay": "Nostaljik tramvay Kaleiçi-Müze hattı",
            "otobus": "Antalya Büyükşehir otobüsleri",
            "taksi": "Başlangıç 20 TL + km başı ~14 TL",
        },
    }

    SEHIRLERARASI = {
        "ucak": "THY, Pegasus, AnadoluJet ile ~1-3 saat. Erken rezervasyon avantajlı.",
        "otobus": "Flixbus, Metro Turizm, Ulusoy — konforlu ve ekonomik seçenek.",
        "tren": "TCDD Yüksek Hızlı Tren (YHT) — Ankara-İstanbul ~4 saat.",
        "arac": "Kendi aracınızla — esneklik en yüksek, yakıt maliyeti hesaba katılmalı.",
    }

    def get_transport_options(self, travel_data: dict) -> dict:
        destination = travel_data.get("destination", "").lower().strip()
        transport_pref = travel_data.get("transport_preference", "otobus")
        budget_cat = travel_data.get("butce_kategorisi", "orta")

        city_key = None
        for k in self.SEHIR_ULASIM:
            if k in destination or destination in k:
                city_key = k
                break

        city_transport = self.SEHIR_ULASIM.get(city_key, {
            "genel": "Şehir merkezi yürüme mesafesinde. Taksi ve özel araç kiralama önerilir.",
            "taksi": "Başlangıç ~20 TL + km başı ~15 TL",
        })

        intercity = self.SEHIRLERARASI.get(transport_pref, self.SEHIRLERARASI["otobus"])

        # Cost estimates
        cost_map = {"ekonomik": 800, "orta": 1500, "luks": 3500}
        base_cost = cost_map.get(budget_cat, 1500)

        ai_suggestions = (
            f"{destination.title()} seyahatinde şehir içi ulaşım için toplu taşıma tercih etmenizi öneririz. "
            f"Günlük ulaşım kartı alarak hem tasarruf hem kolaylık sağlayabilirsiniz. "
            f"{'Lüks' if budget_cat == 'luks' else 'Ekonomik'} bütçenize uygun "
            f"{'özel transfer' if budget_cat == 'luks' else 'toplu taşıma + taksi kombinasyonu'} idealdir."
        )

        return {
            "city_transport": city_transport,
            "intercity_transport": intercity,
            "ai_suggestions": ai_suggestions,
            "estimated_transport_cost": base_cost,
        }

    def act(self, bus: "AgentBus", travel_data: dict) -> dict:
        """Otonom giriş noktası: ACO ajanının bus'a yayınladığı rota mesafesini/
        durak sayısını okuyup Gemini'den gerekçeli bir ulaşım önerisi ister."""
        sig = _sig(travel_data, ["destination", "transport_preference", "butce_kategorisi"])
        prev = bus.latest("ulasim.transport")
        if prev and prev.get("sig") == sig:
            reused = {**prev, "reused": True}
            bus.publish("ulasim", "ulasim.transport", reused)
            return reused

        result = self.get_transport_options(travel_data)
        aco_route = bus.latest("aco.route", {})
        mesafe = aco_route.get("tahmini_toplam_mesafe_km")
        durak = len(aco_route.get("optimized_route", []) or [])
        budget_cat = travel_data.get("butce_kategorisi", "orta")
        destination = travel_data.get("destination", "").strip()

        if mesafe is not None:
            prompt = (
                f"Sen bir ulaşım planlama uzmanısın. {destination.title()} şehrinde, "
                f"ACO rota ajanının belirlediği {durak} duraklı ve toplam {mesafe} km'lik bir güzergah var. "
                f"Bütçe kategorisi: {budget_cat}. Bu mesafe ve durak sayısına göre toplu taşıma mı, "
                f"taksi/özel transfer mi, yoksa karma bir yaklaşım mı daha mantıklı, 2-3 cümlelik "
                f"Türkçe, gerekçeli bir öneri yaz. Sadece düz metin döndür."
            )
            ai_suggestions = _llm_decide(prompt, result["ai_suggestions"])
        else:
            ai_suggestions = result["ai_suggestions"]

        result = {**result, "ai_suggestions": ai_suggestions, "sig": sig, "reused": False}
        bus.publish("ulasim", "ulasim.transport", result)
        return result


# ---------------------------------------------------------------------------
# RESTORAN AJAN
# ---------------------------------------------------------------------------

class RestaurantAgent:
    RESTORANLAR = {
        "istanbul": [
            {"name": "Çiya Sofrası",        "cuisine": "Anadolu mutfağı",  "price": "orta",    "rating": 4.7, "location": "Kadıköy"},
            {"name": "Karaköy Lokantası",   "cuisine": "Türk mutfağı",    "price": "orta",    "rating": 4.5, "location": "Karaköy"},
            {"name": "Pandeli",             "cuisine": "Osmanlı mutfağı", "price": "yüksek",  "rating": 4.6, "location": "Mısır Çarşısı"},
            {"name": "Mikla",               "cuisine": "Modern Türk",     "price": "yüksek",  "rating": 4.8, "location": "Beyoğlu"},
            {"name": "Hamdi Restaurant",    "cuisine": "Kebap",           "price": "orta",    "rating": 4.4, "location": "Eminönü"},
            {"name": "Salt Galata Cafe",    "cuisine": "Cafe/brunch",     "price": "düşük",   "rating": 4.3, "location": "Galata"},
        ],
        "ankara": [
            {"name": "Trilye Restaurant",   "cuisine": "Balık",           "price": "yüksek",  "rating": 4.6, "location": "Çankaya"},
            {"name": "Kınacızade Konağı",   "cuisine": "Türk mutfağı",    "price": "orta",    "rating": 4.4, "location": "Hamamönü"},
            {"name": "Ulucanlar Açıkhava",  "cuisine": "Mangal/Izgara",   "price": "orta",    "rating": 4.3, "location": "Altındağ"},
        ],
        "izmir": [
            {"name": "Veli Usta Meze",      "cuisine": "Ege mutfağı",     "price": "orta",    "rating": 4.7, "location": "Kordon"},
            {"name": "Sakız Restaurant",    "cuisine": "Deniz mahsulleri","price": "yüksek",  "rating": 4.5, "location": "Alsancak"},
            {"name": "Kahve 6",             "cuisine": "Kahvaltı/Cafe",   "price": "düşük",   "rating": 4.4, "location": "Bornova"},
        ],
        "antalya": [
            {"name": "Vanilla Restaurant",  "cuisine": "Akdeniz mutfağı", "price": "yüksek",  "rating": 4.7, "location": "Kaleiçi"},
            {"name": "Club Arma",           "cuisine": "Deniz mahsulleri","price": "yüksek",  "rating": 4.5, "location": "Kaleiçi"},
            {"name": "Parlak Restaurant",   "cuisine": "Türk mutfağı",    "price": "düşük",   "rating": 4.3, "location": "Merkez"},
        ],
    }

    MBTI_TERCIH = {
        "INTJ": ["yüksek", "orta"], "INTP": ["orta", "düşük"],
        "ENTJ": ["yüksek"],         "ENTP": ["orta"],
        "INFJ": ["orta"],           "INFP": ["düşük", "orta"],
        "ENFJ": ["orta", "yüksek"], "ENFP": ["düşük", "orta"],
        "ISTJ": ["orta"],           "ISFJ": ["düşük", "orta"],
        "ESTJ": ["orta", "yüksek"], "ESFJ": ["orta"],
        "ISTP": ["düşük"],          "ISFP": ["düşük", "orta"],
        "ESTP": ["orta"],           "ESFP": ["yüksek", "orta"],
    }

    def get_recommendations(self, travel_data: dict, duration_days: int) -> list:
        destination = travel_data.get("destination", "").lower().strip()
        mbti = travel_data.get("mbti_type", "ENFP")
        preferred_prices = self.MBTI_TERCIH.get(mbti, ["orta"])

        city_key = None
        for k in self.RESTORANLAR:
            if k in destination or destination in k:
                city_key = k
                break

        pool = self.RESTORANLAR.get(city_key, [
            {"name": f"{destination.title()} Merkez Restaurant", "cuisine": "Türk mutfağı", "price": "orta", "rating": 4.3, "location": "Merkez"},
            {"name": f"{destination.title()} Lezzet Evi",        "cuisine": "Yerel mutfak",  "price": "düşük", "rating": 4.1, "location": "Çarşı"},
            {"name": f"{destination.title()} Fine Dining",       "cuisine": "Modern mutfak", "price": "yüksek", "rating": 4.5, "location": "Otel bölgesi"},
        ])

        preferred = [r for r in pool if r["price"] in preferred_prices]
        others = [r for r in pool if r["price"] not in preferred_prices]
        ordered = (preferred + others)[:max(3, duration_days * 2)]
        return ordered

    def create_restaurant_schedule(self, travel_data: dict, recommendations: list) -> list:
        duration = travel_data.get("duration_days", 3)
        schedule = []
        for day in range(1, duration + 1):
            idx = (day - 1) % len(recommendations) if recommendations else 0
            r = recommendations[idx] if recommendations else {"name": "Yerel restoran", "cuisine": "Türk mutfağı"}
            schedule.append({
                "day": day,
                "restaurant": r["name"],
                "cuisine": r.get("cuisine", ""),
                "location": r.get("location", "Merkez"),
                "rating": r.get("rating", 4.0),
            })
        return schedule

    def _llm_rerank(self, pool: list, mbti: str, destination: str, near: list) -> list:
        """Statik fiyat-tercihi sırasını, Gemini'ye son bir akıl-yürütme geçişi yaptırarak
        yeniden sıralar. Halüsinasyon/eksik liste durumunda TAMAMEN statik sıraya döner."""
        if not pool:
            return pool
        names = [r["name"] for r in pool]
        near_str = f" Rotadaki durak/lokasyonlar: {', '.join(near)}." if near else ""
        prompt = (
            f"Sen bir restoran küratörüsün. {destination.title()} için şu restoran listesini, "
            f"{mbti} tipi bir gezginin tercihlerine göre en uygundan en az uyguna doğru yeniden sırala."
            f"{near_str} Restoranlar: {json.dumps(names, ensure_ascii=False)}. "
            f"SADECE geçerli bir JSON dizi döndür, örn: [\"isim1\", \"isim2\"]. "
            f"Listedeki TÜM isimleri birebir aynı yaz, ekleme/çıkarma yapma."
        )
        raw = _gemini_generate(prompt)
        if not raw:
            return pool
        try:
            cleaned = raw.strip()
            if "```" in cleaned:
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            ranked_names = json.loads(cleaned.strip())
            if not isinstance(ranked_names, list):
                return pool
            by_name = {r["name"]: r for r in pool}
            if set(ranked_names) != set(by_name.keys()):
                return pool  # halüsinasyon/eksik liste — tüm-liste doğrulaması başarısız
            return [by_name[n] for n in ranked_names]
        except Exception:
            return pool

    def act(self, bus: "AgentBus", travel_data: dict) -> dict:
        """Otonom giriş noktası: statik fiyat-tercihi filtresini çalıştırır, üstüne
        Gemini ile bir yeniden-sıralama geçişi ekler, sonucu bus'a yayınlar."""
        sig = _sig(travel_data, ["destination", "mbti_type", "duration_days"])
        prev = bus.latest("restoran.recommendations")
        if prev and prev.get("sig") == sig:
            reused = {**prev, "reused": True}
            bus.publish("restoran", "restoran.recommendations", reused)
            schedule = bus.latest("restoran.schedule", [])
            bus.publish("restoran", "restoran.schedule", schedule)
            return reused

        duration = travel_data.get("duration_days", 3)
        ordered = self.get_recommendations(travel_data, duration)

        aco_route = bus.latest("aco.route", {})
        near = aco_route.get("optimized_route", []) or []
        mbti = travel_data.get("mbti_type", "ENFP")
        destination = travel_data.get("destination", "")
        reranked = self._llm_rerank(ordered, mbti, destination, near)

        schedule = self.create_restaurant_schedule(travel_data, reranked)

        result = {"recommendations": reranked, "sig": sig, "reused": False}
        bus.publish("restoran", "restoran.recommendations", result)
        bus.publish("restoran", "restoran.schedule", schedule)
        return result


# ---------------------------------------------------------------------------
# MALİYET YARDIMCI
# ---------------------------------------------------------------------------

def gercekci_maliyet_hesapla(travel_data: dict, duration_days: int) -> dict:
    kat = travel_data.get("butce_kategorisi", "orta")
    kisi = int(travel_data.get("group_size", 1))
    gun = max(1, duration_days)

    # 2026 fiyatları — 1 EUR ≈ 50 TL baz alınarak hesaplandı
    # Konaklama: ekonomik hostel/apart (~50€/gece), orta butik otel (~120€), lüks (~350€)
    KONAKLAMA = {"ekonomik": 2500, "orta": 6000, "luks": 17500}
    # Yemek: ekonomik sokak yemeği (~15€/öğün×3), orta restoran (~40€×3), lüks (~120€×3)
    YEMEK_KW  = {"ekonomik": 750,  "orta": 2000, "luks": 6000}
    # Şehir içi ulaşım: metro/otobüs günlük kart veya taksi ortalaması
    ULASIM_KW = {"ekonomik": 300,  "orta": 750,  "luks": 2000}
    # Aktivite/müze: müze giriş ~15€, tur ~40€, lüks özel tur ~150€/gün
    AKTIVITE  = {"ekonomik": 500,  "orta": 1500, "luks": 5000}
    # Şehirlerarası ulaşım gidiş-dönüş: otobüs ~600TL, uçak ~4000TL, business ~12000TL
    SEHIRLERARASI = {"ekonomik": 1500, "orta": 4000, "luks": 12000}

    geceler = max(1, gun - 1)
    std = {
        "konaklama":    round(KONAKLAMA.get(kat, 2500) * geceler * kisi * 0.9),
        "yemek":        round(YEMEK_KW.get(kat, 600) * gun * kisi * 1.1),
        "sehir_ulasim": round(ULASIM_KW.get(kat, 300) * gun * kisi),
        "aktivite":     round(AKTIVITE.get(kat, 500) * gun * kisi * 1.2),
        "sehirlerarasi":round(SEHIRLERARASI.get(kat, 1500) * kisi),
    }
    std["toplam"] = sum(std.values())

    oz = {
        "konaklama":    round(std["konaklama"] * 0.85),
        "yemek":        round(std["yemek"] * 0.80),
        "sehir_ulasim": round(std["sehir_ulasim"] * 0.75),
        "aktivite":     round(std["aktivite"] * 0.70),
        "sehirlerarasi":round(std["sehirlerarasi"] * 0.90),
    }
    oz["toplam"] = sum(oz.values())

    return {"standart": std, "ozel": oz}


# ---------------------------------------------------------------------------
# MALİYET AJAN
# ---------------------------------------------------------------------------

VERI_KLASORU = "data"
MALIYET_DOSYASI = os.path.join(VERI_KLASORU, "maliyet_gecmisi.json")


def maliyet_kaydet(kullanici, sehir, gun, kat, standart, ozel, tasarruf):
    os.makedirs(VERI_KLASORU, exist_ok=True)
    try:
        with open(MALIYET_DOSYASI, "r", encoding="utf-8") as f:
            mal = json.load(f)
    except Exception:
        mal = {"kayitlar": []}
    mal.setdefault("kayitlar", []).append({
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "kullanici": kullanici, "sehir": sehir,
        "gun_sayisi": gun, "butce_kategorisi": kat,
        "standart_plan_tl": standart, "ozellestirilmis_plan_tl": ozel,
        "tasarruf_yuzdesi": round(tasarruf, 2),
    })
    with open(MALIYET_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(mal, f, ensure_ascii=False, indent=2)


def maliyet_gecmisi_oku() -> list:
    try:
        with open(MALIYET_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f).get("kayitlar", [])
    except Exception:
        return []


class MaliyetAgent:
    SEHIR_CARPAN = {
        "istanbul": 1.3, "ankara": 1.0, "izmir": 1.1, "antalya": 1.15,
        "bodrum": 1.4,   "cesme": 1.3,  "kapadokya": 1.2,
        "paris": 2.8,    "londra": 3.0, "amsterdam": 2.5, "roma": 2.3,
        "barcelona": 2.2,"prag": 1.6,   "budapeste": 1.5, "atina": 1.8,
        "dubai": 3.5,    "tokyo": 2.8,  "bangkok": 1.4,   "new york": 3.5,
    }

    def _sehir_carpan(self, sehir: str) -> float:
        key = (sehir.lower().strip()
               .replace("ı", "i").replace("ğ", "g")
               .replace("ü", "u").replace("ş", "s")
               .replace("ö", "o").replace("ç", "c"))
        for k, v in self.SEHIR_CARPAN.items():
            if k in key or key in k:
                return v
        return 1.0

    def analyze(self, travel_data: dict, ozel_yerler: list) -> dict:
        sehir = travel_data.get("destination", "İstanbul").strip().title()
        kat = travel_data.get("butce_kategorisi", "orta")
        kullanici = travel_data.get("kullanici_adi", "kullanıcı")
        kisi = int(travel_data.get("group_size", 1))
        carpan = self._sehir_carpan(sehir)

        try:
            start = datetime.strptime(travel_data["start_date"], "%Y-%m-%d")
            end = datetime.strptime(travel_data["end_date"], "%Y-%m-%d")
            gun = max(1, (end - start).days + 1)
        except Exception:
            gun = int(travel_data.get("duration_days", 3))

        temel = gercekci_maliyet_hesapla(travel_data, gun)
        oz = dict(temel["ozel"])
        std = dict(temel["standart"])

        for k in ("konaklama", "yemek", "sehir_ulasim", "aktivite"):
            oz[k] = round(oz[k] * carpan)
            std[k] = round(std[k] * carpan)
        oz["toplam"] = sum(oz[k] for k in ("konaklama", "yemek", "sehir_ulasim", "aktivite", "sehirlerarasi"))
        std["toplam"] = sum(std[k] for k in ("konaklama", "yemek", "sehir_ulasim", "aktivite", "sehirlerarasi"))

        tasarruf_tl = std["toplam"] - oz["toplam"]
        tasarruf_yuzde = round(tasarruf_tl / std["toplam"] * 100, 1) if std["toplam"] > 0 else 0

        yer_listesi = []
        for y in (ozel_yerler or []):
            yer_listesi.append(y.get("name", str(y)) if isinstance(y, dict) else str(y))

        butce_ozeti = self._tablo(std, oz, tasarruf_tl, sehir, gun, kat, kisi)
        detayli = self._detayli_rapor(sehir, gun, kisi, kat, carpan, oz, yer_listesi)

        try:
            maliyet_kaydet(kullanici, sehir, gun, kat, std["toplam"], oz["toplam"], tasarruf_yuzde)
        except Exception:
            pass

        return {
            "standart_plan": std, "ozel_plan": oz,
            "tasarruf_tl": tasarruf_tl, "tasarruf_yuzde": tasarruf_yuzde,
            "butce_ozeti": butce_ozeti, "detayli_maliyet_analizi": detayli,
        }

    def act(self, bus: "AgentBus", travel_data: dict) -> dict:
        """Otonom giriş noktası: ACO'nun bus'a yayınladığı yer listesini okur,
        aritmetiği (analyze) değiştirmeden üstüne Gemini tasarruf anlatısı ekler."""
        sig = _sig(travel_data, ["destination", "butce_kategorisi", "group_size",
                                  "start_date", "end_date", "duration_days"])
        prev = bus.latest("maliyet.cost")
        if prev and prev.get("sig") == sig:
            reused = {**prev, "reused": True}
            bus.publish("maliyet", "maliyet.cost", reused)
            return reused

        ozel_yerler = bus.latest("aco.route", {}).get("optimized_route", [])
        result = self.analyze(travel_data, ozel_yerler)

        narrative = _llm_decide(
            f"Bir gezgin için standart plan {result['standart_plan']['toplam']} TL, "
            f"kişiselleştirilmiş plan {result['ozel_plan']['toplam']} TL "
            f"(%{result['tasarruf_yuzde']} tasarruf). Bu tasarrufun nedenini 2 cümlelik "
            f"samimi bir Türkçe anlatıyla açıkla. Sadece düz metin döndür, rakamları tekrarlama.",
            fallback=f"Kişiselleştirilmiş planınız, standart plana göre %{result['tasarruf_yuzde']} "
                     f"tasarruf sağlayacak şekilde optimize edildi.",
        )
        result = {
            **result,
            "detayli_maliyet_analizi": result["detayli_maliyet_analizi"] + f"\n\n### AI Tasarruf Analizi\n{narrative}\n",
            "ai_savings_narrative": narrative, "sig": sig, "reused": False,
        }
        bus.publish("maliyet", "maliyet.cost", result)
        return result

    def reprice(self, bus: "AgentBus", travel_data: dict, drift_factor: float) -> dict:
        """Tier-B otonom demo: kullanıcı hiçbir şeye tıklamadan, zamanla oluşan
        simüle fiyat sürüklenmesini algılayıp maliyeti kendiliğinden günceller."""
        prev = bus.latest("maliyet.cost")
        if not prev:
            return self.act(bus, travel_data)

        std = dict(prev["standart_plan"])
        oz = dict(prev["ozel_plan"])
        for k in ("konaklama", "yemek", "sehir_ulasim", "aktivite", "sehirlerarasi", "toplam"):
            std[k] = round(std[k] * (1 + drift_factor))
            oz[k] = round(oz[k] * (1 + drift_factor))
        tasarruf_tl = std["toplam"] - oz["toplam"]
        tasarruf_yuzde = round(tasarruf_tl / std["toplam"] * 100, 1) if std["toplam"] > 0 else 0

        yon = "yükseldi" if drift_factor > 0 else "geriledi"
        narrative = _llm_decide(
            f"Güncel piyasa fiyatlarındaki dalgalanma nedeniyle bir seyahat planının maliyeti "
            f"%{abs(drift_factor) * 100:.1f} {yon}. Bunu gezgine 1 cümlelik, sakinleştirici "
            f"bir Türkçe bildirimle açıkla. Sadece düz metin döndür.",
            fallback=f"Güncel fiyatlara göre tahmini maliyetiniz %{abs(drift_factor) * 100:.1f} {yon}.",
        )
        result = {
            **prev, "standart_plan": std, "ozel_plan": oz,
            "tasarruf_tl": tasarruf_tl, "tasarruf_yuzde": tasarruf_yuzde,
            "ai_drift_note": narrative, "reused": False,
        }
        bus.publish("maliyet", "maliyet.cost_update", result)
        return result

    def _detayli_rapor(self, sehir, gun, kisi, kat, carpan, oz, yer_listesi) -> str:
        gece   = max(0, gun - 1)
        gk     = round(oz["konaklama"] / gece)  if gece  > 0 else oz["konaklama"]
        gy     = round(oz["yemek"]     / gun)   if gun   > 0 else oz["yemek"]
        gu     = round(oz["sehir_ulasim"] / gun) if gun  > 0 else oz["sehir_ulasim"]
        ga     = round(oz["aktivite"]   / gun)   if gun  > 0 else oz["aktivite"]
        gk_pp  = round(gk  / kisi) if kisi > 1 else gk
        gy_pp  = round(gy  / kisi) if kisi > 1 else gy
        gu_pp  = round(gu  / kisi) if kisi > 1 else gu
        ga_pp  = round(ga  / kisi) if kisi > 1 else ga
        tot_pp = round(oz["toplam"] / kisi) if kisi > 1 else oz["toplam"]
        kat_label = {"ekonomik": "Ekonomik", "orta": "Orta", "luks": "Lüks"}.get(kat, kat)

        kisi_notu = f"\n- Kişi başı: {gk_pp:,.0f} TL/gece" if kisi > 1 else ""
        gy_kisi   = f"\n- Kişi başı: {gy_pp:,.0f} TL/gün"  if kisi > 1 else ""
        gu_kisi   = f"\n- Kişi başı: {gu_pp:,.0f} TL/gün"  if kisi > 1 else ""
        ga_kisi   = f"\n- Kişi başı: {ga_pp:,.0f} TL/gün"  if kisi > 1 else ""

        kahvalti  = round(gy * 0.20)
        ogle      = round(gy * 0.35)
        aksam     = round(gy * 0.45)
        metro_gun = round(gu * 0.40)
        taksi_gun = round(gu * 0.35)
        diger_gun = round(gu * 0.25)

        lines = [
            f"## {sehir} — Detaylı Maliyet Analizi\n",
            f"Haziran 2026 güncel fiyatları · {carpan:.1f}× şehir katsayısı · {kat_label} konsept\n",
            f"**{gun} Gün | {kisi} Kişi | Toplam: {oz['toplam']:,.0f} TL**"
            + (f" ({tot_pp:,.0f} TL/kişi)" if kisi > 1 else "") + "\n---\n",

            f"### Konaklama\n",
            f"- {gece} gece × {kisi} kişi = **{oz['konaklama']:,.0f} TL**\n",
            f"- Gecelik (tüm oda): {gk:,.0f} TL{kisi_notu}\n",
            f"- Bütçe sınıfı: {kat_label} otel ({gk_pp:,.0f} TL/kişi/gece)\n\n",

            f"### Yemek & İçecek\n",
            f"- {gun} gün × 3 öğün × {kisi} kişi = **{oz['yemek']:,.0f} TL**\n",
            f"- Günlük toplam: {gy:,.0f} TL{gy_kisi}\n",
            f"  · Kahvaltı: ~{kahvalti:,.0f} TL/gün\n",
            f"  · Öğle:    ~{ogle:,.0f} TL/gün\n",
            f"  · Akşam:   ~{aksam:,.0f} TL/gün\n\n",

            f"### Ulaşım\n",
            f"- Şehirlerarası (g/d): **{oz['sehirlerarasi']:,.0f} TL**\n",
            f"- Şehir içi {gun} gün: **{oz['sehir_ulasim']:,.0f} TL**\n",
            f"  · Günlük şehir içi: {gu:,.0f} TL{gu_kisi}\n",
            f"  · Metro/otobüs: ~{metro_gun:,.0f} TL/gün\n",
            f"  · Taksi/araç: ~{taksi_gun:,.0f} TL/gün\n",
            f"  · Diğer: ~{diger_gun:,.0f} TL/gün\n\n",

            f"### Aktiviteler & Girişler\n",
            f"- {gun} gün × {kisi} kişi = **{oz['aktivite']:,.0f} TL**\n",
            f"- Günlük aktivite: {ga:,.0f} TL{ga_kisi}\n",
        ]
        if yer_listesi:
            lines.append("- Planlanan mekanlar:\n")
            for y in yer_listesi:
                lines.append(f"  · {y}\n")
        else:
            lines.append(f"- ~{max(3, gun * 2)} ana keşif noktası öngörülmüştür\n")
        lines.append(f"\n### Özet Kalemler\n")
        for k, v in [("Konaklama", oz["konaklama"]), ("Yemek", oz["yemek"]),
                     ("Şehir İçi Ulaşım", oz["sehir_ulasim"]),
                     ("Aktivite", oz["aktivite"]), ("Şehirlerarası", oz["sehirlerarasi"])]:
            pct = round(v / oz["toplam"] * 100) if oz["toplam"] > 0 else 0
            lines.append(f"- {k}: {v:,.0f} TL (%{pct})\n")
        lines.append(f"\n**Genel Toplam: {oz['toplam']:,.0f} TL**\n")
        return "".join(lines)

    @staticmethod
    def _tablo(std, oz, tasarruf_tl, sehir, gun, kat, kisi) -> str:
        kat_tr = {"ekonomik": "Ekonomik", "orta": "Orta", "luks": "Lüks"}.get(kat, kat)
        kalemler = [
            ("Konaklama",        std["konaklama"],    oz["konaklama"]),
            ("Yemek",            std["yemek"],         oz["yemek"]),
            ("Şehir İçi Ulaşım", std["sehir_ulasim"],  oz["sehir_ulasim"]),
            ("Aktivite",         std["aktivite"],       oz["aktivite"]),
            ("Şehirlerarası",    std["sehirlerarasi"],  oz["sehirlerarasi"]),
        ]
        baslik = ('<div style="display:grid;grid-template-columns:2fr 1fr 1fr;'
                  'padding:8px 0;border-bottom:1px solid #e5e7eb;font-weight:600;font-size:13px;color:#6b7280">'
                  '<span>Kalem</span><span style="text-align:right">Standart</span>'
                  '<span style="text-align:right;color:#4f46e5">Kişisel</span></div>')
        rows = ""
        for label, sv, ov in kalemler:
            rows += (f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr;'
                     f'padding:7px 0;border-bottom:1px solid #f3f4f6;font-size:13px;color:#374151">'
                     f'<span>{label}</span>'
                     f'<span style="text-align:right;color:#9ca3af;text-decoration:line-through">{sv:,.0f} TL</span>'
                     f'<span style="text-align:right;font-weight:500">{ov:,.0f} TL</span></div>')
        total_row = (f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr;'
                     f'padding:10px 0;font-weight:700;font-size:14px;border-top:2px solid #e5e7eb">'
                     f'<span>Toplam</span>'
                     f'<span style="text-align:right;color:#9ca3af;text-decoration:line-through">{std["toplam"]:,.0f} TL</span>'
                     f'<span style="text-align:right;color:#059669">{oz["toplam"]:,.0f} TL</span></div>')
        savings = (f'<div style="margin-top:10px;font-size:12px;font-weight:600;color:#059669;'
                   f'text-align:center;padding:7px 12px;background:#f0fdf4;border-radius:8px">'
                   f'Seçimleriniz sayesinde {tasarruf_tl:,.0f} TL tasarruf sağlandı.</div>')
        return (f'<div style="font-family:sans-serif;border:1px solid #e5e7eb;border-radius:12px;'
                f'padding:20px;max-width:500px;background:#fff">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px">'
                f'<span style="font-size:15px;font-weight:700;color:#111827">Bütçe Özeti</span>'
                f'<span style="font-size:11px;color:#9ca3af">{gun} Gün · {kisi} Kişi · {kat_tr}</span></div>'
                f'<div style="font-size:11px;color:#9ca3af;margin-bottom:14px">{sehir} · Haziran 2026</div>'
                f'{baslik}{rows}{total_row}{savings}</div>')


# ---------------------------------------------------------------------------
# PLAN AJAN
# ---------------------------------------------------------------------------

def _sehir_fotograflari(sehir: str, adet: int = 6) -> list:
    """Wikimedia Commons API ile şehre ait fotoğrafları indirir,
    base64 data URI listesi döndürür — Streamlit'te her zaman görünür."""
    try:
        import requests as _req
        api = "https://en.wikipedia.org/w/api.php"
        # 1. Dosya adlarını al
        r = _req.get(api, params={
            "action": "query", "titles": sehir, "prop": "images",
            "imlimit": 30, "format": "json",
        }, timeout=5)
        dosyalar = []
        for page in r.json().get("query", {}).get("pages", {}).values():
            for img in page.get("images", []):
                t = img.get("title", "")
                if (t.lower().endswith((".jpg", ".jpeg", ".png"))
                        and not any(x in t.lower() for x in
                            ("flag", "coat", "logo", "icon", "map", "seal", "blank", "locator"))):
                    dosyalar.append(t)
        if not dosyalar:
            return []
        random.shuffle(dosyalar)
        dosyalar = dosyalar[:adet * 2]
        # 2. Thumb URL'lerini al
        r2 = _req.get(api, params={
            "action": "query", "titles": "|".join(dosyalar),
            "prop": "imageinfo", "iiprop": "url",
            "iiurlwidth": 900, "format": "json",
        }, timeout=5)
        foto_urls = []
        for page in r2.json().get("query", {}).get("pages", {}).values():
            info = page.get("imageinfo", [{}])
            url  = info[0].get("thumburl") or info[0].get("url", "")
            if url and url.startswith("http"):
                foto_urls.append(url)
            if len(foto_urls) >= adet:
                break
        # 3. Görselleri indir → base64 data URI (Streamlit'te external URL çalışmaz)
        data_uris = []
        for url in foto_urls:
            try:
                ir = _req.get(url, timeout=6)
                if ir.status_code == 200:
                    ct  = ir.headers.get("Content-Type", "image/jpeg").split(";")[0]
                    b64 = base64.b64encode(ir.content).decode()
                    data_uris.append(f"data:{ct};base64,{b64}")
            except Exception:
                continue
            if len(data_uris) >= adet:
                break
        return data_uris
    except Exception:
        return []


class PlanAgent:
    def create_plan(self, travel_data: dict, aco_result: dict,
                    ulasim_result: dict, restaurant_schedule=None,
                    maliyet_result=None) -> dict:
        destination = travel_data.get("destination", "İstanbul")
        try:
            start = datetime.strptime(travel_data["start_date"], "%Y-%m-%d")
            end = datetime.strptime(travel_data["end_date"], "%Y-%m-%d")
            duration_days = max(1, (end - start).days + 1)
        except Exception:
            duration_days = int(travel_data.get("duration_days", 3))

        cost = maliyet_result.get("ozel_plan", {}).get("toplam", 0) if maliyet_result else 0
        transport_details = ulasim_result.get("ai_suggestions", "") if ulasim_result else ""

        html_report = self._generate_html_report(
            travel_data, aco_result, ulasim_result,
            restaurant_schedule, maliyet_result, duration_days
        )

        return {
            "destination": destination,
            "duration_days": duration_days,
            "estimated_cost": cost,
            "transport_details": transport_details,
            "html_report": html_report,
            "plan_metni": html_report,
        }

    def _generate_html_report(self, travel_data, aco_result, ulasim_result,
                               restaurant_schedule, maliyet_result, duration_days) -> str:
        return self._static_html_report(travel_data, aco_result, ulasim_result,
                                         restaurant_schedule, maliyet_result, duration_days)

    # Şehre özgü aktivite havuzu — AI yokken anlamlı öneriler üret
    _SEHIR_AKTIVITE = {
        "istanbul":  {"sabah":["Topkapı Sarayı gezisi","Kapalıçarşı turu","Boğaz kahvaltısı"],
                      "ogle":  ["Beyoğlu & İstiklal Caddesi","Arasta Bazaar","Balık-ekmek keyfi"],
                      "aksam": ["Galata Kulesi manzarası","Boğaz teknesi turu","Karaköy mezeleri"]},
        "paris":     {"sabah":["Eyfel Kulesi","Louvre Müzesi","Montmartre yürüyüşü"],
                      "ogle":  ["Seine kıyısı piknik","Marais mahallesi","Boulangerie kahvaltısı"],
                      "aksam": ["Champs-Élysées gezisi","Seine akşam turu","Bistro yemeği"]},
        "roma":      {"sabah":["Kolezyum & Forum Romanum","Vatikan Müzeleri","Pantheon ziyareti"],
                      "ogle":  ["Trastevere mahallesi","Campo de' Fiori pazarı","Aperitivo keyfi"],
                      "aksam": ["Trevi Çeşmesi","Piazza Navona","Trattoria yemeği"]},
        "barcelona": {"sabah":["Sagrada Familia","Park Güell","Barri Gòtic gezisi"],
                      "ogle":  ["La Boqueria pazarı","El Born mahallesi","Tapas turu"],
                      "aksam": ["Barceloneta plajı","Gece hayatı & flamenco","Seafood restoranı"]},
        "tokyo":     {"sabah":["Senso-ji Tapınağı","Tsukiji Balık Pazarı","Shibuya Kavşağı"],
                      "ogle":  ["Harajuku & Takeshita Caddesi","Akihabara elektroniği","Ramen turu"],
                      "aksam": ["Shinjuku gece hayatı","Sumida nehri yürüyüşü","Izakaya yemeği"]},
        "bali":      {"sabah":["Tanah Lot tapınağı","Tegallalang pirinç tarlaları","Ubud maymun ormanı"],
                      "ogle":  ["Kecak dans gösterisi","yerel warung öğle","Seminyak plajı"],
                      "aksam": ["günbatımı seyreder","Jimbaran sahil yemeği","Spa & masaj"]},
        "marakes":   {"sabah":["Djemaa el-Fna meydanı","Medina labirenti","Bahçe ziyareti"],
                      "ogle":  ["Yerel tagine yemeği","El sanatları çarşısı","Hammam deneyimi"],
                      "aksam": ["Hikaye anlatıcıları & müzik","Riyad yemeği","Teras keyfi"]},
    }
    _GENEL_AKTIVITE = {
        "sabah": ["Tarihi merkez & eski şehir turu","Sabah pazarı & yerel kahvaltı",
                  "Müze & kültürel mekân ziyareti","Şehrin simge yapısı","Yerel park & bahçe yürüyüşü"],
        "ogle":  ["Yerel restorantta öğle yemeği","Butik dükkânlar & çarşı","Kafe molası & şehir gözlemi",
                  "Tarihi mahalle keşfi","Açık hava pazarı"],
        "aksam": ["Şehrin en iyi manzara noktası","Yerel mutfak restoranı","Gece pazarı & sokak yemeği",
                  "Kültürel gösteri ya da konser","Nehir / sahil yürüyüşü"],
    }
    _IPUCU = {
        "ekonomik": ["Şehir ulaşım kartı alın — günlük geçiş çok daha ucuz.",
                     "Öğle yemeklerini lokal esnafın gittiği küçük restoranlarda yiyin.",
                     "Müzelerin ücretsiz günlerini önceden araştırın."],
        "orta":     ["Günlük tur yerine uygulamalardan sesli rehber indirin.",
                     "Airbnb'de ev sahibi önerileri en iyi yerel ipuçlarıdır.",
                     "Para bozdururken döviz bürosu yerine ATM tercih edin."],
        "luks":     ["Oteldeki concierge servisi rezervasyon konusunda son derece yardımcıdır.",
                     "Michelin restoranlarında öğle menüsü akşama göre çok daha hesaplıdır.",
                     "Özel rehber tutmak zaman kaybını minimuma indirir."],
    }

    def _static_html_report(self, travel_data, aco_result, ulasim_result,
                              restaurant_schedule, maliyet_result, duration_days) -> str:
        destination  = travel_data.get("destination", "İstanbul")
        mbti         = travel_data.get("mbti_type", "ENFP")
        kat          = travel_data.get("butce_kategorisi", "orta")
        kisi         = int(travel_data.get("group_size", 1))
        bas          = travel_data.get("start_date", "")
        bit          = travel_data.get("end_date", "")
        ulasim_tr    = travel_data.get("transport", "Uçak")

        route   = aco_result.get("optimized_route", []) if aco_result else []
        mesafe  = aco_result.get("tahmini_toplam_mesafe_km", 0) if aco_result else 0
        skor    = aco_result.get("rota_uyumluluk_skoru", 85) if aco_result else 85

        mal      = maliyet_result or {}
        oz       = mal.get("ozel_plan", {})
        toplam   = oz.get("toplam", 0)
        konak    = oz.get("konaklama", 0)
        yemek_m  = oz.get("yemek", 0)
        cost_html      = mal.get("butce_ozeti", "")
        transport_html = ulasim_result.get("ai_suggestions", "") if ulasim_result else ""

        # Fotoğrafları base64 data URI olarak çek — kota hatası olsa bile en az 0 döner
        fotograflar = _sehir_fotograflari(destination, 8)

        kat_label = {"ekonomik": "Ekonomik", "orta": "Orta", "luks": "Lüks"}.get(kat, kat.capitalize())

        # ── CSS — kırık nude palette ──────────────────────────────────────────
        css = """<style>
.plan-wrap { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             max-width: 780px; margin: 0 auto; background: #faf8f5; padding: 4px; }
.gun-baslik { font-size: 14px; font-weight: 700; color: #2c2416;
              padding: 22px 0 8px; margin-top: 20px;
              border-bottom: 2px solid #c4b5a0; letter-spacing: 0.1px; }
.aktivite-kart { display: flex; margin: 14px 0; border-radius: 14px; overflow: hidden;
                 box-shadow: 0 1px 6px rgba(44,36,22,0.08);
                 background: #fffefb; border: 1px solid #e8dfd4; }
.aktivite-kart[data-type="yemek"]     { border-left: 4px solid #d4976a; }
.aktivite-kart[data-type="gezi"]      { border-left: 4px solid #8b7355; }
.aktivite-kart[data-type="konaklama"] { border-left: 4px solid #9eaa8f; }
.aktivite-kart[data-type="genel"]     { border-left: 4px solid #b5a99a; }
.saat-col { min-width: 78px; max-width: 78px; display: flex; flex-direction: column;
            align-items: center; justify-content: flex-start;
            padding: 18px 8px; background: #f2ede6; border-right: 1px solid #e8dfd4; }
.saat-txt { font-size: 13px; font-weight: 800; color: #2c2416;
            letter-spacing: -0.5px; line-height: 1; }
.saat-etiket { font-size: 10px; font-weight: 700; margin-top: 6px;
               text-transform: uppercase; letter-spacing: 0.4px;
               padding: 2px 6px; border-radius: 20px;
               color: #7a6a5a; background: #e8dfd4; white-space: nowrap; }
.icerik-col { flex: 1; padding: 16px 20px; }
.mekan-adi { font-size: 13px; font-weight: 700; color: #2c2416;
             margin: 0 0 8px; display: flex; align-items: center;
             gap: 10px; flex-wrap: wrap; line-height: 1.3; }
.harita-btn { font-size: 11px; font-weight: 700; color: #fff;
              background: #8b7355; padding: 4px 12px; border-radius: 20px;
              text-decoration: none; border: none; white-space: nowrap;
              display: inline-flex; align-items: center; gap: 4px;
              cursor: pointer; transition: background 0.18s; }
.harita-btn:hover { background: #6b5840; }
.blog-metin { font-size: 13px; color: #4a3f35; line-height: 1.78; margin: 0 0 10px; }
.ulasim-notu { font-size: 12px; color: #7a6a5a; background: #f2ede6;
               border: 1px solid #e8dfd4; border-radius: 8px;
               padding: 5px 12px; margin-top: 6px; display: inline-block; }
.foto-karti { margin: 16px 0; border-radius: 12px; overflow: hidden;
              box-shadow: 0 2px 12px rgba(44,36,22,0.12); line-height: 0; }
.foto-karti img { width: 100%; max-height: 240px; object-fit: cover; display: block; }
.stat-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 20px 0; }
.stat-kart { border-radius: 12px; padding: 14px 12px; text-align: center; }
.gun-ayirici { height: 1px; background: #e0d4c4; margin: 28px 0 6px; }
.giris-karti { background: #f2ede6; border: 1px solid #e0d4c4; border-radius: 12px;
               padding: 16px 20px; margin-bottom: 20px;
               font-size: 13px; color: #4a3f35; line-height: 1.8; }
</style>"""

        # ── Header — sıcak kahverengi ─────────────────────────────────────────
        header = (
            f'<div style="background:linear-gradient(135deg,#2d221a 0%,#5a3e2d 100%);'
            f'color:white;padding:32px 30px;border-radius:16px;margin-bottom:24px">'
            f'<div style="font-size:11px;opacity:.6;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:8px">Seyahat Planı</div>'
            f'<h1 style="margin:0 0 6px;font-size:26px;font-weight:800;letter-spacing:-.5px">'
            f'✈️ {destination}</h1>'
            f'<p style="margin:0;opacity:.82;font-size:13px">'
            f'{bas} – {bit} &nbsp;·&nbsp; {duration_days} Gün &nbsp;·&nbsp; '
            f'{kisi} Kişi &nbsp;·&nbsp; {kat_label} &nbsp;·&nbsp; {ulasim_tr} &nbsp;·&nbsp; MBTI: {mbti}</p>'
            f'</div>'
        )

        # ── İstatistik kartları — nude tonlar ─────────────────────────────────
        def stat_card(bg, icon, val, label):
            return (f'<div class="stat-kart" style="background:{bg}">'
                    f'<div style="font-size:22px">{icon}</div>'
                    f'<div style="font-weight:800;font-size:17px;color:#2c2416;margin:4px 0 2px">{val}</div>'
                    f'<div style="font-size:11px;color:#7a6a5a">{label}</div></div>')

        stats = (
            '<div class="stat-grid">'
            + stat_card("#f2ede6", "📍", len(route), "Lokasyon")
            + stat_card("#eef0eb", "🗺️", f"{mesafe} km", "Mesafe")
            + stat_card("#f5ede6", "⭐", f"{skor}/100", "ACO Skoru")
            + stat_card("#ede8e0", "💰", f"{toplam:,.0f} TL" if toplam else kat_label, "Bütçe")
            + '</div>'
        )

        # ── MBTI giriş metni ──────────────────────────────────────────────────
        MBTI_GIRIS = {
            "INTJ": f"{destination} sizin için yalnızca bir destinasyon değil; her dakikası bir amaca hizmet eden, önceden planlanmış bir zihinsel prova alanıdır. Kalabalıklardan uzak, derin tarihin izlerini sürdüğünüz bu rotayı adım adım keşfedeceksiniz.",
            "INTP": f"{destination}'nin sokakları sizin için çözülmesi gereken bir bulmacadır. Her köşe taşı, her tarihi iz bir hipotez sunar. Bu plan sizi en az zaman kaybıyla en çok fikir uyandıracak noktalara götürecek.",
            "ENFP": f"{destination} rotası spontane ruhunuza göre şekillendirildi. Planlı gibi görünen her adım aslında sizi bir sonraki beklenmedik keşfe hazırlıyor. Sokak müzisyenleri, renkli pazarlar ve tanımadığınız yüzler sizi bekliyor.",
            "ESTJ": f"{destination} programı dakik ve verimli bir şekilde tasarlandı. Her saat bloğu bir hedefe odaklanıyor, hiçbir dakika boşa gitmiyor. Sizi şehrin en değerli noktalarından en kısa yollarla geçirecek.",
            "INFJ": f"{destination}'nin ruhu, turist kalabalıklarının ardında saklı. Bu plan sizi yüzeyin altına, şehrin gerçek kalbine götürecek. Her mekânda derin bir anlam, her restoranın arkasında bir hikâye var.",
            "ISFP": f"{destination}, her köşesi bir fotoğraf karesine dönüşen, renk ve dokuyla dolu bir şehirdir. Bu rotada durup hissetmek, acele etmekten çok daha değerli. Güzel anları yakalamak için kendinize zaman verin.",
            "ENTP": f"{destination}'de her şey tartışılmaya değer: tarihi katmanlar, mimari çelişkiler, kültürel paradokslar. Bu plan sizi hem rahat hem de zihinsel olarak uyarılmış tutacak şekilde tasarlandı.",
        }
        giris = MBTI_GIRIS.get(mbti,
            f"{destination} rotası, {mbti} gezgin profilinize özel olarak hazırlandı. "
            f"Şehrin karakteriyle sizin karakteriniz bu planda buluşuyor.")
        giris_html = f'<div class="giris-karti">{giris}</div>\n'

        # ── Lokasyon listesi normalize et ─────────────────────────────────────
        locs = []
        for r in route:
            locs.append(r.get("name", str(r)) if isinstance(r, dict) else str(r))

        try:
            start_dt = datetime.strptime(bas, "%Y-%m-%d")
        except Exception:
            start_dt = None

        # ── Aktivite zenginleştirici metinler ─────────────────────────────────
        _MBTI_GEZI = {
            "INTJ": "Mekânın yapısal mantığını sorgulayarak gezmek size en büyük tatmini sağlayacak. Mimari kararların arkasındaki stratejiyi düşünün.",
            "INTP": "Buradaki her detay ayrı bir hipotez. Rehber anlatısının ötesine geçip kendi bağlantılarınızı kurun.",
            "ENTJ": "Bu mekânın şehir ekonomisine ve prestijine katkısı değerlendirmeye değer. Büyük resmi görmeye çalışın.",
            "ENTP": "Burayı hem tarihi hem de çağdaş yorumlamayla sorgulamak sizi düşünürken eğlendirecek.",
            "INFJ": "Bu durakta gözlemlemek, fotoğraf çekmekten daha değerli. İnsanları ve mekânın enerjisini hissedin.",
            "INFP": "Buranın size anlattığı hikâye ne? Bir köşe bulun, oturun, hissettiklerinizi kaydedin.",
            "ENFJ": "Rehber veya yerel biriyle konuşmak bu mekânı çok daha zengin kılacak. Bağlantı kurun.",
            "ENFP": "Beklentisiz girin, içgüdülerinize güvenin — en güzel anlar planlanmayan anlardır.",
            "ISTJ": "Mekânı metodolojik keşfedin. Girişten çıkışa doğrusal ilerlemek içeriği anlamanızı kolaylaştırır.",
            "ISFJ": "Sessizce ve dikkatle gözlemlemek en büyük keyfiniz. Kalabalık olmayan bir köşeye odaklanın.",
            "ESTJ": "Zamanınızı iyi yönetin; giriş, ana bölüm, çıkış sıralaması en verimli keşfi sağlar.",
            "ESFJ": "Grup ya da yerel rehber eşliğinde gezmek bu mekânı sosyal bir deneyime dönüştürür.",
            "ISTP": "Teknik detaylar sizi cezbedecek. Yapının nasıl inşa edildiğini düşünmek farklı bir perspektif sunar.",
            "ISFP": "Fotoğraf makinenizi hazırlayın — her açıdan farklı bir doku, farklı bir ışık var burada.",
            "ESTP": "Uzun duraksama yerine hızlı tur, ardından dışarıda kahve. Bu sizin ritminiz.",
            "ESFP": "Selfie yerine canlı bir video kaydı burayı sosyal medyada çok daha iyi anlatır.",
        }
        _MBTI_YEMEK = {
            "INTJ": "Sipariş öncesi menüye bakın; menü tasarımı restoran felsefesi hakkında çok şey söyler.",
            "INTP": "Alışılmadık bir seçenek deneyin. Bu tip mekânlarda gizli kalmış kombinasyonlar olabilir.",
            "ENTJ": "Şef önerisi veya günün spesiyali — en iyi kalite/verimlilik dengesini bulmak için.",
            "ENTP": "Garsonla sohbet edin, 'en beklenmedik tabak ne?' diye sorun. Tartışmayı seviyorsunuz.",
            "INFJ": "Sakin bir masa seçin. Yemek deneyimi sadece lezzet değil; atmosfer ve sessizliktir.",
            "INFP": "Yerel ve özgün bir tat arayın. Kitle üretimi değil, el yapımı, hikâyeli bir yemek.",
            "ENFJ": "Arkadaş gibi hizmet eden bir garsonla tanışmak bu yemeği anıya dönüştürecek.",
            "ENFP": "Paylaşımlı tabaklar sipariş edin; çeşitlilik sizin için tek çeşitten çok daha tatmin edicidir.",
            "ISTJ": "Tarifine sadık, doğru pişirilmiş klasik yemekler sizin için en güvenilir seçimdir.",
            "ISFJ": "Sıcak, ev yapımı tatları arayın. Anı hatırlatacak bir lezzet bu öğünü özel kılar.",
            "ESTJ": "Bekleme süresini ve servisi değerlendirin; organizasyon kaliteyi yansıtır.",
            "ESFJ": "Masadaki herkesi düşünerek sipariş verin; ortak beğeni bir mekânı onu ziyaret eden herkes için özel kılar.",
            "ISTP": "Alerjen veya içerik sorun; bileşenleri bilmek seçiminizi daha bilinçli yapar.",
            "ISFP": "Yemeği fotoğraflamadan önce kokusunu alın ve sunum estetini fark edin.",
            "ESTP": "Hızlı karar verin, yan tarafa da bakın. Sonraki durağa yetiştirmeniz gerekiyor.",
            "ESFP": "En renkli, en instagramlık tabağı seçmekten çekinmeyin — zevkinizi yaşayın.",
        }
        _mbti_gezi_hint = _MBTI_GEZI.get(mbti, "Mekânı kendi temponuzda, kendi gözlemlerinizle keşfedin.")
        _mbti_yemek_hint = _MBTI_YEMEK.get(mbti, "Yerel lezzetlere açık olun ve sipariş vermeden önce menüye göz atın.")

        # ── Şehre özgü kapsamlı bilgi ─────────────────────────────────────────
        _SEHIR_BILGI = {
            "barcelona": {
                "ulke": "İspanya", "para": "Euro (€)", "dil": "Katalanca / İspanyolca",
                "transit_kart": "T-Casual kartı (10 biniş ~12€, her binişte sarfa gerek yok)",
                "metro": "L1 Kırmızı, L2 Mor, L3 Yeşil, L4 Sarı, L5 Mavi",
                "ortalama_binis": "Metro durağı 2–3 dk; ortalama güzergah 3–6 durak ≈ 10–18 dk.",
                "yemek_kultur": "Pintxos ve tapas küçük porsiyonlar hâlinde paylaşımlı yenir; öğle 14:00, akşam 21:00'den sonra yoğunlaşır.",
                "tarih": "1992 Olimpiyat şehri; Roma, Vizigot ve Mağrip katmanları üzerine inşa edilmiş Katalonya başkenti.",
                "ipucu": "Las Ramblas'ta dikkatli olun, turistik bölgelerde cep hırsızlığı yaygındır. Boqueria Pazarı sabah 9–11 arası kalabalık değildir.",
            },
            "istanbul": {
                "ulke": "Türkiye", "para": "Türk Lirası (₺)", "dil": "Türkçe",
                "transit_kart": "İstanbulkart (dolum ~100 ₺, biniş ~10 ₺; aktarmalarda indirim)",
                "metro": "M1–M9 arası metro hatları; T1 Tramvay (Sultanahmet–Zeytinburnu); F1 Füniküler",
                "ortalama_binis": "Metro durağı 2–3 dk; Sultanahmet–Taksim arası T1+Füniküler ≈ 25 dk.",
                "yemek_kultur": "Sabah kahvaltısı Türk kültürünün merkezinde; peynir, zeytin, reçel. Akşam meze kültürü (meyhane).",
                "tarih": "3000+ yıllık Konstantinopolis–Bizans–Osmanlı katmanları; Asya ve Avrupa kıtalarının buluşma noktası.",
                "ipucu": "Kapalıçarşı ve Mısır Çarşısı sabah 8:30'da açılır, kalabalıktan önce girmenizi öneririz. İstanbulkart metrobüste de geçerli.",
            },
            "roma": {
                "ulke": "İtalya", "para": "Euro (€)", "dil": "İtalyanca",
                "transit_kart": "48 saatlik BIT kartı (bilet ~2.50€/tek yön, günlük kart ~7€)",
                "metro": "Metro A (Spagna, Barberini) ve Metro B (Colosseo durağı); gece taksi tavsiye edilir.",
                "ortalama_binis": "Metro durağı 2 dk; Termini'den Spagna'ya Metro A ≈ 10 dk.",
                "yemek_kultur": "Carbonara, cacio e pepe ve supplì (kızarmış pirinç topu) Roma'ya özeldir. 13:00–15:00 pranzo (öğle) kapanışı olan restoranlar var.",
                "tarih": "M.Ö. 753'ten bu yana yerleşim; Cumhuriyet, İmparatorluk ve Papalık katmanları her adımda görülür.",
                "ipucu": "Fontanalarda ücretsiz içme suyu (nasoni) var; şişe almak zorunda değilsiniz. Vatikan için online rezervasyon şart.",
            },
            "paris": {
                "ulke": "Fransa", "para": "Euro (€)", "dil": "Fransızca",
                "transit_kart": "Navigo Hebdomadaire (haftalık ~30€) veya carnet (10 bilet ~17€)",
                "metro": "14 metro hattı; RER A–E bölgeler arası; her hat 2–5 dk arayla çalışır.",
                "ortalama_binis": "Metro durağı 1.5–2 dk; Châtelet'ten Champs-Élysées ≈ 8 dk Metro 1.",
                "yemek_kultur": "Kahvaltı croissant+café, öğle brasserie, akşam bistro; servis saatleri katı (19:00–22:00).",
                "tarih": "Lutetia'dan Aydınlanma'ya, Napolyon'dan Belle Époque'a uzanan katmanlar; müzeler günceli geçmiş yapar.",
                "ipucu": "Musée d'Orsay Perşembe 21:45'e kadar açık — kuyruğu sabah 09:00'da veya akşam üstü atlatabilirsiniz.",
            },
            "tokyo": {
                "ulke": "Japonya", "para": "Yen (¥)", "dil": "Japonca",
                "transit_kart": "IC Cart (Suica/Pasmo, 2000¥ — 500¥ depozit); tüm metro ve shinkansen'de geçerli.",
                "metro": "13 Tokyo Metro + 4 Toei hattı; JR Yamanote halkası şehri çepeçevre dolaşır.",
                "ortalama_binis": "Metro durağı 1.5–2 dk; Shinjuku–Shibuya JR ≈ 5 dk.",
                "yemek_kultur": "Ramen, sushi, yakitori ve tempura; konbini (7-Eleven, Lawson) her saat açık ve yüksek kaliteli.",
                "tarih": "Edo döneminden (1603) bu yana 40 milyonluk metropolitan; deprem-dayanıklı mimari katmanlar.",
                "ipucu": "IC kart olmadan bilet almak zor; havalimanında Suica alın. Sessizlik trenlerde kural; telefon konuşması yapılmaz.",
            },
            "amsterdam": {
                "ulke": "Hollanda", "para": "Euro (€)", "dil": "Hollandaca",
                "transit_kart": "OV-chipkaart (4€ + yükleme) veya 24/48/72 saatlik GVB kartı (~8/14/20€)",
                "metro": "Metro 50/51/52/53/54; Tram 1–26 arası; çoğu yer bisikletle de ulaşılabilir.",
                "ortalama_binis": "Tramvay durağı 2 dk; Centraal Station–Rijksmuseum Tram 2 ≈ 12 dk.",
                "yemek_kultur": "Stamppot (ezilmiş patates+lahana), haring (çiğ ringa) ve stroopwafel yerel lezzetler.",
                "tarih": "17. yy Hollanda Altın Çağı'nın kanal şehri; dünya ticaretinin merkezi VOC döneminde buradaydı.",
                "ipucu": "Bisiklet yolları bisikletlilere ait — yürürken dikkat edin. Anne Frank Müzesi için 2–3 hafta önceden rezervasyon şart.",
            },
        }
        _dest_key2 = destination.lower().replace("ş","s").replace("ı","i").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
        _sb = next((v for k,v in _SEHIR_BILGI.items() if k in _dest_key2 or _dest_key2.startswith(k)), {})
        _transit_kart = _sb.get("transit_kart", f"{destination} toplu taşıma kartı")
        _metro_bilgi  = _sb.get("metro", "Metro ve otobüs ağı")
        _ort_binis    = _sb.get("ortalama_binis", "Metro durağı ~2 dk; ortalama güzergah 10–20 dk.")
        _yemek_kultur = _sb.get("yemek_kultur", f"{destination} mutfağı yerel malzeme ve geleneksel tariflerle öne çıkar.")
        _tarih_bilgi  = _sb.get("tarih", f"{destination} zengin tarihi ve kültürel mirasa sahip bir şehirdir.")
        _sehir_ipucu  = _sb.get("ipucu", "Toplu taşıma kullanırken günlük kart almanız tasarruf sağlar.")

        def _enrich(act_name: str, act_type: str) -> str:
            _ai_txt = ai_enrich_map.get(act_name, "") if act_type in ("yemek", "gezi") else ""
            if _ai_txt:
                _hint = _mbti_yemek_hint if act_type == "yemek" else _mbti_gezi_hint
                return f"{_ai_txt}<br><br><i style='color:#8b7355'>{_hint}</i>"
            if act_type == "yemek":
                _clean = act_name.replace("&amp;","&")
                if " — " in _clean:
                    _mekan = _clean.split(" — ",1)[1].strip()
                    _ogun  = _clean.split(" — ",1)[0].strip()
                else:
                    _mekan = _clean; _ogun = ""
                _ogun_tr = {"Kahvaltı": "sabah", "Öğle": "öğle", "Akşam Yemeği": "akşam"}.get(_ogun, "")
                _para_birimi = _sb.get("para", "TL")
                return (
                    f"<b>{_mekan}</b>, {destination}'nin {_ogun_tr} saatlerinde tercih edilen köklü "
                    f"mekânlarından biri olarak öne çıkıyor. Bulunduğu mahallede yıllardır süregelen "
                    f"bir lezzet geleneğini sürdüren bu yer, hem yerel müdavimlerini hem de "
                    f"seyahatseverleri bir araya getiriyor. "
                    f"<br><br>"
                    f"Menüde öne çıkan seçenekler arasında bölgeye has fermantasyon ve pişirme teknikleriyle "
                    f"hazırlanmış tabaklar yer alıyor. {_yemek_kultur} Sipariş verirken garsonun günün "
                    f"önerisini sormanız genellikle en taze ve en yerel lezzeti almanızı sağlar. "
                    f"Ortalama kişi başı fiyat: {_para_birimi} cinsinden orta sınıf; "
                    f"ödeme genellikle nakit veya kart kabul edilir. "
                    f"<br><br>"
                    f"<b>Pratik Bilgi:</b> Yoğun saatlerde (12:30–14:00 ve 19:30–21:30) bekleme süresi "
                    f"15–25 dakikaya çıkabilir; rezervasyon yapmanız önerilir. "
                    f"Mekânın yakınındaki yan sokaklarda daha sakin alternatifler de bulunabilir. "
                    f"<i style='color:#8b7355'>{_mbti_yemek_hint}</i>"
                )
            elif act_type == "gezi":
                return (
                    f"<b>{act_name}</b>, {destination}'nin sadece bir turistik noktası değil; "
                    f"şehrin kimliğini, tarihini ve kültürel özünü barındıran bir deneyim alanıdır. "
                    f"{_tarih_bilgi} "
                    f"Bu mekân, söz konusu tarihin en görünür ve en erişilebilir katmanlarından birini "
                    f"sunuyor. "
                    f"<br><br>"
                    f"İçeride veya çevresinde dikkat etmeniz gereken detaylar: mimari öğelerin ölçeği "
                    f"ve simetri anlayışı, kullanılan taş ve yapı malzemeleri, farklı dönemlere ait "
                    f"eklentiler ve restorasyonlar. Kalabalık saatleri (10:00–14:00) atlatmak için "
                    f"sabahın erken saatlerinde ya da öğleden sonra 16:00 civarında ziyaret "
                    f"planlamanız fark yaratır. "
                    f"<br><br>"
                    f"<b>Pratik Bilgi:</b> Giriş bileti önceden çevrimiçi alınmalı — kapıda fiyat "
                    f"genellikle %15–20 daha yüksektir ve ciddi kuyruklar oluşabilir. Fotoğraf için "
                    f"en iyi ışık sabah 09:00–10:30 arası veya altın saat 17:30–19:00'dur. "
                    f"Mekânda en az 75–90 dakika geçirmeniz önerilir; yüzeysel bir tur 30–45 dakikada "
                    f"biter ama derinlemesine keşif için zaman ayırın. "
                    f"Özel konuşmacı veya rehberli tur çoğu zaman mekânın gizli katmanlarını açar. "
                    f"<br><br>"
                    f"{_sehir_ipucu} "
                    f"<i style='color:#8b7355'>{_mbti_gezi_hint}</i>"
                )
            elif act_type == "konaklama":
                return (
                    f"Bugünkü yoğun programın ardından konaklamanıza geri dönme zamanı. "
                    f"Bavulunuzu bırakın, odanızı keşfedin — varsa balkon ya da pencereden "
                    f"{destination}'nin siluetini izleyin. Bu kısa mola, vücudunuzun günün "
                    f"temposuna uyum sağlaması için oldukça kıymetlidir. "
                    f"<br><br>"
                    f"<b>Check-in &amp; Pratik Bilgi:</b> Standart check-in saati 14:00–15:00'tir. "
                    f"Erken varışta oteli önceden bilgilendirirseniz bagaj depolama imkânı sunulur "
                    f"ve oda hazır olduğunda size haber verilir. "
                    f"Odaya yerleştikten sonra Wi-Fi şifresini not alın, klima ve kasa ayarlarını "
                    f"kontrol edin ve sabah için kahvaltı saatini teyit edin. "
                    f"<br><br>"
                    f"{_sehir_ipucu} "
                    f"Konakladığınız bölgeden çevresine kısa bir yürüyüş yaparak mahalle dokusunu "
                    f"keşfetmek, sabaha programlanmış yerlerin kafanızda daha net yerleşmesini sağlar."
                )
            else:
                return (
                    f"<b>{act_name}</b>, {destination} rotanızın önemli bir durağı olarak "
                    f"günün temposunu dengeleyen bir bağlantı noktasıdır. "
                    f"Çevresindeki sokaklar, bağımsız butik dükkanlar ve ara kafeler kısa bir "
                    f"yürüyüşle keşfedilebilir; şehrin gerçek dokusunu yakalamak için "
                    f"büyük turistik caddelerden ziyade yan yolları tercih edin. "
                    f"<br><br>"
                    f"Yerel halkla küçük sohbetler kurmak — kasiyerle, fırıncıyla ya da park bankında "
                    f"oturan biriyle — seyahat kitaplarında bulunmayan bilgilerin kapısını açar. "
                    f"{_tarih_bilgi} "
                    f"Bu bağlam gözlerinizi açık tutmanızı kolaylaştırır. "
                    f"<br><br>"
                    f"<b>Pratik Bilgi:</b> {_ort_binis} "
                    f"{_sehir_ipucu} "
                    f"<i style='color:#8b7355'>{_mbti_gezi_hint}</i>"
                )

        # ── Şehre özgü aktivite havuzu ────────────────────────────────────────
        dest_key = (destination.lower()
                    .replace("ş","s").replace("ı","i").replace("ğ","g")
                    .replace("ü","u").replace("ö","o").replace("ç","c"))
        akt = None
        for k, v in self._SEHIR_AKTIVITE.items():
            if k in dest_key:
                akt = v
                break
        g = self._GENEL_AKTIVITE

        # ── Transit yönlendirmeler: Gemini ile şehre özgü ────────────────────
        _ulasim_modu   = (ulasim_tr or "").lower()
        _ULASIM_IPUCU  = {
            "ucak":  "Havalimanından merkeze: taksi (~30 dk), havalimanı otobüsü veya metro (~40–60 dk).",
            "tren":  "Tren garından: metro veya tramvay ile 10–20 dk içinde otel bölgesine ulaşabilirsiniz.",
            "otobus":"Otobüs terminalinden merkeze: dolmuş/metro ile genellikle 20–30 dakika.",
            "arac":  "Kiralık araçla esneklik yüksektir; merkezdeki otopark ücretlerine (günlük 5–25€) dikkat edin.",
        }
        _sabah_ulasim  = next((v for k,v in _ULASIM_IPUCU.items() if k in _ulasim_modu),
                              "Şehir içi toplu taşımada günlük kart almanız tasarruf sağlar.")

        # Tüm gün-mekan çiftlerini topla
        _all_pairs = []
        _enrich_targets = []
        for _d in range(duration_days):
            _s  = akt["sabah"][_d % len(akt["sabah"])] if akt else g["sabah"][_d % len(g["sabah"])]
            _o  = akt["ogle"][_d % len(akt["ogle"])]   if akt else g["ogle"][_d % len(g["ogle"])]
            _a  = akt["aksam"][_d % len(akt["aksam"])] if akt else g["aksam"][_d % len(g["aksam"])]
            _l1 = locs[_d % len(locs)] if locs else destination
            _l2 = locs[(_d + 1) % len(locs)] if locs else destination
            if _d == 0:
                _all_pairs.append(("Otel", _s))
            _all_pairs.append((_s, _l1))
            _all_pairs.append((_l1, _o))
            _all_pairs.append((_o, _l2))
            _all_pairs.append((_l2, _a))
            _enrich_targets += [(_s, "yemek"), (_o, "yemek"), (_a, "yemek"),
                                 (_l1, "gezi"), (_l2, "gezi")]
        _enrich_targets = list(dict.fromkeys(_enrich_targets))[:24]

        # Gemini'den şehre özgü transit talimatları al
        transit_map = {}
        try:
            _uniq_pairs = list(dict.fromkeys(_all_pairs))[:18]
            _pairs_text = "\n".join([f"- {a} → {b}" for a, b in _uniq_pairs])
            _transit_prompt = (
                f"Şehir: {destination}\n"
                f"Ulaşım tercihi: {ulasim_tr}\n"
                f"Şehir transit ağı: {_metro_bilgi}\n"
                f"Transit kartı: {_transit_kart}\n\n"
                f"Aşağıdaki mekan çiftleri arasında {destination}'e özgü, GERÇEK toplu taşıma "
                f"adım adım talimatı ver. Her çift için: hangi hat/araç türü, biniş durağı, "
                f"kaç durak, iniş durağı, varsa aktarma, yürüyüş süresi. "
                f"Eğer mekânlar {destination}'de gerçekten varsa gerçek hat ve durak isimlerini kullan. "
                f"Max 2 cümle per çift. Format: JSON object.\n\n"
                f"Mekan çiftleri:\n{_pairs_text}\n\n"
                f"SADECE JSON döndür. Key=\"A → B\", value=\"talimat\""
            )
            _raw = (_gemini_generate(_transit_prompt) or "").strip()
            if "```" in _raw:
                _raw = _raw.split("```")[1]
                if _raw.startswith("json"):
                    _raw = _raw[4:]
            transit_map = json.loads(_raw.strip()) if _raw.strip() else {}
        except Exception:
            transit_map = {}

        # Gemini'den her mekan için gerçek, doğru ve geniş kapsamlı içerik al
        ai_enrich_map = {}
        try:
            _targets_text = "\n".join([f"- {n} (tür: {t})" for n, t in _enrich_targets])
            _enrich_prompt = (
                f"Sen {destination} şehrini çok iyi bilen yerel bir seyahat rehberisin. "
                f"Aşağıdaki mekan/aktiviteler için gerçek, doğru ve güncel bilgilere dayanan, "
                f"geniş kapsamlı Türkçe açıklama paragrafları yaz. Her biri için: mekanın ne olduğu, "
                f"neden önemli/özel olduğu, varsa gerçek tarihi/kültürel detaylar, ziyaret saati önerisi, "
                f"fiyat aralığı ve pratik bir ipucu içersin. Gezgin MBTI tipi: {mbti} — öneri ve dili "
                f"buna göre şekillendir.\n\n"
                f"Mekanlar:\n{_targets_text}\n\n"
                f"Kurallar:\n"
                f"- Yalnızca <b>, <br><br>, <i> etiketlerini kullan. style veya class ATTRİBUTE'u KULLANMA, "
                f"renk teması belirleme.\n"
                f"- Her açıklama iki paragraf olsun (<br><br> ile ayrılmış), ikinci paragraf "
                f"'<b>Pratik Bilgi:</b>' ile başlasın.\n"
                f"- SADECE JSON döndür. Key = mekan adı (yukarıdaki ile birebir aynı yazım), "
                f"value = HTML açıklama metni."
            )
            _eraw = (_gemini_generate(_enrich_prompt) or "").strip()
            if "```" in _eraw:
                _eraw = _eraw.split("```")[1]
                if _eraw.startswith("json"):
                    _eraw = _eraw[4:]
            ai_enrich_map = json.loads(_eraw.strip()) if _eraw.strip() else {}
        except Exception:
            ai_enrich_map = {}

        def _transit_hint(frm: str, to: str) -> str:
            key1 = f"{frm} → {to}"
            key2 = f"{frm.strip()} → {to.strip()}"
            hint = transit_map.get(key1) or transit_map.get(key2)
            if hint:
                return hint
            # Varsayılan şehre özgü fallback
            return (f"{_metro_bilgi.split(';')[0]} ile ulaşabilirsiniz. "
                    f"{_transit_kart} kullanmanız tavsiye edilir.")

        # ── Gün gün HTML üretimi ──────────────────────────────────────────────
        body       = ""
        foto_index = 0
        kart_sayac = 0

        for day_num in range(duration_days):
            if day_num > 0:
                body += '<div class="gun-ayirici"></div>\n'

            if start_dt:
                cur_date  = (start_dt + timedelta(days=day_num)).strftime("%Y-%m-%d")
                day_label = f"Gün {day_num + 1} — {cur_date}"
            else:
                day_label = f"Gün {day_num + 1}"

            body += f'<div class="gun-baslik">{day_label}</div>\n'
            kart_sayac = 0

            sabah_act = (akt["sabah"][day_num % len(akt["sabah"])] if akt
                         else g["sabah"][day_num % len(g["sabah"])])
            ogle_act  = (akt["ogle"][day_num % len(akt["ogle"])]   if akt
                         else g["ogle"][day_num % len(g["ogle"])])
            aksam_act = (akt["aksam"][day_num % len(akt["aksam"])] if akt
                         else g["aksam"][day_num % len(g["aksam"])])

            loc_name  = locs[day_num % len(locs)] if locs else destination
            loc2_name = locs[(day_num + 1) % len(locs)] if locs else aksam_act

            def _osm_link(place: str, city: str) -> str:
                """Google Maps arama linki — tarayıcı açılışında sunucu taraflı
                çözümlenir, ekstra ağ isteği/gecikme gerekmez ve restoran/POI
                kapsaması Nominatim'den çok daha güvenilirdir."""
                import urllib.parse as _up2
                _q2 = _up2.quote(f"{place}, {city}")
                return f"https://www.google.com/maps/search/?api=1&query={_q2}"

            def kart(time_str, act_type, label, title, enrich_text, hint="", osm_url=""):
                hint_html = (f'<div class="ulasim-notu">🚇 {hint}</div>' if hint else "")
                harita_html = ""
                if act_type in ("yemek", "gezi", "konaklama"):
                    import urllib.parse as _urlenc
                    raw_title = title.replace("&amp;", "&")
                    if " — " in raw_title:
                        search_q = raw_title.split(" — ", 1)[1].strip()
                    elif " - " in raw_title:
                        search_q = raw_title.split(" - ", 1)[1].strip()
                    else:
                        search_q = raw_title
                    _link = osm_url if osm_url else _osm_link(search_q, destination)
                    harita_html = (
                        f'<a class="harita-btn" href="{_link}" '
                        f'target="_blank" rel="noopener noreferrer">'
                        f'🗺 Haritada Gör</a>'
                    )
                return (
                    f'<div class="aktivite-kart" data-type="{act_type}">\n'
                    f'  <div class="saat-col">'
                    f'<span class="saat-txt">{time_str}</span>'
                    f'<span class="saat-etiket">{label}</span></div>\n'
                    f'  <div class="icerik-col">'
                    f'<h3 class="mekan-adi">{title}{harita_html}</h3>'
                    f'<div class="blog-metin">{enrich_text}</div>'
                    f'{hint_html}'
                    f'</div>\n</div>\n'
                )

            def foto_card():
                nonlocal foto_index
                if foto_index < len(fotograflar):
                    uri = fotograflar[foto_index]
                    foto_index += 1
                    return (f'<div class="foto-karti">'
                            f'<img src="{uri}" loading="lazy" '
                            f'onerror="this.parentElement.style.display=\'none\'"/>'
                            f'</div>\n')
                return ""

            # Gün 1: varış check-in
            if day_num == 0:
                _varis_txt = _enrich("Otel", "konaklama")
                body += kart("09:00", "konaklama", "Konaklama",
                             f"Varış &amp; Check-in — {destination}",
                             _varis_txt,
                             _sabah_ulasim)
                kart_sayac += 1

            # Kahvaltı — ulaşım: Otel → kahvaltı mekanı
            body += kart("09:30", "yemek", "Kahvaltı",
                         f"Kahvaltı — {sabah_act}",
                         _enrich(sabah_act, "yemek"),
                         _transit_hint("Otel", sabah_act) if day_num == 0
                         else _transit_hint(aksam_act, sabah_act))
            kart_sayac += 1
            if kart_sayac % 2 == 0:
                body += foto_card()

            # Sabah gezisi — ulaşım: kahvaltı → sabah gezi
            body += kart("11:00", "gezi", "Gezi",
                         loc_name,
                         _enrich(loc_name, "gezi"),
                         _transit_hint(sabah_act, loc_name))
            kart_sayac += 1
            if kart_sayac % 2 == 0:
                body += foto_card()

            # Öğle yemeği — ulaşım: sabah gezi → öğle yemeği
            body += kart("13:00", "yemek", "Öğle",
                         f"Öğle Yemeği — {ogle_act}",
                         _enrich(ogle_act, "yemek"),
                         _transit_hint(loc_name, ogle_act))
            kart_sayac += 1
            if kart_sayac % 2 == 0:
                body += foto_card()

            # Öğleden sonra gezisi — ulaşım: öğle → öğleden sonra gezi
            body += kart("15:00", "gezi", "Gezi",
                         loc2_name,
                         _enrich(loc2_name, "gezi"),
                         _transit_hint(ogle_act, loc2_name))
            kart_sayac += 1
            if kart_sayac % 2 == 0:
                body += foto_card()

            # Akşam yemeği — ulaşım: öğleden sonra gezi → akşam yemeği
            body += kart("19:30", "yemek", "Akşam",
                         f"Akşam Yemeği — {aksam_act}",
                         _enrich(aksam_act, "yemek"),
                         _transit_hint(loc2_name, aksam_act))
            kart_sayac += 1

        # ── Ulaşım ───────────────────────────────────────────────────────────
        transport_section = ""
        if transport_html:
            transport_section = (
                f'<div class="gun-baslik" style="margin-top:24px">🚌 Ulaşım Bilgileri</div>'
                f'<div style="background:#f2ede6;border:1px solid #e8dfd4;border-radius:12px;'
                f'padding:16px 20px;margin:12px 0;font-size:13px;color:#4a3f35;line-height:1.8">'
                f'{transport_html}</div>'
            )

        # ── Bütçe özeti — nude tonlar ─────────────────────────────────────────
        butce_html = ""
        if toplam:
            butce_html = (
                f'<h3 style="color:#2c2416;margin:24px 0 8px;font-size:15px">Bütçe Özeti</h3>'
                f'<div style="background:#f2ede6;border-radius:12px;padding:16px 18px;border:1px solid #e0d4c4">'
                f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">'
                f'<div style="text-align:center"><div style="font-size:11px;color:#7a6a5a">Konaklama</div>'
                f'<div style="font-weight:700;color:#8b7355">{konak:,.0f} TL</div></div>'
                f'<div style="text-align:center"><div style="font-size:11px;color:#7a6a5a">Yemek</div>'
                f'<div style="font-weight:700;color:#9eaa8f">{yemek_m:,.0f} TL</div></div>'
                f'<div style="text-align:center"><div style="font-size:11px;color:#7a6a5a">Toplam</div>'
                f'<div style="font-weight:700;color:#d4976a">{toplam:,.0f} TL</div></div>'
                f'</div></div>'
            )
        elif cost_html:
            butce_html = cost_html

        # ── İpuçları ──────────────────────────────────────────────────────────
        ipuclari = self._IPUCU.get(kat, self._IPUCU["orta"])
        ipucu_html = "".join(
            f'<li style="margin-bottom:8px;color:#374151;font-size:13px">{tip}</li>'
            for tip in ipuclari
        )

        return (
            f'{css}\n<div class="plan-wrap">'
            f'{header}'
            f'{stats}'
            f'{giris_html}'
            f'{body}'
            f'{transport_section}'
            f'{butce_html}'
            f'<h3 style="color:#2c2416;margin:24px 0 10px;font-size:15px">Pratik İpuçları</h3>'
            f'<ul style="padding-left:18px;margin:0 0 28px">{ipucu_html}</ul>'
            f'</div>'
        )

    def _gunluk_program(self, destination, duration, route, restaurant_schedule) -> str:
        dest_key = destination.lower().replace("ş","s").replace("ı","i").replace("ğ","g")
        # Şehre özgü aktivite seti varsa kullan, yoksa genel havuz
        akt = None
        for k, v in self._SEHIR_AKTIVITE.items():
            if k in dest_key:
                akt = v
                break

        html = '<h3 style="color:#1e1b4b;margin:24px 0 12px;font-size:15px">📅 Günlük Program</h3>'
        colors = ["#7c3aed","#2563eb","#059669","#d97706","#dc2626","#0891b2","#6d28d9"]
        for day in range(1, duration + 1):
            loc_raw = route[(day - 1) % len(route)] if route else None
            loc = loc_raw["name"] if isinstance(loc_raw, dict) else (str(loc_raw) if loc_raw else f"{destination} Merkezi")
            color = colors[(day - 1) % len(colors)]

            if akt:
                sabah = akt["sabah"][(day - 1) % len(akt["sabah"])]
                ogle  = akt["ogle"][(day - 1)  % len(akt["ogle"])]
                aksam = akt["aksam"][(day - 1)  % len(akt["aksam"])]
            else:
                g = self._GENEL_AKTIVITE
                sabah = g["sabah"][(day - 1) % len(g["sabah"])]
                ogle  = g["ogle"][(day - 1)  % len(g["ogle"])]
                aksam = g["aksam"][(day - 1)  % len(g["aksam"])]

            rest_name = ""
            if restaurant_schedule:
                for rs in restaurant_schedule:
                    if rs.get("day") == day:
                        rest_name = rs.get("restaurant", "")
                        break

            aksam_str = f'{aksam} · 🍽️ {rest_name}' if rest_name else aksam

            html += (
                f'<div style="border-left:3px solid {color};padding:14px 18px;margin:10px 0;'
                f'background:#fafafa;border-radius:0 10px 10px 0">'
                f'<div style="font-weight:700;color:#1e1b4b;margin-bottom:8px;font-size:13px">'
                f'Gün {day} — {loc}</div>'
                f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
                f'<div style="background:white;border-radius:8px;padding:8px 10px">'
                f'<div style="font-size:10px;color:#9ca3af;font-weight:600;margin-bottom:3px">🌅 SABAH</div>'
                f'<div style="font-size:12px;color:#374151">{sabah}</div></div>'
                f'<div style="background:white;border-radius:8px;padding:8px 10px">'
                f'<div style="font-size:10px;color:#9ca3af;font-weight:600;margin-bottom:3px">☀️ ÖĞLE</div>'
                f'<div style="font-size:12px;color:#374151">{ogle}</div></div>'
                f'<div style="background:white;border-radius:8px;padding:8px 10px">'
                f'<div style="font-size:10px;color:#9ca3af;font-weight:600;margin-bottom:3px">🌆 AKŞAM</div>'
                f'<div style="font-size:12px;color:#374151">{aksam_str}</div></div>'
                f'</div></div>'
            )
        return html


# ---------------------------------------------------------------------------
# HARİTA AJAN
# ---------------------------------------------------------------------------

class MapAgent:
    def __init__(self):
        self.api_key = os.getenv("OSM_API_KEY", "")

    def get_location_data(self, location_name: str, destination_city: str) -> dict:
        full_query = f"{location_name}, {destination_city}"
        if self.api_key:
            result = self._locationiq(full_query)
            if result:
                return result
        return self._osm_fallback(full_query, location_name)

    def _locationiq(self, query: str) -> dict | None:
        try:
            encoded = urllib.parse.quote(query)
            url = (f"https://us1.locationiq.com/v1/search.php"
                   f"?key={self.api_key}&q={encoded}&format=json&limit=1")
            req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelAI/1.0 (ilaydanudak@icloud.com)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            if data:
                lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                # OpenStreetMap deep-link (koordinatlı)
                map_link = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=17"
                return {"map_link": map_link, "status": "success", "latitude": lat, "longitude": lon}
        except Exception:
            pass
        return None

    def _osm_fallback(self, query: str, name: str) -> dict:
        encoded = urllib.parse.quote(query)
        map_link = f"https://www.openstreetmap.org/search?query={encoded}"
        return {
            "map_link": map_link,
            "status": "osm_fallback",
            "latitude": None,
            "longitude": None,
        }


# ---------------------------------------------------------------------------
# KULLANICI YÖNETİMİ
# ---------------------------------------------------------------------------

USERS_FILE = os.path.join("data", "users.json")


def _load_users() -> dict:
    os.makedirs("data", exist_ok=True)
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_users(users: dict):
    os.makedirs("data", exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def register_user(username: str, password: str, email: str = "") -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Kullanıcı adı en az 3 karakter olmalıdır."
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalıdır."
    users = _load_users()
    if username in users:
        return False, "Bu kullanıcı adı zaten alınmış."
    users[username] = {
        "password_hash": _hash_password(password),
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mbti_type": None,
        "travel_history": [],
    }
    _save_users(users)
    return True, "Kayıt başarılı!"


def login_user(username: str, password: str) -> tuple[bool, str]:
    users = _load_users()
    if username not in users:
        return False, "Kullanıcı adı bulunamadı."
    if users[username]["password_hash"] != _hash_password(password):
        return False, "Şifre hatalı."
    return True, "Giriş başarılı!"


def get_user_profile(username: str) -> dict:
    users = _load_users()
    return users.get(username, {})


def update_user_mbti(username: str, mbti_type: str):
    users = _load_users()
    if username in users:
        users[username]["mbti_type"] = mbti_type
        _save_users(users)


def save_travel_history(username: str, travel_record: dict):
    users = _load_users()
    if username in users:
        users[username].setdefault("travel_history", []).append({
            **travel_record,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        _save_users(users)
