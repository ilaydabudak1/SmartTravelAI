# SmartTravel AI — MBTI Tabanlı Çok Ajanlı Seyahat Planlama Sistemi

Kişilik testi, serbest metin notu ve geçmiş seyahatleri birleştirip; dört ajanın ortak
bir pano üzerinden konuşarak kişiye özel, bütçe kısıtlı ve tekrar etmeyen bir gezi planı
ürettiği kavram kanıtı (proof of concept).

## Çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

`.env` dosyasına anahtarlar eklenebilir (hiçbiri zorunlu değil):

| Anahtar | Ne işe yarar | Yoksa |
|---|---|---|
| `ANTHROPIC_API_KEY` | Profil ajanı **Claude Opus**, Plan/Eleştirmen ajanları **Claude Sonnet** | Gemini'ye düşer |
| `GEMINI_API_KEY` | Maliyet ajanı **Gemini 2.5 Flash**; Claude yoksa diğer ajanların yedeği | Kural tabanlı mod |
| `GOOGLE_MAPS_API_KEY` | Google Maps: gerçek yürüyüş mesafesi ve gerçek gezi noktaları | Açık kaynak servisler (OSRM, OpenStreetMap) kullanılır |
| `SMARTTRAVEL_DATA` | Veri klasörü (varsayılan `data/`) | — |
| `SMARTTRAVEL_OFFLINE=1` | Tüm ağ/LLM çağrılarını kapatır (testler) | — |

### Google Maps anahtarı

Google Cloud Console'da şu iki API'yi etkinleştirip anahtarı `.env` dosyasına
`GOOGLE_MAPS_API_KEY=...` olarak ekleyin:

| API | Ne için |
|---|---|
| Routes API | Günlük rotanın gerçek yürüyüş mesafesi ve süresi |
| Places API (New) | Pilot olmayan şehirlerde gerçek gezi noktaları |

"Harita" ve "Günün rotasını Google Maps'te aç" bağlantıları anahtar gerektirmez, her zaman Google Maps'e gider.
Konum bulma (pilot olmayan şehirler) ücretsiz açık kaynak servisle yapılır.

## Mimari (sunum, slayt 15)

```
1 · VERİ GİRDİ      kişilik testi · serbest not · şehir/gün/bütçe · geçmiş seyahatler
2 · AJAN KATMANI    ① Profil (Opus) → ② Plan (Sonnet) ⇄ Eleştirmen (Sonnet) → ③ Rota (algoritma) → ④ Maliyet (Gemini)
3 · HAFIZA          JSON + SQLite — profiller · seyahat geçmişi · algoritma istatistikleri · maliyet kayıtları
4 · ÇIKTI           gün gün rota + harita · seyahat notu · algoritma raporu · bütçe karşılaştırması
```

| Sunumdaki bileşen | Kod |
|---|---|
| Kullanıcı Profili Ajanı, serbest not çözümleme, seyahat notu | `multiagent.py` → `ProfilAjani`, `notu_cozumle` |
| Plan Ajanı (5+ gezi noktası, JSON), halüsinasyon kontrolü | `PlanAjani`, `ElestirmenAjani` |
| Rota Ajanı: Haversine, NN, NN+2-opt, KKO, GA, gerçek yol, VRPTW | `routing.py`, `RotaAjani` |
| Maliyet Tahmin Ajanı: çıpa fiyatlar, kalem kalem, tasarruf (%) | `MaliyetAjani` |
| Bütçe kısıtı ve müzakere | `Orkestrator._muzakere` |
| Heterojen model seçimi | `llm.py` → `ROL_MODELLERI` |
| Hafıza: 4 depo, tekrar önermeme, geri bildirim | `memory.py` |
| Yedek bilgi tabanı (10 pilot destinasyon) | `poi_data.py` |
| Google Maps (yol tarifi, konum, yer arama, harita) | `google_maps.py` |
| 90 problemlik deney, Wilcoxon + Holm + Cohen d, eşit bütçe | `benchmark.py` |
| Gezi hazırlığı: yapılacaklar, bavul listesi, günlük harcama | `hazirlik.py` |
| Otomatik testler | `tests/` (`python -m pytest`) |

### Ajanlar nasıl "aktif"?

Ajanlar birbirini doğrudan çağırmaz; `Pano` üzerine mesaj (`bilgi | istek | ret | karar | uyari`) bırakır:

* **Eleştirmen → Plan:** tekrar, daha önce gidilmiş, kaçınılan tür, şehirden uzak (olası halüsinasyon)
  ya da profile uymayan yerleri **reddeder**; Plan Ajanı reddedilenleri bilerek yeniden üretir (en fazla 3 tur).
* **Rota → Plan:** gün çok uzarsa ya da bir yer kapanmadan ziyaret edilemiyorsa profile en az uyan durağı çıkarır.
* **Maliyet → Plan / Orkestratör:** bütçe aşılırsa müzakere başlatır: ulaşım → yemek → konaklama →
  ücretli durakların profile uygun ücretsiz alternatifleri → şehirlerarası ulaşım. Her tur kaydedilir;
  bütçe karşılanamazsa açıkça raporlanır.

Kullanıcı arayüzü sonuca odaklanır; ajanların konuşma kaydı (`sonuc["mesajlar"]`), algoritma yarışı ve müzakere turları plan kaydıyla birlikte saklanır ve `data/hafiza/<kullanıcı>.json` içinde incelenebilir.

### Hafıza ("sistem öğrenmiyor, hatırlıyor")

* Her plan sonrası gidilen yerler, algoritma sonuçları, maliyet kaydı, serbest not, üretilen seyahat notu
  ve profil SQLite'a; okunabilir kopyası `data/hafiza/<kullanıcı>.json` dosyasına yazılır.
* Bir sonraki planda Profil Ajanı'na bağlam olarak verilir: daha önce gidilen yerler (bulanık eşleştirme ile)
  **tekrar önerilmez**, gezi sonrası geri bildirimdeki "sevmedim"ler kaçınma listesine girer.
* **📖 Seyahatlerim** sekmesinde gezi haritası, harcama geçmişi, profil özeti, gezi sonrası puan/sevdim/sevmedim
  ve sistem dışı gezilerde gidilen yerler bir arada bulunur.

## Deney

```bash
python benchmark.py --ornek 30
```

5/10/20 durak × 30 örnek. Referans: 5 durakta kaba kuvvet, 10–20 durakta OR-Tools (kuruluysa),
yoksa "en iyi bilinen" çözüm. Rapor `data/benchmark/` altına Markdown + JSON olarak yazılır.

## Sınırlılıklar

Kişilik testi soruları için geçerlik/güvenirlik analizi yapılmadı. Bütçe rakamları gerçek fiyat değil,
tahmindir; tasarruf oranı bir kanıt değildir. Yedek bilgi tabanındaki ücret ve saatler yaklaşıktır.
KKO ve GA varsayılan ayarlarla çalışır.
