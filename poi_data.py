# poi_data.py — Plan Ajanı'nın yedek bilgi tabanı
#
# LLM erişimi yokken (ya da halüsinasyon kontrolünde referans olarak) kullanılan
# şehir → gezi noktası (POI) ve restoran listeleri. Her POI:
#   isim, lat, lon, kategori, sure_dk, acilis, kapanis, ucret_tl (yetişkin, tahmini), etiketler
# Ücretler 2026 için yaklaşık değerlerdir (1 € ≈ 50 TL); gerçek fiyat değildir.
# Listede olmayan şehirler için OpenStreetMap (Nominatim + Overpass) üzerinden
# canlı POI çekilir.

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from memory import normalize

KATEGORILER = ["tarih", "muze", "sanat", "ibadet", "doga", "manzara", "alisveris",
               "yemek", "gece", "sahil", "mahalle", "bilim", "macera"]


def _p(isim, lat, lon, kategori, sure, acilis="09:00", kapanis="18:00", ucret=0, etiket=""):
    return {"isim": isim, "lat": lat, "lon": lon, "kategori": kategori, "sure_dk": sure,
            "acilis": acilis, "kapanis": kapanis, "ucret_tl": ucret,
            "etiketler": [e for e in etiket.split(",") if e]}


POI = {
    "istanbul": [
        _p("Ayasofya", 41.0086, 28.9802, "tarih", 75, "09:00", "19:00", 0, "ikonik,kalabalik,mimari"),
        _p("Topkapı Sarayı", 41.0115, 28.9834, "muze", 150, "09:00", "18:00", 650, "ikonik,kalabalik,tarih"),
        _p("Sultanahmet Camii", 41.0054, 28.9768, "ibadet", 40, "08:30", "16:30", 0, "ikonik,kalabalik,mimari"),
        _p("Yerebatan Sarnıcı", 41.0084, 28.9779, "tarih", 45, "09:00", "22:00", 600, "ikonik,kalabalik"),
        _p("Kapalıçarşı", 41.0107, 28.9681, "alisveris", 90, "09:00", "19:00", 0, "kalabalik,yerel"),
        _p("Mısır Çarşısı", 41.0166, 28.9706, "alisveris", 50, "08:00", "19:30", 0, "yerel,yemek"),
        _p("Süleymaniye Camii", 41.0162, 28.9639, "ibadet", 50, "09:00", "18:00", 0, "sakin,mimari,manzara"),
        _p("Galata Kulesi", 41.0256, 28.9741, "manzara", 50, "08:30", "23:00", 1000, "ikonik,fotograf"),
        _p("İstiklal Caddesi", 41.0335, 28.9777, "gece", 90, "00:00", "23:59", 0, "kalabalik,gece,sokak"),
        _p("Dolmabahçe Sarayı", 41.0391, 29.0005, "muze", 120, "09:00", "18:00", 1050, "tarih,lüks"),
        _p("İstanbul Modern", 41.0263, 28.9837, "sanat", 90, "10:00", "18:00", 450, "sanat,modern"),
        _p("Pera Müzesi", 41.0319, 28.9751, "sanat", 75, "10:00", "19:00", 300, "sanat,sakin"),
        _p("Balat Sokakları", 41.0294, 28.9487, "mahalle", 90, "08:00", "20:00", 0, "fotograf,yerel,sakin"),
        _p("Kariye Camii (Chora)", 41.0312, 28.9393, "tarih", 50, "09:00", "17:00", 500, "mozaik,sakin"),
        _p("Gülhane Parkı", 41.0133, 28.9812, "doga", 45, "07:00", "22:00", 0, "sakin,doga"),
        _p("Ortaköy Meydanı", 41.0473, 29.0270, "sahil", 60, "00:00", "23:59", 0, "manzara,yemek"),
        _p("Moda Sahili", 40.9790, 29.0260, "sahil", 75, "00:00", "23:59", 0, "yerel,sakin,gunbatimi"),
        _p("İstanbul Arkeoloji Müzeleri", 41.0117, 28.9813, "muze", 90, "09:00", "18:00", 340, "arkeoloji,sakin"),
        _p("Rumeli Hisarı", 41.0847, 29.0567, "tarih", 60, "09:00", "17:30", 200, "manzara,fotograf"),
        _p("Kız Kulesi", 41.0211, 29.0041, "manzara", 60, "09:00", "18:00", 750, "ikonik,fotograf"),
        _p("Sakıp Sabancı Müzesi", 41.1086, 29.0558, "sanat", 90, "10:00", "18:00", 300, "sanat,sakin"),
        _p("Emirgan Korusu", 41.1080, 29.0520, "doga", 60, "07:00", "22:00", 0, "sakin,park"),
        _p("Rahmi M. Koç Müzesi (İstanbul)", 41.0423, 28.9490, "bilim", 120, "10:00", "17:00", 300, "teknik"),
        _p("Pierre Loti Tepesi", 41.0550, 28.9330, "manzara", 45, "08:00", "23:00", 0, "manzara,sakin"),
        _p("Kadıköy Çarşısı", 40.9905, 29.0250, "yemek", 75, "08:00", "22:00", 0, "yerel,yemek"),
        _p("Bebek Sahili", 41.0770, 29.0430, "sahil", 60, "00:00", "23:59", 0, "yerel,gunbatimi"),
        _p("Büyük Çamlıca Tepesi", 41.0270, 29.0690, "manzara", 45, "06:00", "23:00", 0, "manzara"),
    ],
    "ankara": [
        _p("Anıtkabir", 39.9250, 32.8369, "tarih", 120, "09:00", "17:00", 0, "ikonik,tarih"),
        _p("Anadolu Medeniyetleri Müzesi", 39.9385, 32.8617, "muze", 120, "08:30", "19:00", 400, "arkeoloji,tarih"),
        _p("Ankara Kalesi", 39.9409, 32.8644, "manzara", 60, "00:00", "23:59", 0, "tarih,manzara"),
        _p("Hamamönü", 39.9350, 32.8630, "mahalle", 75, "08:00", "23:00", 0, "yerel,yemek"),
        _p("Kocatepe Camii", 39.9165, 32.8601, "ibadet", 30, "06:00", "22:00", 0, "mimari"),
        _p("Gençlik Parkı", 39.9365, 32.8505, "doga", 45, "06:00", "23:00", 0, "park"),
        _p("CerModern", 39.9346, 32.8476, "sanat", 75, "10:00", "18:00", 150, "sanat,modern"),
        _p("Erimtan Arkeoloji ve Sanat Müzesi", 39.9396, 32.8628, "muze", 60, "10:00", "18:00", 200, "arkeoloji,sakin"),
        _p("Rahmi M. Koç Müzesi", 39.9392, 32.8620, "bilim", 75, "10:00", "17:00", 150, "teknik,bilim"),
        _p("Atakule", 39.8863, 32.8559, "manzara", 45, "10:00", "22:00", 150, "manzara"),
        _p("Kuğulu Park", 39.9026, 32.8608, "doga", 30, "00:00", "23:59", 0, "sakin"),
        _p("Atatürk Orman Çiftliği", 39.9440, 32.7990, "doga", 90, "08:00", "20:00", 0, "doga,yemek"),
    ],
    "izmir": [
        _p("Kemeraltı Çarşısı", 38.4196, 27.1316, "alisveris", 120, "09:00", "20:00", 0, "yerel,kalabalik,yemek"),
        _p("Konak Saat Kulesi", 38.4189, 27.1287, "tarih", 20, "00:00", "23:59", 0, "ikonik,fotograf"),
        _p("Kordon", 38.4335, 27.1390, "sahil", 90, "00:00", "23:59", 0, "gunbatimi,yerel"),
        _p("Tarihi Asansör", 38.4105, 27.1295, "manzara", 40, "08:00", "23:00", 0, "manzara"),
        _p("Kadifekale", 38.4097, 27.1453, "manzara", 50, "08:00", "20:00", 0, "tarih,manzara"),
        _p("Smyrna Antik Agorası", 38.4185, 27.1395, "tarih", 60, "08:30", "19:00", 200, "arkeoloji"),
        _p("İzmir Arkeoloji Müzesi", 38.4140, 27.1290, "muze", 75, "08:30", "19:00", 150, "arkeoloji,sakin"),
        _p("Kültürpark", 38.4295, 27.1470, "doga", 60, "06:00", "23:00", 0, "park"),
        _p("Alsancak", 38.4370, 27.1430, "gece", 90, "10:00", "23:59", 0, "gece,yemek"),
        _p("Konak Pier", 38.4290, 27.1340, "alisveris", 45, "10:00", "22:00", 0, "sahil"),
    ],
    "antalya": [
        _p("Kaleiçi", 36.8841, 30.7056, "mahalle", 120, "00:00", "23:59", 0, "tarih,fotograf,yerel"),
        _p("Hadrian Kapısı", 36.8855, 30.7082, "tarih", 20, "00:00", "23:59", 0, "ikonik"),
        _p("Antalya Müzesi", 36.8853, 30.6820, "muze", 90, "08:30", "19:00", 400, "arkeoloji"),
        _p("Düden Şelalesi (Karpuzkaldıran)", 36.8517, 30.7811, "doga", 60, "08:00", "20:00", 0, "doga,manzara"),
        _p("Konyaaltı Plajı", 36.8681, 30.6510, "sahil", 150, "00:00", "23:59", 0, "plaj,kalabalik"),
        _p("Yivli Minare", 36.8869, 30.7046, "ibadet", 20, "08:00", "20:00", 0, "tarih"),
        _p("Karaalioğlu Parkı", 36.8819, 30.7068, "doga", 45, "00:00", "23:59", 0, "gunbatimi,sakin"),
        _p("Perge Antik Kenti", 36.9617, 30.8540, "tarih", 120, "08:00", "19:00", 500, "arkeoloji"),
        _p("Eski Liman", 36.8857, 30.7036, "sahil", 45, "00:00", "23:59", 0, "manzara,tekne"),
    ],
    "kapadokya": [
        _p("Göreme Açık Hava Müzesi", 38.6400, 34.8450, "muze", 120, "08:00", "19:00", 600, "ikonik,kalabalik"),
        _p("Uçhisar Kalesi", 38.6306, 34.8050, "manzara", 60, "08:00", "20:00", 150, "manzara,fotograf"),
        _p("Paşabağları", 38.6740, 34.8440, "doga", 60, "08:00", "19:00", 200, "peri bacasi,fotograf"),
        _p("Avanos Çömlek Atölyeleri", 38.7150, 34.8470, "sanat", 75, "09:00", "19:00", 0, "el sanatlari,yerel"),
        _p("Zelve Açık Hava Müzesi", 38.6730, 34.8640, "tarih", 90, "08:00", "19:00", 200, "sakin,yuruyus"),
        _p("Kaymaklı Yeraltı Şehri", 38.4600, 34.7520, "tarih", 75, "08:00", "19:00", 500, "macera"),
        _p("Ortahisar Kalesi", 38.6270, 34.8590, "manzara", 45, "09:00", "19:00", 100, "manzara"),
        _p("Aşk Vadisi", 38.6620, 34.8230, "doga", 120, "06:00", "20:00", 0, "yuruyus,doga,sakin"),
        _p("Kızılçukur Vadisi (Gün Batımı)", 38.6580, 34.8640, "doga", 90, "06:00", "21:00", 0, "gunbatimi,yuruyus"),
        _p("Güvercinlik Vadisi", 38.6340, 34.8150, "doga", 45, "00:00", "23:59", 0, "manzara"),
    ],
    "eskisehir": [
        _p("Odunpazarı Evleri", 39.7638, 30.5263, "mahalle", 90, "00:00", "23:59", 0, "tarih,fotograf,yerel"),
        _p("Odunpazarı Modern Müze (OMM)", 39.7651, 30.5260, "sanat", 75, "10:00", "18:00", 200, "sanat,modern"),
        _p("Kurşunlu Camii ve Külliyesi", 39.7625, 30.5238, "ibadet", 30, "09:00", "18:00", 0, "tarih,sakin"),
        _p("Lületaşı Müzesi", 39.7630, 30.5250, "muze", 30, "09:00", "17:00", 20, "el sanatlari"),
        _p("Porsuk Çayı ve Adalar", 39.7720, 30.5150, "sahil", 75, "00:00", "23:59", 0, "gondol,yerel"),
        _p("Balmumu Heykeller Müzesi", 39.7710, 30.5180, "muze", 45, "10:00", "18:00", 150, "eglence"),
        _p("Haller Gençlik Merkezi", 39.7745, 30.5165, "gece", 60, "10:00", "23:59", 0, "gece,yemek"),
        _p("Kent Park", 39.7700, 30.4970, "doga", 60, "06:00", "23:00", 0, "park,plaj"),
        _p("Sazova Parkı ve Masal Şatosu", 39.7590, 30.4560, "doga", 120, "09:00", "19:00", 0, "aile,fotograf"),
        _p("Sabancı Uzay Evi", 39.7600, 30.4570, "bilim", 60, "10:00", "17:00", 100, "bilim"),
        _p("Eti Arkeoloji Müzesi", 39.7750, 30.5100, "muze", 45, "09:00", "17:00", 30, "arkeoloji,sakin"),
    ],
    "roma": [
        _p("Kolezyum", 41.8902, 12.4922, "tarih", 120, "09:00", "19:00", 900, "ikonik,kalabalik"),
        _p("Forum Romanum", 41.8925, 12.4853, "tarih", 90, "09:00", "19:00", 0, "arkeoloji"),
        _p("Pantheon", 41.8986, 12.4769, "tarih", 40, "09:00", "19:00", 250, "ikonik,mimari"),
        _p("Trevi Çeşmesi", 41.9009, 12.4833, "manzara", 25, "00:00", "23:59", 0, "ikonik,kalabalik"),
        _p("İspanyol Merdivenleri", 41.9060, 12.4828, "manzara", 30, "00:00", "23:59", 0, "kalabalik"),
        _p("Vatikan Müzeleri", 41.9065, 12.4536, "muze", 180, "08:00", "18:00", 1000, "sanat,kalabalik"),
        _p("Aziz Petrus Bazilikası", 41.9022, 12.4539, "ibadet", 75, "07:00", "19:00", 0, "ikonik,mimari"),
        _p("Piazza Navona", 41.8992, 12.4731, "manzara", 40, "00:00", "23:59", 0, "sokak"),
        _p("Trastevere", 41.8897, 12.4700, "mahalle", 120, "00:00", "23:59", 0, "yerel,yemek,gece"),
        _p("Castel Sant'Angelo", 41.9031, 12.4663, "muze", 75, "09:00", "19:30", 800, "manzara"),
        _p("Villa Borghese", 41.9142, 12.4923, "doga", 75, "00:00", "23:59", 0, "park,sakin"),
        _p("Galleria Borghese", 41.9142, 12.4922, "sanat", 120, "09:00", "19:00", 750, "sanat"),
        _p("Campo de' Fiori", 41.8956, 12.4722, "alisveris", 40, "07:00", "14:00", 0, "pazar,yerel"),
    ],
    "paris": [
        _p("Eyfel Kulesi", 48.8584, 2.2945, "manzara", 120, "09:30", "23:00", 1450, "ikonik,kalabalik"),
        _p("Louvre Müzesi", 48.8606, 2.3376, "muze", 180, "09:00", "18:00", 1100, "sanat,kalabalik"),
        _p("Notre-Dame Katedrali", 48.8530, 2.3499, "ibadet", 60, "07:45", "19:00", 0, "ikonik,mimari"),
        _p("Sacré-Cœur Bazilikası", 48.8867, 2.3431, "ibadet", 50, "06:30", "22:30", 0, "manzara"),
        _p("Montmartre", 48.8867, 2.3400, "mahalle", 120, "00:00", "23:59", 0, "sanat,fotograf"),
        _p("Musée d'Orsay", 48.8600, 2.3266, "sanat", 150, "09:30", "18:00", 800, "sanat"),
        _p("Zafer Takı", 48.8738, 2.2950, "manzara", 60, "10:00", "23:00", 800, "ikonik"),
        _p("Champs-Élysées", 48.8698, 2.3076, "alisveris", 75, "00:00", "23:59", 0, "kalabalik,lüks"),
        _p("Lüksemburg Bahçesi", 48.8462, 2.3372, "doga", 60, "07:30", "21:00", 0, "sakin,park"),
        _p("Le Marais", 48.8590, 2.3620, "mahalle", 120, "00:00", "23:59", 0, "yerel,yemek"),
        _p("Sainte-Chapelle", 48.8554, 2.3450, "tarih", 45, "09:00", "19:00", 650, "vitray,sakin"),
    ],
    "barcelona": [
        _p("Sagrada Família", 41.4036, 2.1744, "ibadet", 120, "09:00", "20:00", 1300, "ikonik,kalabalik"),
        _p("Park Güell", 41.4145, 2.1527, "doga", 90, "09:30", "19:30", 500, "gaudi,manzara"),
        _p("Casa Batlló", 41.3916, 2.1649, "sanat", 75, "09:00", "20:00", 1750, "gaudi"),
        _p("La Pedrera", 41.3953, 2.1619, "sanat", 75, "09:00", "20:30", 1250, "gaudi"),
        _p("La Rambla", 41.3809, 2.1735, "alisveris", 60, "00:00", "23:59", 0, "kalabalik"),
        _p("La Boqueria Pazarı", 41.3818, 2.1716, "yemek", 45, "08:00", "20:30", 0, "pazar,yerel"),
        _p("Gotik Mahalle", 41.3833, 2.1777, "mahalle", 120, "00:00", "23:59", 0, "tarih,yerel"),
        _p("Barceloneta Plajı", 41.3784, 2.1925, "sahil", 120, "00:00", "23:59", 0, "plaj"),
        _p("Picasso Müzesi", 41.3852, 2.1810, "sanat", 90, "10:00", "19:00", 750, "sanat"),
        _p("Montjuïc", 41.3636, 2.1580, "manzara", 120, "00:00", "23:59", 0, "manzara,park"),
        _p("Ciutadella Parkı", 41.3881, 2.1873, "doga", 60, "10:00", "22:30", 0, "sakin,park"),
    ],
    "amsterdam": [
        _p("Rijksmuseum", 52.3600, 4.8852, "muze", 150, "09:00", "17:00", 1150, "ikonik,sanat,kalabalik"),
        _p("Van Gogh Müzesi", 52.3584, 4.8811, "sanat", 120, "09:00", "18:00", 1100, "ikonik,kalabalik"),
        _p("Anne Frank Evi", 52.3752, 4.8840, "tarih", 75, "09:00", "22:00", 800, "ikonik"),
        _p("Vondelpark", 52.3580, 4.8686, "doga", 60, "00:00", "23:59", 0, "sakin,park"),
        _p("Jordaan", 52.3740, 4.8800, "mahalle", 90, "00:00", "23:59", 0, "yerel,fotograf"),
        _p("Dam Meydanı ve Kraliyet Sarayı", 52.3731, 4.8913, "tarih", 60, "10:00", "17:00", 625, "kalabalik"),
        _p("Kanal Turu", 52.3780, 4.9000, "manzara", 75, "09:00", "22:00", 900, "tekne,fotograf"),
        _p("A'DAM Lookout", 52.3843, 4.9019, "manzara", 60, "10:00", "22:00", 900, "manzara"),
        _p("Albert Cuyp Pazarı", 52.3557, 4.8946, "alisveris", 60, "09:00", "17:00", 0, "pazar,yerel,yemek"),
        _p("NEMO Bilim Müzesi", 52.3740, 4.9124, "bilim", 120, "10:00", "17:30", 975, "aile"),
        _p("Begijnhof", 52.3693, 4.8901, "tarih", 30, "09:00", "17:00", 0, "sakin"),
        _p("Çiçek Pazarı (Bloemenmarkt)", 52.3667, 4.8916, "alisveris", 30, "09:00", "17:30", 0, "fotograf"),
    ],
}


