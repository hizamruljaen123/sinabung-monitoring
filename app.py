"""
Sinabung Monitoring — Entry Point
──────────────────────────────────────────────────────────────
Struktur Modular:
  config.py                   → Semua konstanta & ENV loading
  services/monitoring.py      → Cek proses CPU/RAM, Telegram alert
  services/database.py        → Koneksi DB, query helper
  services/telegram_bot.py    → Bot polling & command handler
  routes/api.py               → Semua Flask Blueprint routes
  app.py                      → Entry point (file ini)
──────────────────────────────────────────────────────────────
"""
import os
import threading
from flask import Flask
from routes.api import api
from routes.filemanager import filemanager
from services.telegram_bot import run_telegram_bot
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.register_blueprint(api)
app.register_blueprint(filemanager)

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
        "img-src 'self' data:; "
        "font-src 'self' fonts.gstatic.com; "
        "connect-src 'self' cdn.jsdelivr.net;"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# ─── Background Service Initialization ────────────────────────────────────────
# We start these threads at the module level so they run even when the app is 
# started by a WSGI server like Gunicorn (which skips the if __name__ == '__main__' block).
# We use a simple lock-like check to ensure we don't start them multiple times if the module is re-imported.
_threads_initialized = False

def start_background_threads():
    global _threads_initialized
    if _threads_initialized:
        return
    _threads_initialized = True
    
    print("[*] Initializing background threads (Telegram Bot & Alert Loop)...")
    
    # 1. Telegram Bot Polling
    threading.Thread(target=run_telegram_bot, daemon=True).start()

    # 2. DevOps Alert Engine
    from services.bot_so_alerts import run_so_alert_loop
    threading.Thread(target=run_so_alert_loop, daemon=True).start()

# Only start if NOT in reloader's child process (handled by use_reloader=False usually, 
# but good to be safe for Gunicorn environments too).
if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    start_background_threads()

if __name__ == '__main__':
    # When running directly: python app.py
    print("[*] Sinabung Monitoring started — reloader DISABLED to prevent duplicate alerts.")
    app.run(host="0.0.0.0", port=9000, debug=True, use_reloader=False)
