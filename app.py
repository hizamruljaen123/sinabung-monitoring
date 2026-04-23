import os
import time
import requests
import threading
from flask import Flask, render_template, jsonify
import psutil
from datetime import datetime
import mysql.connector

try:
    from dotenv import load_dotenv
    # Look for .env in the parent mahameru-terminal-be directory as a fallback
    parent_env_path = os.path.join(os.path.dirname(__file__), '..', 'mahameru-terminal-be', '.env')
    load_dotenv(parent_env_path)
    
    # Load local .env (this will override parent .env if same keys exist)
    local_env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(local_env_path, override=True)
except ImportError:
    pass

DEV_MODE = os.getenv("DEV_MODE", "True").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
RAM_ALERT_THRESHOLD = int(os.getenv("RAM_ALERT_THRESHOLD", "1500")) # Threshold in MB
CPU_COUNT = psutil.cpu_count() or 1

app = Flask(__name__)

SERVICE_PORTS_MAPPING = {
    "news_service.py": [5101, 5102, 5103, 5104, 5105],
    "backup_service.py": [5004],
    "sentiment_service.py": [5008],
    "entity_service.py": [5005],
    "ta_service.py": [5007],
    "deep_ta_service.py": [5200],
    "sky_service.py": [5002],
    "ais_service.py": [8080],
    "geo_data_service.py": [8091],
    "submarine_cable_service.py": [8120],
    "satellite_visual_service.py": [8130],
    "crypto_service.py": [8085],
    "forex_service.py": [8086],
    "commodity_service.py": [8087],
    "market_service.py": [8088],
    "oil_refinery_service.py": [8089],
    "disaster_service.py": [8095],
    "tv_service.py": [5003],
    "infrastructure_service.py": [8097],
    "port_service.py": [8098],
    "mines_service.py": [8082],
    "power_plant_service.py": [8093],
    "oil_trade_service.py": [8090],
    "gnews_service.py": [5006],
    "vessel_intelligence_service.py": [8100],
    "industrial_zone_service.py": [8094],
    "datacenter_service.py": [8110],
    "rail_station_service.py": [8111],
    "conflict_service.py": [8140],
    "government_facility_service.py": [8150],
    "military_service.py": [8160],
    "crypto_stream_service.py": [8092],
    "dashboard_service.py": [8000]
}

# Reverse mapping: Port -> Log file name
PORT_TO_LOG = {}
for py_file, ports in SERVICE_PORTS_MAPPING.items():
    log_name = py_file.replace('.py', '.log')
    for p in ports:
        PORT_TO_LOG[p] = log_name

BE_PORTS = {
    5101: "News Node 1 (Core)",
    5102: "News Node 2 (Intel)",
    5103: "News Node 3 (Legal)",
    5104: "News Node 4 (Indus)",
    5105: "News Node 5 (ESG)",
    5004: "Backup/Socket Svc",
    5005: "Entity Engine",
    5007: "TA Engine",
    5008: "Sentiment Engine",
    5200: "Deep TA AI",
    8000: "Dashboard API",
    8080: "AIS Tracking",
    8091: "Geo Intelligence",
    8120: "Submarine Cables",
    8130: "Satellite Visual",
    8085: "Crypto Market",
    8086: "Forex Market",
    8087: "Commodity Market",
    8088: "Global Market",
    8089: "Oil Refinery",
    8090: "Oil Trade",
    8094: "Industrial Hubs",
    8093: "Power Plants",
    8095: "Disaster Intel",
    8097: "Infrastructure",
    8098: "Port Intelligence",
    8082: "Mines Intelligence",
    5002: "Sky/Aviation Svc",
    5003: "TV Stream Svc",
    5006: "GNews Crawler",
    8092: "Crypto Streamer",
    8100: "Vessel Intelligence",
    8110: "Datacenter",
    8111: "Rail Station",
    8140: "Conflict Svc",
    8150: "Gov Facility Svc",
    8160: "Military Svc",
    }

DEV_ESSENTIAL_PORTS = [5006, 8092, 8200, 8097, 8098, 8093, 8094, 5151]

if DEV_MODE:
    BE_PORTS = {k: v for k, v in BE_PORTS.items() if k in DEV_ESSENTIAL_PORTS}

FE_PORTS = {
    5151: "Vite SolidJS FE"
}

