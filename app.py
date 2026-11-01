# app.py — SmartTravel AI

import os
import html as _html
import streamlit as st
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from agents import MBTIAgent
from db import (
    register_user, login_user, get_user_profile,
    update_user_mbti, save_travel_history, delete_travel_plan,
)
import memory
from multiagent import Orkestrator, hafizaya_kaydet
from plan_render import (
    gunluk_html, seyahat_notu_karti, KATEGORI_ETIKET,
    plan_ozet_html, butce_dokum_html, restoran_listesi_html, yedek_yerler_html, ipuclari_html,
    ilerleme_paneli_html,
)
import google_maps
import hava
import hazirlik
import poi_data
from poi_data import PILOT_DESTINASYONLAR

st.set_page_config(
    page_title="SmartTravel AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Genel ── */
*, *::before, *::after {
    font-family: 'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif !important;
}
/* Streamlit simgeleri (expander oku vb.) kendi simge fontunu kullanmalı; yoksa "arrow_down" yazısı görünür */
[data-testid="stIconMaterial"], span[class*="material-symbols"], .material-symbols-rounded {
    font-family: 'Material Symbols Rounded' !important;
}
[data-testid="stAppViewContainer"] { background: #dce9f4; }
/* ── Tatil Listesi (uygulama paletinde) ── */
.st-key-tatil_listesi { background:#fffefb; border:1px solid #e8dfd4; border-radius:16px; padding:22px 22px 14px; }
.st-key-tatil_listesi .tl-ust { display:flex; justify-content:space-between; align-items:flex-end; gap:12px;
    border-bottom:1px solid #efe8de; padding-bottom:14px; margin-bottom:16px; }
.st-key-tatil_listesi .tl-ust-etiket { font-size:10px; font-weight:800; color:#8b7355; text-transform:uppercase; letter-spacing:.7px; }
.st-key-tatil_listesi .tl-baslik { font-size:22px; font-weight:800; color:#2c2416; letter-spacing:-.3px; margin-top:3px; }
.st-key-tatil_listesi .tl-alt { font-size:12px; color:#7a6a5a; margin-top:2px; }
.st-key-tatil_listesi .tl-kart-baslik { display:flex; align-items:center; gap:9px; margin-bottom:8px; }
.st-key-tatil_listesi .tl-ikon { width:28px; height:28px; border-radius:8px; display:flex; align-items:center;
    justify-content:center; font-size:14px; flex-shrink:0; }
.st-key-tatil_listesi .tl-etiket { font-size:10.5px; font-weight:800; color:#2c2416; text-transform:uppercase; letter-spacing:.6px; }
.st-key-tatil_listesi .tl-sayac { margin-left:auto; font-size:11px; font-weight:700; color:#8b7355;
    background:#f2ede6; border-radius:20px; padding:2px 9px; }
.st-key-tatil_listesi .tl-alt-yazi { text-align:center; color:#b5a99a; font-size:11px; font-weight:700;
    text-transform:uppercase; letter-spacing:1px; margin-top:10px; }
.st-key-tatil_listesi [class*="st-key-tlkart_"] { background:#faf8f5; border:1px solid #e8dfd4; border-radius:12px;
    padding:14px 16px 8px; }
.st-key-tatil_listesi [data-testid="stCheckbox"] p { font-size:13px !important; color:#3a2f24 !important; }
.st-key-tatil_listesi [data-testid="stCheckbox"] { margin-bottom:-8px; }
.st-key-tatil_listesi textarea { font-size:13px !important; background:#fffefb !important;
    border:1px solid #e8dfd4 !important; border-radius:8px !important; }
/* Gezi sonrası yorum kartı */
.yorum-notu { font-size: 12.5px; color: #6b5a48; line-height: 1.7; background: #f8f4ee;
              border: 1px solid #ece3d7; border-radius: 10px; padding: 10px 14px; margin-bottom: 10px; }
[data-testid="stMain"] > div { background: transparent !important; }
[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 28px 32px 32px !important; max-width: 100% !important; }

/* ── Sol Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="collapsedControl"] {
    background: #16213e !important; color: white !important;
    border-radius: 0 8px 8px 0 !important;
}
[data-testid="stSidebar"] .stMarkdown { margin: 0 !important; padding: 0 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.07) !important; margin: 0 !important; }

/* Nav butonlar — genel */
[data-testid="stSidebar"] .stButton > button {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
    background: transparent !important;
    color: rgba(255,255,255,0.52) !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    border-radius: 0 10px 10px 0 !important;
    text-align: left !important;
    width: 100% !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.2px !important;
    padding: 11px 16px 11px 13px !important;
    margin: 2px 0 !important;
    transition: background 0.18s, color 0.18s, border-color 0.18s !important;
    box-shadow: none !important;
    justify-content: flex-start !important;
    line-height: 1.45 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.08) !important;
    color: rgba(255,255,255,0.88) !important;
    border-left-color: rgba(212,151,106,0.45) !important;
}
/* Aktif nav öğesi — aria-label "▶" ile başlar */
[data-testid="stSidebar"] .stButton > button[aria-label^="▶"] {
    background: rgba(212,151,106,0.18) !important;
    color: #f5dfc6 !important;
    font-weight: 700 !important;
    border-left: 3px solid #d4976a !important;
    letter-spacing: 0.25px !important;
}
[data-testid="stSidebar"] .stButton > button[aria-label^="▶"]:hover {
    background: rgba(212,151,106,0.24) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c4b5a0; border-radius: 3px; }

/* ── Genel butonlar ── */
.stButton > button {
    font-family: 'Inter', -apple-system, sans-serif !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border: none !important;
    transition: all 0.15s !important;
    letter-spacing: 0.1px !important;
}
.stButton > button[kind="primary"] { background: #4f46e5 !important; color: white !important; }
.stButton > button[kind="primary"]:hover {
    background: #4338ca !important;
    box-shadow: 0 4px 12px rgba(79,70,229,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important; color: #374151 !important; border: 1px solid #e5e7eb !important;
}
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    font-family: 'Inter', sans-serif !important;
    border-radius: 8px !important; border: 1px solid #e5e7eb !important;
    background: white !important; font-size: 13px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #8b7355 !important;
    box-shadow: 0 0 0 3px rgba(139,115,85,0.12) !important;
}
.stFormSubmitButton > button {
    background: #4f46e5 !important; color: white !important;
    border-radius: 8px !important; font-weight: 700 !important;
    font-size: 13.5px !important; letter-spacing: 0.2px !important;
    padding: 0.5rem 1.5rem !important; width: 100% !important;
}
.stFormSubmitButton > button:hover { background: #4338ca !important; }
[data-testid="metric-container"] {
    background: white; border: 1px solid #e5e7eb;
    border-radius: 12px; padding: 16px !important;
}
.streamlit-expanderHeader {
    font-family: 'Inter', sans-serif !important;
    background: white !important; border: 1px solid #e5e7eb !important;
    border-radius: 8px !important; font-weight: 600 !important; color: #374151 !important;
}
.stAlert { border-radius: 10px !important; }
.stTabs [data-baseweb="tab-list"] { gap: 2px !important; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; font-size: 12.5px !important;
    color: #6b7280 !important; border-radius: 8px 8px 0 0 !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] { color: #2c2416 !important; font-weight: 700 !important; }
.stRadio > div { gap: 6px; }
.stRadio > div > label {
    font-family: 'Inter', sans-serif !important;
    background: white; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 8px 12px !important; cursor: pointer; transition: all 0.1s;
    font-size: 13px !important;
}
.stRadio > div > label:hover { border-color: #8b7355; }
.stRadio > div > label:has(input:checked) {
    border-color: #4f46e5 !important;
    background: #eef2ff !important;
    box-shadow: 0 0 0 1px #4f46e5 inset;
}
.stRadio > div > label:has(input:checked) p { color: #3730a3 !important; font-weight: 700 !important; }

hr { border-color: #e5e7eb !important; margin: 1rem 0 !important; }

/* ── page_header tutarlılığı ── */
h1, h2, h3 {
    font-family: 'Inter', -apple-system, sans-serif !important;
    letter-spacing: -0.3px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
_defaults = {
    "logged_in": False, "username": "",
    "user_data": {}, "mbti_completed": False,
    "mbti_report": "", "mbti_archetype": "",
    "travel_history": [], "last_plan": None,
    "last_t_data": None, "current_tab": 0,
    "_profil_yuklendi": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── MBTI veri tabloları ────────────────────────────────────────────────────────
MBTI_SEYAHAT = {
    "INTJ": {"tercih": "Derin planlama, tarihi alanlar, soliter kültür turları", "kac": "Kalabalık gruplar, spontane değişiklikler, gövde gösterisi turları", "ideal": "Japonya çay seremonisi, Roma müzeleri, Edinburgh kalesi", "renk": "#6d28d9"},
    "INTP": {"tercih": "Bilim müzesi, arkeoloji, sessiz doğal alanlar, kütüphaneler", "kac": "Plaj partileri, yüksek sesli mekanlar, kalabalık alışveriş", "ideal": "Atina Akropolü, Krakow tarihi merkez, İzlanda fiyortları", "renk": "#7c3aed"},
    "ENTJ": {"tercih": "Verimli rota, business sınıf, lüks otel, liderlik turları", "kac": "Organizasyonsuz geziler, hostel, uzun bekleme", "ideal": "Singapur, Zürih, Tokyo iş merkezi", "renk": "#4338ca"},
    "ENTP": {"tercih": "Yeni fikirler, tartışma kafeleri, startup sahnesi, farklı kültürler", "kac": "Rutin turist rotaları, tur rehberi, kısıtlayıcı programlar", "ideal": "Berlin sanat sahnesi, İstanbul agorası, Amsterdam", "renk": "#2563eb"},
    "INFJ": {"tercih": "Anlamlı deneyimler, yerel halk ile tanışma, manevi mekanlar", "kac": "Yüzeysel turist noktaları, kalabalık, gürültü", "ideal": "Hindistan ashram, Kyoto tapınakları, Fas medina", "renk": "#0891b2"},
    "INFP": {"tercih": "Romantik şehirler, edebiyat turları, doğal ortamlar, sanat", "kac": "Kalabalık turistik mekanlar, zaman baskısı, katı program", "ideal": "Edinburgh, Prag, Yeni Zelanda doğası", "renk": "#0d9488"},
    "ENFJ": {"tercih": "Kültür takası, topluluk deneyimleri, rehberli turlar, insanlarla bağlanma", "kac": "Yalnız uzlet, kuvvetli tur programı", "ideal": "Brezilya karnavalı, Hindistan kültür turları, Gana", "renk": "#059669"},
    "ENFP": {"tercih": "Spontane keşifler, festival, yerel pazar, yeni insanlar", "kac": "Katı programlar, standart otel, tekrar eden rotalar", "ideal": "Tayland festivalleri, Marakeş meydanı, Barselona", "renk": "#65a30d"},
    "ISTJ": {"tercih": "Planlı ve organize, tarihi mekanlar, müzeler, güvenilir ulaşım", "kac": "Son dakika değişiklikler, belirsizlik, hostel kaos", "ideal": "Viyana, Londra müze turu, Japonya trenleri", "renk": "#ca8a04"},
    "ISFJ": {"tercih": "Güvenli, rahat, aile dostu mekanlar, geleneksel yemekler", "kac": "Riskli maceralar, bilinmezlik, kalabalık gece hayatı", "ideal": "Provence Fransa, Toskana köyü, Yeni Zelanda", "renk": "#d97706"},
    "ESTJ": {"tercih": "Verimli program, lüks otel, organize turlar, önem verilen mekanlar", "kac": "Kaos ve plansızlık, kirli mekanlar, zaman kaybı", "ideal": "Viyana opera, Londra iş merkezi, Singapur", "renk": "#dc2626"},
    "ESFJ": {"tercih": "Aile tatilleri, sosyal aktiviteler, hoş restoranlar, fotoğraflık noktalar", "kac": "Yalnızlık, sert koşullar, soğuk mekanlar", "ideal": "Paris romantik turu, Bali tatil köyü, Santorini", "renk": "#e11d48"},
    "ISTP": {"tercih": "Macera sporları, mekanik teknik turlar, dağ, doğa kampı", "kac": "Kalabalık şehir merkezleri, organize turlar, sosyal zorunluluk", "ideal": "Norveç dağ trekkingi, Moğolistan step, Patagonya", "renk": "#0284c7"},
    "ISFP": {"tercih": "Sanat galerileri, doğada yürüyüş, yerel el sanatları, sessiz kafeler", "kac": "Soğuk konferans tarzı turlar, kalabalık alışveriş merkezleri", "ideal": "Floransa sanat turu, Bali Ubud, Oaxaca Meksika", "renk": "#7c3aed"},
    "ESTP": {"tercih": "Aksiyon sporları, gece hayatı, hızlı şehir keşifleri, macera parkları", "kac": "Müze saatleri, yavaş tempolu turlar, kültürel zorunluluklar", "ideal": "Dubai, Las Vegas, Bangkok gece hayatı", "renk": "#ea580c"},
    "ESFP": {"tercih": "Festival, plaj, sosyal etkinlikler, dans, canlı müzik", "kac": "Sakin ve izole mekanlar, uzun müze turları, yalnız gezi", "ideal": "Rio karnavalı, İbiza, Bali festivalleri", "renk": "#db2777"},
}

MBTI_BLOG = {
    "INTJ": "INTJ'ler seyahat ederken her ayrıntıyı önceden planlar, kaostan nefret ederler. Popüler alışveriş mağazaları onlar için zaman kaybıdır; antik kentleri, felsefi derinliği olan müzeleri ve sessiz doğa rotalarını tercih ederler.",
    "INTP": "INTP'ler seyahati çözülmesi gereken bir bilim projesi gibi görürler. Arkeolojik kazı alanları, bilim merkezleri ve kütüphaneler onları büyüler. Katı seyahat planlarından nefret ederler.",
    "ENTJ": "ENTJ'ler tatilde bile verimlilik ve stratejik planlama ararlar. Prestijli destinasyonları, lüks otelleri ve dünya standartlarında hizmet veren mekanları seçerler.",
    "ENTP": "ENTP'ler rutin tatil rotalarını reddeden vizyon avcılarıdır. Startup kültürünün yoğun olduğu şehirleri, entelektüel tartışma kafelerini ve alternatif sanat galerilerini tercih ederler.",
    "INFJ": "INFJ'ler için seyahat, içsel ve ruhsal bir derinleşme yolculuğudur. Yerel halkın yaşamına karışabilecekleri otantik mahalleleri ve sessiz doğa köşelerini severler.",
    "INFP": "INFP'ler her şehirde bir masalın izini süren romantik gezginlerdir. Ünlü yazarların vakit geçirdiği tarihi kafeler, eski kitapçılar ve bohem mahalleler onlar için cennettir.",
    "ENFJ": "ENFJ'ler her destinasyonda insanları bir araya getiren rehberlerdir. Kültür takasının yapıldığı festivaller, yerel halk dansları ve sokak tiyatroları onları besler.",
    "ENFP": "ENFP'ler için seyahat, tüm planları yırtıp spontane hareket etmek demektir. Sokak müzisyenleri, renkli lokal pazarlar ve enerjik festivaller tam onlara göredir.",
    "ISTJ": "ISTJ'ler için mükemmel seyahat, milimetrik düzen ve önceden test edilmiş bir programa bağlıdır. Tarihi mekanları ve belgelenmiş anıtları özenle araştırırlar.",
    "ISFJ": "ISFJ'ler güvenli, sıcak ve aile dostu ortamlar ararlar. Nostaljik eski kasabaları ve huzurlu sahil köylerini tercih ederler.",
    "ESTJ": "ESTJ'ler seyahatin her anında tam kontrol sağlamak isteyen gerçek organizatörlerdir. Net şekilde organize şehir turlarını ve tarihi anıtları checklist mantığıyla gezerler.",
    "ESFJ": "ESFJ'ler seyahati sosyal paylaşım ve kolektif eğlence aracı olarak görürler. Şehrin en canlı caddelerini, fotojenik meydanları ve eğlenceli turistik mekanları severler.",
    "ISTP": "ISTP'ler fiziksel aksiyonu ve doğanın zorluklarıyla mücadeleyi seven özgür kaşiflerdir. Dağ trekkingi, kamp ve motosikletle bilinmeyen yollara sapmak tam onların tatil tanımıdır.",
    "ISFP": "ISFP'ler dünyayı gözleri ve kalpleriyle hisseden estetik duyarlılığı yüksek sanatçı gezginlerdir. Yerel sanat galerileri, el sanatları atölyeleri ve mimari estetiği olan eski sokaklar onları büyüler.",
    "ESTP": "ESTP'ler için durağan bir tatil tam anlamıyla bir kabustur. Adrenalin dolu macera sporları, sabaha kadar süren gece hayatı ve hızlı şehir keşifleri onların kan grubudur.",
    "ESFP": "ESFP'ler ayak bastıkları her destinasyonu devasa bir eğlence sahnesine dönüştüren hayat dolu turistlerdir. Büyük müzik festivalleri, plaj partileri ve karnavallar onların seyahat dilidir.",
}

MBTI_DESTINASYONLAR = {
    "INTJ": {
        "ozet": "INTJ'ler için ideal seyahat, derin hazırlık ve stratejik bir bakış açısı gerektirir. Kalabalıktan uzak, entelektüel uyarım sağlayan ve tarihin mimariye yansıdığı destinasyonlar bu tipin ruhuna en çok hitap eder.",
        "sehirler": [
            {"isim": "Kyoto, Japonya", "neden": "Kyoto, yüzyıllar boyu Japon imparatorluğunun merkezi olmuştur. INTJ'ler için Fushimi Inari'nin sabah erken ıssız gezilmesi, Ryoanji kum bahçesinde sessiz meditasyon ve wabi-sabi estetiği mükemmel bir entelektüel uğraştır."},
            {"isim": "Edinburgh, İskoçya", "neden": "Karanlık ortaçağ tarihi, volkanik kayalıklar üzerinde yükselen kale ve dünya edebiyat festivali ile INTJ'lere derinden dokunan bir şehirdir. Arthur's Seat solo yürüyüşü şehre hâkim bir bakış sunar."},
            {"isim": "Viyana, Avusturya", "neden": "Viyana'nın entelektüel ağırlığı eşsizdir: Freud'un muayenehanesi, Klimt'in altın yaprakları ve Habsburg arşivleri aynı şehirdedir. Kafeler burada yüzyıllık entelektüel bir geleneği taşır."},
            {"isim": "Reykjavik, İzlanda", "neden": "Jeotermal alanlar, buzullar ve aurora borealis — bu doğal fenomenleri bilimsel bağlamda derinlemesine anlamak INTJ için seyahatin ta kendisidir. İzlanda'nın sessiz sosyal kültürü enerji tüketimini minimumda tutar."},
            {"isim": "Prag, Çek Cumhuriyeti", "neden": "Kafka'nın labirentimsi sokaklara yansıyan varoluşsal estetiği ve Bohemya'nın felsefi tarihi INTJ'leri büyüler. Josefov ve Vyšehrad günler süren araştırma programı oluşturur."},
        ],
    },
    "INTP": {
        "ozet": "INTP'ler seyahati çözülmesi gereken bir bilim projesi olarak yaşar. Arkeolojik derinlik, bilimsel fenomenler ve entelektüel uyarımın yüksek olduğu destinasyonlar önerilmiştir.",
        "sehirler": [
            {"isim": "Atina, Yunanistan", "neden": "Batı uygarlığının felsefi temelleri Atina'da somut biçimde yaşar. Akropolis açılışında kalabalık olmadan gezilmesi ve agora'da Sokrates'in izinden yürümek INTP için soyut düşünceleri mekâna bağlayan bir deneyimdir."},
            {"isim": "Krakow, Polonya", "neden": "Wieliczka tuz madeninin 700 yıllık mühendislik tarihi ve Wawel kalesi'nin çok katmanlı mimarisi INTP'leri büyüler. Üniversite kenti enerjisi ve ucuz kahve fiyatları bu tipin bütçesine uyar."},
            {"isim": "İzlanda Hinterland", "neden": "İzlanda'nın iç kesimleri INTP için adeta canlı bir bilim laboratuvarıdır. Ring Road'da kendi hızında ilerleyen bir solo sürüş, her noktada durma ve araştırma özgürlüğü sunar."},
            {"isim": "Singapur", "neden": "Singapur, INTP'nin sistem odaklı düşüncesine hitap eder. Lojistik mükemmeliyeti, çok katmanlı etnik yapısı ve Gardens by the Bay'in biyo-mühendislik harikası bu tipi büyüler."},
            {"isim": "Berlin, Almanya", "neden": "Holocaust Anıtı, Stasi Müzesi ve Topography of Terror ile 20. yüzyılın en dürüst tarihsel yüzleşmesi Berlin'dedir. Kesintisiz gelişen sanat ve teknoloji sahnesi farklı sistemlerin birlikteliğini gösterir."},
        ],
    },
    "ENTJ": {
        "ozet": "ENTJ'ler için seyahat, prestij, verimlilik ve güçlü bir anlatı gerektirir. Liderlik tarihinin iz bıraktığı metropoller ve dünya standartlarında hizmet sunan destinasyonlar bu tip için idealdir.",
        "sehirler": [
            {"isim": "Singapur", "neden": "Bir şehir devletinin nasıl global ekonomik güç hâline gelebildiğini somutlaştıran en çarpıcı örnektir. Marina Bay Sands, finans bölgesi gökdelenleri ve Changi Havalimanı'nın kusursuz lojistiği ENTJ için ilham kaynağıdır."},
            {"isim": "Tokyo, Japonya", "neden": "Metropol organizasyonunun zirvesi: dakikası dakikasına çalışan trenler, Michelin yıldızlı restoran yoğunluğu ve iş çevrelerinin derinliği ENTJ'nin verimliliğe duyduğu hayranlıkla örtüşür."},
            {"isim": "Zürih, İsviçre", "neden": "Küresel finans, saat mühendisliği ve temiz kentsel yaşamın simgesidir. Bahnhofstrasse'nin lüks mağazaları ve İsviçre finansal sisteminin derinliği ENTJ için seçici bir ayrıcalık işaretidir."},
            {"isim": "New York, ABD", "neden": "Wall Street'in tarihsel anlatısı, Broadway'in profesyonellik standartları ve Met'in koleksiyon derinliği bu tipin farklı boyutlarına hitap eder. Şehrin 'ya büyürsün ya çekilirsin' felsefesi ENTJ ile rezonans kurar."},
            {"isim": "Dubai, BAE", "neden": "Dubai, kısa sürede imkânsızı mümkün kılan kentsel dönüşüm hikâyesidir — ENTJ'nin vizyon ve hız sevgisiyle birebir örtüşür. Burj Khalifa'nın zirvesinden şehre bakmak bu tipin büyüklüğe duyduğu ilgiyi karşılar."},
        ],
    },
    "ENTP": {
        "ozet": "ENTP'ler rutin rotaları reddeder, fikir ateşleyen ortamlar arar. Startup sahnesi, alternatif sanat ve farklı kültürlerin çarpıştığı şehirler bu tipin seyahat enerjisini canlı tutar.",
        "sehirler": [
            {"isim": "Berlin, Almanya", "neden": "ENTP'nin kural tanımaz yaratıcılığına en çok yer açan Avrupa şehridir. Kreuzberg'in bağımsız galerileri, startup ekosistemi ve geç saate kadar açık felsefe kafeleri bu tip için doğal habitattır."},
            {"isim": "İstanbul, Türkiye", "neden": "İki kıtanın arasındaki bu benzersiz konum ENTP'nin sentez yapma tutkusunu besler. Kapalıçarşı'nın kaotik müzakere kültürü, Beyoğlu'nun eklektik bar sahnesi ve şehrin çelişkili enerjisi bu tipin zevkleriyle mükemmel uyum içindedir."},
            {"isim": "Barselona, İspanya", "neden": "Gaudí'nin Sagrada Família'sı doğrusal mimari mantığını tamamen yıkar — ENTP bu tür paradigma kırıcı örneklerden derin tatmin alır. El Born'un deneysel restoranları ve Katalon kimliğinin siyasi gerilimi canlı bir tartışma laboratuvarıdır."},
            {"isim": "Amsterdam, Hollanda", "neden": "Düşünce özgürlüğüne tarihin derinliklerine uzanan önem ENTP'yi çeker. Rijksmuseum klasik başlangıçtır; ancak bu tipin asıl ilgisi Jordaan'ın küçük galerileri ve EYE sinema müzesidir."},
            {"isim": "Lizbon, Portekiz", "neden": "Avrupa'nın en az tüketilmiş büyük başkentlerinden biri — bu da ENTP'nin 'henüz kimse bilmiyor' estetiğine hitap eder. LX Factory'nin endüstriyel dönüşüm kompleksi ve Portekizlilerin sıcak sohbet kültürü bu tipi besler."},
        ],
    },
    "INFJ": {
        "ozet": "INFJ'ler seyahatte anlam ve dönüşüm arar. Ruhsal derinliği olan, yerel halkla gerçek bağ kurulabilen ve içsel bir yolculuğu tetikleyecek destinasyonlar bu tip için idealdir.",
        "sehirler": [
            {"isim": "Kyoto, Japonya", "neden": "Kyoto'nun wabi-sabi felsefesi INFJ'nin derinlik arayışıyla mükemmel rezonans kurar. Philosopher's Path boyunca kiraz çiçeklerinin altında yürümek ve Zen tapınaklarında meditasyon programlarına katılmak bu tipin içsel yolculuk ihtiyacını doğrudan karşılar."},
            {"isim": "Varanasi, Hindistan", "neden": "Ganj kıyısında ölüm ile yaşamın her gün ritüelleştiği bu şehir INFJ'nin varoluşsal meraklarına doğrudan hitap eder. Sabah aarti törenini şafak vakti kayıktan izlemek bu tipin ruhunu besler."},
            {"isim": "Fes, Fas", "neden": "Fes'in medina'sı 9. yüzyıldan bu yana değişmeden işleyen bir şehirdir. Yerel ailelerle riad'da konaklamak ve geleneksel boyahaneleri izlemek INFJ'nin anlam ve köklülük arayışını doyurur."},
            {"isim": "Kopenhag, Danimarka", "neden": "Sosyal adalet, tasarım etiği ve çevre bilincini günlük yaşama entegre etmiş bu şehir INFJ'nin değer sistemiyle uyumludur. Christiania'nın alternatif topluluk deneyi bu tip için hem ilham hem yansıma zemini sunar."},
            {"isim": "Tbilisi, Gürcistan", "neden": "Tbilisi, Doğu ile Batı'nın sessizce kaynaştığı ve turistleşmeden önce keşfedilmeyi hak eden bir şehirdir. Geleneksel ağırlama kültürü, balkon mimarisi ve polyphonic Gürcü müziği INFJ'nin manevi katmanlarını aynı anda besler."},
        ],
    },
    "INFP": {
        "ozet": "INFP'ler için her seyahat içsel bir hikâyedir. Romantik şehirler, edebiyat mirası ve doğal güzellik bu tipin seyahat ruhunu besler. Kalabalıktan uzak, anın içinde kalınabilen destinasyonlar idealdir.",
        "sehirler": [
            {"isim": "Edinburgh, İskoçya", "neden": "Edinburgh, J.K. Rowling, Stevenson ve Walter Scott gibi isimleri dünyaya armağan etmiştir. Şehrin sis ve granit atmosferi, dar taş sokakları ve Greyfriars Kirkyard INFP'nin hayal dünyasını besler."},
            {"isim": "Prag, Çek Cumhuriyeti", "neden": "Prag'ın kıvrımlı köprüleri ve barok kiliseler gerçeklikle masalın sınırında bir şehir yaratır. Kafka'nın evine gitmek ve Vltava kıyısında akşam karanlığında oturmak INFP'nin romantik içedönüklüğüne zemin hazırlar."},
            {"isim": "Porto, Portekiz", "neden": "Porto'nun azulejos kaplı eski binaları, fado'nun melankolik tınısı ve Douro kıyısı INFP için hem görsel hem duygusal bir şölen sunar. Livraria Lello kitabevinin merdivenlerinde durmak bu tip için unutulmaz bir andır."},
            {"isim": "Hoi An, Vietnam", "neden": "Fenerlerle aydınlanan eski liman kenti; geleneksel el sanatları atölyeleri ve değişmeyen sakin ritmi INFP'ye şiirsel bir atmosfer sunar."},
            {"isim": "Oaxaca, Meksika", "neden": "Oaxaca'nın canlı renkleri ve Día de los Muertos geleneğinin ölüme şiirsel bakışı INFP'nin duygusal dünyasıyla rezonans kurar. Monte Albán'ın sessizliğinde yalnız dolaşmak bu tipin anlamlı yalnızlık ihtiyacını karşılar."},
        ],
    },
    "ENFJ": {
        "ozet": "ENFJ'ler için seyahat, insanlarla derin bağ kurma ve kültürel köprüler inşa etme sürecidir. Topluluk odaklı etkinlikler ve paylaşım kültürü güçlü destinasyonlar bu tipin enerjisini besler.",
        "sehirler": [
            {"isim": "Barselona, İspanya", "neden": "La Boqueria pazarında sabah alışverişi yapmak, yerel ailelerle tapas paylaşmak ve La Mercè festivali sırasında şehrin kolektif coşkusunu yaşamak ENFJ'nin insanlara dokunan anılar biriktirme ihtiyacını karşılar."},
            {"isim": "Bali, Endonezya", "neden": "Bali'nin kolektif ruhani pratiği — her gün sunulan sesajenler, köy meydanlarındaki gamelan müziği ve Nyepi'nin toplumsal sessizlik ritüeli — ENFJ'nin anlam ve bağ özlemini karşılar."},
            {"isim": "Nairobi & Masai Mara, Kenya", "neden": "Topluluk temelli safari deneyimleri ENFJ'nin hem doğa hem insan bağını aynı anda tatmin eder. Masai köylerini ziyaret etmek ve savanada büyük göç izlemek bu tipin empati repertuarını genişletir."},
            {"isim": "Medellín, Kolombiya", "neden": "Dünyanın en dikkat çekici kentsel dönüşüm hikâyelerinden biri. ENFJ'ler için Comunas'ın duvar resimleri ve yerel halkın dönüşüm gururunu paylaşma isteği son derece ilham vericidir."},
            {"isim": "Seul, Güney Kore", "neden": "Seul'ün K-kültür etkisi ve misafirperver kültürü ENFJ'nin sosyal enerji ihtiyacını karşılar. Gwangjang Pazarı'nda yerel halkla omuz omuza yemek yemek ve jimjilbang kültürü bu tipin paylaşım ihtiyacını doyurur."},
        ],
    },
    "ENFP": {
        "ozet": "ENFP'ler için seyahat, planları yırtıp spontane akmak demektir. Renkli festivaller, yerel pazarlar, yeni insanlar ve anlık kararların mümkün olduğu destinasyonlar bu tipin ruhunu besler.",
        "sehirler": [
            {"isim": "Marakeş, Fas", "neden": "Djemaa el-Fna meydanı — yılan oynatıcıları, hikâye anlatıcıları, taze portakal suyu satıcıları ve dans eden kalabalıklar — ENFP için sonsuz bir spontane keşif sahnesine dönüşür. Medina labirentinde kaybolmak bu tipin özgür ruhuna hitap eder."},
            {"isim": "Chiang Mai, Tayland", "neden": "Yi Peng'in binlerce fener uçurulan gece şenliği ve Songkran su festivali ENFP'nin kolektif sevinç ihtiyacını maksimumda karşılar. Düşük maliyet uzun süreli konaklamaya olanak tanır."},
            {"isim": "Meksika City", "neden": "Frida Kahlo Müzesi, Coyoacán pazar atmosferi ve Roma Norte'nin hipster kafeleri ENFP'nin estetik kaosunu besler. Sabah Teotihuacan'da, öğlen taco kuyruğunda, akşam rooftop'ta — bir günde üç farklı dünya."},
            {"isim": "Lizbon, Portekiz", "neden": "Tram 28'de rastlantısal duraklar yapmak, Alfama'da fado sesi takip etmek ve LX Factory pazarında keşfetmek ENFP'nin spontane enerjisiyle uyum içindedir."},
            {"isim": "Buenos Aires, Arjantin", "neden": "Tango kültürü ENFP için seyahat değil, hayat felsefesidir. Milonga'ya katılmak, Palermo'nun pazar festivallerinde dolaşmak ve Arjantinlilerin geç saatli akşam sohbetlerine dahil olmak bu tipin sosyal bağ ihtiyacını karşılar."},
        ],
    },
    "ISTJ": {
        "ozet": "ISTJ'ler için seyahat, dikkatli araştırma ve kanıtlanmış kaliteye dayanır. Tarihi belgeli şehirler, güvenilir ulaşım ve önceden test edilmiş programlar bu tipin konforunu sağlar.",
        "sehirler": [
            {"isim": "Viyana, Avusturya", "neden": "Mükemmel kamu ulaşımı, müze rezervasyon sistemi ve saatlik programa bağlı kalmayı kolaylaştıran şehir yapısı ISTJ için ideal çerçeve oluşturur. Habsburg tarihi derinlemesine araştırılmış ve belgelenmiştir."},
            {"isim": "Kyoto, Japonya", "neden": "Japon dakikliği ve protokol kültürü ISTJ'nin değer sistemiyle örtüşür. Tapınak saatleri kesindir, rezervasyon sistemleri güvenilirdir ve şehrin harita okunaklılığı mükemmeldir."},
            {"isim": "Londra, İngiltere", "neden": "British Museum, National Gallery ve Imperial War Museum gibi kuruluşlar dünyanın en sistematik koleksiyonlarını barındırır. Oyster kartlı metro sistemi ve kesin tren tarifeleri ISTJ'nin organizasyon ihtiyacını karşılar."},
            {"isim": "Singapur", "neden": "Hukuk düzeni, ultra temiz sokaklar ve lojistik mükemmeliyeti ISTJ'nin seyahatte aradığı güven ve öngörülebilirliği maksimize eder. Her şey çalışır, her şey zamanındadır."},
            {"isim": "Washington D.C., ABD", "neden": "Smithsonian Müzeler Kompleksi'nin tamamı ücretsizdir ve sistematik biçimde gezilebilir. Şehrin grid düzenli cadde yapısı yönlenmeyi kolaylaştırır."},
        ],
    },
    "ISFJ": {
        "ozet": "ISFJ'ler güvenli, sıcak ve aile dostu ortamlarda en mutlu gezginlerdir. Nostaljik şehirler, yerel gelenekler ve ev sıcaklığı sunan konaklamalar bu tip için idealdir.",
        "sehirler": [
            {"isim": "Floransa, İtalya", "neden": "Floransa'nın insan ölçeğindeki şehir yapısı, erişilebilir müzeleri ve her köşedeki trattoria sıcaklığı ISFJ için mükemmel ortam yaratır. Boboli Bahçeleri'nde sakin öğleden sonra geçirmek bu tipin ruhuna dokunur."},
            {"isim": "Provence, Fransa", "neden": "Lavanta tarlaları, küçük taş kasabalar ve köklü Fransız mutfak geleneği ISFJ'nin güzelliğe ve huzura duyduğu özlemi karşılar. Aix-en-Provence'da pazar gezmek bu tipin seyahat dilini oluşturur."},
            {"isim": "Salzburg, Avusturya", "neden": "Salzburg'un masalsı silueti, Mozart mirası ve Avusturya'nın ev sıcaklığını yansıtan yemek kültürü ISFJ için güvenli ve anlamlı bir destinasyon oluşturur."},
            {"isim": "Kyoto, Japonya", "neden": "Geleneksel değerlerin yaşayan müzesi: kimono giyimli günler, çay seremonisi kültürü ve arashiyama bambu ormanının sakin yürüyüşleri ISFJ'nin kalp coğrafyasıyla örtüşür."},
            {"isim": "Toskana, İtalya", "neden": "Toskana'nın kırsal yaşam ritmi — sabah zeytin bahçelerinde yürümek, öğlen farm-to-table yemek, akşam köy piazzasında oturmak — ISFJ'nin huzur değerleriyle örtüşür."},
        ],
    },
    "ESTJ": {
        "ozet": "ESTJ'ler her seyahati verimli, önceden planlanmış ve kontrol altında tutmayı tercih eder. Prestijli şehirler, tanınmış müzeler ve organize turlar bu tipin programını oluşturur.",
        "sehirler": [
            {"isim": "Londra, İngiltere", "neden": "Londra, ESTJ'nin düzen, prestij ve verimlilik beklentilerini aynı anda karşılayan bir dünya başkentidir. Oyster kart tabanlı metro sistemi dakika dakika planlamaya izin verir. Michelin yıldızlı restoranlar ve City of London finans bölgesi bu tipin kalite standartlarını karşılar."},
            {"isim": "Tokyo, Japonya", "neden": "Tokyo'nun disiplinli kamu kültürü — dakikası dakikasına çalışan trenler ve hata kabul etmeyen hizmet standardı — ESTJ'nin değer sisteminin dışa yansımış halidir. JR Pass ile Japonya sistematik biçimde keşfedilebilir."},
            {"isim": "Singapur", "neden": "Singapur, bir şehrin nasıl kusursuz biçimde işletilebileceğini gösteren global bir örnek vakadır. Changi Havalimanı'nın mükemmeliyeti ve yasal düzenin görünür varlığı ESTJ için hem estetik hem pratik bir tatmin kaynağıdır."},
            {"isim": "Viyana, Avusturya", "neden": "Habsburg mirası, opera evleri ve resmi kahve evi kültürü ESTJ için entelektüel ve sosyal bir prestij çerçevesi sunar. Schönbrunn Sarayı turu önceden rezervasyonla mükemmel biçimde planlanabilir."},
            {"isim": "Zürih, İsviçre", "neden": "İsviçre'nin saat hassasiyetindeki tren ağı, şehrin ultra temiz caddeleri ve Bahnhofstrasse'nin prestijli mağazaları ESTJ için ideal kentsel zemin oluşturur. Şehrin yüksek maliyeti bu tip için caydırıcı değil, seçici bir prestij işaretidir."},
        ],
    },
    "ESFJ": {
        "ozet": "ESFJ'ler seyahati sevdikleriyle paylaşmak için yaşar. Fotojenik mekânlar, sosyal aktiviteler, sıcak yerel kültür ve herkesin keyif alacağı ortamlar bu tipin seyahat anlayışını oluşturur.",
        "sehirler": [
            {"isim": "Paris, Fransa", "neden": "Eiffel Kulesi'nden manzara, Montmartre'da sabah kahvesi, Seine kıyısında akşam yemeği ve Versailles bahçeleri fotoğraflanabilir anılar üretir. Şehrin kafe kültürü uzun, keyifli sohbetler için biçilmiş kaftandır."},
            {"isim": "Santorini, Yunanistan", "neden": "Mavi kubbeli kiliseler ve beyaz badanalı duvarlar dünyanın en çok fotoğraflanan manzaralarından birini oluşturur. Oia'da gün batımı izlemek grup dinamiği için kusursuz bir etkinliktir."},
            {"isim": "Bali, Endonezya", "neden": "Resort kültürü, spa deneyimleri ve kolektif yoga retreatları ESFJ'nin hem sosyal hem dinlendirici seyahat ihtiyacına cevap verir. Ubud'un pirinç terası yürüyüşleri ve ateş dansı gösterileri grup için mükemmel aktivitelerdir."},
            {"isim": "Dubrovnik, Hırvatistan", "neden": "Surlarla çevrili tarihi merkez, Adriyatik'e bakan restoranlar ve gün batımında kırmızıya dönen taş dokusu ESFJ için görsel ve sosyal açıdan zengin deneyim sunar."},
            {"isim": "Barselona, İspanya", "neden": "Tapas kültürü bu tipin paylaşımlı yemek sevgisini doğrudan karşılar. Gaudí yapıları grup fotoğrafları için ikonik arka planlar sunar ve şehrin gece hayatı ESFJ'nin sosyal enerjisiyle örtüşür."},
        ],
    },
    "ISTP": {
        "ozet": "ISTP'ler hareketi, fiziksel zorluğu ve pratik beceriyi ödüllendiren destinasyonlar ister. Doğa, dağ ve spontane macera bu tipin seyahat enerjisini şarj eder.",
        "sehirler": [
            {"isim": "Norveç Fiyortları", "neden": "Preikestolen ve Trolltunga trekking rotaları ISTP'nin fiziksel zorluğa duyduğu açlığı karşılar. Kayıkla fiyort gezmek, kamp kurmak ve sert hava koşullarıyla başa çıkmak bu tipin pragmatik beka becerilerini aktive eder."},
            {"isim": "Moğolistan Stepi", "neden": "Stepte at binmek, ger çadırında kalmak ve Gobi Çölü'nde motosiklet sürmek ISTP için dünyanın sunabileceği en saf macera deneyimlerinden biridir. Modernliğin sıfırlandığı bu ortamda temel beceriler öne çıkar."},
            {"isim": "Patagonya, Arjantin/Şili", "neden": "Torres del Paine'in zorlu yürüyüş parkurları, Perito Moreno buzulunun çatlamaları ISTP'nin limitlerini test etme isteğini tatmin eder."},
            {"isim": "Japonya — Hokkaido", "neden": "Hokkaido'nun kış sporları kültürü, Niseko'nun dünyaca ünlü kayak yamaçları ve açık doğa onsen deneyimleri ISTP'nin pratik macera anlayışına hitap eder."},
            {"isim": "Yeni Zelanda — Güney Adası", "neden": "Queenstown bungee jumping, skydiving ve jet boat gibi adrenalin sporlarının başkentidir. Milford Track ve Routeburn Track zorlu trekking programları sunar."},
        ],
    },
    "ISFP": {
        "ozet": "ISFP'ler dünyayı estetik bir deneyim olarak yaşar. Sanat, el sanatları ve doğanın güzelliği bu tipin seyahat ruhunu besler. Aceleye getirilmemiş, izlenebilecek anların bol olduğu destinasyonlar idealdir.",
        "sehirler": [
            {"isim": "Floransa, İtalya", "neden": "Uffizi'nin Botticelli salonunda saatlerce durmak, San Miniato al Monte'den Arno vadisini izlemek ve Oltrarno'da küçük bir çerçeveci atölyesine adım atmak ISFP için seyahatin özüdür. Floransa sanatı müzeye hapsetmez."},
            {"isim": "Bali — Ubud", "neden": "Ubud'un pirinç terası manzaraları, geleneksel dans gösterileri ve el sanatları atölyeleri ISFP'nin estetik duyarlılığını besler. Bir batik boyama kursuna katılmak bu tipin anları yoğun hissetme ihtiyacıyla örtüşür."},
            {"isim": "Oaxaca, Meksika", "neden": "Canlı renkleri, yerli dokuma gelenekleri ve çömlek atölyeleri ISFP için görsel ve dokunsal bir cennet yaratır. Küçük bir atölyede ustadan boyama öğrenmek bu tipin içsel ritmine uyum sağlar."},
            {"isim": "Kyoto, Japonya", "neden": "Çiçek döneminde kiraz ağaçlarının altında durmak, Nishiki'nin renkli tezgahları arasında yavaşça ilerlemek ve Gion'da akşam ışığını beklemek ISFP'nin anlık güzelliğe duyduğu derin duyarlılığa hitap eder."},
            {"isim": "Kopenhag, Danimarka", "neden": "İskandinav tasarım felsefesi — işlevsellikle estetiği birleştiren minimalist yaklaşım — ISFP'nin görsel dünyasını zenginleştirir. Designmuseum Denmark ve Nørrebro'nun vintage mağazaları keyifli bir estetik rotadır."},
        ],
    },
    "ESTP": {
        "ozet": "ESTP'ler için seyahat maksimum hız ve aksiyon demektir. Gece hayatı, adrenalin sporları ve anlık kararların serbestçe alındığı ortamlar bu tipin ateşini tutuşturur.",
        "sehirler": [
            {"isim": "Dubai, BAE", "neden": "Burj Khalifa'dan base jumping, Ski Dubai, Formula E parkurunda araba deneyimi ve Atlantis su parkı ESTP'nin adrenalin ihtiyacını şehir konforunu koruyarak karşılar. Gece hayatı küresel DJ'lerle 7 gün 7 gece devam eder."},
            {"isim": "Las Vegas, ABD", "neden": "Poker masası, gece kulübü, açık büfe ve motorsports arena aynı oteldedir. Strip'in ışıkları ve sürekli değişen uyarım ortamı ESTP'nin doğasına birebir uyar."},
            {"isim": "Bangkok, Tayland", "neden": "Gece pazarları, muay thai kulüpleri, scooter kiralayarak trafik labirentinde ilerlemek ve hızlı tekne turları ESTP için ideal aksiyon programı oluşturur."},
            {"isim": "Queenstown, Yeni Zelanda", "neden": "Dünya'nın macera sporları başkenti: bungee jumping, skydiving, canyon swing, jet boat. ESTP için bu şehir sadece bir destinasyon değil, fiziksel limitlerini test etmek için özelleşmiş bir platformdur."},
            {"isim": "İbiza, İspanya", "neden": "Gece kulübü kültürü ESTP'nin topluluk enerjisiyle dans etme ve adrenalini sosyal ortamda hissetme ihtiyacını maksimize eder. Gündüzleri plaj sporları, geceleri Pacha veya Amnesia — ritim hiç kesintisiz akar."},
        ],
    },
    "ESFP": {
        "ozet": "ESFP'ler her destinasyonu bir sahneye dönüştürür. Müzik, dans, kalabalık ve canlı sosyal ortamlar bu tipin seyahat enerjisinin kaynağıdır. Fotoğraflanabilir anlar ve yeni arkadaşlıklar bu tipin beklentisidir.",
        "sehirler": [
            {"isim": "Rio de Janeiro, Brezilya", "neden": "Copacabana'da sahil voleybolu, Cristo Redentor'dan panoramik selfie, samba okulu provalerında dans etmek ve boteco'larda caipirinha içmek ESFP'nin seyahat anılarının merkezini oluşturur."},
            {"isim": "İbiza, İspanya", "neden": "Gündüz plaj partileri ve gece kulüp kültürü ESFP için mükemmel bir sahne sunar. Yeni insanlarla tanışmak, dans pistinde saatler geçirmek ve sabah denize girerek geceyi kapatmak bu tipin ritmine doğal uyar."},
            {"isim": "Bali, Endonezya", "neden": "Seminyak ve Kuta plajlarının gün batımı bar kültürü, pool party sahnesi ve sosyal yoga retreatları ESFP'nin hem eğlence hem bağ kurma ihtiyacını dengeler. Her gün yeni insanlarla tanışmak burada otomatik bir sonuçtur."},
            {"isim": "Barselona, İspanya", "neden": "Barceloneta sahilinde öğlen, Gaudí fotoğrafları için Las Ramblas'ta akşam öncesi, Opium veya Pacha'da gece — bu ritim ESFP için mükemmeldir."},
            {"isim": "Seul, Güney Kore", "neden": "K-pop kültürü, canlı sokak yeme-içme sahnesi ve Hongdae'nin geç saatlere kadar açık müzik barları ESFP için her gece yeni bir keşif vaat eder. BTS gibi ikonların doğduğu kültürü yerinde yaşamak bu tipin enerjisiyle rezonans kurar."},
        ],
    },
}

# ── Yardımcı ──────────────────────────────────────────────────────────────────

def go_tab(idx: int):
    st.session_state.current_tab = idx


def page_header(title, subtitle=""):
    sub = f'<p style="color:#6b7280;font-size:14px;margin:4px 0 16px">{subtitle}</p>' if subtitle else '<div style="margin-bottom:16px"></div>'
    st.markdown(
        f'<h1 style="font-size:22px;font-weight:700;color:#111827;margin:0 0 4px">{title}</h1>{sub}',
        unsafe_allow_html=True,
    )


def _masaustu_klasoru() -> str:
    """Kullanıcının gerçek Masaüstü klasörünü döndürür — OneDrive ile yönlendirilmiş
    masaüstlerini de (bu makinedeki gibi) doğru tespit eder."""
    home = os.path.expanduser("~")
    for aday in (os.path.join(home, "OneDrive", "Desktop"), os.path.join(home, "Desktop")):
        if os.path.isdir(aday):
            return aday
    return home


def _plan_pdf_bytes(baslik: str, alt_baslik: str, gun_metinleri: list) -> bytes:
    """Plan metnini basit, okunabilir bir PDF'e dönüştürür. Türkçe karakterler için
    (fpdf2'nin çekirdek fontları desteklemiyor) sistemdeki bir Unicode TTF kullanılır,
    bulunamazsa çekirdek fonta düşer."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    font_yolu = None
    for aday in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(aday):
            font_yolu = aday
            break

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    if font_yolu:
        pdf.add_font("govde", "", font_yolu)
        font_adi = "govde"
    else:
        font_adi = "helvetica"

    # multi_cell varsayılan olarak imleci satır sonunda bırakır (sol kenara
    # dönmez) — new_x/new_y açıkça verilmezse bir sonraki multi_cell çağrısı
    # kalan (neredeyse sıfır) genişliğe sığmaya çalışıp FPDFException fırlatır.
    def _satir(metin, boy):
        pdf.multi_cell(0, boy, metin, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font(font_adi, size=18)
    pdf.set_text_color(30, 30, 30)
    _satir(baslik, 10)
    pdf.set_font(font_adi, size=11)
    pdf.set_text_color(90, 90, 90)
    _satir(alt_baslik, 7)
    pdf.ln(4)

    for metin in gun_metinleri:
        if not metin.strip():
            continue
        pdf.set_draw_color(224, 224, 224)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 174, pdf.get_y())
        pdf.ln(3)
        pdf.set_font(font_adi, size=10.5)
        pdf.set_text_color(20, 20, 20)
        _satir(metin, 6)
        pdf.ln(2)

    return bytes(pdf.output())


# ════════════════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════════════════

def auth_screen():
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("""
<div style="text-align:center;padding:32px 0 24px">
  <div style="font-size:48px">✈️</div>
  <h1 style="margin:8px 0 4px;font-size:26px;font-weight:800;color:#111827">SmartTravel AI</h1>
  <p style="color:#6b7280;font-size:14px;margin:0">Yapay zeka destekli kişisel seyahat asistanın</p>
</div>""", unsafe_allow_html=True)
        tab_l, tab_r = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
        with tab_l:
            with st.form("login_form"):
                username = st.text_input("Kullanıcı Adı", placeholder="kullaniciadi")
                password = st.text_input("Şifre", type="password", placeholder="••••••")
                if st.form_submit_button("Giriş Yap", use_container_width=True):
                    ok, msg = login_user(username.strip(), password)
                    if ok:
                        st.session_state.logged_in    = True
                        st.session_state.username     = username.strip()
                        profile = get_user_profile(username.strip())
                        saved_mbti = profile.get("mbti_type", "")
                        if saved_mbti:
                            _mbti_agent = MBTIAgent()
                            _arch  = _mbti_agent.ARKETIPLER.get(saved_mbti, "Özgün Gezgin")
                            _prefs = _mbti_agent.SEYAHAT_TERCIHLERI.get(saved_mbti, ["keşif"])
                            _rapor = (_mbti_agent.STATIK_RAPORLAR.get(saved_mbti)
                                      or _mbti_agent._default_rapor(saved_mbti, _arch, _prefs))
                            st.session_state.user_data["mbti_type"] = saved_mbti
                            st.session_state.mbti_archetype          = _arch
                            st.session_state.mbti_report             = _rapor
                            st.session_state.mbti_completed          = True
                            st.session_state.current_tab             = 1
                            st.session_state["_profil_yuklendi"]     = True
                        st.rerun()
                    else:
                        st.error(msg)
        with tab_r:
            with st.form("register_form", clear_on_submit=True):
                new_user  = st.text_input("Kullanıcı Adı", key="reg_user")
                new_email = st.text_input("E-posta (isteğe bağlı)", key="reg_email")
                new_pw    = st.text_input("Şifre", type="password", key="reg_pw")
                new_pw2   = st.text_input("Şifre Tekrar", type="password", key="reg_pw2")
                if st.form_submit_button("Kayıt Ol", use_container_width=True):
                    if new_pw != new_pw2:
                        st.error("Şifreler eşleşmiyor.")
                    else:
                        ok, msg = register_user(new_user.strip(), new_pw, new_email.strip())
                        if ok:
                            st.success(msg + " Şimdi giriş yapabilirsiniz.")
                        else:
                            st.error(msg)


if not st.session_state.logged_in:
    auth_screen()
    st.stop()

# ════════════════════════════════════════════════════════════════════════════
# SOL SİDEBAR
# ════════════════════════════════════════════════════════════════════════════

cur          = st.session_state.current_tab
mbti_type    = st.session_state.user_data.get("mbti_type", "")
mbti_arch    = st.session_state.mbti_archetype
renk_map     = {
    "INTJ":"#6d28d9","INTP":"#7c3aed","ENTJ":"#4338ca","ENTP":"#2563eb",
    "INFJ":"#0891b2","INFP":"#0d9488","ENFJ":"#059669","ENFP":"#65a30d",
    "ISTJ":"#ca8a04","ISFJ":"#d97706","ESTJ":"#dc2626","ESFJ":"#e11d48",
    "ISTP":"#0284c7","ISFP":"#7c3aed","ESTP":"#ea580c","ESFP":"#db2777",
}
mbti_renk = renk_map.get(mbti_type, "#6366f1")

NAV_ITEMS = [
    (0, "🧬", "Kimlik Testi",   st.session_state.mbti_completed),
    (1, "🗺️", "Rota Formu",     True),
    (2, "📋", "Plan Sonucu",    st.session_state.last_plan is not None),
    (3, "🧳", "Gezi Hazırlığı", st.session_state.last_plan is not None),
    (4, "📖", "Seyahatlerim",   True),
]

with st.sidebar:
    # Logo
    st.markdown("""
<div style="padding:22px 18px 14px">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:36px;height:36px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                border-radius:10px;display:flex;align-items:center;justify-content:center;
                font-size:18px;flex-shrink:0">✈️</div>
    <div>
      <div style="font-size:14px;font-weight:800;color:white;line-height:1.1">SmartTravel</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.45);font-weight:500;letter-spacing:0.3px">AI · Beta</div>
    </div>
  </div>
</div>
<div style="height:1px;background:rgba(255,255,255,0.08);margin:0 14px 10px"></div>
<div style="padding:0 14px 6px">
  <div style="font-size:9px;font-weight:700;color:rgba(255,255,255,0.35);
              text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Adımlar</div>
</div>
""", unsafe_allow_html=True)

    # Nav butonları
    for idx, icon, label, done in NAV_ITEMS:
        is_active = (idx == cur)
        check     = "  ✓" if done and not is_active else ""
        # ▶ ile başlayan label → aria-label^="▶" CSS aktif seçici ile eşleşir
        btn_label = f"▶ {icon}  {label}" if is_active else f"   {icon}  {label}{check}"
        if st.button(btn_label, key=f"nav_btn_{idx}", use_container_width=True):
            go_tab(idx)
            st.rerun()

    # Ayraç
    st.markdown('<div style="height:1px;background:rgba(255,255,255,0.08);margin:10px 14px"></div>',
                unsafe_allow_html=True)

    # ── Profil kartı ──────────────────────────────────────────────────────────
    _uname_init = st.session_state.username[:1].upper() if st.session_state.username else "?"
    if mbti_type:
        st.markdown(f"""
<div style="padding:0 12px 10px">
  <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.09);
              border-radius:12px;padding:12px 14px">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
                  background:linear-gradient(135deg,{mbti_renk},{mbti_renk}88);
                  display:flex;align-items:center;justify-content:center;
                  font-size:12px;font-weight:800;color:white">
        {_uname_init}
      </div>
      <div style="min-width:0">
        <div style="font-size:12.5px;font-weight:700;color:white;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
          {st.session_state.username}</div>
        <div style="font-size:10.5px;color:rgba(255,255,255,0.45);margin-top:1px">
          {mbti_arch or "Gezgin"}</div>
      </div>
      <div style="margin-left:auto;flex-shrink:0;background:{mbti_renk}33;
                  border:1px solid {mbti_renk}66;border-radius:6px;
                  padding:3px 8px;font-size:11px;font-weight:800;color:{mbti_renk}">
        {mbti_type}
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
      <div style="background:rgba(255,255,255,0.05);border-radius:8px;padding:7px 10px">
        <div style="font-size:9px;color:rgba(255,255,255,0.35);
                    text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px">Plan</div>
        <div style="font-size:14px;font-weight:800;color:white">
          {len(st.session_state.travel_history)}</div>
      </div>
      <div style="background:rgba(255,255,255,0.05);border-radius:8px;padding:7px 10px">
        <div style="font-size:9px;color:rgba(255,255,255,0.35);
                    text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px">Durum</div>
        <div style="font-size:10px;font-weight:700;color:#9eaa8f">● Aktif</div>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="padding:0 12px 10px">
  <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.09);
              border-radius:12px;padding:12px 14px">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
                  background:rgba(255,255,255,0.1);
                  display:flex;align-items:center;justify-content:center;
                  font-size:13px;font-weight:800;color:rgba(255,255,255,0.6)">
        {_uname_init}
      </div>
      <div>
        <div style="font-size:12.5px;font-weight:700;color:white">{st.session_state.username}</div>
        <div style="font-size:10.5px;color:rgba(255,255,255,0.4)">Profil henüz oluşturulmadı</div>
      </div>
    </div>
    <div style="background:rgba(255,165,0,0.12);border:1px solid rgba(255,165,0,0.25);
                border-radius:8px;padding:7px 10px;font-size:10.5px;color:rgba(255,200,100,0.8)">
      🧬 Kimlik Testi'ni tamamlayın
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Sekmeye özel ipucu ────────────────────────────────────────────────────
    _tab_hints = {
        0: ("🧬", "Kimlik Testi", "20 soruyla gezgin tipinizi belirleyin. Sonuç tüm analizleri etkiler."),
        1: ("🗺️", "Rota Formu", "Destinasyon, tarih ve bütçe bilgilerinizi girerek plan oluşturun."),
        2: ("📋", "Plan Sonucu", "Gün gün detaylı program, galeri ve bütçe özetini buradan görün."),
        3: ("🧳", "Gezi Hazırlığı", "Sana özel tatil listesi ve günlük harcama planı."),
        4: ("📖", "Seyahatlerim", "Gezilerin, gittiğin yerler ve yorumların — sonraki planın bunları hatırlar."),
    }
    if cur in _tab_hints:
        _h_icon, _h_title, _h_desc = _tab_hints[cur]
        st.markdown(f"""
<div style="padding:0 12px 12px">
  <div style="background:rgba(212,151,106,0.1);border:1px solid rgba(212,151,106,0.2);
              border-radius:10px;padding:10px 12px">
    <div style="font-size:9px;font-weight:700;color:rgba(212,151,106,0.7);
                text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px">
      {_h_icon} {_h_title}</div>
    <div style="font-size:10.5px;color:rgba(255,255,255,0.5);line-height:1.5">{_h_desc}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # Çıkış butonu
    if st.button("Çıkış Yap", key="logout_btn", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# SEKME 0 — KİMLİK TESTİ
# ════════════════════════════════════════════════════════════════════════════

if cur == 0:
    if st.session_state.mbti_completed:
        mbti   = st.session_state.user_data.get("mbti_type", "")
        arch   = st.session_state.mbti_archetype
        profil = MBTI_SEYAHAT.get(mbti, {"tercih": "Kişisel keşifler", "kac": "Standart rotalar", "ideal": "Size özel destinasyonlar", "renk": "#4f46e5"})
        renk   = profil["renk"]

        page_header("Gezgin Profilin")

        # ── Kişilik boyutları hesapla ──────────────────────────────────────
        _dim_labels = [
            ("E","I","Dışavurumcu","İçedönük"),
            ("N","S","Sezgisel","Gözlemci"),
            ("T","F","Mantıksal","Duygusal"),
            ("J","P","Planlayıcı","Esnek"),
        ]
        _dim_vals = []
        for idx, (a, b, _la, _lb) in enumerate(_dim_labels):
            _letter = mbti[idx] if idx < len(mbti) else a
            _is_a   = (_letter == a)
            _dim_vals.append((_is_a, _la if _is_a else _lb))

        _blog_txt = MBTI_BLOG.get(mbti, "")

        # ── Karakter özellikleri chip listesi ─────────────────────────────
        _trait_map = {
            "INTJ": ["Stratejik","Bağımsız","Analitik","Kararlı","Öngörülü"],
            "INTP": ["Meraklı","Nesnel","Yenilikçi","Analitik","Sessiz"],
            "ENTJ": ["Lider","Verimli","Güçlü","Stratejik","Kararli"],
            "ENTP": ["Yaratıcı","Tartışmacı","Vizyoner","Hızlı","Esnek"],
            "INFJ": ["Empatik","Anlayışlı","İçgörülü","İdealci","Sakin"],
            "INFP": ["Romantik","Yaratıcı","Özgün","Duyarlı","Hayalperest"],
            "ENFJ": ["Karizmatik","İlham Veren","Empatik","Sosyal","Yardımsever"],
            "ENFP": ["Enerjik","Özgür","Coşkulu","Meraklı","Spontane"],
            "ISTJ": ["Güvenilir","Düzenli","Sorumlu","Kararlı","Pratik"],
            "ISFJ": ["Sıcak","Koruyucu","Sadık","Sabırlı","Özenli"],
            "ESTJ": ["Organizatör","Güçlü","Net","Sorumlu","Verimli"],
            "ESFJ": ["Sosyal","Sevgi Dolu","Fedakâr","Uyumlu","Cana Yakın"],
            "ISTP": ["Pratik","Mekanik","Cesur","Sessiz","Bağımsız"],
            "ISFP": ["Sanatçı","Hassas","Uysal","Anlık","Estetik"],
            "ESTP": ["Maceracı","Hızlı","Pratik","Sosyal","Cesur"],
            "ESFP": ["Neşeli","Spontane","Eğlenceli","Sosyal","Coşkulu"],
        }
        _traits = _trait_map.get(mbti, ["Özgün","Keşifçi","Meraklı","Bağımsız","Esnek"])

        # ── Kişilik boyut çubukları HTML ──────────────────────────────────
        def _dim_bar(letter_a, letter_b, label_a, label_b, is_a):
            _fill = 72 if is_a else 28
            return f"""
<div style="margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
    <span style="font-size:11px;font-weight:{'800' if is_a else '500'};
                 color:{'#2c2416' if is_a else '#b5a99a'}">{label_a} ({letter_a})</span>
    <span style="font-size:11px;font-weight:{'800' if not is_a else '500'};
                 color:{'#2c2416' if not is_a else '#b5a99a'}">{label_b} ({letter_b})</span>
  </div>
  <div style="background:#e8dfd4;border-radius:99px;height:7px;overflow:hidden">
    <div style="height:100%;width:{_fill}%;background:linear-gradient(90deg,#d4976a,#8b7355);
                border-radius:99px;{'margin-left:auto' if not is_a else ''}"></div>
  </div>
</div>"""

        _boyut_html = "".join(
            _dim_bar(_dim_labels[i][0], _dim_labels[i][1],
                     _dim_labels[i][2], _dim_labels[i][3],
                     _dim_vals[i][0])
            for i in range(4)
        )

        # Chip'leri hero (koyu zemin) için önceden hesapla
        _trait_chips_dark = "".join(
            f'<span style="background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.18);'
            f'border-radius:99px;padding:4px 12px;font-size:11px;font-weight:600;'
            f'color:rgba(255,255,255,0.88);display:inline-block;margin:3px 2px">{t}</span>'
            for t in _traits
        )

        # ── Hero banner (st.html — position:absolute destekler) ──────────
        st.html(f"""
<div style="background:linear-gradient(135deg,#2c2416 0%,#4a3828 60%,#6b4c35 100%);
            border-radius:20px;padding:32px 36px;margin-bottom:20px;
            position:relative;overflow:hidden;font-family:'Inter',sans-serif">
  <div style="position:absolute;right:-40px;top:-40px;width:220px;height:220px;
              border-radius:50%;background:rgba(255,255,255,0.04)"></div>
  <div style="position:absolute;right:50px;bottom:-70px;width:160px;height:160px;
              border-radius:50%;background:rgba(212,151,106,0.10)"></div>
  <div style="position:absolute;left:-30px;bottom:-30px;width:100px;height:100px;
              border-radius:50%;background:rgba(158,170,143,0.08)"></div>

  <div style="position:relative;display:flex;align-items:flex-start;gap:36px;flex-wrap:wrap">
    <div style="min-width:140px">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;
                  color:rgba(255,255,255,0.4);text-transform:uppercase;margin-bottom:8px">
        Gezgin Tipin
      </div>
      <div style="font-size:80px;font-weight:900;letter-spacing:-5px;line-height:0.9;
                  color:white">{mbti}</div>
      <div style="margin-top:14px;display:inline-block;background:rgba(212,151,106,0.22);
                  border:1px solid rgba(212,151,106,0.4);border-radius:8px;
                  padding:5px 14px;font-size:13px;font-weight:700;color:#e8b882;
                  letter-spacing:0.3px">{arch}</div>
    </div>

    <div style="flex:1;min-width:200px;padding-top:4px">
      <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.38);
                  letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px">
        Kişilik Özelliklerin
      </div>
      <div style="line-height:1.4">{_trait_chips_dark}</div>
      <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08);
                  font-size:11.5px;color:rgba(255,255,255,0.42);display:flex;align-items:center;gap:8px">
        <span style="width:6px;height:6px;border-radius:50%;background:#9eaa8f;
                     display:inline-block;flex-shrink:0"></span>
        Planların bu profile göre hazırlanır
      </div>
    </div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;
            font-family:'Inter',sans-serif">
  <div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:16px;padding:20px 22px">
    <div style="font-size:10px;font-weight:700;color:#8b7355;text-transform:uppercase;
                letter-spacing:1.2px;margin-bottom:16px">Kişilik Boyutları</div>
    {_boyut_html}
  </div>
  <div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:16px;padding:20px 22px">
    <div style="font-size:10px;font-weight:700;color:#8b7355;text-transform:uppercase;
                letter-spacing:1.2px;margin-bottom:12px">Seyahat Tarzın</div>
    <div style="font-size:13px;color:#3d3128;line-height:1.8">{_blog_txt}</div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;
            font-family:'Inter',sans-serif">
  <div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:16px 18px">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
      <span style="font-size:15px;color:#9eaa8f">✦</span>
      <span style="font-size:9px;font-weight:700;color:#9eaa8f;text-transform:uppercase;
                   letter-spacing:0.9px">Sevdiklerin</span>
    </div>
    <div style="font-size:12.5px;color:#2c2416;line-height:1.7">{profil['tercih']}</div>
  </div>
  <div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:16px 18px">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
      <span style="font-size:15px;color:#c07a5a">✕</span>
      <span style="font-size:9px;font-weight:700;color:#c07a5a;text-transform:uppercase;
                   letter-spacing:0.9px">Kaçındıkların</span>
    </div>
    <div style="font-size:12.5px;color:#2c2416;line-height:1.7">{profil['kac']}</div>
  </div>
  <div style="background:linear-gradient(150deg,#f7f1e8,#f0e8dc);border:1px solid #ddd0bf;
              border-radius:14px;padding:16px 18px">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
      <span style="font-size:15px;color:#d4976a">◈</span>
      <span style="font-size:9px;font-weight:700;color:#d4976a;text-transform:uppercase;
                   letter-spacing:0.9px">İdeal Destinasyon</span>
    </div>
    <div style="font-size:12.5px;color:#2c2416;line-height:1.7">{profil['ideal']}</div>
  </div>
</div>""")

        if st.session_state.mbti_report:
            _report_raw = st.session_state.mbti_report
            st.html(f"""
<div style="font-family:'Inter',sans-serif;margin-bottom:16px">
  <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
    <div style="width:36px;height:36px;border-radius:10px;flex-shrink:0;
                background:linear-gradient(135deg,#d4976a,#8b7355);
                display:flex;align-items:center;justify-content:center;
                font-size:16px">✦</div>
    <div>
      <div style="font-size:10px;font-weight:700;color:#8b7355;text-transform:uppercase;
                  letter-spacing:1.2px">AI Gezgin Analizi</div>
      <div style="font-size:12px;color:#b5a99a;margin-top:2px">
        Yapay zeka tarafından kişiselleştirilmiş profil raporu
      </div>
    </div>
    <div style="margin-left:auto;background:#f2ede6;border:1px solid #e0d5c8;
                border-radius:99px;padding:4px 12px;font-size:10px;
                font-weight:700;color:#8b7355">{mbti}</div>
  </div>

  <div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:16px;
              padding:24px 28px;position:relative;overflow:hidden">
    <div style="position:absolute;top:0;left:0;width:4px;height:100%;
                background:linear-gradient(180deg,#d4976a,#9eaa8f);
                border-radius:4px 0 0 4px"></div>
    <div style="padding-left:8px">
      <style>
        .mbti-rapor h2 {{
          font-size:17px;font-weight:800;color:#2c2416;
          margin:0 0 10px;letter-spacing:-0.3px;
          padding-bottom:8px;border-bottom:1px solid #f0e8de;
        }}
        .mbti-rapor h3 {{
          font-size:13px;font-weight:700;color:#8b7355;
          text-transform:uppercase;letter-spacing:0.8px;
          margin:18px 0 8px;
        }}
        .mbti-rapor p {{
          font-size:13.5px;color:#3d3128;line-height:1.82;margin:0 0 10px;
        }}
        .mbti-rapor ul, .mbti-rapor ol {{
          padding-left:18px;margin:6px 0 12px;
        }}
        .mbti-rapor li {{
          font-size:13px;color:#4a3f35;line-height:1.75;margin-bottom:4px;
        }}
        .mbti-rapor strong {{
          color:#2c2416;font-weight:700;
        }}
        .mbti-rapor a {{ color:#d4976a;text-decoration:none; }}
      </style>
      <div class="mbti-rapor">{_report_raw}</div>
    </div>
  </div>
</div>""")

        dest_data = MBTI_DESTINASYONLAR.get(mbti)
        if dest_data:
            _rank_icons = ["①","②","③","④","⑤"]
            sehir_html = ""
            for i, s in enumerate(dest_data["sehirler"]):
                sehir_html += f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:12px;
            padding:14px 16px;display:flex;gap:12px;align-items:flex-start">
  <div style="font-size:22px;line-height:1;flex-shrink:0;margin-top:1px;
              color:#d4976a;font-weight:900">{_rank_icons[i]}</div>
  <div>
    <div style="font-size:13px;font-weight:700;color:#2c2416;margin-bottom:4px">{s['isim']}</div>
    <div style="font-size:12px;color:#6b5c4e;line-height:1.65">{s['neden']}</div>
  </div>
</div>"""
            st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:16px;
            padding:20px 22px;margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <div style="font-size:10px;font-weight:700;color:#8b7355;text-transform:uppercase;
                letter-spacing:1px">{mbti} için Destinasyon Önerileri</div>
    <div style="background:#f2ede6;border:1px solid #e0d5c8;border-radius:99px;
                padding:3px 10px;font-size:10px;font-weight:700;color:#8b7355">{len(dest_data['sehirler'])} şehir</div>
  </div>
  <div style="font-size:12.5px;color:#6b5c4e;line-height:1.7;margin-bottom:14px;
              padding-bottom:14px;border-bottom:1px solid #f0e8de">{dest_data['ozet']}</div>
  <div style="display:flex;flex-direction:column;gap:8px">{sehir_html}</div>
</div>""", unsafe_allow_html=True)

        col_a, col_b = st.columns([5, 1])
        with col_a:
            if st.button("Rota Oluşturmaya Geç →", key="go_rota", type="primary"):
                go_tab(1); st.rerun()
        with col_b:
            if st.button("Yeniden Çöz", key="redo_mbti"):
                st.session_state.mbti_completed = False; st.rerun()

    else:
        page_header("Gezgin Kimlik Testi", "20 soruyla seyahat kişiliğini belirliyoruz — her soruda iki seçenek var")
        st.markdown("""
<div style="background:linear-gradient(135deg,#ffffff,#f8f7f4);border:1px solid #e5e7eb;border-radius:14px;
            padding:16px 22px;margin-bottom:20px;display:flex;align-items:center;gap:16px;
            box-shadow:0 1px 3px rgba(30,20,10,0.04)">
  <div style="width:42px;height:42px;border-radius:11px;flex-shrink:0;
              background:linear-gradient(135deg,#4f46e5,#818cf8);
              display:flex;align-items:center;justify-content:center;font-size:19px">🧬</div>
  <div style="flex:1;min-width:160px">
    <div style="font-size:13px;font-weight:700;color:#1f2937">Kimlik Testi</div>
    <div style="font-size:11.5px;color:#6b7280;margin-top:2px">
      Doğru ya da yanlış cevap yok — sana daha yakın gelen seçeneği (A ya da B) işaretle.
    </div>
  </div>
  <div style="display:flex;gap:8px">
    <div style="background:#eef2ff;border-radius:10px;padding:8px 14px;text-align:center;min-width:54px">
      <div style="font-size:17px;font-weight:800;color:#4f46e5">20</div>
      <div style="font-size:10px;color:#6b7280">Soru</div>
    </div>
    <div style="background:#f0fdf4;border-radius:10px;padding:8px 14px;text-align:center;min-width:54px">
      <div style="font-size:17px;font-weight:800;color:#059669">3 dk</div>
      <div style="font-size:10px;color:#6b7280">Süre</div>
    </div>
    <div style="background:#fdf4ff;border-radius:10px;padding:8px 14px;text-align:center;min-width:54px">
      <div style="font-size:17px;font-weight:800;color:#9333ea">16</div>
      <div style="font-size:10px;color:#6b7280">Profil</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        _yol = st.radio("Nasıl devam etmek istersin?", ["📝 Testi çöz (20 soru)", "✅ Tipimi zaten biliyorum"],
                        horizontal=True, label_visibility="collapsed", key="mbti_yol")
        if _yol.startswith("✅"):
            with st.container(border=True):
                st.markdown("**Tipini seç** — resmi MBTI ya da başka bir testten öğrendiğin dört harfli tip.")
                _tip = st.selectbox("Tipin", MBTIAgent.TIPLER, index=None, placeholder="Örn: ENFP",
                                    format_func=lambda t: f"{t} — {MBTIAgent.ARKETIPLER.get(t, '')}")
                if st.button("Bu tiple devam et", type="primary", disabled=_tip is None):
                    with st.spinner("Profiliniz oluşturuluyor..."):
                        res = MBTIAgent().tip_profili(_tip)
                    st.session_state.mbti_report    = res.get("description", "")
                    st.session_state.user_data["mbti_type"] = res["mbti_type"]
                    st.session_state.mbti_archetype = res.get("archetype", "Gezgin")
                    st.session_state.mbti_completed = True
                    update_user_mbti(st.session_state.username, res["mbti_type"])
                    go_tab(0); st.rerun()
            st.stop()

        _sorular = MBTIAgent.SORULAR
        _bolumler = [
            ("Bölüm 1 / 2", "Kişilik &amp; Motivasyon", "Sorular 1 – 10", "#4f46e5", "#eef2ff", "#c7d2fe", "#1e1b4b", 0),
            ("Bölüm 2 / 2", "Turizm Kimliği &amp; Keşif Tarzı", "Sorular 11 – 20", "#059669", "#f0fdf4", "#a7f3d0", "#064e3b", 10),
        ]
        with st.form("mbti_form"):
            cevaplar = [None] * len(_sorular)
            for kol, (etk, baslik, alt, renk, zemin, kenar, koyu, bas) in zip(st.columns(2, gap="large"), _bolumler):
                with kol:
                    st.markdown(f"""<div style="background:{zemin};border-radius:12px;padding:12px 16px;
                        margin-bottom:14px;border:1px solid {kenar}">
  <div style="font-size:9px;font-weight:700;color:{renk};text-transform:uppercase;letter-spacing:0.6px">{etk}</div>
  <div style="font-size:13px;font-weight:700;color:{koyu};margin-top:2px">{baslik}</div>
  <div style="font-size:11px;color:#6b7280">{alt}</div>
</div>""", unsafe_allow_html=True)
                    for i in range(bas, bas + 10):
                        soru, a_metni, b_metni, _, _ = _sorular[i]
                        with st.container(border=True):
                            cevaplar[i] = st.radio(f"{i + 1}. {soru}", [f"A) {a_metni}", f"B) {b_metni}"],
                                                   index=None, key=f"mbti_ab_q{i + 1}")

            extra = st.text_area("Opsiyonel Not", placeholder="Örnek: Vejetaryenim, fotoğraf çekmekten hoşlanıyorum...")

            if st.form_submit_button("Profil Oluştur", type="primary"):
                eksik = [str(i + 1) for i, c in enumerate(cevaplar) if c is None]
                if eksik:
                    st.warning(f"Lütfen tüm soruları yanıtla — boş kalanlar: {', '.join(eksik)}")
                else:
                    with st.spinner("Profiliniz oluşturuluyor..."):
                        try:
                            res = MBTIAgent().analyze(cevaplar)
                            st.session_state.mbti_report    = res.get("description", "")
                            st.session_state.user_data["mbti_type"] = res.get("mbti_type", "ENFP")
                            st.session_state.mbti_archetype = res.get("archetype", "Gezgin")
                            st.session_state.mbti_completed = True
                            update_user_mbti(st.session_state.username, res.get("mbti_type", ""))
                            if extra and extra.strip():
                                memory.not_ekle(st.session_state.username, extra, "serbest_not")
                            go_tab(0); st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")


# ════════════════════════════════════════════════════════════════════════════
# SEKME 1 — ROTA FORMU
# ════════════════════════════════════════════════════════════════════════════

elif cur == 1:
    if not st.session_state.mbti_completed:
        st.warning("Devam etmek için önce Kimlik Testini tamamlayın.")
        if st.button("Kimlik Testine Git", type="primary"):
            go_tab(0); st.rerun()
        st.stop()

    # ── Profil otomatik yüklenme bildirimi ──────────────────────────────────
    if st.session_state.get("_profil_yuklendi"):
        _ym = st.session_state.user_data.get("mbti_type", "")
        _ya = st.session_state.mbti_archetype
        st.html(f"""
<div style="background:linear-gradient(135deg,#f0ece5,#ece6dd);border:1px solid #d4c9b8;
            border-radius:14px;padding:14px 20px;margin-bottom:16px;
            display:flex;align-items:center;gap:14px;font-family:'Inter',sans-serif">
  <div style="width:36px;height:36px;border-radius:10px;flex-shrink:0;
              background:linear-gradient(135deg,#2c2416,#6b4c35);
              display:flex;align-items:center;justify-content:center;
              font-size:15px;color:white">🧬</div>
  <div style="flex:1">
    <div style="font-size:13px;font-weight:700;color:#2c2416">
      Profiliniz otomatik yüklendi:
      <span style="color:#d4976a">{_ym}</span> — {_ya}
    </div>
    <div style="font-size:11.5px;color:#7a6a5a;margin-top:2px">
      Kimlik Testini yeniden çözmek isterseniz sol menüden
      <strong>🧬 Kimlik Testi</strong> sekmesine gidin.
    </div>
  </div>
  <div style="background:#2c2416;border-radius:8px;padding:4px 12px;
              font-size:11px;font-weight:800;color:#e8c99a;flex-shrink:0">{_ym}</div>
</div>""")
        st.session_state["_profil_yuklendi"] = False

    left, right = st.columns([3, 2], gap="large")

    with left:
        page_header("Seyahat Planını Oluştur", "Rotanızı ve tercihlerinizi girin, yapay zeka sizin için planlasın")

        with st.form("travel_form"):
            st.markdown('<div style="font-size:10px;font-weight:700;color:#4f46e5;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:5px">Destinasyon</div>', unsafe_allow_html=True)
            hedef = st.text_input("Destinasyon", value="İstanbul", label_visibility="collapsed",
                                  placeholder="Şehir ya da ülke — Örnek: İstanbul, Roma, İspanya")
            st.markdown(
                '<div style="font-size:11.5px;color:#7a6a5a;margin-top:-6px;line-height:1.7">'
                '<b>Pilot destinasyonlar:</b> ⭐ İstanbul · ' + " · ".join(_d for _d in PILOT_DESTINASYONLAR[1:])
                + '<br>Ülke yazarsan (ör. İspanya, Hollanda) plan o ülkenin pilot şehrinde kurulur; '
                  'listede olmayan şehirler için de plan yapılır.</div>', unsafe_allow_html=True)

            st.markdown('<div style="font-size:10px;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.6px;margin:14px 0 5px">Tarihler</div>', unsafe_allow_html=True)
            d1, d2 = st.columns(2)
            bas = d1.date_input("Giriş", value=date.today())
            bit = d2.date_input("Çıkış", value=date.today())

            st.markdown('<div style="font-size:10px;font-weight:700;color:#d97706;text-transform:uppercase;letter-spacing:0.6px;margin:14px 0 5px">Seyahat Detayları</div>', unsafe_allow_html=True)
            r1, r2, r3 = st.columns(3)
            kisi       = r1.number_input("Kişi Sayısı", min_value=1, max_value=20, value=1)
            ulasim_sec = r2.selectbox("Ulaşım", ["Uçak", "Otobüs", "Tren", "Araba"])
            butce_kat  = r3.selectbox("Bütçe", ["ekonomik", "orta", "luks"],
                            format_func=lambda x: {"ekonomik": "Ekonomik", "orta": "Orta", "luks": "Lüks"}[x])

            st.markdown('<div style="font-size:10px;font-weight:700;color:#db2777;text-transform:uppercase;letter-spacing:0.6px;margin:14px 0 5px">Bütçe Kısıtı</div>', unsafe_allow_html=True)
            b1, b2 = st.columns([1.2, 1])
            butce        = b1.number_input("Toplam Bütçe Üst Sınırı (TL)", min_value=500, value=25_000, step=500,
                                           help="Tüm grup için; konaklama, yemek, ulaşım ve girişler dahil.")
            b2.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
            butce_uygula = b2.checkbox("Maliyet tasarrufu", value=True,
                                         help="Açıksa plan bu bütçeyi aşmayacak şekilde ayarlanır.")

            st.markdown('<div style="font-size:10px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:0.6px;margin:14px 0 5px">Serbest Not — Bu geziden ne bekliyorsun?</div>', unsafe_allow_html=True)
            serbest_not = st.text_area(
                "Serbest not", label_visibility="collapsed", height=110, max_chars=1500,
                placeholder="Kendi cümlelerinle yaz — testten önceliklidir. Örn: Kalabalık yerleri sevmem, "
                            "müze ve sanat galerilerine bayılırım. Vejetaryenim, akşamları sakin bir yer isterim.")

            submitted = st.form_submit_button("✈️ Planımı Oluştur", type="primary")

        if submitted:
            errors = []
            if not hedef.strip(): errors.append("Şehir adı boş bırakılamaz.")
            if bit < bas:         errors.append("Çıkış tarihi başlangıçtan önce olamaz.")
            for err in errors:
                st.error(err)

            if not errors and (bit - bas).days + 1 > 14:
                errors.append("En fazla 14 günlük plan oluşturulabilir.")
                st.error(errors[-1])

            if not errors:
                gun_farki = (bit - bas).days + 1
                # Plan sayfasının başlık kartı için gereken alanlar
                t_data = {
                    "destination": hedef.strip(), "start_date": str(bas), "end_date": str(bit),
                    "group_size": int(kisi), "transport": ulasim_sec,
                    "mbti_type": st.session_state.user_data.get("mbti_type", "ENFP"),
                }
                istek = {
                    "sehir": hedef.strip(), "gun": gun_farki, "kisi": int(kisi),
                    "butce_kategorisi": butce_kat, "butce_limiti": float(butce) if butce_uygula else None,
                    "mbti": t_data["mbti_type"], "serbest_not": serbest_not.strip(),
                    "ulasim": ulasim_sec, "baslangic": str(bas),
                }

                # Ajanlar çalışırken ilerleme paneli: çubuk + o anki adım + adım kaydı
                _panel = st.empty()
                _ilerleme = {"yuzde": 4, "adim": "Başlatılıyor…", "kayit": []}

                def _ciz(durum="calisiyor"):
                    _panel.markdown(ilerleme_paneli_html(_ilerleme["yuzde"], _ilerleme["adim"],
                                                         _ilerleme["kayit"], durum), unsafe_allow_html=True)

                def _adim(yuzde, metin, alt=""):
                    _ilerleme.update(yuzde=yuzde, adim=metin)
                    _ilerleme["kayit"].append((metin, alt))
                    _ciz()

                # Ülke yazıldıysa (ör. İspanya) hava, planın kurulacağı şehirden alınır
                _hava_sehri = poi_data.hedef_coz(hedef.strip())["sehir"] or hedef.strip()
                _konum = poi_data.sehir_koordinati(_hava_sehri)
                _hava = hava.simdiki_hava(_konum["lat"], _konum["lon"]) if _konum else None
                _adim(8, f"{_hava_sehri} için hava durumu alınıyor",
                      f"{_hava['sicaklik']}°C, {_hava['durum']}" if _hava else "hava bilgisi alınamadı")

                _goruldu = set()

                def _canli(m):
                    if m.gonderen == "hafiza" and "hafiza" not in _goruldu:
                        _goruldu.add("hafiza")
                        _adim(16, "Hafıza — geçmiş geziler hatırlanıyor", m.icerik)
                    elif m.gonderen == "profil" and "profil" not in _goruldu:
                        _goruldu.add("profil")
                        _adim(30, "Ajan 1 — kişilik profili çıkarılıyor")
                    elif m.gonderen == "plan" and m.tur == "istek" and m.veri.get("adaylar") is not None:
                        _adim(52, f"Ajan 2 — plan & eleştirmen diyaloğu ({len(m.veri['adaylar'])} yer seçiliyor)")
                    elif m.gonderen == "elestirmen" and m.tur == "ret":
                        _ilerleme["kayit"].append((f"Eleştirmen {len(m.veri.get('reddedilen', []))} öneriyi geri gönderdi",
                                                   "uygun olmayanlar yeniden seçiliyor"))
                        _ciz()
                    elif m.gonderen == "rota" and "rota" not in _goruldu:
                        _goruldu.add("rota")
                        _adim(74, "Ajan 3 — rota optimizasyonu (NN, 2-opt, KKO, GA)")
                    elif m.gonderen == "maliyet" and "maliyet" not in _goruldu:
                        _goruldu.add("maliyet")
                        _adim(88, "Ajan 4 — maliyet tahmini ve bütçe kontrolü")
                    elif m.gonderen == "maliyet" and m.icerik.startswith("Müzakere turu"):
                        _ilerleme["kayit"].append(("Bütçe müzakeresi", m.icerik.split(":", 1)[-1].strip()[:90]))
                        _ciz()

                try:
                    sonuc = Orkestrator(dinleyici=_canli).planla(istek, st.session_state.username)
                except Exception as e:
                    _ilerleme["adim"] = "Plan oluşturulamadı"
                    _ciz("hata")
                    if isinstance(e, (RuntimeError, ValueError)):      # beklenen durum: sade mesaj
                        st.warning(str(e), icon="🧭")
                    else:
                        st.error("Plan oluşturulurken beklenmeyen bir sorun oluştu. Lütfen tekrar dene.")
                        import traceback
                        with st.expander("Teknik detay"):
                            st.code(traceback.format_exc())
                    st.stop()
                _ilerleme.update(yuzde=100, adim="Planın hazır — plan sayfası açılıyor")
                _ciz("bitti")

                kis = sonuc["maliyet"]["kisisel"]["kalemler"]
                # Ülke yazıldıysa plan seçilen şehirde kurulur: "Barcelona (İspanya)"
                if sonuc["istek"].get("hedef_girdi"):
                    _g = sonuc["istek"]["hedef_girdi"].strip()
                    _g = ("İ" if _g[:1] == "i" else _g[:1].upper()) + _g[1:]     # Türkçe büyük harf: ispanya → İspanya
                    hedef = f"{sonuc['istek']['sehir']} ({_g})"
                    t_data["destination"] = hedef
                plan = {
                    "destination":       hedef.strip(),
                    "duration_days":     gun_farki,
                    "estimated_cost":    kis["toplam"],
                    "html_report":       gunluk_html(sonuc),
                    "start_date": str(bas), "end_date": str(bit),
                    "group_size": int(kisi), "transport": ulasim_sec,
                    "butce_kategorisi": butce_kat,
                    "sonuc": sonuc,
                }
                st.session_state.travel_history.append(plan)
                st.session_state.last_plan      = plan
                st.session_state.last_t_data    = t_data

                try:
                    duraklar = [p["isim"] for g in sonuc["rota"]["gunler"] for p in g["duraklar"]]
                    ozet = (f"{hedef.strip()} · {gun_farki} gün · {len(duraklar)} durak: "
                            + ", ".join(duraklar[:6]) + ("…" if len(duraklar) > 6 else "")
                            + f". {sonuc['profil'].get('seyahat_notu', '')}")
                    plan_id = save_travel_history(st.session_state.username, {
                        "destination":    hedef.strip(),
                        "start_date":     str(bas),
                        "end_date":       str(bit),
                        "duration_days":  gun_farki,
                        "group_size":     int(kisi),
                        "transport":      ulasim_sec,
                        "budget":         butce_kat,
                        "mbti_type":      t_data["mbti_type"],
                        "estimated_cost": kis["toplam"],
                        "plan_ozeti":     ozet[:1200],
                        "full_plan":      plan,
                    })
                    hafizaya_kaydet(st.session_state.username, sonuc, plan_id)
                    plan["_id"] = plan_id
                except Exception as e:
                    st.warning(f"Plan oluşturuldu ama hafızaya kaydedilemedi: {e}")

                go_tab(2); st.rerun()

    with right:
        mbti_cur = st.session_state.user_data.get("mbti_type", "?")
        arch_cur = st.session_state.mbti_archetype
        renk     = renk_map.get(mbti_cur, "#4f46e5")
        blog     = MBTI_BLOG.get(mbti_cur, "Seyahat tarzınız tamamen kendinize özgü.")

        st.markdown(f"""
<div style="border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);margin-top:42px">
  <div style="background:linear-gradient(150deg,{renk},{renk}cc);padding:22px;color:white">
    <div style="font-size:9px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Gezgin Profili</div>
    <div style="font-size:34px;font-weight:900;letter-spacing:-1px;line-height:1">{mbti_cur}</div>
    <div style="font-size:12px;opacity:0.85;margin-top:7px;font-weight:500">{arch_cur}</div>
  </div>
  <div style="background:white;padding:16px 18px">
    <div style="font-size:12px;color:#374151;line-height:1.75">{blog}</div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Hafıza paneli ──────────────────────────────────────────────────────
        _hz = memory.hafiza_baglami(st.session_state.username)
        _sehirler = _hz["ziyaret_edilen_yerler"]
        _sehir_satir = "".join(
            f'<div style="display:flex;justify-content:space-between;font-size:11.5px;padding:4px 0;'
            f'border-bottom:1px solid #f3efe9"><span>{_html.escape(str(_s))}</span><span style="color:#8b7355;font-weight:700">'
            f'{len(set(_y))} yer</span></div>'
            for _s, _y in list(_sehirler.items())[:6])
        _fb = len(_hz["geri_bildirimler"])
        st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:16px 18px;margin-top:14px">
  <div style="font-size:10px;font-weight:800;color:#8b7355;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">
    💾 Seni hatırlıyoruz</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px">
    <div style="background:#f2ede6;border-radius:8px;padding:8px;text-align:center">
      <div style="font-size:18px;font-weight:900;color:#2c2416">{_hz['seyahat_sayisi']}</div>
      <div style="font-size:9.5px;color:#7a6a5a">seyahat</div></div>
    <div style="background:#eef0eb;border-radius:8px;padding:8px;text-align:center">
      <div style="font-size:18px;font-weight:900;color:#2c2416">{sum(len(set(v)) for v in _sehirler.values())}</div>
      <div style="font-size:9.5px;color:#7a6a5a">gidilen yer</div></div>
    <div style="background:#f5ede6;border-radius:8px;padding:8px;text-align:center">
      <div style="font-size:18px;font-weight:900;color:#2c2416">{_fb}</div>
      <div style="font-size:9.5px;color:#7a6a5a">geri bildirim</div></div>
  </div>
  {_sehir_satir or '<div style="font-size:11.5px;color:#9a8a7a">Henüz kayıtlı gezi yok — ilk planından sonra burada görünecek.</div>'}
  <div style="font-size:10.5px;color:#9a8a7a;margin-top:8px;line-height:1.5">
    Daha önce gittiğin yerler tekrar önerilmez; gezi sonrası yorumların bir sonraki planı şekillendirir.</div>
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SEKME 2 — PLAN SONUCU
# ════════════════════════════════════════════════════════════════════════════

elif cur == 2:
    page_header("Plan Sonucu")
    if not st.session_state.last_plan:
        st.info("Henüz plan oluşturulmadı. 'Rota Formu' sekmesinden bir plan oluşturun.")
    else:
        import re as _re, base64 as _b64

        plan        = st.session_state.last_plan
        t_d2        = st.session_state.last_t_data or {}
        dest_up     = t_d2.get("destination", plan.get("destination", "")).capitalize()
        bas2        = t_d2.get("start_date", "")
        bit2        = t_d2.get("end_date", "")
        kisi2       = t_d2.get("group_size", 1)
        trans2      = t_d2.get("transport", "")
        mbti2       = t_d2.get("mbti_type", "")
        days2       = plan.get("duration_days", 1)
        cost2       = float(plan.get("estimated_cost") or 0)
        html_report = plan.get("html_report", "")
        if plan.get("sonuc"):
            # Gün kartları kayıtlı plan verisinden yeniden üretilir — eski planlar da güncel görünümü alır
            try:
                html_report = gunluk_html(plan["sonuc"])
            except Exception:
                pass

        # ── Landmark carousel — base64 (kota hatası olsa da çalışır) ─────────
        _WIKI_HDR = {"User-Agent": "SmartTravelAI/1.0 (edu; ilaydanudak@icloud.com)"}
        _LANDMARK_DB = {
            "istanbul":  ["Hagia Sophia","Topkapi Palace","Bosphorus","Grand Bazaar, Istanbul","Galata Tower","Blue Mosque","Dolmabahce Palace","Basilica Cistern"],
            "ankara":    ["Anıtkabir","Ankara Castle","Museum of Anatolian Civilizations","Kocatepe Mosque","Atatürk Forest Farm"],
            "izmir":     ["Ephesus","Kadifekale","Kordon, İzmir","Asansör, İzmir","Agora of Smyrna","Çeşme"],
            "antalya":   ["Perge","Aspendos","Kaleiçi","Düden Waterfalls","Hadrian's Gate","Termessos"],
            "roma":      ["Colosseum","Trevi Fountain","Pantheon, Rome","Roman Forum","Vatican Museums","Piazza Navona","Spanish Steps","Castel Sant'Angelo"],
            "paris":     ["Eiffel Tower","Louvre Museum","Notre-Dame de Paris","Sacré-Cœur, Paris","Palace of Versailles","Musée d'Orsay","Arc de Triomphe","Seine"],
            "barcelona": ["Sagrada Família","Park Güell","La Rambla","Camp Nou","Gothic Quarter, Barcelona","Casa Batlló","Barceloneta Beach","Palau de la Música Catalana"],
            "amsterdam": ["Rijksmuseum","Anne Frank House","Van Gogh Museum","Vondelpark","Keukenhof","Heineken Experience","A'DAM Tower"],
            "prag":      ["Prague Castle","Charles Bridge","Old Town Square, Prague","Prague Astronomical Clock","Wenceslas Square","Petřín","Josefov"],
            "viyana":    ["Schönbrunn Palace","St. Stephen's Cathedral, Vienna","Belvedere, Vienna","Vienna State Opera","Hofburg","Prater","Kunsthistorisches Museum"],
            "londra":    ["Tower of London","Buckingham Palace","Big Ben","Tower Bridge","British Museum","Tate Modern","Hyde Park","Westminster Abbey"],
            "dubai":     ["Burj Khalifa","Palm Jumeirah","Dubai Mall","Dubai Frame","Burj Al Arab","Dubai Creek","Gold Souk, Dubai","Dubai Museum"],
            "tokyo":     ["Tokyo Tower","Senso-ji","Shibuya crossing","Shinjuku Gyoen","Tokyo Skytree","Meiji Shrine","Akihabara","teamLab Borderless"],
            "bangkok":   ["Grand Palace, Bangkok","Wat Pho","Wat Arun","Chatuchak Weekend Market","Khao San Road","Lumphini Park","Jim Thompson House"],
            "atina":     ["Acropolis of Athens","Parthenon","National Archaeological Museum, Athens","Plaka","Temple of Hephaestus","Monastiraki","Panathenaic Stadium"],
            "budapeste": ["Hungarian Parliament Building","Buda Castle","Chain Bridge, Budapest","Fisherman's Bastion","Széchenyi thermal bath","Matthias Church","Heroes' Square"],
            "tiflis":    ["Narikala","Tbilisi Old Town","Bridge of Peace, Tbilisi","Metekhi Church","Mtatsminda","Anchiskhati Basilica"],
            "new york":  ["Statue of Liberty","Empire State Building","Central Park","Times Square","Brooklyn Bridge","Metropolitan Museum of Art","High Line","One World Trade Center"],
            "singapur":  ["Marina Bay Sands","Gardens by the Bay","Merlion","Sentosa Island","Chinatown, Singapore","Clarke Quay","Singapore Botanic Gardens"],
            "marakes":   ["Jemaa el-Fna","Koutoubia","Bahia Palace","Medina of Marrakesh","Majorelle Garden","Saadian Tombs","Mouassine Fountain"],
            "bali":      ["Tanah Lot","Uluwatu Temple","Tegallalang Rice Terraces","Sacred Monkey Forest Sanctuary","Besakih Temple","Tirta Empul","Pura Luhur Batukaru"],
            "salzburg":  ["Hohensalzburg Fortress","Mirabell Palace","Mozart Birthplace","Hellbrunn Palace","Untersberg"],
            "floransa":  ["Uffizi Gallery","Florence Cathedral","Ponte Vecchio","Piazzale Michelangelo","Palazzo Vecchio","Baptistery of Saint John"],
            "lizbon":    ["Belém Tower","Jerónimos Monastery","Sintra","Alfama","LX Factory","Praça do Comércio"],
            "edinburgh": ["Edinburgh Castle","Arthur's Seat","Holyrood Palace","Royal Mile","Greyfriars Kirkyard","Calton Hill"],
            "kyoto":     ["Fushimi Inari","Kinkaku-ji","Arashiyama Bamboo Grove","Gion","Nijo Castle","Ryoan-ji","Philosopher's Path"],
        }

        @st.cache_data(show_spinner=False, ttl=86400)
        def _carousel_b64(sehir: str) -> list:
            """Landmark fotoğraflarını base64 data URI listesi olarak döndürür."""
            try:
                import requests as _rq
                api  = "https://en.wikipedia.org/w/api.php"
                key  = (sehir.lower()
                        .replace("ı","i").replace("ş","s").replace("ğ","g")
                        .replace("ü","u").replace("ö","o").replace("ç","c"))
                titles = next((v for k, v in _LANDMARK_DB.items() if k in key or key.startswith(k)), [])

                # Thumbnail URL'lerini topla
                urls, seen = [], set()
                if titles:
                    r = _rq.get(api, params={"action":"query","titles":"|".join(titles[:8]),
                                              "prop":"pageimages","pithumbsize":1200,"format":"json"},
                                headers=_WIKI_HDR, timeout=7)
                    tm = {pg.get("title",""): pg.get("thumbnail",{}).get("source","")
                          for pg in r.json().get("query",{}).get("pages",{}).values()
                          if pg.get("thumbnail",{}).get("source","")}
                    for t in titles[:8]:
                        u = tm.get(t, "")
                        if u and u not in seen:
                            seen.add(u); urls.append(u)

                # Yedek arama — yalnızca mimari/tarihi yapı görselleri
                _arch_queries = [
                    f"{sehir} historic architecture",
                    f"{sehir} cathedral church mosque temple",
                    f"{sehir} palace castle fortress",
                    f"{sehir} ancient ruins monument",
                    f"{sehir} old town historic district",
                ]
                for q in (_arch_queries if len(urls) < 6 else []):
                    try:
                        sr = _rq.get(api, params={"action":"query","generator":"search",
                                                   "gsrsearch":q,"gsrlimit":6,
                                                   "prop":"pageimages","pithumbsize":1200,"format":"json"},
                                     headers=_WIKI_HDR, timeout=6)
                        for pg in sr.json().get("query",{}).get("pages",{}).values():
                            u = pg.get("thumbnail",{}).get("source","")
                            # Bayrak, ikon, logo, kişi fotoğrafı filtrele
                            if (u and u not in seen and len(urls) < 7
                                    and not any(x in u.lower() for x in
                                                ["flag","icon","logo","portrait","person","people",
                                                 "food","plate","dish","svg","map","coat"])):
                                seen.add(u); urls.append(u)
                        if len(urls) >= 6:
                            break
                    except Exception:
                        continue

                # Her URL'yi indir → base64
                result = []
                for url in urls[:6]:
                    try:
                        ir = _rq.get(url, headers=_WIKI_HDR, timeout=6)
                        if ir.status_code == 200:
                            ct  = ir.headers.get("Content-Type","image/jpeg").split(";")[0]
                            b64 = _b64.b64encode(ir.content).decode()
                            result.append(f"data:{ct};base64,{b64}")
                    except Exception:
                        continue
                return result
            except Exception:
                return []

        galeri = _carousel_b64(dest_up) if dest_up else []

        # ── Hero overlay (header) ─────────────────────────────────────────────
        mbti_badge = (f'<span style="background:rgba(255,255,255,0.18);border-radius:6px;'
                      f'padding:4px 10px;font-size:12px;font-weight:600">{mbti2}</span>'
                      if mbti2 else "")
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#2d221a,#5a3e2d);border-radius:16px;
            padding:22px 26px;color:white;
            display:flex;justify-content:space-between;align-items:flex-end;
            margin-bottom:18px">
  <div>
    <div style="font-size:10px;opacity:0.60;font-weight:700;text-transform:uppercase;
                letter-spacing:0.6px;margin-bottom:6px">Seyahat Planı</div>
    <div style="font-size:30px;font-weight:800;letter-spacing:-0.5px;line-height:1">{dest_up}</div>
    <div style="font-size:13px;opacity:0.80;margin-top:8px;display:flex;gap:14px;flex-wrap:wrap">
      <span>{bas2} — {bit2}</span><span>{days2} Gün</span>
      <span>{kisi2} Kişi</span><span>{trans2}</span>
    </div>
    <div style="margin-top:10px">{mbti_badge}</div>
  </div>
  <div style="text-align:right;flex-shrink:0">
    <div style="font-size:10px;opacity:0.60;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">Tahmini Maliyet</div>
    <div style="font-size:28px;font-weight:900;letter-spacing:-1px">{cost2:,.0f}</div>
    <div style="font-size:12px;opacity:0.70;margin-top:2px">TL · {kisi2} kişi</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Seyahat notu, plan özeti, harita ──────────────────────────────────
        _sonuc2 = plan.get("sonuc")
        if _sonuc2:
            if _sonuc2.get("hedef_notu"):
                st.info(_sonuc2["hedef_notu"], icon="📍")
            st.markdown(seyahat_notu_karti(_sonuc2), unsafe_allow_html=True)
            st.markdown(plan_ozet_html(_sonuc2), unsafe_allow_html=True)
            if _sonuc2.get("haric_tutulan"):
                st.caption("🔁 Hafızadan dolayı tekrar önerilmeyen yerler: "
                           + ", ".join(dict.fromkeys(_sonuc2["haric_tutulan"]))[:400])
            _merkez = _sonuc2["rota"]["merkez"]
            _gunler2 = _sonuc2["rota"]["gunler"]
            try:
                import pydeck as _pdk
                _renkler = [[139, 115, 85], [212, 151, 106], [79, 107, 79], [79, 70, 229],
                            [190, 75, 120], [8, 145, 178], [202, 138, 4]]
                _yollar, _noktalar = [], []
                for _g in _sonuc2["rota"]["gunler"]:
                    _r = _renkler[(_g["gun"] - 1) % len(_renkler)]
                    _yol = [[_merkez["lon"], _merkez["lat"]]] + [[p["lon"], p["lat"]] for p in _g["duraklar"]] \
                           + [[_merkez["lon"], _merkez["lat"]]]
                    _yollar.append({"path": _yol, "renk": _r, "ad": f"Gün {_g['gun']}"})
                    for _i, p in enumerate(_g["duraklar"], start=1):
                        _noktalar.append({"lon": p["lon"], "lat": p["lat"], "renk": _r,
                                          "ad": f"Gün {_g['gun']} · {_i}. {p['isim']}", "no": str(_i)})
                _noktalar.append({"lon": _merkez["lon"], "lat": _merkez["lat"], "renk": [30, 30, 30],
                                  "ad": "Konaklama bölgesi (başlangıç)", "no": "H"})
                st.pydeck_chart(_pdk.Deck(
                    map_provider="carto", map_style="light",
                    initial_view_state=_pdk.ViewState(latitude=_merkez["lat"], longitude=_merkez["lon"], zoom=12.3),
                    layers=[
                        _pdk.Layer("PathLayer", _yollar, get_path="path", get_color="renk",
                                   width_min_pixels=3, pickable=True),
                        _pdk.Layer("ScatterplotLayer", _noktalar, get_position=["lon", "lat"],
                                   get_fill_color="renk", get_radius=70, radius_min_pixels=7, pickable=True),
                        _pdk.Layer("TextLayer", _noktalar, get_position=["lon", "lat"], get_text="no",
                                   get_size=13, get_color=[255, 255, 255], get_alignment_baseline="'center'"),
                    ],
                    tooltip={"text": "{ad}"},
                ), height=380)
                st.caption("Haritadaki numaralar ziyaret sırasıdır; her gün ayrı renkte. "
                           "Altlık: © OpenStreetMap katkıcıları, © CARTO")
            except Exception:
                pass
            _baglanti = " · ".join(f'<a href="{_html.escape(google_maps.rota_linki(_merkez, g["duraklar"]))}" '
                                    f'target="_blank" style="color:#8b7355;font-weight:600">Gün {g["gun"]}</a>'
                                    for g in _gunler2)
            st.markdown(f'<div style="font-size:12px;color:#7a6a5a;margin:-4px 0 14px">🗺️ Rotayı Google Maps’te aç: '
                        f'{_baglanti}</div>', unsafe_allow_html=True)

        # ── Carousel ──────────────────────────────────────────────────────────
        DEST_ACIKLAMA = {
            "istanbul": "İki kıtayı bir arada barındıran, 8000 yıllık tarihin mimariye yansıdığı eşsiz şehir. Boğaz kıyısında antik saraylar, çarşılar ve modern İstanbul iç içedir.",
            "roma": "Batı uygarlığının beşiği, her köşesinde antik bir katman saklı. Kolezyum, Forum ve Vatikan aynı şehirde, yürüyerek gezilebilir mesafede.",
            "paris": "Sanatın, modasının ve gastronominin dünya başkenti. Eiffel Kulesi, Louvre ve Montmartre ile sinema karelerinden fırlamış gibi görünen bir şehir.",
            "barcelona": "Gaudí'nin mimarisi ve Akdeniz enerjisiyle benzersiz bir metropol. Deniz, mimari, yemek ve gece hayatı kusursuz dengede.",
            "tokyo": "40 milyonluk metropolün sıfır kaos toleransıyla işlemesi bir mucize. Anime kültüründen Michelin mutfağına, teknoloji müzelerinden tapınaklara kadar her şey burada.",
            "dubai": "Çöl üzerinde 50 yılda inşa edilmiş imkânsız şehir. Dünyanın en uzun binası, yapay adalar ve lüksün her biçimi bir arada.",
            "amsterdam": "Kanal şehri, düşünce özgürlüğünün ve sanatın anavatanı. Bisikletlerle dolu köprüler, dünya müzeleri ve hoşgörü kültürüyle küçük ama güçlü.",
            "londra": "Tarih ile çağdaşlığın en başarılı evliliği. Türlü kültürün kaynaştığı bu şehirde her mahalle ayrı bir dünya.",
            "viyana": "Klasik müziğin, kahve geleneğinin ve Habsburg mirasının şehri. Müzeler, operalar ve kafeler INTJ ve ESTJ'lerin rüya destinasyonu.",
            "prag": "Orta Avrupa gotik mimarisinin en iyi korunmuş örneği. Kafka'nın labirentimsi sokakları Batı Avrupa fiyatlarının çok altında gezilebilir.",
            "kyoto": "800 tapınak ve 200 bahçesiyle Japonya'nın kültürel kalbi. Fushimi Inari'nin turuncu torii kapıları ve Gion mahallesinin gece estetiği eşsizdir.",
            "bali": "Tanrılara sunulan çiçek seajenlerden oluşan bir ada. Pirinç terrası manzaraları, Hindu tapınakları ve dünyaca ünlü sörf plajları bir arada.",
            "marakes": "Kuzey Afrika'nın en canlı pazarı ve medina kültürü. Djemaa el-Fna meydanında bir akşam, seyahat anılarının zirvesine oturur.",
            "atina": "Demokrasinin, felsefenin ve Batı uygarlığının anavatanı. Akropolis bugün hâlâ şehre hükmeden bir anıt olarak yükselir.",
            "budapeste": "Tuna boyunca uzanan görkemli silueti ve termal hamam kültürüyle Orta Avrupa'nın incisi. Parlamento binası gece fotoğrafçılığının vazgeçilmezidir.",
            "tiflis": "Kafkasya'nın az keşfedilmiş hazinesi; balkon mimarisi, kükürt hamamları ve Gürcü polyphonic müziğinin anavatanı.",
            "singapur": "Dünyanın en verimli şehri. Etnik çeşitlilik, futuristik botanik bahçeler ve lezzetin bir arada bulunduğu küçük ada devleti.",
            "new york": "Dünyanın en ikonik silueti, en çeşitli gastronomi sahnesi ve kültürel üretimin merkezi. Her mahalle ayrı bir şehir gibi.",
        }
        _dcn = dest_up.lower().replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
        aciklama = next((v for k, v in DEST_ACIKLAMA.items() if k in _dcn or _dcn.startswith(k)), None)

        if galeri:
            cid = "car_" + dest_up.lower().replace(" ", "_")
            # Şehir adını fotoğraf sayısıyla carousel başlığında göster
            st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
  <span style="font-size:12px;font-weight:700;color:#2c2416;text-transform:uppercase;letter-spacing:0.4px">{dest_up} — Görsel Galeri</span>
  <span style="font-size:11px;color:#b5a99a;background:#f2ede6;padding:2px 8px;border-radius:20px;border:1px solid #e0d4c4">{len(galeri)} fotoğraf</span>
</div>""", unsafe_allow_html=True)
            imgs_html = "".join(
                f'<div style="flex:0 0 auto;height:260px;width:420px;border-radius:12px;'
                f'overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.18)">'
                f'<img src="{u}" style="width:100%;height:100%;object-fit:cover;display:block;'
                f'filter:sepia(8%) saturate(90%) brightness(1.02);transition:transform .4s ease" '
                f'onmouseover="this.style.transform=\'scale(1.04)\'" '
                f'onmouseout="this.style.transform=\'scale(1)\'" '
                f'onerror="this.parentElement.style.display=\'none\'"/></div>'
                for u in galeri
            )
            st.markdown(f"""
<div style="position:relative;margin-bottom:14px;user-select:none">
  <button onclick="document.getElementById('{cid}').scrollBy({{left:-440,behavior:'smooth'}})"
    style="position:absolute;left:-14px;top:50%;transform:translateY(-50%);z-index:10;
           width:38px;height:38px;border-radius:50%;border:none;cursor:pointer;
           background:white;box-shadow:0 2px 10px rgba(0,0,0,0.18);
           font-size:17px;color:#2d221a;display:flex;align-items:center;justify-content:center;
           transition:box-shadow .2s" onmouseover="this.style.boxShadow='0 4px 16px rgba(0,0,0,0.26)'"
    onmouseout="this.style.boxShadow='0 2px 10px rgba(0,0,0,0.18)'">&#8249;</button>
  <div id="{cid}"
    style="display:flex;gap:10px;overflow-x:auto;scroll-behavior:smooth;
           padding:4px 2px 10px;scrollbar-width:none;-ms-overflow-style:none">
    {imgs_html}
  </div>
  <style>#{cid}::-webkit-scrollbar{{display:none}}</style>
  <button onclick="document.getElementById('{cid}').scrollBy({{left:440,behavior:'smooth'}})"
    style="position:absolute;right:-14px;top:50%;transform:translateY(-50%);z-index:10;
           width:38px;height:38px;border-radius:50%;border:none;cursor:pointer;
           background:white;box-shadow:0 2px 10px rgba(0,0,0,0.18);
           font-size:17px;color:#2d221a;display:flex;align-items:center;justify-content:center;
           transition:box-shadow .2s" onmouseover="this.style.boxShadow='0 4px 16px rgba(0,0,0,0.26)'"
    onmouseout="this.style.boxShadow='0 2px 10px rgba(0,0,0,0.18)'">&#8250;</button>
</div>
""", unsafe_allow_html=True)
            # Şehir açıklama metni
            if aciklama:
                st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:10px;
            padding:12px 16px;margin-bottom:16px;display:flex;gap:10px;align-items:flex-start">
  <span style="font-size:16px;flex-shrink:0">🗺️</span>
  <div style="font-size:12.5px;color:#4a3f35;line-height:1.7">{aciklama}</div>
</div>""", unsafe_allow_html=True)

        # ── Metrik bant — nude tonlar ─────────────────────────────────────────
        gezi_count  = len(_re.findall(r'data-type=["\']gezi["\']',  html_report))
        yemek_count = len(_re.findall(r'data-type=["\']yemek["\']', html_report))
        st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px">
  <div style="background:#f2ede6;border:1px solid #e8dfd4;border-radius:12px;padding:16px;
              text-align:center;border-top:3px solid #8b7355">
    <div style="font-size:10px;color:#7a6a5a;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.4px">Toplam Gün</div>
    <div style="font-size:28px;font-weight:900;color:#2c2416;line-height:1">{days2}</div>
  </div>
  <div style="background:#eef0eb;border:1px solid #dde5d8;border-radius:12px;padding:16px;
              text-align:center;border-top:3px solid #9eaa8f">
    <div style="font-size:10px;color:#7a6a5a;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.4px">Gezi Durağı</div>
    <div style="font-size:28px;font-weight:900;color:#2c2416;line-height:1">{gezi_count or "—"}</div>
  </div>
  <div style="background:#f5ede6;border:1px solid #e8dfd4;border-radius:12px;padding:16px;
              text-align:center;border-top:3px solid #d4976a">
    <div style="font-size:10px;color:#7a6a5a;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.4px">Yemek Durağı</div>
    <div style="font-size:28px;font-weight:900;color:#2c2416;line-height:1">{yemek_count or "—"}</div>
  </div>
  <div style="background:#ede8e0;border:1px solid #e0d4c4;border-radius:12px;padding:16px;
              text-align:center;border-top:3px solid #b5a99a">
    <div style="font-size:10px;color:#7a6a5a;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.4px">Kişi Sayısı</div>
    <div style="font-size:28px;font-weight:900;color:#2c2416;line-height:1">{kisi2}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Destinasyon bilgi kartı ───────────────────────────────────────────
        DEST_BILGI = {
            "istanbul":  {"dil": "Türkçe", "para": "TL (₺)", "zaman": "UTC+3", "hava": "Yazın sıcak, kışın ılık", "vize": "Kimlik kartı yeterli"},
            "ankara":    {"dil": "Türkçe", "para": "TL (₺)", "zaman": "UTC+3", "hava": "Karasal, 4 mevsim", "vize": "Kimlik kartı yeterli"},
            "izmir":     {"dil": "Türkçe", "para": "TL (₺)", "zaman": "UTC+3", "hava": "Akdeniz, yazın çok sıcak", "vize": "Kimlik kartı yeterli"},
            "antalya":   {"dil": "Türkçe", "para": "TL (₺)", "zaman": "UTC+3", "hava": "Akdeniz, yıl boyu sıcak", "vize": "Kimlik kartı yeterli"},
            "roma":      {"dil": "İtalyanca", "para": "Euro (€)", "zaman": "UTC+1/+2", "hava": "Akdeniz, yazın kuru sıcak", "vize": "Pasaport (Schengen)"},
            "paris":     {"dil": "Fransızca", "para": "Euro (€)", "zaman": "UTC+1/+2", "hava": "Ilıman, yaz sıcak kış soğuk", "vize": "Pasaport (Schengen)"},
            "barcelona": {"dil": "İspanyolca/Katalanca", "para": "Euro (€)", "zaman": "UTC+1/+2", "hava": "Akdeniz, yazın sıcak", "vize": "Pasaport (Schengen)"},
            "amsterdam": {"dil": "Hollandaca", "para": "Euro (€)", "zaman": "UTC+1/+2", "hava": "Serin ve yağışlı", "vize": "Pasaport (Schengen)"},
            "prag":      {"dil": "Çekçe", "para": "Çek Korunası", "zaman": "UTC+1/+2", "hava": "4 mevsim belirgin", "vize": "Pasaport (Schengen)"},
            "viyana":    {"dil": "Almanca", "para": "Euro (€)", "zaman": "UTC+1/+2", "hava": "4 mevsim belirgin", "vize": "Pasaport (Schengen)"},
            "londra":    {"dil": "İngilizce", "para": "Sterlin (£)", "zaman": "UTC+0/+1", "hava": "Serin ve yağışlı", "vize": "Pasaport + ETA"},
            "dubai":     {"dil": "Arapça/İngilizce", "para": "AED (د.إ)", "zaman": "UTC+4", "hava": "Çöl, yazın çok sıcak", "vize": "30 gün vizesiz"},
            "tokyo":     {"dil": "Japonca", "para": "Yen (¥)", "zaman": "UTC+9", "hava": "4 mevsim, yazın nemli", "vize": "90 gün vizesiz"},
            "bangkok":   {"dil": "Tayca", "para": "Baht (฿)", "zaman": "UTC+7", "hava": "Tropikal, yüksek nem", "vize": "30 gün vizesiz"},
            "marakes":   {"dil": "Arapça/Fransızca", "para": "Dirhem (MAD)", "zaman": "UTC+1", "hava": "Yarı-kurak, yazın çok sıcak", "vize": "90 gün vizesiz"},
            "atina":     {"dil": "Yunanca", "para": "Euro (€)", "zaman": "UTC+2/+3", "hava": "Akdeniz, yazın çok sıcak", "vize": "Pasaport (Schengen)"},
            "budapeste": {"dil": "Macarca", "para": "Forint (Ft)", "zaman": "UTC+1/+2", "hava": "4 mevsim belirgin", "vize": "Pasaport (Schengen)"},
            "tiflis":    {"dil": "Gürcüce", "para": "Lari (₾)", "zaman": "UTC+4", "hava": "Ilıman, 4 mevsim", "vize": "365 gün vizesiz"},
            "new york":  {"dil": "İngilizce", "para": "Dolar ($)", "zaman": "UTC-5/-4", "hava": "4 mevsim belirgin", "vize": "ESTA zorunlu"},
            "singapur":  {"dil": "İngilizce/Çince", "para": "SGD ($)", "zaman": "UTC+8", "hava": "Tropikal, sıcak ve nemli", "vize": "30 gün vizesiz"},
            "bali":      {"dil": "Endonezçe", "para": "Rupiah (Rp)", "zaman": "UTC+8", "hava": "Tropikal, yağışlı sezon Ekim–Nisan", "vize": "30 gün vizesiz"},
        }
        dest_norm = (dest_up.lower()
                     .replace("ı","i").replace("ş","s").replace("ğ","g")
                     .replace("ü","u").replace("ö","o").replace("ç","c"))
        bilgi = next((v for k, v in DEST_BILGI.items() if k in dest_norm or dest_norm.startswith(k)), None)
        if bilgi:
            badges = "".join([
                f'<div style="background:#f2ede6;border:1px solid #e8dfd4;border-radius:10px;'
                f'padding:10px 14px;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="font-size:11px;color:#7a6a5a;font-weight:600">{k}</span>'
                f'<span style="font-size:12px;color:#2c2416;font-weight:500">{v}</span></div>'
                for k, v in [("Dil", bilgi["dil"]), ("Para Birimi", bilgi["para"]),
                              ("Zaman Dilimi", bilgi["zaman"]), ("İklim", bilgi["hava"])]
            ])
            st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:18px 20px;margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-size:13px;font-weight:700;color:#2c2416">{dest_up} Hakkında</span>
    <span style="background:#eef0eb;color:#5a7a5a;font-size:11px;font-weight:700;
                 padding:3px 10px;border-radius:20px;border:1px solid #c0d0b8">
      Vize: {bilgi["vize"]}
    </span>
  </div>
  <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px">{badges}</div>
</div>
""", unsafe_allow_html=True)

        # ── Plan HTML — gün tabları ───────────────────────────────────────────
        if html_report:
            # Kart kenar renkleri plan_render.CSS içinde tanımlı
            style_m     = _re.search(r'<style>.*?</style>', html_report, _re.DOTALL)
            style_block = style_m.group(0) if style_m else ""
            body_only   = _re.sub(r'<style>.*?</style>', '', html_report, flags=_re.DOTALL).strip()
            parcalar    = _re.split(r'(?=<div[^>]*class=["\']gun-baslik["\'])', body_only)
            gun_parcalari = [p for p in parcalar if "gun-baslik" in p]

            # ── Araç çubuğu: indir butonu (PDF, doğrudan masaüstüne) ─────────
            col_ind, _ = st.columns([1.3, 4.7])
            with col_ind:
                if st.button("⬇ Planı İndir", key="plan_indir", use_container_width=True, type="primary"):
                    try:
                        kaynaklar = gun_parcalari if len(gun_parcalari) > 1 else [body_only]
                        gun_metinleri = []
                        for parca in kaynaklar:
                            t = _re.sub(r'<[^>]+>', ' ', parca)
                            t = _re.sub(r'[ \t]{2,}', ' ', t).strip()
                            if t:
                                gun_metinleri.append(t)
                        pdf_bytes = _plan_pdf_bytes(
                            f"{dest_up} Seyahat Planı",
                            f"{bas2} – {bit2}  ·  {kisi2} kişi  ·  {days2} gün  ·  {cost2:,.0f} TL",
                            gun_metinleri,
                        )
                        dosya_adi = f"{dest_up.lower().replace(' ', '_')}_plan.pdf"
                        hedef_yol = os.path.join(_masaustu_klasoru(), dosya_adi)
                        with open(hedef_yol, "wb") as f:
                            f.write(pdf_bytes)
                        st.success(f"Plan masaüstüne kaydedildi: {dosya_adi}", icon="✅")
                    except Exception as e:
                        st.error(f"Plan indirilemedi: {e}")

            if len(gun_parcalari) > 1:
                gun_isimleri = []
                for idx_g, gi in enumerate(gun_parcalari):
                    m2 = _re.search(r'class=["\']gun-baslik["\'][^>]*>(.*?)</div>', gi, _re.DOTALL)
                    raw = _re.sub(r'<[^>]+>', '', m2.group(1)).strip() if m2 else f"Gün {idx_g+1}"
                    lbl = raw[:22] or f"Gün {idx_g+1}"
                    gun_isimleri.append(lbl if lbl not in gun_isimleri else f"{lbl} ({idx_g+1})")
                tabs = st.tabs(gun_isimleri)
                for tab, icerik in zip(tabs, gun_parcalari):
                    with tab:
                        st.html(f"<style>body{{margin:0;padding:0}}</style>{style_block}"
                                f"<div class='plan-wrap'>{icerik}</div>")
            else:
                st.html(f"<style>body{{margin:0;padding:0}}</style>{style_block}"
                        f"<div class='plan-wrap'>{body_only}</div>")

        # ── Planın devamı: bütçe, yeme-içme, yedek yerler, ipuçları ──────────
        if _sonuc2:
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            _sol, _sag = st.columns([1, 1], gap="medium")
            with _sol:
                st.markdown(butce_dokum_html(_sonuc2), unsafe_allow_html=True)
            with _sag:
                st.markdown(ipuclari_html(_sonuc2), unsafe_allow_html=True)
                st.markdown(restoran_listesi_html(_sonuc2), unsafe_allow_html=True)
            st.markdown(yedek_yerler_html(_sonuc2), unsafe_allow_html=True)
            if st.button("🧳 Gezi hazırlığına geç", type="primary"):
                go_tab(3); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# SEKME 3 — GEZİ HAZIRLIĞI
# ════════════════════════════════════════════════════════════════════════════

elif cur == 3:
    page_header("Gezi Hazırlığı", "Tatil listen ve günlük harcama planın")
    _s3 = (st.session_state.last_plan or {}).get("sonuc")
    if not _s3:
        st.info("Önce Rota Formu'ndan bir plan oluştur — hazırlık listesi planına ve profiline göre hazırlanır.")
    else:
        _i3 = _s3["istek"]
        _anahtar = f"{_i3['sehir']}|{_i3.get('baslangic', '')}|{_i3['gun']}|{_s3['maliyet']['kisisel']['kalemler']['toplam']}"
        import hashlib as _hl
        _hk = _hl.md5(_anahtar.encode()).hexdigest()[:8]
        _isaretli = memory.hazirlik_oku(st.session_state.username, _anahtar)
        _tatil = hazirlik.tatil_listesi(_s3)
        _tum_maddeler = [f"t:{m}" for _, liste in _tatil for m in liste]
        _biten = sum(1 for m in _tum_maddeler if m in _isaretli)

        _kg = hazirlik.kalan_gun(_i3.get("baslangic", ""))
        if _kg is None:
            _kg_txt = ""
        elif _kg > 1:
            _kg_txt = f"Yolculuğa <b>{_kg} gün</b> kaldı"
        elif _kg == 1:
            _kg_txt = "Yolculuk <b>yarın</b>!"
        elif _kg == 0:
            _kg_txt = "Bugün yola çıkıyorsun — iyi yolculuklar!"
        else:
            _kg_txt = "Bu gezi tamamlandı — Seyahatlerim sekmesinden nasıl geçtiğini anlat."
        _yuzde = int(_biten / max(1, len(_tum_maddeler)) * 100)
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#2d221a,#5a3e2d);border-radius:16px;padding:20px 24px;color:white;
            display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;gap:16px">
  <div>
    <div style="font-size:10px;opacity:.6;text-transform:uppercase;letter-spacing:.6px">Hazırlık</div>
    <div style="font-size:24px;font-weight:800;margin:4px 0">{_html.escape(_i3['sehir'])} · {_i3['gun']} gün · {_i3['kisi']} kişi</div>
    <div style="font-size:13px;opacity:.85">{_kg_txt}</div>
  </div>
  <div style="text-align:right;min-width:150px">
    <div style="font-size:28px;font-weight:900">%{_yuzde}</div>
    <div style="font-size:11px;opacity:.7">{_biten}/{len(_tum_maddeler)} madde hazır</div>
    <div style="background:rgba(255,255,255,.18);border-radius:6px;height:7px;margin-top:6px">
      <div style="background:#e8c99a;height:7px;border-radius:6px;width:{_yuzde}%"></div></div>
  </div>
</div>""", unsafe_allow_html=True)

        def _isaret_degisti(madde, anahtar_widget):
            secili = memory.hazirlik_oku(st.session_state.username, _anahtar)
            if st.session_state.get(anahtar_widget):
                secili.add(madde)
            else:
                secili.discard(madde)
            memory.hazirlik_kaydet(st.session_state.username, _anahtar, secili)

        def _poster():
            """Tatil listesi: 3 sütunlu kategori kartları + Notlar (uygulamanın kart stilinde)."""
            with st.container(key="tatil_listesi"):
                st.markdown(
                    '<div class="tl-ust"><div><div class="tl-ust-etiket">✈️ Tatil listesi</div>'
                    '<div class="tl-baslik">Her şey hazır, güzel anılar bizi bekliyor</div>'
                    '<div class="tl-alt">Planına, mevsime ve tercihlerine göre hazırlandı.</div></div></div>',
                    unsafe_allow_html=True)

                def kart(anahtar, maddeler):
                    baslik, ikon, renk = hazirlik.TATIL_KATEGORILERI[anahtar]
                    biten_k = sum(1 for m in maddeler if f"t:{m}" in _isaretli)
                    with st.container(key=f"tlkart_{anahtar}"):
                        st.markdown(
                            f'<div class="tl-kart-baslik"><span class="tl-ikon" style="background:{renk}">{ikon}</span>'
                            f'<span class="tl-etiket">{baslik}</span>'
                            f'<span class="tl-sayac">{biten_k}/{len(maddeler)}</span></div>', unsafe_allow_html=True)
                        for i, madde in enumerate(maddeler):
                            wk = f"hz_{_hk}_{anahtar}_{i}"
                            st.checkbox(madde, value=f"t:{madde}" in _isaretli, key=wk,
                                        on_change=_isaret_degisti, args=(f"t:{madde}", wk))
                        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

                kartlar = list(_tatil)
                son_satir = kartlar[-1:] if len(kartlar) % 3 == 1 else (kartlar[-2:] if len(kartlar) % 3 == 2 else [])
                ust = kartlar[:len(kartlar) - len(son_satir)] if son_satir else kartlar
                for r in range(0, len(ust), 3):
                    for kol, (a, m) in zip(st.columns(3, gap="medium"), ust[r:r + 3]):
                        with kol:
                            kart(a, m)
                    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

                # Son satır: kalan kart(lar) + Notlar kartı (fotoğraftaki gibi)
                oranlar = [1] * len(son_satir) + [3 - len(son_satir)] if son_satir else [1]
                kolonlar = st.columns(oranlar, gap="medium")
                for kol, (a, m) in zip(kolonlar, son_satir):
                    with kol:
                        kart(a, m)
                with kolonlar[-1]:
                    with st.container(key="tlkart_notlar"):
                        st.markdown('<div class="tl-kart-baslik"><span class="tl-ikon" style="background:#f2ede6">📝</span>'
                                    '<span class="tl-etiket">Notlar</span></div>', unsafe_allow_html=True)
                        nk = f"hz_{_hk}_not"
                        st.text_area("Notlar", value=memory.hazirlik_not_oku(st.session_state.username, _anahtar),
                                     key=nk, height=130, label_visibility="collapsed",
                                     placeholder="Unutmamak istediğin bir şey yaz…",
                                     on_change=lambda: memory.hazirlik_not_kaydet(
                                         st.session_state.username, _anahtar, st.session_state.get(nk, "")))
                st.markdown('<div class="tl-alt-yazi">İyi tatiller ✈️</div>', unsafe_allow_html=True)

        _gh = hazirlik.gunluk_harcama(_s3)
        _gunluk_ort = sum(r["Toplam"] for r in _gh) / max(1, len(_gh))

        _t1, _t2 = st.tabs([f"📝 Tatil Listesi  {_biten}/{len(_tum_maddeler)}",
                            f"💳 Günlük harcama  ~{_gunluk_ort:,.0f} TL"])
        with _t1:
            _poster()
        with _t2:
            st.caption("Kişi başı, gün gün tahmini cep harcaması (yemek, şehir içi ulaşım, giriş ücretleri).")
            _gk = st.columns(len(_gh)) if len(_gh) <= 4 else None
            for _gi, _r in enumerate(_gh):
                _kutu = (f'<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:14px 16px;'
                         f'margin-bottom:10px"><div style="font-size:12px;font-weight:800;color:#8b7355;'
                         f'text-transform:uppercase;letter-spacing:.5px">{_r["Gün"]}</div>'
                         f'<div style="font-size:24px;font-weight:900;color:#2c2416;margin:4px 0 8px">{_r["Toplam"]:,.0f} TL</div>'
                         f'<div style="font-size:12px;color:#6b5a48;line-height:1.8">🍽️ Yemek: {_r["Yemek"]:,.0f} TL<br>'
                         f'🚇 Ulaşım: {_r["Ulaşım"]:,.0f} TL<br>🎟️ Girişler: {_r["Girişler"]:,.0f} TL</div></div>')
                if _gk:
                    _gk[_gi].markdown(_kutu, unsafe_allow_html=True)
                else:
                    st.markdown(_kutu, unsafe_allow_html=True)
            _kk = _s3["maliyet"]["kisisel"]["kalemler"]
            st.caption(f"Konaklama ({_kk['konaklama']:,.0f} TL) ve şehirlerarası ulaşım ({_kk['sehirlerarasi']:,.0f} TL) "
                       "genelde önceden ödendiği için bu tabloya dahil değildir. Rakamlar tahminidir.")


# ════════════════════════════════════════════════════════════════════════════
# SEKME 4 — SEYAHATLERİM
# ════════════════════════════════════════════════════════════════════════════

elif cur == 4:
    page_header("Seyahatlerim", "Gezilerin, gittiğin yerler ve seni nasıl tanıdığımız — hepsi bir arada")
    _u = st.session_state.username
    profile = get_user_profile(_u)
    history = profile.get("travel_history", [])
    _hz4 = memory.hafiza_baglami(_u)
    _ziy4 = memory.ziyaret_edilenler(_u)
    _mal4 = memory.maliyet_kayitlari(_u)
    _not4 = memory.notlar(_u, limit=300)
    _puanlar = [n["puan"] for n in _not4 if n["tur"] == "geri_bildirim" and n.get("puan")]
    _sehirler4 = {(h.get("destination") or "").strip().title() for h in history} | {(z["sehir"] or "").strip().title() for z in _ziy4}
    _sehirler4.discard("")
    _toplam_harcama = sum(float(h.get("estimated_cost") or 0) for h in history)

    # ── Özet ─────────────────────────────────────────────────────────────
    _m1, _m2, _m3, _m4, _m5 = st.columns(5)
    _m1.metric("🧳 Seyahat", len(history))
    _m2.metric("🏙️ Şehir", len(_sehirler4))
    _m3.metric("📍 Gidilen yer", len({(z["sehir"], z["yer"]) for z in _ziy4}))
    _m4.metric("💰 Toplam harcama", f"{_toplam_harcama:,.0f} TL", help="Planların tahmini toplamı")
    _m5.metric("⭐ Memnuniyet", f"{sum(_puanlar) / len(_puanlar):.1f}/5" if _puanlar else "—")

    # ── Harita + seni nasıl tanıyoruz ───────────────────────────────────
    _hl, _hr = st.columns([3, 2], gap="large")
    with _hl:
        st.markdown("#### 🗺️ Gezi haritam")
        _nokta4 = []
        _pal = [[139, 115, 85], [212, 151, 106], [79, 107, 79], [79, 70, 229], [190, 75, 120], [8, 145, 178]]
        _renk_sehir = {}
        with memory.db._conn() as _c4:
            _satirlar = _c4.execute("SELECT sehir, yer, lat, lon FROM ziyaret_edilen_yerler "
                                    "WHERE username=? AND lat IS NOT NULL", (_u,)).fetchall()
        for _r4 in _satirlar:
            _rk = _renk_sehir.setdefault(_r4["sehir"], _pal[len(_renk_sehir) % len(_pal)])
            _nokta4.append({"lat": _r4["lat"], "lon": _r4["lon"], "ad": f"{_r4['yer']} · {_r4['sehir']}", "renk": _rk})
        if _nokta4:
            try:
                import pydeck as _pdk4
                _lat0 = sum(p["lat"] for p in _nokta4) / len(_nokta4)
                _lon0 = sum(p["lon"] for p in _nokta4) / len(_nokta4)
                _yayilim = max(max(p["lat"] for p in _nokta4) - min(p["lat"] for p in _nokta4),
                               max(p["lon"] for p in _nokta4) - min(p["lon"] for p in _nokta4))
                _zoom = 12 if _yayilim < 0.1 else 9 if _yayilim < 1 else 6 if _yayilim < 6 else 4
                st.pydeck_chart(_pdk4.Deck(
                    map_provider="carto", map_style="light",
                    initial_view_state=_pdk4.ViewState(latitude=_lat0, longitude=_lon0, zoom=_zoom),
                    layers=[_pdk4.Layer("ScatterplotLayer", _nokta4, get_position=["lon", "lat"],
                                        get_fill_color="renk", get_radius=90, radius_min_pixels=6, pickable=True)],
                    tooltip={"text": "{ad}"}), height=320)
                st.caption("Planlarındaki bütün duraklar · " + " · ".join(
                    _html.escape(str(s)) for s in _renk_sehir))
            except Exception:
                pass
        else:
            st.info("İlk planını oluşturduğunda gittiğin yerler burada haritada görünecek.")

    with _hr:
        _pr4 = _hz4["onceki_profil"]
        _mb4 = st.session_state.user_data.get("mbti_type", "")
        st.markdown("#### 🧠 Seni nasıl tanıyoruz")
        if _pr4:
            _ilgi4 = " ".join(
                f'<span style="background:#eef0eb;color:#4f6b4f;border-radius:20px;padding:3px 10px;font-size:11px;'
                f'font-weight:600;display:inline-block;margin:2px">{KATEGORI_ETIKET.get(k, k)}</span>'
                for k in _pr4.get("ilgi_alanlari", [])[:6])
            _kac4 = " ".join(
                f'<span style="background:#fbeee4;color:#b0643a;border-radius:20px;padding:3px 10px;font-size:11px;'
                f'font-weight:600;display:inline-block;margin:2px">✕ {KATEGORI_ETIKET.get(k, k)}</span>'
                for k in _pr4.get("kacinilacaklar", []))
            _or4 = "".join(f"<li>{_html.escape(o)}</li>" for o in _pr4.get("gecmis_oruntuler", [])[:4])
            _tempo4 = {"sakin": "Sakin", "dengeli": "Dengeli", "yogun": "Yoğun"}.get(_pr4.get("tempo"), "-")
            st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:14px;padding:16px 18px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="font-size:22px;font-weight:900;color:#2c2416">{_html.escape(_mb4) or '—'}</span>
    <span style="font-size:11px;color:#7a6a5a">{_tempo4} tempo · günde {_pr4.get('gunluk_durak', '-')} durak · {_pr4.get('baslangic_saati', '')}</span>
  </div>
  <div style="font-size:12.5px;color:#4a3f35;line-height:1.6;margin-bottom:8px">{_html.escape(_pr4.get('seyahat_tarzi', ''))}</div>
  <div>{_ilgi4} {_kac4}</div>
  {f'<ul style="font-size:12px;color:#6b5a48;margin:10px 0 0;padding-left:18px">{_or4}</ul>' if _or4 else ''}
  <div style="font-size:10.5px;color:#a89580;margin-top:10px">Her plandan ve yorumlarından sonra güncellenir.</div>
</div>""", unsafe_allow_html=True)
        else:
            st.info("İlk planından sonra ilgi alanların, temponu ve kaçındıklarını burada göreceksin.")

    # ── Harcama geçmişi ─────────────────────────────────────────────────
    if len(_mal4) >= 1:
        st.markdown("#### 💳 Harcama geçmişim")
        _grafik = {}
        for _m in reversed(_mal4):
            _t = str(_m["tarih"])
            _etk = f"{_m['sehir']} · {_t[8:10]}.{_t[5:7]}"
            while _etk in _grafik:
                _etk += " "
            _grafik[_etk] = round(_m["kisisel_tl"])
        st.bar_chart(_grafik, color="#8b7355", horizontal=True,
                     height=min(60 + 38 * len(_grafik), 320), x_label="TL", y_label="")
        if _hz4["gunluk_ortalama_harcama_tl"]:
            st.caption(f"Günlük ortalama harcaman ~{_hz4['gunluk_ortalama_harcama_tl']:,.0f} TL · "
                       f"bütçeyi aşan plan: {_hz4['butce_asim_sayisi']}")

    # ── Gezi günlüğü ────────────────────────────────────────────────────
    st.markdown("#### 📖 Gezi günlüğüm")
    st.caption("Geziden döndükten sonra her planın altındaki “Yorumun bekleniyor” bölümüne kısa bir yorum bırak — "
               "bir sonraki planın buna göre şekillenir.")
    if not history:
        st.markdown("""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:12px;
            padding:36px;text-align:center">
  <div style="font-size:14px;color:#7a6a5a;margin-bottom:4px">Henüz kayıtlı seyahatin yok.</div>
  <div style="font-size:13px;color:#b5a99a">İlk planını Rota Formu'ndan oluştur!</div>
</div>""", unsafe_allow_html=True)
    else:
        for h_idx, record in enumerate(reversed(history)):
            dest   = record.get("destination", "Bilinmiyor").capitalize()
            start  = record.get("start_date", "")
            end    = record.get("end_date", "")
            dur    = record.get("duration_days", 0)
            budget = record.get("budget", record.get("butce_kategorisi","orta"))
            cost   = record.get("estimated_cost", 0)
            mbti   = record.get("mbti_type", "")
            saved  = record.get("saved_at", "")
            trans  = record.get("transport", "—")
            kisi   = record.get("group_size", 1)
            blabel = {"ekonomik": "Ekonomik", "orta": "Orta", "luks": "Lüks"}.get(budget, budget.capitalize() if budget else "—")

            try:
                cost_fmt = f"{float(cost):,.0f}"
            except Exception:
                cost_fmt = str(cost)

            chip = lambda txt, bg, cl: (
                f'<span style="background:{bg};color:{cl};font-size:11px;font-weight:600;'
                f'padding:3px 10px;border-radius:20px;border:1px solid {cl}22">{txt}</span>'
            )
            chips_parts = [
                chip(trans, "#f2ede6", "#8b7355") if trans and trans != "—" else "",
                chip(blabel, "#eef0eb", "#5a7a5a") if blabel and blabel != "—" else "",
                chip(mbti, "#f5ede6", "#c47a45") if mbti else "",
                chip(f"{kisi} kişi", "#ede8e0", "#7a6a5a") if kisi else "",
            ]
            chips_html = " ".join(filter(None, chips_parts))

            st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:16px;
            padding:20px 24px;margin-bottom:12px;
            box-shadow:0 1px 4px rgba(44,36,22,0.06)">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
    <div>
      <div style="font-size:20px;font-weight:800;color:#2c2416;letter-spacing:-0.3px">{dest}</div>
      <div style="font-size:12px;color:#7a6a5a;margin-top:3px">{start} — {end} &nbsp;·&nbsp; {dur} gün</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:22px;font-weight:900;color:#8b7355;letter-spacing:-0.5px">{cost_fmt} TL</div>
      <div style="font-size:10px;color:#b5a99a;margin-top:2px">{saved}</div>
    </div>
  </div>
  <div style="display:flex;gap:6px;flex-wrap:wrap">{chips_html}</div>
</div>""", unsafe_allow_html=True)

            col_gor, col_sil, _ = st.columns([1.7, 0.7, 3.6])
            with col_gor:
                if record.get("full_plan"):
                    if st.button("🔍 Planı Görüntüle", key=f"gecmis_goruntule_{h_idx}"):
                        st.session_state.last_plan = record["full_plan"]
                        st.session_state.last_t_data = {
                            "destination":      record.get("destination", ""),
                            "start_date":       start,
                            "end_date":         end,
                            "group_size":       kisi,
                            "transport":        trans,
                            "mbti_type":        mbti,
                        }
                        go_tab(2)
                        st.rerun()
                else:
                    st.caption("Tam görünüm yok (eski kayıt)")
            with col_sil:
                if st.button("🗑️", key=f"gecmis_sil_{h_idx}", help="Bu planı ve hafızadaki izlerini sil"):
                    if record.get("_id") is not None:
                        delete_travel_plan(st.session_state.username, record["_id"])
                        memory.plan_hafizasini_sil(st.session_state.username, record["_id"])
                    st.rerun()

            # ── Gezi sonrası yorum → hafıza → sonraki plan ──
            _pid = record.get("_id")
            if _pid is not None:
                _plan_notlari = [n for n in memory.notlar(st.session_state.username, limit=200)
                                 if n.get("plan_id") == _pid]
                _sn = next((n for n in _plan_notlari if n["tur"] == "seyahat_notu"), None)
                _gb = [n for n in _plan_notlari if n["tur"] == "geri_bildirim"]
                with st.expander("⭐ Yorumun bekleniyor" if not _gb else "✅ Yorumun kaydedildi"):
                    if _sn and _sn.get("metin"):
                        _kisa = _sn["metin"] if len(_sn["metin"]) <= 260 else _sn["metin"][:257].rsplit(" ", 1)[0] + "…"
                        st.markdown(f'<div class="yorum-notu">📝 {_html.escape(_kisa)}</div>', unsafe_allow_html=True)
                    for _g in _gb:
                        _parca = [("★" * int(_g["puan"]) + "☆" * (5 - int(_g["puan"]))) if _g.get("puan") else ""]
                        if _g.get("begenilen"):
                            _parca.append(f"👍 {_html.escape(_g['begenilen'])}")
                        if _g.get("begenilmeyen"):
                            _parca.append(f"👎 {_html.escape(_g['begenilmeyen'])}")
                        if _g.get("metin"):
                            _parca.append(f"<i>{_html.escape(_g['metin'])}</i>")
                        st.markdown('<div style="font-size:13px;color:#3a2f24;margin-bottom:6px">'
                                    + " · ".join(p for p in _parca if p) + "</div>", unsafe_allow_html=True)
                    with st.form(f"gb_form_{_pid}", clear_on_submit=True):
                        st.markdown('<div style="font-size:13px;color:#6b5a48;margin-bottom:4px">'
                                    'Geziden döndün mü? Yorumun bir sonraki planını şekillendirir.</div>',
                                    unsafe_allow_html=True)
                        _puan = st.radio("Gezi nasıl geçti?", [1, 2, 3, 4, 5], index=3, horizontal=True,
                                         format_func=lambda x: "★" * x, key=f"gb_puan_{_pid}")
                        _c1, _c2 = st.columns(2)
                        _beg = _c1.text_input("Neleri sevdin?", placeholder="Örn: müzeler, sahil yürüyüşü",
                                              key=f"gb_beg_{_pid}")
                        _begm = _c2.text_input("Neleri sevmedin?", placeholder="Örn: kalabalık çarşılar",
                                               key=f"gb_begm_{_pid}")
                        _not = st.text_input("Eklemek istediğin bir şey var mı?", key=f"gb_not_{_pid}",
                                             placeholder="Örn: Sabahları erken başlamak iyi geldi")
                        if st.form_submit_button("Kaydet", type="primary"):
                            memory.not_ekle(st.session_state.username, _not, "geri_bildirim",
                                            record.get("destination"), _pid, _puan, _beg, _begm)
                            st.success("Teşekkürler! Bir sonraki planın bunu dikkate alacak.")
                            st.rerun()

    # ── Gittiğim yerler ──────────────────────────────────────────────────
    st.markdown("#### 📍 Gittiğim yerler")
    st.caption("Bu yerler yeni planlarda tekrar önerilmez.")
    if _ziy4:
        _grup4 = {}
        for z in _ziy4:
            _grup4.setdefault(z["sehir"] or "?", []).append(z)
        _gcols = st.columns(min(3, len(_grup4)))
        for _gi, (_sehir4, _liste4) in enumerate(_grup4.items()):
            with _gcols[_gi % len(_gcols)]:
                _yerler4 = list(dict.fromkeys(z["yer"] for z in _liste4))
                _li4 = "".join(f'<li>{_html.escape(y)}</li>' for y in _yerler4[:12])
                _fazla = f'<div style="font-size:11px;color:#a89580">+{len(_yerler4) - 12} yer daha</div>' if len(_yerler4) > 12 else ""
                st.markdown(f"""
<div style="background:#fffefb;border:1px solid #e8dfd4;border-radius:12px;padding:12px 16px;margin-bottom:10px">
  <div style="display:flex;justify-content:space-between"><b style="color:#2c2416">{_html.escape(str(_sehir4))}</b>
  <span style="font-size:11px;color:#8b7355;font-weight:700">{len(_yerler4)} yer</span></div>
  <ul style="font-size:12px;color:#4a3f35;margin:6px 0 0;padding-left:18px;line-height:1.6">{_li4}</ul>{_fazla}
</div>""", unsafe_allow_html=True)

    with st.expander("➕ Sistem dışında yaptığım bir geziyi ekle"):
        with st.form("elle_gecmis", clear_on_submit=True):
            _e1, _e2 = st.columns([1, 2])
            _es = _e1.text_input("Şehir", placeholder="Örn: İstanbul")
            _ey = _e2.text_input("Gittiğin yerler (virgülle)", placeholder="Örn: Ayasofya, Galata Kulesi, Kapalıçarşı")
            _ec1, _ec2 = st.columns(2)
            _ebeg = _ec1.text_input("Neleri sevdin?", placeholder="Örn: müzeler, deniz kenarı")
            _ebegm = _ec2.text_input("Neleri sevmedin?", placeholder="Örn: kalabalık çarşılar")
            if st.form_submit_button("Seyahatlerime ekle"):
                _yerler = [y.strip() for y in _ey.split(",") if y.strip()]
                if _es.strip() and _yerler:
                    memory.ziyaretleri_kaydet(_u, _es.strip(), _yerler, None)
                    if _ebeg.strip() or _ebegm.strip():
                        memory.not_ekle(_u, "", "geri_bildirim", _es.strip(), None, None, _ebeg, _ebegm)
                    st.success(f"{len(_yerler)} yer eklendi.")
                    st.rerun()
                else:
                    st.warning("Şehir ve en az bir yer gir.")

    # ── Notlarım ────────────────────────────────────────────────────────
    _gorunur = [n for n in _not4 if (n.get("metin") or n.get("begenilen") or n.get("begenilmeyen"))]
    if _gorunur:
        st.markdown("#### 📝 Notlarım")
        _tur_ad = {"serbest_not": ("✍️", "Plana yazdığın not"), "seyahat_notu": ("📝", "Sana özel seyahat notu"),
                   "geri_bildirim": ("⭐", "Gezi sonrası yorumun")}
        for _n in _gorunur[:8]:
            _ik, _ad = _tur_ad.get(_n["tur"], ("•", _n["tur"]))
            _detay = []
            if _n.get("puan"):
                _detay.append(f"{_n['puan']}/5")
            if _n.get("begenilen"):
                _detay.append(f"👍 {_html.escape(_n['begenilen'])}")
            if _n.get("begenilmeyen"):
                _detay.append(f"👎 {_html.escape(_n['begenilmeyen'])}")
            _metin = _html.escape((_n.get("metin") or "")[:400])
            st.markdown(f"""
<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #ece4d9">
  <div style="font-size:18px">{_ik}</div>
  <div style="flex:1"><div style="font-size:11px;color:#9a8a7a">{_ad} · {_html.escape(str(_n.get('sehir') or ''))} · {_n['tarih']}</div>
  <div style="font-size:12.5px;color:#3a2f24;line-height:1.6">{_metin}</div>
  <div style="font-size:12px;color:#6b5a48">{' · '.join(_detay)}</div></div>
</div>""", unsafe_allow_html=True)

    # ── Verilerim ───────────────────────────────────────────────────────
    with st.expander("🔒 Verilerim"):
        _yol4 = memory.json_disa_aktar(_u)
        st.caption("Planların, gittiğin yerler, notların ve tahmini harcamaların bu cihazda saklanır. "
                   "Tamamını tek bir dosya olarak indirebilirsin.")
        if _yol4 and os.path.exists(_yol4):
            with open(_yol4, encoding="utf-8") as _f4:
                st.download_button("⬇ Verilerimi indir (JSON)", _f4.read(), file_name=os.path.basename(_yol4),
                                   mime="application/json")
