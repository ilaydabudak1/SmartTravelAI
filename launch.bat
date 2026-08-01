@echo off
title SmartTravel AI
cd /d "%~dp0"

echo SmartTravel AI baslatiliyor...

REM Gerekli paketleri kur (ilk calismada)
pip install -r requirements.txt --quiet

REM Streamlit'i arka planda baslat
start "" /B streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false

REM Biraz bekle, sonra tarayiciyi ac
timeout /t 3 /nobreak > nul
start http://localhost:8501

echo Uygulama acildi! Tarayici penceresi gozukmuyorsa http://localhost:8501 adresini ac.
echo Kapatmak icin bu pencereyi kapatin veya Ctrl+C tuslayın.

REM Streamlit procesini on planda tut (kapatilinca app da kapansin)
streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