PROCESS_CACHE = {}
ALERT_COOLDOWN = {}

def check_and_alert(port, name, ram):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if ram > RAM_ALERT_THRESHOLD:
        now = time.time()
        # Cooldown 15 minutes per port
        if port not in ALERT_COOLDOWN or now - ALERT_COOLDOWN[port] > 900:
            msg = f"🚨 *SINABUNG MONITORING ALERT* 🚨\n\n*Service:* `{name}`\n*Port:* `{port}`\n*Status:* ⚠️ *High RAM Usage*\n*RAM:* `{ram} MB` (Threshold: {RAM_ALERT_THRESHOLD} MB)"
            try:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": msg,
                    "parse_mode": "Markdown"
                }, timeout=5)
            except Exception as e:
                print(f"Telegram alert failed: {e}")
            ALERT_COOLDOWN[port] = now

def get_process_info(port, name):
    global PROCESS_CACHE
    try:
        target_conn = None
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                target_conn = conn
                break
        
        if not target_conn:
            if port in PROCESS_CACHE: del PROCESS_CACHE[port]
            return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

        pid = target_conn.pid
        
        if port not in PROCESS_CACHE or PROCESS_CACHE[port].pid != pid:
            try:
                PROCESS_CACHE[port] = psutil.Process(pid)
                PROCESS_CACHE[port].cpu_percent()
            except:
                return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}
        
        proc = PROCESS_CACHE[port]
        with proc.oneshot():
            # psutil.Process.cpu_percent() can exceed 100% on multi-core systems.
            # Normalizing by CPU_COUNT gives the usage relative to total system capacity.
            cpu = proc.cpu_percent() / CPU_COUNT
            ram = proc.memory_info().rss / (1024 * 1024)
            ram = round(ram, 1)
            
            # Check for telegram alert
            check_and_alert(port, name, ram)
            
            return {"cpu": round(cpu, 1), "ram": ram, "pid": pid, "status": "ONLINE"}
            
    except Exception as e:
        if port in PROCESS_CACHE: del PROCESS_CACHE[port]
        pass
    return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'mahameru-terminal-be', 'logs')

def get_error_counts(port):
    log_file_name = PORT_TO_LOG.get(port)
    if not log_file_name: return 0
    log_path = os.path.join(LOGS_DIR, log_file_name)
    if not os.path.exists(log_path): return 0
    
    error_count = 0
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            seek_pos = max(0, size - 500000) # last 500KB
            f.seek(seek_pos)
            content = f.read()
            error_count = content.count('ERROR')
    except Exception:
        pass
    return error_count

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "asetpedia"),
            port=int(os.getenv("DB_PORT", "3306"))
        )
        return conn
    except Exception as e:
        print(f"DB Error: {e}")
        return None

IMPORTANT_TABLES = [
    "article", "ais_history", "global_conflicts", "global_trade_alerts", 
    "government_facilities", "military_facilities", "power_plants", 
    "oil_refineries", "datacenter_hub", "mines_data", "offshore_platforms",
    "petroleum_terminals", "oil_trades"
]

def get_table_counts():
    conn = get_db_connection()
    counts = {}
    if conn:
        cursor = conn.cursor()
        for table in IMPORTANT_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                result = cursor.fetchone()
                counts[table] = result[0] if result else 0
            except:
                counts[table] = -1
        cursor.close()
        conn.close()
    else:
        for table in IMPORTANT_TABLES:
            counts[table] = -1
    return counts

