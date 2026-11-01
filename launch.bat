@echo off
title SmartTravel AI
cd /d "%~dp0"

echo SmartTravel AI baslatiliyor...

REM Gerekli paketleri kur (ilk calismada)
pip install -r requirements.txt --quiet

REM Streamlit tarayiciyi kendisi acar; bu pencere kapaninca uygulama da kapanir
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
