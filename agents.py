# agents.py — Kimlik testi (MBTI) ajanı.
# Seyahat planlama ajanları multiagent.py'dedir; bu dosya yalnızca test sonucunu
# hesaplar ve Gemini ile (yoksa hazır metinle) kişilik raporu yazar.

import os
import re

try:
    from google import genai as _genai
except Exception:
    _genai = None


def _gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if _genai and api_key and os.getenv("SMARTTRAVEL_OFFLINE") != "1":
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
        # Kod bloğu sarmalını temizle: ```html ... ``` veya ``` ... ```
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
        text = re.sub(r"\s*```\s*$", "", text.strip())
        # <html><body> sarmalını temizle — sadece içeriği al
        body = re.search(r"<body[^>]*>([\s\S]*?)</body>", text, re.IGNORECASE)
        if body:
            text = body.group(1).strip()
        return text.strip() if text.strip() else None
    except Exception:
        return None


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

    # 20 soru × 2 seçenek: her soruda birbirine zıt iki ifade, kullanıcı kendine yakın olanı seçer
    # (OEJTS ve MBTI Form M'deki zorunlu seçim biçimi örnek alınmıştır; maddeler yazarlarındır).
    # Her boyut (E/I, S/N, T/F, J/P) için 5 soru, dönüşümlü sıralı. Şık dengesi: her boyutta
    # A şıkkı 3 soruda bir kutba, 2 soruda diğer kutba aittir — hep "A" seçmek sonucu tek yöne itmez.
    # Sorular 1–10 genel kişilik, 11–20 seyahat davranışı. Boyut başına 5 (tek) soru → beraberlik olmaz.
    # (soru, A ifadesi, B ifadesi, A kutbu, B kutbu)
    SORULAR = [
        # ── Bölüm 1: Kişilik & motivasyon ──────────────────────────────────
        ("Yeni bir durumla karşılaştığında",
         "Karışmadan önce gözlemlemeyi ve analiz etmeyi tercih ederim.",
         "Hemen dahil olur, yaparak ve konuşarak öğrenirim.", "I", "E"),
        ("Bilgiye nasıl güvenirsin?",
         "Somut gerçeklere ve kanıtlanmış yöntemlere güvenirim.",
         "Olasılıklara, sezgilerime ve yeni fikirlere güvenirim.", "S", "N"),
        ("Önemli bir karar verirken",
         "Bilinçli kararlar almak için veri toplar ve analiz ederim.",
         "Kararın insanlara ve değerlerime nasıl dokunacağına bakarım.", "T", "F"),
        ("İşlerini nasıl yürütürsün?",
         "Seçeneklerimi açık tutmayı, son ana kadar esnek kalmayı severim.",
         "İşleri planlayıp erkenden karara bağlamayı severim.", "P", "J"),
        ("Yorucu bir günün ardından",
         "Arkadaşlarla buluşmak beni dinlendirir.",
         "Yalnız kalıp kendi başıma vakit geçirmek beni dinlendirir.", "E", "I"),
        ("Neye odaklanırsın?",
         "Ayrıntılardan çok büyük resmi ve anlamı görmeye odaklanırım.",
         "Büyük resimden çok ayrıntılara ve somut adımlara odaklanırım.", "N", "S"),
        ("Bir tartışmada",
         "Doğruyu ortaya koymak, uyumu korumaktan daha önemlidir.",
         "Uyumu korumak, haklı çıkmaktan daha önemlidir.", "T", "F"),
        ("Gündelik düzenin",
         "Yapılacaklar listem olmadan kendimi düzensiz hissederim.",
         "Listeler beni kısıtlar; işleri akışına göre hallederim.", "J", "P"),
        ("İlgini daha çok ne çeker?",
         "Fikirlerden çok insanlarla ve sosyal etkileşimle ilgilenirim.",
         "Sosyal etkileşimden çok fikir ve kavramlarla ilgilenirim.", "E", "I"),
        ("Yeni bir şey öğrenirken",
         "Önce pratik örneklerini ve nasıl uygulandığını görmek isterim.",
         "Önce ardındaki teoriyi ve bağlantıları anlamak isterim.", "S", "N"),
        # ── Bölüm 2: Turizm kimliği & keşif tarzı ───────────────────────────
        ("Otel seçerken",
         "Samimi ve sıcak hissettirmesine bakarım.",
         "Konum, fiyat ve puanları karşılaştırırım.", "F", "T"),
        ("Gezi programın",
         "Saat saat planlıdır.",
         "Sadece ilk gün planlıdır, gerisi akışta.", "J", "P"),
        ("Seyahatte akşamlarını",
         "Sakin bir köşede kitap ya da günlükle geçiririm.",
         "Canlı meydanlarda ve kalabalık mekânlarda geçiririm.", "I", "E"),
        ("Keşif tarzın",
         "Bilinen, denenmiş popüler rotaları tercih ederim.",
         "Haritada olmayan ara sokakları keşfetmeyi tercih ederim.", "S", "N"),
        ("Gezide beklenmedik bir sorun çıkarsa",
         "Önce mantıklı bir çözüm üretirim.",
         "Önce herkesin moralini düşünürüm.", "T", "F"),
        ("Konaklama konusunda",
         "Yer bulmayı vardığım yere bırakmak bana heyecan verir.",
         "Rezervasyonlarımı haftalar önceden garantiye alırım.", "P", "J"),
        ("Gittiğin yerde yerel halkla",
         "Hemen sohbet başlatırım.",
         "Konuşmaktan çok gözlemlemeyi severim.", "E", "I"),
        ("Bir şehri değerlendirirken",
         "Hikâyesi ve atmosferi, görülecek yerler listesinden önemlidir.",
         "Önce en bilinen somut yapılarını görmek isterim.", "N", "S"),
        ("Yol arkadaşınla",
         "Onun mutlu olması, rotanın verimli olmasından önemlidir.",
         "Rotanın verimli olması, herkesin keyfine göre esnemekten önemlidir.", "F", "T"),
        ("Bavulunu",
         "Günler öncesinden, listeyle hazırlarım.",
         "Son gece, aklıma geldikçe hazırlarım.", "J", "P"),
    ]

    TIPLER = [a + b + c + d for a in "EI" for b in "SN" for c in "TF" for d in "JP"]

    def _determine_mbti(self, answers) -> str:
        """answers: 20 elemanlı "A"/"B" listesi ya da {"q1": "A", ...} sözlüğü.
        "A) metin" biçimindeki değerlerin yalnızca ilk harfine bakılır."""
        if isinstance(answers, dict):
            answers = [answers.get(f"q{i}", "A") for i in range(1, len(self.SORULAR) + 1)]
        puan = {h: 0 for h in "EISNTFJP"}
        for (_, _, _, a, b), cevap in zip(self.SORULAR, answers):
            harf = str(cevap or "A").strip()[:1].upper()
            puan[b if harf == "B" else a] += 1
        return "".join(x if puan[x] > puan[y] else y for x, y in (("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")))

    def analyze(self, answers) -> dict:
        return self.tip_profili(self._determine_mbti(answers))

    def tip_profili(self, mbti: str) -> dict:
        """Testten ya da kullanıcının zaten bildiği tipten profil raporu üretir."""
        mbti = mbti.upper()
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