def generate_detailed_summary():
    """Generates a neat, monospace summary of the system status."""
    combined = {**BE_PORTS, **FE_PORTS}
    services_list = []
    online_count = 0
    
    for port, name in sorted(combined.items()):
        info = get_process_info(port, name)
        is_online = info['status'] == "ONLINE"
        if is_online: online_count += 1
        
        services_list.append({
            "name": name,
            "port": port,
            "status": "ON" if is_online else "OFF",
            "cpu": info['cpu'],
            "ram": info['ram']
        })
    
    sys_cpu = psutil.cpu_percent()
    sys_ram = psutil.virtual_memory()
    ram_used = sys_ram.used / (1024**3)
    ram_total = sys_ram.total / (1024**3)
    
    # Format the report
    separator = "-" * 36 + "\n"
    txt = "🌋 SINABUNG MONITORING SYSTEM\n"
    txt += f"Sync Time : {datetime.now().strftime('%H:%M:%S')}\n"
    txt += separator
    txt += f"CPU Load  : {sys_cpu:>5.1f}%\n"
    txt += f"Memory    : {ram_used:>4.2f}/{ram_total:>4.1f} GB ({sys_ram.percent}%)\n"
    txt += f"Services  : {online_count}/{len(services_list)} ONLINE\n"
    txt += separator
    
    # Add Database Section
    db_counts = get_table_counts()
    txt += "📊 DATABASE STATUS\n"
    txt += separator
    for table, count in db_counts.items():
        name = table.replace('_', ' ').capitalize()
        val = f"{count:,}" if count >= 0 else "Error"
        txt += f"{name:<20}: {val:>14}\n"
    
    txt += separator
    txt += f"{'SERVICE NAME':<15} {'PRT':<5} {'ST':<3} {'CPU':<5} {'RAM':<6}\n"
    txt += separator
    
    for s in services_list:
        txt += f"{s['name'][:15]:<15} {s['port']:<5} {s['status']:<3} {s['cpu']:>4.1f}% {s['ram']:>5.0f}M\n"
    
    txt += separator
    return txt

def run_telegram_bot():
    """Background task to poll for Telegram commands."""
    if not TELEGRAM_BOT_TOKEN:
        print("[!] No Telegram Token found. Bot listener disabled.")
        return
    
    last_id = 0
    # Try to sync with the latest message to avoid spamming on start
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?limit=1&offset=-1", timeout=5)
        if r.status_code == 200:
            res = r.json().get("result", [])
            if res: last_id = res[0]["update_id"]
    except: pass

    print(f"[*] Sinabung Bot initialized. Listening for commands...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_id+1}&timeout=20"
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
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"🌋 *SINABUNG MONITORING ONLINE*\n\nBot successfully joined this chat.\nChat ID: `{chat_id}`\n\n_To receive alerts here, set this ID as TELEGRAM_CHAT_ID in your configuration._",
                            "parse_mode": "Markdown"
                        })
                        continue

                    # Clean command from bot mentions (e.g. /getUpdate@SinabungBot -> /getUpdate)
                    cmd = text.split()[0].lower() if text else ""
                    if "@" in cmd:
                        cmd = cmd.split("@")[0]

                    # Handle /get_id command
                    if cmd == "/get_id":
                        print(f"[*] Sending Chat ID to {chat_id}")
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"📍 *CONNECTION ESTABLISHED*\n\nYour Chat ID: `{chat_id}`\n\n_Use this ID in your .env file as TELEGRAM_CHAT_ID._",
                            "parse_mode": "Markdown"
                        })

                    elif cmd == "/getupdate":
                        print(f"[*] Received /getUpdate from chat {chat_id}")
                        summary = generate_detailed_summary()
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": f"<pre>{summary}</pre>",
                            "parse_mode": "HTML"
                        })


        except Exception as e:
            print(f"Telegram Bot Error: {e}")
        time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html', DEV_MODE=DEV_MODE)

@app.route('/api/stats')
def stats():
    all_stats = []
    combined = {**BE_PORTS, **FE_PORTS}
    
    for port, name in sorted(combined.items()):
        info = get_process_info(port, name)
        error_count = get_error_counts(port)
        all_stats.append({
            "name": name,
            "port": port,
            "pid": info['pid'],
            "status": info['status'],
            "cpu": info['cpu'],
            "ram": info['ram'],
            "errors": error_count
        })
        
    db_counts = get_table_counts()
    
    # Use system-wide metrics for a more accurate "Global" view
    system_cpu = psutil.cpu_percent()
    system_ram = psutil.virtual_memory()
    
    return jsonify({
        "services": all_stats,
        "total_cpu": round(system_cpu, 1),
        "total_ram": round(system_ram.used / (1024**3), 2),
        "total_ram_capacity": round(system_ram.total / (1024**3), 1),
        "ram_percent": system_ram.percent,
        "db_counts": db_counts,
        "time": datetime.now().strftime("%H:%M:%S"),
        "dev_mode": DEV_MODE
    })

if __name__ == '__main__':
    # Start the modular Telegram Bot in a background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # use_reloader=False is used to prevent starting the bot thread twice in debug mode
    app.run(host="0.0.0.0", port=9000, debug=True, use_reloader=False)
