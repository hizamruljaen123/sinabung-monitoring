import time
import psutil
import requests
from config import (
    CPU_COUNT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    RAM_ALERT_THRESHOLD, PORT_TO_LOG, LOGS_DIR
)

PROCESS_CACHE = {}
ALERT_COOLDOWN = {}


def check_and_alert(port, name, ram):
    """Send a Telegram alert if RAM usage exceeds the threshold (with 15-min cooldown)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if ram > RAM_ALERT_THRESHOLD:
        now = time.time()
        if port not in ALERT_COOLDOWN or now - ALERT_COOLDOWN[port] > 900:
            msg = (
                f"🚨 *SINABUNG MONITORING ALERT* 🚨\n\n"
                f"*Service:* `{name}`\n*Port:* `{port}`\n"
                f"*Status:* ⚠️ *High RAM Usage*\n"
                f"*RAM:* `{ram} MB` (Threshold: {RAM_ALERT_THRESHOLD} MB)"
            )
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                    timeout=5
                )
            except Exception as e:
                print(f"Telegram alert failed: {e}")
            ALERT_COOLDOWN[port] = now


def get_process_info(port, name):
    """Return CPU/RAM/PID/status for the process listening on the given port."""
    global PROCESS_CACHE
    try:
        target_conn = None
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                target_conn = conn
                break

        if not target_conn:
            if port in PROCESS_CACHE:
                del PROCESS_CACHE[port]
            return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

        pid = target_conn.pid

        if port not in PROCESS_CACHE or PROCESS_CACHE[port].pid != pid:
            try:
                PROCESS_CACHE[port] = psutil.Process(pid)
                PROCESS_CACHE[port].cpu_percent()
            except Exception:
                return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

        proc = PROCESS_CACHE[port]
        with proc.oneshot():
            # psutil.Process.cpu_percent() can exceed 100% on multi-core systems.
            # Normalizing by CPU_COUNT gives the usage relative to total system capacity.
            cpu = proc.cpu_percent() / CPU_COUNT
            ram = round(proc.memory_info().rss / (1024 * 1024), 1)
            check_and_alert(port, name, ram)
            return {"cpu": round(cpu, 1), "ram": ram, "pid": pid, "status": "ONLINE"}

    except Exception:
        if port in PROCESS_CACHE:
            del PROCESS_CACHE[port]

    return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}


def get_error_counts(port):
    """Scan the last 500KB of the service's log file and count ERROR occurrences."""
    import os
    log_file_name = PORT_TO_LOG.get(port)
    if not log_file_name:
        return 0
    log_path = os.path.join(LOGS_DIR, log_file_name)
    if not os.path.exists(log_path):
        return 0

    error_count = 0
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 500000))  # last 500KB
            error_count = f.read().count('ERROR')
    except Exception:
        pass
    return error_count
