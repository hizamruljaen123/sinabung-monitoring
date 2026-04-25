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

if __name__ == '__main__':
    # IMPORTANT: use_reloader=False is REQUIRED.
    # Flask's reloader spawns a second child process, causing background threads
    # (Telegram bot, alert loop) to run TWICE → duplicate messages.
    # For hot-reload during development, use watchdog/nodemon externally instead.
    threading.Thread(target=run_telegram_bot, daemon=True).start()

    from services.bot_so_alerts import run_so_alert_loop
    threading.Thread(target=run_so_alert_loop, daemon=True).start()

    print("[*] Sinabung Monitoring started — reloader DISABLED to prevent duplicate alerts.")
    app.run(host="0.0.0.0", port=9000, debug=True, use_reloader=False)
