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
                p = psutil.Process(pid)
                # First call to cpu_percent(interval=None) will return 0.0, 
                # but it seeds the internal state for the next call.
                p.cpu_percent(interval=None) 
                PROCESS_CACHE[port] = p
                # Short sleep or just wait for next poll to get real data
            except Exception:
                return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

        proc = PROCESS_CACHE[port]
        try:
            with proc.oneshot():
                # On Windows/Linux, calling this again returns the usage since last call.
                # Normalized by CPU_COUNT for 'Total System Share' perspective.
                cpu_raw = proc.cpu_percent(interval=None)
                cpu = cpu_raw / CPU_COUNT
                ram = round(proc.memory_info().rss / (1024 * 1024), 1)
                check_and_alert(port, name, ram)
                return {"cpu": round(cpu, 1), "ram": ram, "pid": pid, "status": "ONLINE"}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            del PROCESS_CACHE[port]
            return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

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


def get_disk_usage():
    """Calculate disk usage for each project in the workspace."""
    import os
    projects = ['mahameru-terminal-be', 'mahameru-terminal-fe', 'sinabung-monitoring', 'kerinci-maps']
    base = os.path.join(os.path.dirname(__file__), '..', '..')
    
    stats = []
    for p in projects:
        path = os.path.abspath(os.path.join(base, p))
        size = 0
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                # Skip node_modules and .git for speed
                if 'node_modules' in dirs: dirs.remove('node_modules')
                if '.git' in dirs: dirs.remove('.git')
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        if not os.path.islink(fp):
                            size += os.path.getsize(fp)
                    except: pass
        
        stats.append({
            "name": p,
            "size": round(size / (1024 * 1024), 2), # MB
            "path": path
        })
    return stats


def purge_all_logs():
    """Clear all contents from log files in the LOGS_DIR."""
    import os
    if not os.path.exists(LOGS_DIR):
        return {"status": "error", "message": "Logs directory not found"}
    
    cleared = []
    try:
        for f in os.listdir(LOGS_DIR):
            if f.endswith('.log'):
                path = os.path.join(LOGS_DIR, f)
                with open(path, 'w') as log:
                    log.truncate(0)
                cleared.append(f)
        return {"status": "success", "cleared": cleared}
    except Exception as e:
        return {"status": "error", "message": str(e)}
