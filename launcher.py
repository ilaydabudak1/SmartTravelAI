import os
import sys
import time
import socket
import atexit
import subprocess
import urllib.request
import webview

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
APP_PY   = os.path.join(BASE_DIR, "app.py")

def _free_port() -> int:
    """Her seferinde boş bir port döndürür — çakışma imkansız."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

PORT = _free_port()

LOADING_HTML = """
<!DOCTYPE html><html><body style="margin:0;background:linear-gradient(135deg,#2c2416,#6b4c35);
display:flex;flex-direction:column;align-items:center;justify-content:center;
height:100vh;font-family:sans-serif;color:white;user-select:none">
<div style="font-size:64px">✈️</div>
<h2 style="margin:14px 0 8px;font-size:24px;font-weight:800">SmartTravel AI</h2>
<p style="opacity:.75;font-size:14px;margin:0">Uygulama başlatılıyor, lütfen bekleyin…</p>
</body></html>
"""

def _find_python():
    for candidate in [sys.executable, "python", "python3"]:
        try:
            r = subprocess.run([candidate, "--version"], capture_output=True, timeout=3)
            if r.returncode == 0:
                return candidate
        except Exception:
            pass
    return sys.executable

def _start_streamlit():
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.Popen(
        [_find_python(), "-m", "streamlit", "run", APP_PY,
         f"--server.port={PORT}",
         "--server.headless=true",
         "--browser.gatherUsageStats=false",
         "--browser.serverAddress=localhost",
         "--server.enableCORS=false",
         "--server.enableXsrfProtection=false"],
        cwd=BASE_DIR,
        creationflags=flags,
    )

def _wait_ready(timeout=60):
    url = f"http://localhost:{PORT}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False

proc = None

def _cleanup():
    """Uygulama kapandığında Streamlit sürecini kes."""
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

atexit.register(_cleanup)

def _startup(window):
    global proc
    proc = _start_streamlit()
    if _wait_ready(60):
        window.load_url(f"http://localhost:{PORT}")
    else:
        window.load_html(
            "<body style='font-family:sans-serif;padding:40px;background:#faf8f5'>"
            "<h2>Hata</h2><p>Streamlit 60 saniye içinde başlatılamadı.</p></body>"
        )

window = webview.create_window(
    "SmartTravel AI",
    html=LOADING_HTML,
    width=1280,
    height=820,
    resizable=True,
    confirm_close=False,
)

webview.start(_startup, window)
