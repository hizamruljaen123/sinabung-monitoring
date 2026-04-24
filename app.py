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

if __name__ == '__main__':
    # Telegram Command Bot (polls for /so_ and /mt_ commands)
    threading.Thread(target=run_telegram_bot, daemon=True).start()

    # SO Alert Loop — Server DevOps push alerts
    from services.bot_so_alerts import run_so_alert_loop
    threading.Thread(target=run_so_alert_loop, daemon=True).start()

    app.run(host="0.0.0.0", port=9000, debug=True, use_reloader=True)