def _r(isim, lat, lon, fiyat, mutfak):
    return {"isim": isim, "lat": lat, "lon": lon, "fiyat": fiyat, "mutfak": mutfak}


RESTORAN = {
    "istanbul": [
        _r("Tarihi Sultanahmet Köftecisi", 41.0080, 28.9770, "ekonomik", "köfte"),
        _r("Hamdi Restaurant", 41.0165, 28.9715, "orta", "kebap"),
        _r("Karaköy Lokantası", 41.0230, 28.9780, "orta", "Türk mutfağı"),
        _r("Çiya Sofrası", 40.9905, 29.0253, "orta", "Anadolu mutfağı"),
        _r("Pandeli", 41.0167, 28.9705, "luks", "Osmanlı mutfağı"),
        _r("Mikla", 41.0315, 28.9745, "luks", "modern Türk"),
        _r("Zencefil", 41.0347, 28.9789, "orta", "vejetaryen ev yemekleri"),
        _r("Bi Nevi Deli", 41.0800, 29.0350, "orta", "vegan & vejetaryen"),
        _r("Kadıköy Fıccın", 40.9890, 29.0270, "ekonomik", "Kafkas mutfağı"),
    ],
    "ankara": [
        _r("Uludağ Kebapçısı", 39.9410, 32.8560, "orta", "İskender"),
        _r("Kınacızade Konağı", 39.9352, 32.8628, "orta", "Türk mutfağı"),
        _r("Zenger Paşa Konağı", 39.9405, 32.8640, "orta", "Ankara mutfağı"),
        _r("Trilye", 39.8950, 32.8620, "luks", "balık"),
    ],
    "izmir": [
        _r("Kemeraltı Boyozcusu", 38.4190, 27.1310, "ekonomik", "boyoz & gevrek"),
        _r("Veli Usta Meze", 38.4350, 27.1400, "orta", "Ege mezeleri"),
        _r("Sakız Restaurant", 38.4330, 27.1420, "luks", "deniz ürünleri"),
    ],
    "antalya": [
        _r("Piyazcı Ahmet", 36.8870, 30.7020, "ekonomik", "piyaz & şiş köfte"),
        _r("Vanilla", 36.8840, 30.7050, "luks", "Akdeniz"),
        _r("Club Arma", 36.8850, 30.7040, "luks", "deniz ürünleri"),
    ],
    "kapadokya": [
        _r("Fırın Express", 38.6430, 34.8300, "ekonomik", "testi kebabı & pide"),
        _r("Topdeck Cave Restaurant", 38.6430, 34.8290, "orta", "ev yemekleri"),
        _r("Seki Restaurant", 38.6300, 34.8060, "luks", "modern Anadolu"),
    ],
    "eskisehir": [
        _r("Odunpazarı çibörek salonu", 39.7645, 30.5255, "ekonomik", "Tatar mutfağı (çibörek)"),
        _r("Porsuk kenarı balaban köfteci", 39.7725, 30.5160, "ekonomik", "balaban köfte"),
        _r("Odunpazarı konak restoranı", 39.7640, 30.5270, "orta", "yöresel mutfak"),
    ],
    "roma": [
        _r("Pizzarium", 41.9070, 12.4470, "ekonomik", "pizza al taglio"),
        _r("Da Enzo al 29", 41.8885, 12.4770, "orta", "Roma mutfağı"),
        _r("Armando al Pantheon", 41.8985, 12.4765, "orta", "Roma mutfağı"),
        _r("Roscioli", 41.8940, 12.4730, "luks", "İtalyan"),
    ],
    "paris": [
        _r("Bouillon Chartier", 48.8720, 2.3430, "ekonomik", "Fransız klasikleri"),
        _r("L'As du Fallafel", 48.8573, 2.3590, "ekonomik", "falafel"),
        _r("Le Comptoir du Relais", 48.8520, 2.3390, "orta", "bistro"),
        _r("Le Train Bleu", 48.8447, 2.3730, "luks", "Fransız"),
    ],
    "barcelona": [
        _r("La Cova Fumada", 41.3790, 2.1890, "ekonomik", "tapas"),
        _r("El Xampanyet", 41.3843, 2.1820, "orta", "tapas & cava"),
        _r("Cervecería Catalana", 41.3920, 2.1610, "orta", "tapas"),
        _r("Bar Cañete", 41.3800, 2.1720, "luks", "Katalan"),
    ],
    "amsterdam": [
        _r("The Pancake Bakery", 52.3767, 4.8835, "ekonomik", "Hollanda pankeki"),
        _r("Foodhallen", 52.3667, 4.8697, "orta", "sokak lezzetleri (vejetaryen seçenekli)"),
        _r("Moeders", 52.3718, 4.8774, "orta", "Hollanda mutfağı"),
        _r("De Kas", 52.3550, 4.9330, "luks", "sera mutfağı, vejetaryen menü"),
    ],
}

