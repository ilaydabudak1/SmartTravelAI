import os, sys, time, socket, atexit, subprocess, urllib.request, webview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PY   = os.path.join(BASE_DIR, "app.py")
LOG_DIR  = os.path.join(BASE_DIR, "data", "logs")
LOG_PATH = os.path.join(LOG_DIR, "streamlit.log")

# pythonw.exe ile açılınca sys.executable pythonw olur; Streamlit'i konsolsuz python.exe ile başlat
_py = sys.executable
if os.path.basename(_py).lower() == "pythonw.exe":
    _aday = os.path.join(os.path.dirname(_py), "python.exe")
    if os.path.exists(_aday):
        _py = _aday
PYTHON = _py


def _bos_port() -> int:
    """İşletim sisteminden boş bir port ister — eski/başka bir sunucuyla çakışma olmaz."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _bos_port()

LOADING_HTML = """<!DOCTYPE html><html><body style="margin:0;
background:linear-gradient(135deg,#2c2416,#6b4c35);display:flex;flex-direction:column;
align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:white">
<div style="font-size:64px">&#9992;&#65039;</div>
<h2 style="margin:14px 0 8px;font-size:24px;font-weight:800">SmartTravel AI</h2>
<p style="opacity:.75;font-size:14px;margin:0">Uygulama ba&#351;lat&#305;l&#305;yor&#8230;</p>
</body></html>"""

proc = None
log_dosyasi = None


def _start_streamlit():
    global log_dosyasi
    os.makedirs(LOG_DIR, exist_ok=True)
    log_dosyasi = open(LOG_PATH, "w", encoding="utf-8", errors="replace")
    log_dosyasi.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] port={PORT} python={PYTHON}\n")
    log_dosyasi.flush()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.Popen(
        [PYTHON, "-m", "streamlit", "run", APP_PY,
         f"--server.port={PORT}",
         "--server.address=127.0.0.1",
         "--server.headless=true",
         "--browser.gatherUsageStats=false",
         "--browser.serverAddress=localhost",
         "--server.enableCORS=false",
         "--server.enableXsrfProtection=false"],
        cwd=BASE_DIR, env=env,
        stdout=log_dosyasi, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def _wait_ready(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:     # sunucu çöktü — beklemeye gerek yok
            return False
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/_stcore/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def _son_log(n=25) -> str:
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            satirlar = f.readlines()[-n:]
        return "".join(satirlar).replace("&", "&amp;").replace("<", "&lt;")
    except Exception:
        return "(log okunamadı)"


def _cleanup():
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if log_dosyasi:
        try:
            log_dosyasi.close()
        except Exception:
            pass


atexit.register(_cleanup)


def _startup(win):
    global proc
    proc = _start_streamlit()
    if _wait_ready(60):
        win.load_url(f"http://localhost:{PORT}")
    else:
        win.load_html(
            "<body style='font-family:sans-serif;padding:32px;background:#faf8f5;color:#2c2416'>"
            "<h2>Uygulama başlatılamadı</h2>"
            f"<p>Ayrıntılar: <code>{LOG_PATH}</code></p>"
            f"<pre style='background:#f2ede6;padding:12px;border-radius:8px;white-space:pre-wrap;font-size:12px'>{_son_log()}</pre>"
            "</body>")


ICON_PATH = os.path.join(BASE_DIR, "smarttravel.ico")

win = webview.create_window(
    "SmartTravel AI", html=LOADING_HTML,
    width=1280, height=820, resizable=True,
)
webview.start(_startup, win, icon=ICON_PATH if os.path.exists(ICON_PATH) else None)
_cleanup()
