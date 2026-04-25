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
    """Calculate disk usage for each project in all environments."""
    import os
    from config import ENVIRONMENTS
    
    stats = []
    # Base projects in the current workspace
    base_projects = ['sinabung-monitoring', 'kerinci-maps']
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # 1. Check workspace projects
    for p in base_projects:
        path = os.path.join(workspace_root, p)
        if os.path.exists(path):
            stats.append({"name": p, "size": _get_dir_size(path), "path": path})

    # 2. Check all environments
    for env_name, cfg in ENVIRONMENTS.items():
        for key in ["be_path", "fe_path"]:
            path = cfg[key]
            name = f"{env_name.upper()} {'BE' if 'be' in key else 'FE'}"
            if os.path.exists(path):
                # Avoid duplicates if paths overlap
                if not any(s["path"] == path for s in stats):
                    stats.append({"name": name, "size": _get_dir_size(path), "path": path})
    
    return stats

def _get_dir_size(path):
    """Helper to calculate directory size in MB."""
    import os
    size = 0
    for root, dirs, files in os.walk(path):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if '.git' in dirs: dirs.remove('.git')
        for f in files:
            fp = os.path.join(root, f)
            try:
                if not os.path.islink(fp):
                    size += os.path.getsize(fp)
            except: pass
    return round(size / (1024 * 1024), 2)


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

def start_environment(env_name):
    """Start a specific environment (BE & FE)."""
    from config import ENVIRONMENTS
    import subprocess
    import sys
    import os
    
    if env_name not in ENVIRONMENTS:
        return {"status": "error", "message": f"Environment {env_name} not found"}
    
    cfg = ENVIRONMENTS[env_name]
    results = []
    
    try:
        # 1. Start Backend via launcher.py
        be_cmd = [sys.executable, "launcher.py"]
        subprocess.Popen(be_cmd, cwd=cfg["be_path"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        results.append("BE started")
        
        # 2. Start Frontend via npm
        fe_cmd = f"npm run dev -- --port {cfg['fe_port']} --host 0.0.0.0"
        subprocess.Popen(fe_cmd, cwd=cfg["fe_path"], shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        results.append("FE started")
        
        return {"status": "success", "message": f"{env_name.upper()} started successfully", "details": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def stop_environment(env_name):
    """Stop a specific environment by killing processes on its ports."""
    from config import ENVIRONMENTS
    import psutil
    
    if env_name not in ENVIRONMENTS:
        return {"status": "error", "message": f"Environment {env_name} not found"}
    
    cfg = ENVIRONMENTS[env_name]
    ports_to_kill = [cfg["be_port"], cfg["fe_port"]]
    killed_count = 0
    
    try:
        for port in ports_to_kill:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN' and conn.pid:
                    try:
                        p = psutil.Process(conn.pid)
                        # Kill the process and its children
                        for child in p.children(recursive=True):
                            child.kill()
                        p.kill()
                        killed_count += 1
                    except: pass
        
        return {"status": "success", "message": f"{env_name.upper()} stopped", "killed_count": killed_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
