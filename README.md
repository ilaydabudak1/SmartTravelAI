# SmartTravel AI — MBTI Tabanlı Çok Ajanlı Seyahat Planlama Sistemi

Kişilik testi, serbest metin notu ve geçmiş seyahatleri birleştirip; dört ajanın ortak bir
pano üzerinden konuşarak **kişiye özel, bütçe kısıtlı ve tekrar etmeyen** bir gezi planı
ürettiği kavram kanıtı (proof of concept).

## Öne çıkanlar

- **4 ajan + eleştirmen:** Profil (Claude Opus) → Plan (Claude Sonnet) ⇄ Eleştirmen → Rota (algoritmalar) → Maliyet (Gemini)
- **Rota optimizasyonu:** En Yakın Komşu, 2-opt, Karınca Kolonisi (KKO) ve Genetik Algoritma yarışır; en iyisi seçilir
- **Hafıza:** SQLite + JSON; daha önce gidilen yerler bir daha önerilmez, geri bildirimler sonraki plana yansır
- **Bütçe kısıtı:** Bütçe aşılırsa ajanlar müzakere eder, ücretsiz alternatiflere geçer
- **Canlı ajan izleme paneli:** Plan hazırlanırken her ajan adımı, eleştirmen geri dönüşleri ve şehrin anlık hava durumu gösterilir
- **10 pilot destinasyon:** İstanbul (ana pilot), Ankara, İzmir, Antalya, Kapadokya, Eskişehir, Roma, Paris, Barcelona, Amsterdam.
  Ülke ya da bölge adı girilirse (ör. "İspanya", "Ege") uygun pilot şehre yönlendirilir.

## Kurulum ve çalıştırma

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

Masaüstü uygulaması gibi açmak için `launcher.pyw` (ayrıca `pip install pywebview` gerekir) ya da
`launch.bat` kullanılabilir. `launcher.pyw` boş bir port bulur ve günlükleri `data/logs/streamlit.log` dosyasına yazar.

### Ortam değişkenleri (`.env`)

Hiçbiri zorunlu değildir; anahtar yoksa sistem bir alt seviyeye düşerek çalışmaya devam eder.

| Anahtar | Ne işe yarar | Yoksa |
|---|---|---|
| `ANTHROPIC_API_KEY` | Profil ajanı **Claude Opus**, Plan/Eleştirmen ajanları **Claude Sonnet** | Gemini'ye düşer |
| `GEMINI_API_KEY` | Maliyet ajanı **Gemini 2.5 Flash**; Claude yoksa diğer ajanların yedeği, kişilik raporu | Kural tabanlı mod |
| `GOOGLE_MAPS_API_KEY` | Gerçek yürüyüş mesafesi ve pilot olmayan şehirlerde gerçek gezi noktaları | Açık kaynak servisler (OSRM, OpenStreetMap) |
| `SMARTTRAVEL_DATA` | Veri klasörü (varsayılan `data/`) | — |
| `SMARTTRAVEL_OFFLINE=1` | Tüm ağ ve dil modeli çağrılarını kapatır (testler) | — |

### Google Maps anahtarı (faturalandırma gerektirmez)

Google Cloud Console'da yalnızca şu iki API'yi etkinleştirin:

| API | Ne için |
|---|---|
| Routes API | Günlük rotanın gerçek yürüyüş mesafesi ve süresi |
| Places API (New) | Pilot olmayan şehirlerde gerçek gezi noktaları |

"Haritada aç" ve "Günün rotasını Google Maps'te aç" bağlantıları anahtar gerektirmez.
Şehir konumu ücretsiz Nominatim (OpenStreetMap) ile, hava durumu anahtarsız **Open-Meteo** ile alınır.

## Kullanım akışı

Uygulama beş sekmeden oluşur:

1. **🧬 Kimlik Testi** — 20 soruluk A/B kişilik testi (her boyut için 5 soru) ya da "Tipimi biliyorum" ile doğrudan tip seçimi.
2. **🗺️ Rota Formu** — destinasyon, tarihler, kişi sayısı, ulaşım, bütçe üst sınırı, "Maliyet tasarrufu" seçeneği ve serbest not.
   "Seni hatırlıyoruz" paneli geçmiş gezilerden çıkarılanları gösterir. Plan hazırlanırken ajan izleme paneli açılır.
3. **📋 Plan Sonucu** — kişisel seyahat notu, harita, gün gün aktivite kartları (Google Maps bağlantılarıyla), bütçe dökümü,
   restoran önerileri, "Vaktin kalırsa" yedek yerler, ipuçları ve PDF indirme.
4. **🧳 Gezi Hazırlığı** — plana göre oluşan Tatil Listesi (işaretlemeler kaydedilir) ve günlük harcama planı.
5. **📖 Seyahatlerim** — gezi haritası, profil özeti, harcama geçmişi, gezi sonrası yorum/puan, sistem dışı geziler, notlar ve verileri JSON olarak indirme.

## Mimari

```
1 · VERİ GİRDİ      kişilik testi · serbest not · şehir/gün/bütçe · geçmiş seyahatler
2 · AJAN KATMANI    ① Profil (Opus) → ② Plan (Sonnet) ⇄ Eleştirmen → ③ Rota (algoritma) → ④ Maliyet (Gemini)
3 · HAFIZA          SQLite + JSON — profiller · ziyaretler · algoritma istatistikleri · maliyet kayıtları · notlar
4 · ÇIKTI           gün gün rota + harita · seyahat notu · bütçe karşılaştırması · gezi hazırlığı
```

