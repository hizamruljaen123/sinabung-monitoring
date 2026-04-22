import os
from flask import Flask, render_template, jsonify
import psutil
from datetime import datetime
try:
    from dotenv import load_dotenv
    # Look for .env in the parent be directory
    env_path = os.path.join(os.path.dirname(__file__), '..', 'be', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

DEV_MODE = os.getenv("DEV_MODE", "True").lower() == "true"
app = Flask(__name__)

# Config Ports
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
    8200: "Correlation Engine"
}

# Essential Services for DEV_MODE
DEV_ESSENTIAL_PORTS = [5006, 8092, 8200, 8097, 8098, 8093, 8094, 5173]

if DEV_MODE:
    # Filter only essential ports in Dev Mode
    BE_PORTS = {k: v for k, v in BE_PORTS.items() if k in DEV_ESSENTIAL_PORTS}

FE_PORTS = {
    5173: "Vite SolidJS FE"
}

# Process Cache to allow cpu_percent to work correctly
PROCESS_CACHE = {}

def get_process_info(port):
    global PROCESS_CACHE
    try:
        # Try to find the process for this port
        target_conn = None
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                target_conn = conn
                break
        
        if not target_conn:
            # Port is not listening
            if port in PROCESS_CACHE: del PROCESS_CACHE[port]
            return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

        pid = target_conn.pid
        
        # Get or create process object
        if port not in PROCESS_CACHE or PROCESS_CACHE[port].pid != pid:
            try:
                PROCESS_CACHE[port] = psutil.Process(pid)
                # First call to cpu_percent() initializes it
                PROCESS_CACHE[port].cpu_percent()
            except:
                return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}
        
        proc = PROCESS_CACHE[port]
        with proc.oneshot():
            # Second call (on subsequent API hit) will return real value
            cpu = proc.cpu_percent()
            ram = proc.memory_info().rss / (1024 * 1024)
            return {"cpu": round(cpu, 1), "ram": round(ram, 1), "pid": pid, "status": "ONLINE"}
            
    except Exception as e:
        if port in PROCESS_CACHE: del PROCESS_CACHE[port]
        pass
    return {"cpu": 0, "ram": 0, "pid": "-", "status": "OFFLINE"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    all_stats = []
    total_cpu = 0
    total_ram = 0
    
    # Combined ports
    combined = {**BE_PORTS, **FE_PORTS}
    
    for port, name in sorted(combined.items()):
        info = get_process_info(port)
        all_stats.append({
            "name": name,
            "port": port,
            "pid": info['pid'],
            "status": info['status'],
            "cpu": info['cpu'],
            "ram": info['ram']
        })
        total_cpu += info['cpu']
        total_ram += info['ram']
        
    return jsonify({
        "services": all_stats,
        "total_cpu": round(total_cpu, 1),
        "total_ram": round(total_ram / 1024, 2),
        "time": datetime.now().strftime("%H:%M:%S"),
        "dev_mode": DEV_MODE
    })

if __name__ == '__main__':
    # Run on port 9000 for monitoring
    app.run(port=9000, debug=True)