# Ayrıntılı veri tabanı olan 10 pilot destinasyon — İstanbul ana pilot şehir
PILOT_DESTINASYONLAR = ["İstanbul", "Ankara", "İzmir", "Antalya", "Kapadokya", "Eskişehir",
                        "Roma", "Paris", "Barcelona", "Amsterdam"]

# Şehir fiyat çarpanı (İstanbul ≈ 1.3, Ankara = 1.0 taban) — maliyet ajanının çıpası
SEHIR_CARPAN = {
    "istanbul": 1.3, "ankara": 1.0, "izmir": 1.1, "antalya": 1.15, "kapadokya": 1.2,
    "eskisehir": 0.9, "bodrum": 1.4, "cesme": 1.3, "trabzon": 0.95, "bursa": 0.95,
    "paris": 2.8, "londra": 3.0, "amsterdam": 2.5, "roma": 2.3, "barcelona": 2.2,
    "prag": 1.6, "budapeste": 1.5, "atina": 1.8, "viyana": 2.3, "dubai": 3.5,
    "tokyo": 2.8, "bangkok": 1.4, "new york": 3.5, "tiflis": 1.1, "berlin": 2.3,
    "lizbon": 1.9, "madrid": 2.0, "saraybosna": 1.0, "uskup": 0.9, "baku": 1.2,
}