### Ajanlar nasıl "aktif"?

Ajanlar birbirini doğrudan çağırmaz; ortak `Pano` üzerine mesaj (`bilgi | istek | ret | karar | uyari`) bırakır:

* **Eleştirmen → Plan:** tekrar eden, daha önce gidilmiş, kaçınılan türde, seçilen şehrin dışında (olası halüsinasyon)
  ya da profile uymayan yerleri **reddeder**; Plan Ajanı reddedilenleri bilerek yeniden üretir (en fazla 3 tur).
* **Rota → Plan:** gün 21:30'u geçerse ya da bir yer kapanmadan ziyaret edilemiyorsa profile en az uyan durağı çıkarır.
* **Maliyet → Orkestratör:** bütçe aşılırsa müzakere başlatır (ulaşım → yemek → konaklama → ücretli durakların
  ücretsiz alternatifleri → şehirlerarası ulaşım, en fazla 6 tur). Bütçe karşılanamazsa açıkça raporlanır.

Ajanların konuşma kaydı, algoritma yarışı ve müzakere turları plan kaydıyla birlikte saklanır;
`data/hafiza/<kullanıcı>.json` içinde incelenebilir.

### Rota algoritmaları

| Algoritma | Ayarlar |
|---|---|
| Haversine mesafe matrisi | — |
| En Yakın Komşu (NN), NN + 2-opt | — |
| Karınca Kolonisi (KKO) | 20 karınca, 100 iterasyon, ρ=0,5, α=1, β=2 |
| Genetik Algoritma (GA) | popülasyon 50, 100 nesil, turnuva 3, mutasyon 0,1, elit 5, OX çaprazlama |
| Zaman pencereleri (VRPTW benzeri) | açılış-kapanış saatleri, öğle molası, 1,5 km üstü toplu taşıma |

### Hafıza ("sistem öğrenmiyor, hatırlıyor")

* Her plan sonrası gidilen yerler, algoritma sonuçları, maliyet kaydı, serbest not, seyahat notu ve profil
  SQLite'a (`data/smarttravel.db`), okunabilir kopyası `data/hafiza/<kullanıcı>.json` dosyasına yazılır.
* Sonraki planda Profil Ajanı'na bağlam olarak verilir: daha önce gidilen yerler (bulanık eşleştirme ile)
  **tekrar önerilmez**, gezi sonrası "sevmedim"ler kaçınma listesine girer.

## Proje yapısı

| Dosya | İçerik |
|---|---|
| `app.py` | Streamlit arayüzü (5 sekme, giriş/kayıt, ajan izleme paneli) |
| `multiagent.py` | `ProfilAjani`, `PlanAjani`, `ElestirmenAjani`, `RotaAjani`, `MaliyetAjani`, `Orkestrator`, `Pano` |
| `llm.py` | Rol bazlı model yönlendirici (`ROL_MODELLERI`): Claude → Gemini → kural tabanlı |
| `routing.py` | Mesafe, NN, 2-opt, KKO, GA, kaba kuvvet, günlere bölme, zaman çizelgesi, gerçek yol |
| `memory.py` | Hafıza tabloları, tekrar önermeme, notlar, gezi hazırlığı durumu, JSON dışa aktarma |
| `db.py` | Kullanıcılar (PBKDF2 parola), seyahat planları |
| `agents.py` | 20 soruluk A/B kişilik testi ve 16 tip profili |
| `poi_data.py` | 10 pilot destinasyonun gezi noktaları ve restoranları, ülke/şehir çözümleme |
| `google_maps.py` | Routes API, Places API (New), anahtarsız harita bağlantıları |
| `hava.py` | Open-Meteo ile anlık hava durumu |
| `plan_render.py` | Plan sayfası ve ilerleme paneli HTML bileşenleri |
| `hazirlik.py` | Tatil Listesi ve günlük harcama planı |
| `benchmark.py` | Algoritma deneyi |
| `launcher.pyw`, `launch.bat` | Masaüstü başlatıcıları |
| `tests/` | Otomatik testler |

## Testler

```bash
python -m pytest
```

Testler `SMARTTRAVEL_OFFLINE=1` ile ve geçici bir veritabanıyla çalışır; ağ ya da API anahtarı gerektirmez.

## Deney

```bash
python benchmark.py --ornek 30
```

5/10/20 durak × 30 örnek = 90 problem. Referans: 5 durakta kaba kuvvet, 10–20 durakta OR-Tools
(`pip install ortools` kuruluysa), yoksa "en iyi bilinen" çözüm. Wilcoxon işaretli sıra testi, Holm düzeltmesi,
Cohen d ve eşit hesaplama bütçeli GA karşılaştırması içerir. Rapor `data/benchmark/` altına Markdown + JSON olarak yazılır.

## Sınırlılıklar

* Kişilik testi sorularının özgün metni resmî MBTI maddeleri değildir (resmî maddeler telif korumalıdır);
  açık kaynak OEJTS biçiminden esinlenilmiştir ve geçerlik/güvenirlik analizi yapılmamıştır.
* Eleştirmen konum, tekrar ve profil hatalarını yakalar; ancak dil modelinin önerdiği bir yerin gerçekten
  var olduğunu yalnızca bilgi tabanı ve Google Places kaynaklı yerler için doğrulayabilir.
* Bütçe rakamları gerçek fiyat değil tahmindir; yedek bilgi tabanındaki ücret ve saatler yaklaşıktır.
* KKO ve GA varsayılan ayarlarla çalışır.
