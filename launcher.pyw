import os, sys, time, subprocess, urllib.request, webview

PYTHON   = r"C:\Users\ilayd\AppData\Local\Programs\Python\Python314\python.exe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PY   = os.path.join(BASE_DIR, "app.py")
PORT     = 8502

LOADING_HTML = """<!DOCTYPE html><html><body style="margin:0;
background:linear-gradient(135deg,#667eea,#764ba2);display:flex;flex-direction:column;
align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:white">
<div style="font-size:64px">&#9992;&#65039;</div>
<h2 style="margin:14px 0 8px;font-size:24px;font-weight:800">SmartTravel AI</h2>
<p style="opacity:.75;font-size:14px;margin:0">Uygulama ba&#351;lat&#305;l&#305;yor&#8230;</p>
</body></html>"""

def _start_streamlit():
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"]              = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"]   = "false"
    env["STREAMLIT_SERVER_PORT"]                  = str(PORT)
    return subprocess.Popen(
        [PYTHON, "-m", "streamlit", "run", APP_PY,
         f"--server.port={PORT}",
         "--server.headless=true",
         "--browser.gatherUsageStats=false",
         "--server.enableCORS=false",
         "--server.enableXsrfProtection=false"],
        cwd=BASE_DIR,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

def _wait_ready(timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{PORT}", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False

proc = None

def _startup(win):
    global proc
    proc = _start_streamlit()
    if _wait_ready(45):
        win.load_url(f"http://localhost:{PORT}")
    else:
        win.load_html("<body style='font-family:sans-serif;padding:40px'>"
                      "<h2>Hata</h2><p>Streamlit 45 saniyede ba&#351;lat&#305;lamad&#305;.</p></body>")

ICON_PATH = os.path.join(BASE_DIR, "smarttravel.ico")

win = webview.create_window(
    "SmartTravel AI", html=LOADING_HTML,
    width=1280, height=820, resizable=True,
)
webview.start(_startup, win, icon=ICON_PATH if os.path.exists(ICON_PATH) else None)

if proc:
    try: proc.terminate()
    except: pass