YURTDISI = {"paris", "londra", "amsterdam", "roma", "barcelona", "prag", "budapeste", "atina",
            "viyana", "dubai", "tokyo", "bangkok", "new york", "tiflis", "berlin", "lizbon",
            "madrid", "saraybosna", "uskup", "baku"}

_TAKMA = {"rome": "roma", "kapadokya": "kapadokya", "cappadocia": "kapadokya", "goreme": "kapadokya",
          "nevsehir": "kapadokya", "london": "londra", "prague": "prag", "athens": "atina",
          "vienna": "viyana", "budapest": "budapeste", "tbilisi": "tiflis", "lisbon": "lizbon",
          "barselona": "barcelona", "barcelona": "barcelona", "stanbul": "istanbul", "constantinople": "istanbul",
          "smyrna": "izmir", "ephesus": "izmir", "efes": "izmir", "alanya": "antalya", "kemer": "antalya",
          "urgup": "kapadokya", "uchisar": "kapadokya", "odunpazari": "eskisehir"}


# Ülke yazılırsa planın kurulacağı üs şehir (birkaç günlük gezide tek şehir mantıklıdır)
ULKE_BAZ = {
    "ispanya": "Barcelona", "spain": "Barcelona", "katalonya": "Barcelona", "hollanda": "Amsterdam",
    "marmara": "İstanbul", "ege": "İzmir", "akdeniz": "Antalya", "ic anadolu": "Ankara",
    "orta anadolu": "Ankara", "toskana": "Floransa", "italya": "Roma", "italy": "Roma",
    "fransa": "Paris", "france": "Paris", "yunanistan": "Atina", "greece": "Atina",
    "ingiltere": "Londra", "birlesik krallik": "Londra", "england": "Londra", "almanya": "Berlin",
    "germany": "Berlin", "hollanda": "Amsterdam", "netherlands": "Amsterdam", "portekiz": "Lizbon",
    "portugal": "Lizbon", "japonya": "Tokyo", "japan": "Tokyo", "cekya": "Prag", "czechia": "Prag",
    "cek cumhuriyeti": "Prag", "macaristan": "Budapeşte", "hungary": "Budapeşte", "avusturya": "Viyana",
    "austria": "Viyana", "gurcistan": "Tiflis", "georgia": "Tiflis", "fas": "Marakeş", "morocco": "Marakeş",
    "birlesik arap emirlikleri": "Dubai", "bae": "Dubai", "tayland": "Bangkok", "thailand": "Bangkok",
    "abd": "New York", "amerika": "New York", "usa": "New York", "turkiye": "İstanbul", "turkey": "İstanbul",
    "azerbaycan": "Bakü", "bosna hersek": "Saraybosna", "kuzey makedonya": "Üsküp", "isvicre": "Zürih",
    "belcika": "Brüksel", "polonya": "Krakow", "hirvatistan": "Dubrovnik", "misir": "Kahire",
    "endonezya": "Bali", "danimarka": "Kopenhag", "isvec": "Stockholm",
}


