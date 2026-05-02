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
from services.bot_cache import get_today_messages, clear_today_cache

def handle_so_clear_history(chat_id):
    """Batch delete all messages tracked for TODAY in SQLite."""
    count = 0
    mids = get_today_messages(chat_id)
    
    for mid in mids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage",
                json={"chat_id": chat_id, "message_id": mid},
                timeout=5
            )
            count += 1
        except: pass
    
    # Clear cache for this chat for today
    clear_today_cache(chat_id)
    send_message(chat_id, f"🧹 <b>CLEANUP COMPLETE</b>\nRemoved {count} messages from today's history.", auto_delete_seconds=10)

def handle_clear_all(chat_id):
    """Batch delete ALL messages tracked in SQLite for this chat."""
    from services.bot_cache import get_all_messages, clear_all_cache
    count = 0
    mids = get_all_messages(chat_id)
    
    # Send a wait message
    wait_msg = send_message(chat_id, f"⏳ <b>CLEANING FULL HISTORY...</b>\nTargeting {len(mids)} messages.")
    
    for mid in mids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage",
                json={"chat_id": chat_id, "message_id": mid},
                timeout=5
            )
            count += 1
        except: pass
    
    clear_all_cache(chat_id)
    send_message(chat_id, f"🔥 <b>NUKED!</b>\nSuccessfully wiped {count} messages from bot history.", auto_delete_seconds=15)

# ─── Import DevOps command handlers ───────────────────────────────────────────
from services.bot_so_devops import (
    handle_so_status, handle_so_cpu, handle_so_ram, handle_so_disk,
    handle_so_db_stats, handle_so_logs_clear, handle_so_restart_node,
    handle_so_backup_now, handle_so_git_pull, handle_so_npm_build,
    handle_so_env, handle_so_start_env, handle_so_stop_env
)

# ─── Help Text ────────────────────────────────────────────────────────────────
HELP_TEXT = """
🌋 <b>SINABUNG MONITORING — OPERATIONAL HUB</b>

<b>── MULTI-ENV MANAGEMENT ──</b>
/so_env            🌐 List Envs (Main, Staging, Dev)
/so_status         ⚡ [env] Cluster Node Health Check
/so_start_env      🚀 [env] Start Dev/Staging (On)
/so_stop_env       🛑 [env] Stop Dev/Staging (Off)
/so_restart_node   🔄 [env] [node] Restart Microservice
/so_git_pull       📦 [env] [be/fe] Pull Latest Source
/so_npm_build      🏗️ [env] Rebuild Frontend Assets

<b>── SERVER DIAGNOSTICS ──</b>
/so_cpu            📊 CPU Utilization (Logical Cores)
/so_ram            🧠 Memory Allocation & Top Consumers
/so_disk           💾 Storage Capacity & Project Sizes
/so_db_stats       📈 Database Table Row Counts

<b>── SYSTEM CONTROL ──</b>
/so_logs_clear     🗑️ Purge All System Logs (Free Space)
/so_clear_history  🧹 Clear Current Bot Chat Session
/so_backup_now     📦 Trigger Instant DB Backup

<b>── UTILITIES ──</b>
/clear_message     Alias for session cleanup
/clear_all         🔥 Wipe ALL Bot Messages in this chat
/so_get_id         Get current Telegram Chat ID
/help              Display this guide
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
        handle_so_status(chat_id, args)

    elif cmd == "/so_env":
        handle_so_env(chat_id)

    elif cmd == "/so_start_env":
        handle_so_start_env(chat_id, args)

    elif cmd == "/so_stop_env":
        handle_so_stop_env(chat_id, args)

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
        handle_so_npm_build(chat_id, args)

    elif cmd in ("/so_clear_history", "/clear_message"):
        handle_so_clear_history(chat_id)

    elif cmd == "/clear_all":
        handle_clear_all(chat_id)

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
    print("[*] Starting Sinabung Bot thread...")
    try:
        print(f"[*] Fetching bot info with token: {TELEGRAM_BOT_TOKEN[:10]}...")
        r_me = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=10)
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
    except Exception as e:
        print(f"[!] Bot Init Error: {e}")
        pass

    handler_count = len([c for c in globals() if c.startswith('handle_so_')])
    print(f"[*] Sinabung Bot (@{bot_username}) ready. {handler_count} handlers registered.")

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

                    # Only handle /so_ commands (plus /help, /start, /clear_message)
                    if not (raw_cmd.startswith("/so_") or raw_cmd in ("/help", "/start", "/clear_message")):
                        continue

                    print(f"[Bot] CMD: {raw_cmd} {args} from chat {chat_id}")
                    _dispatch(raw_cmd, args, chat_id)

        except Exception as e:
            print(f"[Bot Polling] Error: {e}")
        time.sleep(1)
