import time
import requests
import psutil
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BE_PORTS, FE_PORTS
from services.monitoring import get_process_info
from services.database import get_table_counts


def generate_detailed_summary():
    """Generates a neat, monospace summary of the system status for Telegram."""
    combined = {**BE_PORTS, **FE_PORTS}
    services_list = []
    online_count = 0

    for port, name in sorted(combined.items()):
        info = get_process_info(port, name)
        is_online = info['status'] == "ONLINE"
        if is_online:
            online_count += 1
        services_list.append({
            "name": name,
            "port": port,
            "status": "ON" if is_online else "OFF",
            "cpu": info['cpu'],
            "ram": info['ram']
        })

    sys_cpu = psutil.cpu_percent()
    sys_ram = psutil.virtual_memory()
    ram_used = sys_ram.used / (1024 ** 3)
    ram_total = sys_ram.total / (1024 ** 3)

    separator = "-" * 36 + "\n"
    txt = "🌋 SINABUNG MONITORING SYSTEM\n"
    txt += f"Sync Time : {datetime.now().strftime('%H:%M:%S')}\n"
    txt += separator
    txt += f"CPU Load  : {sys_cpu:>5.1f}%\n"
    txt += f"Memory    : {ram_used:>4.2f}/{ram_total:>4.1f} GB ({sys_ram.percent}%)\n"
    txt += f"Services  : {online_count}/{len(services_list)} ONLINE\n"
    txt += separator

    db_counts = get_table_counts()
    txt += "📊 DATABASE STATUS\n"
    txt += separator
    for table, count in db_counts.items():
        label = table.replace('_', ' ').capitalize()
        val = f"{count:,}" if count >= 0 else "Error"
        txt += f"{label:<20}: {val:>14}\n"

    txt += separator
    txt += f"{'SERVICE NAME':<15} {'PRT':<5} {'ST':<3} {'CPU':<5} {'RAM':<6}\n"
    txt += separator

    for s in services_list:
        txt += f"{s['name'][:15]:<15} {s['port']:<5} {s['status']:<3} {s['cpu']:>4.1f}% {s['ram']:>5.0f}M\n"

    txt += separator
    return txt


def _send_message(chat_id, text, parse_mode="Markdown"):
    """Helper to post a Telegram message."""
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=5
    )


def run_telegram_bot():
    """Background task to poll for Telegram commands (runs in a daemon thread)."""
    if not TELEGRAM_BOT_TOKEN:
        print("[!] No Telegram Token found. Bot listener disabled.")
        return

    # Get Bot Username for mention detection
    bot_username = "bot"
    last_id = 0
    try:
        r_me = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=5)
        if r_me.status_code == 200:
            bot_username = r_me.json().get("result", {}).get("username", "bot")

        # Sync to the latest message to avoid spamming on startup
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

    print(f"[*] Sinabung Bot (@{bot_username}) initialized. Listening for commands...")

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

                    if not text and "new_chat_members" not in msg:
                        continue

                    # Handle bot being added to a group
                    if "new_chat_members" in msg:
                        print(f"[*] Bot added to chat {chat_id}")
                        _send_message(
                            chat_id,
                            f"🌋 *SINABUNG MONITORING ONLINE*\n\nBot successfully joined this chat.\n"
                            f"Chat ID: `{chat_id}`\n\n"
                            f"_To receive alerts here, set this ID as TELEGRAM_CHAT_ID in your configuration._"
                        )
                        continue

                    # Clean command from bot mentions (e.g. /so_update@SinabungBot -> /so_update)
                    cmd = text.split()[0].lower() if text else ""
                    if "@" in cmd:
                        cmd = cmd.split("@")[0]

                    # ONLY PROCESS IF COMMAND STARTS WITH /so_
                    if not cmd.startswith("/so_"):
                        continue

                    if cmd == "/so_get_id":
                        print(f"[*] Sending Chat ID to {chat_id}")
                        _send_message(
                            chat_id,
                            f"📍 *CONNECTION ESTABLISHED*\n\nYour Chat ID: `{chat_id}`\n\n"
                            f"_Use this ID in your .env file as TELEGRAM_CHAT_ID._"
                        )

                    elif cmd in ["/so_update", "/so_status", "/so_get_update"]:
                        print(f"[*] Received status request from chat {chat_id}")
                        summary = generate_detailed_summary()
                        _send_message(
                            chat_id,
                            f"👋 *SYSTEM_REPORT*\n<pre>{summary}</pre>",
                            parse_mode="HTML"
                        )

        except Exception as e:
            print(f"Telegram Bot Error: {e}")
        time.sleep(1)
