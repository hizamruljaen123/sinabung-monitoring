"""
telegram_bot.py — Sinabung Bot Orchestrator
─────────────────────────────────────────────
Central dispatcher. Handles polling and routes
every command to the correct module:

  /so_*  → bot_so_devops.py  (DevOps / server)
  /so_*  → bot_so_devops.py  (DevOps / server)

Auto-alerts run in separate daemon threads:
  bot_so_alerts.py → Server monitoring push alerts
"""
import time
import requests
from config import TELEGRAM_BOT_TOKEN
from services.bot_helpers import send_message

# ─── Import DevOps command handlers ───────────────────────────────────────────
from services.bot_so_devops import (
    handle_so_status, handle_so_cpu, handle_so_ram, handle_so_disk,
    handle_so_db_stats, handle_so_logs_clear, handle_so_restart_node,
    handle_so_backup_now, handle_so_git_pull, handle_so_npm_build,
)

# ─── Help Text ────────────────────────────────────────────────────────────────
HELP_TEXT = """
🌋 <b>SINABUNG MONITORING BOT COMMANDS</b>

<b>── SERVER / DEVOPS (/so_) ──</b>
/so_status         Status semua node cluster
/so_cpu            Utilisasi CPU per core
/so_ram            Alokasi memori & top consumers
/so_disk           Kapasitas disk & ukuran project
/so_db_stats       Jumlah baris tabel database
/so_logs_clear     Hapus semua file log (free disk)
/so_restart_node   [nama] Restart satu service
/so_backup_now     Trigger backup database sekarang
/so_git_pull       [be/fe] Pull kode terbaru dari git
/so_npm_build      Build ulang frontend (npm build)

<b>── UTILS ──</b>
/so_get_id   Dapatkan Chat ID grup ini
/help        Tampilkan pesan ini
"""


# ─── Main Dispatcher ─────────────────────────────────────────────────────────

def _dispatch(cmd: str, args: list, chat_id: int):
    """Route a command to the correct handler."""

    # ── Utility ──────────────────────────────────────────────────────────────
    if cmd in ("/so_get_id",):
        send_message(chat_id,
            f"📍 <b>CHAT ID</b>\n\n<code>{chat_id}</code>\n\n"
            "<i>Set this as TELEGRAM_CHAT_ID in your .env file.</i>")

    elif cmd in ("/help", "/start"):
        send_message(chat_id, HELP_TEXT)

    # ── /so_ DevOps ──────────────────────────────────────────────────────────
    elif cmd in ("/so_status", "/so_update", "/so_get_update"):
        handle_so_status(chat_id)

    elif cmd == "/so_cpu":
        handle_so_cpu(chat_id)

    elif cmd == "/so_ram":
        handle_so_ram(chat_id)

    elif cmd == "/so_disk":
        handle_so_disk(chat_id)

    elif cmd == "/so_db_stats":
        handle_so_db_stats(chat_id)

    elif cmd == "/so_logs_clear":
        handle_so_logs_clear(chat_id)

    elif cmd == "/so_restart_node":
        handle_so_restart_node(chat_id, args)

    elif cmd == "/so_backup_now":
        handle_so_backup_now(chat_id)

    elif cmd == "/so_git_pull":
        handle_so_git_pull(chat_id, args)

    elif cmd == "/so_npm_build":
        handle_so_npm_build(chat_id)

    else:
        # Unknown command from this bot prefix
        if cmd.startswith("/so_"):
            send_message(chat_id,
                f"❓ Unknown command: <code>{cmd}</code>\n"
                "Send /help for the full command list.")


# ─── Polling Loop ─────────────────────────────────────────────────────────────

def run_telegram_bot():
    """Background polling loop. Run in a daemon thread from app.py."""
    if not TELEGRAM_BOT_TOKEN:
        print("[!] No Telegram Token found. Bot listener disabled.")
        return

    bot_username = "bot"
    last_id = 0
    try:
        r_me = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=5)
        if r_me.status_code == 200:
            bot_username = r_me.json().get("result", {}).get("username", "bot")

        r_upd = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?limit=1&offset=-1",
            timeout=5
        )
        if r_upd.status_code == 200:
            res = r_upd.json().get("result", [])
            if res:
                last_id = res[0]["update_id"]
    except Exception:
        pass

    print(f"[*] Sinabung Bot (@{bot_username}) ready. {len([c for c in dir() if c.startswith('handle')])} handlers registered.")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_id + 1}&timeout=20"
            resp = requests.get(url, timeout=25)
            if resp.status_code == 200:
                updates = resp.json().get("result", [])
                for upd in updates:
                    last_id = upd["update_id"]
                    msg = upd.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")

                    if not text:
                        # Handle bot being added to a group
                        if "new_chat_members" in msg:
                            send_message(chat_id,
                                f"🌋 <b>SINABUNG MONITORING BOT ONLINE</b>\n\n"
                                f"Chat ID: <code>{chat_id}</code>\n\n"
                                "Use /help to see all available commands.")
                        continue

                    parts = text.strip().split()
                    raw_cmd = parts[0].lower()
                    args = parts[1:]

                    # Strip bot mention (e.g. /so_cpu@SinabungBot)
                    if "@" in raw_cmd:
                        raw_cmd = raw_cmd.split("@")[0]

                    # Only handle /so_ commands (plus /help, /start)
                    if not (raw_cmd.startswith("/so_") or raw_cmd in ("/help", "/start")):
                        continue

                    print(f"[Bot] CMD: {raw_cmd} {args} from chat {chat_id}")
                    _dispatch(raw_cmd, args, chat_id)

        except Exception as e:
            print(f"[Bot Polling] Error: {e}")
        time.sleep(1)