def hedef_coz(girdi: str) -> dict:
    """Kullanıcının yazdığı hedefi çözer: şehir mi, ülke mi?
    Dönüş: {"tur": "sehir"|"ulke", "sehir": plan kurulacak şehir ya da None (LLM seçsin)}."""
    n = normalize(girdi).split(",")[0].strip()
    if n in ULKE_BAZ:
        return {"tur": "ulke", "sehir": ULKE_BAZ[n]}
    anahtar = sehir_anahtari(girdi)
    if anahtar in POI:      # pilot destinasyon: düzgün yazımıyla döndür ("istanbul" → "İstanbul")
        return {"tur": "sehir", "sehir": next(d for d in PILOT_DESTINASYONLAR if sehir_anahtari(d) == anahtar)}
    if anahtar or _ag_kapali():
        return {"tur": "sehir", "sehir": girdi}
    try:   # listede olmayan bir ülke/bölge mi? (Nominatim adres türü)
        url = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&addressdetails=1&q="
               + urllib.parse.quote(girdi))
        with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=6) as r:
            data = json.loads(r.read())
        if data and data[0].get("addresstype") in ("country", "state", "region"):
            return {"tur": "ulke", "sehir": None}
    except Exception:
        pass
    return {"tur": "sehir", "sehir": girdi}


def sehir_anahtari(sehir: str) -> str | None:
    """'İstanbul', 'istanbul, Türkiye', 'Rome' → bilgi tabanı anahtarı."""
    n = normalize(sehir).split(",")[0].strip()
    if not n:
        return None
    if n in _TAKMA:
        return _TAKMA[n]
    for k in list(POI) + list(SEHIR_CARPAN):
        if n == k or n.startswith(k) or k.startswith(n):
            return k
    for kelime in n.split():
        if kelime in _TAKMA:
            return _TAKMA[kelime]
        if kelime in POI or kelime in SEHIR_CARPAN:
            return kelime
    return None


def sehir_carpani(sehir: str) -> float:
    k = sehir_anahtari(sehir)
    return SEHIR_CARPAN.get(k, 1.0) if k else 1.0


def yurtdisi_mi(sehir: str) -> bool:
    k = sehir_anahtari(sehir)
    return bool(k and k in YURTDISI)


def yerel_poi(sehir: str) -> list:
    k = sehir_anahtari(sehir)
    return [dict(p) for p in POI.get(k, [])] if k else []


def yerel_restoran(sehir: str) -> list:
    k = sehir_anahtari(sehir)
    return [dict(r) for r in RESTORAN.get(k, [])] if k else []


# ---------------------------------------------------------------------------
# OpenStreetMap — listede olmayan şehirler ve koordinat doğrulama
# ---------------------------------------------------------------------------

_UA = {"User-Agent": "SmartTravelAI/2.0 (egitim projesi)"}


def _ag_kapali() -> bool:
    return os.getenv("SMARTTRAVEL_OFFLINE") == "1"


def sehir_koordinati(sehir: str, timeout: float = 6.0) -> dict | None:
    yerel = yerel_poi(sehir)
    if yerel:
        return {"lat": sum(p["lat"] for p in yerel) / len(yerel),
                "lon": sum(p["lon"] for p in yerel) / len(yerel)}
    if _ag_kapali():
        return None
    try:
        url = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&q="
               + urllib.parse.quote(sehir))
        with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout) as r:
            data = json.loads(r.read())
        if data:
            return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    except Exception:
        pass
    return None


_OSM_KATEGORI = [
    ("tourism", "museum", "muze", 90), ("tourism", "gallery", "sanat", 60),
    ("tourism", "viewpoint", "manzara", 30), ("tourism", "attraction", "tarih", 60),
    ("historic", "castle", "tarih", 75), ("historic", "monument", "tarih", 30),
    ("historic", "ruins", "tarih", 60), ("historic", "memorial", "tarih", 20),
    ("amenity", "place_of_worship", "ibadet", 30), ("leisure", "park", "doga", 45),
]


def osm_poi(sehir: str, yaricap_m: int = 6000, limit: int = 30, timeout: float = 20.0) -> list:
    """Overpass API ile şehrin isimli turistik noktalarını çeker (ücret/saat bilinmez)."""
    merkez = sehir_koordinati(sehir)
    if not merkez or _ag_kapali():
        return []
    lat, lon = merkez["lat"], merkez["lon"]
    parcalar = []
    for anahtar, deger, _, _ in _OSM_KATEGORI:
        parcalar.append(f'nwr(around:{yaricap_m},{lat},{lon})["{anahtar}"="{deger}"]["name"];')
    sorgu = f"[out:json][timeout:{int(timeout)}];({''.join(parcalar)});out center 120;"
    try:
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=urllib.parse.urlencode({"data": sorgu}).encode(), headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout + 5) as r:
            data = json.loads(r.read())
    except Exception:
        return []
    sonuc, gorulen = [], set()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        ad = tags.get("name:tr") or tags.get("name")
        plat = el.get("lat") or el.get("center", {}).get("lat")
        plon = el.get("lon") or el.get("center", {}).get("lon")
        if not ad or plat is None or normalize(ad) in gorulen:
            continue
        kat, sure = "tarih", 45
        for anahtar, deger, k, s in _OSM_KATEGORI:
            if tags.get(anahtar) == deger:
                kat, sure = k, s
                break
        # Wikidata/Wikipedia bağlantısı olanlar genelde daha önemli yerlerdir
        onem = 2 if ("wikidata" in tags or "wikipedia" in tags) else 1
        gorulen.add(normalize(ad))
        # OSM opening_hours biçimi karmaşık; güvenli varsayılan pencere kullanılır
        sonuc.append({**_p(ad, float(plat), float(plon), kat, sure, "09:00", "18:00", 0, "osm"),
                      "_onem": onem})
    sonuc.sort(key=lambda p: -p["_onem"])
    for p in sonuc:
        p.pop("_onem", None)
    return sonuc[:limit]
