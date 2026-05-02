import os
import psutil

try:
    from dotenv import load_dotenv
    parent_env_path = os.path.join(os.path.dirname(__file__), '..', 'mahameru-terminal-be', '.env')
    load_dotenv(parent_env_path)
    local_env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(local_env_path, override=True)
except ImportError:
    pass

DEV_MODE = os.getenv("DEV_MODE", "True").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
RAM_ALERT_THRESHOLD = int(os.getenv("RAM_ALERT_THRESHOLD", "1500"))  # Threshold in MB
CPU_COUNT = psutil.cpu_count() or 1

# ─── Multi-Environment Configuration ──────────────────────────────────────────
# Based on ENVIRONMENT_SPEC.txt
ENVIRONMENTS = {
    "dev": {
        "be_path": "/home/project/dev/mahameru-terminal-be",
        "fe_path": "/home/project/dev/mahameru-terminal-fe",
        "be_port": 5001,
        "fe_port": 3001,
        "be_domain": "api-dev.asetpedia.online",
        "fe_domain": "terminal-dev.asetpedia.online",
        "db": "asetpedia_dev"
    },
    "staging": {
        "be_path": "/home/project/staging/mahameru-terminal-be",
        "fe_path": "/home/project/staging/mahameru-terminal-fe",
        "be_port": 5002,
        "fe_port": 3002,
        "be_domain": "api-staging.asetpedia.online",
        "fe_domain": "terminal-staging.asetpedia.online",
        "db": "asetpedia_staging"
    },
    "main": {
        "be_path": os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mahameru-terminal-be')),
        "fe_path": os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mahameru-terminal-fe')),
        "be_port": 8000, # Dashboard API
        "fe_port": 5151,
        "be_domain": "api.asetpedia.online",
        "fe_domain": "terminal.asetpedia.online",
        "db": "asetpedia"
    }
}

# ─── File Manager Config ─────────────────────────────────────────────────────
# Root directory the file manager can access. Change to '/' for full server access.
FM_ROOT_PATH = os.getenv("FM_ROOT_PATH", os.path.expanduser("~"))
# Password required to unlock the File Manager panel
FM_PASSWORD = os.getenv("FM_PASSWORD", "sinabung2024")
# Flask secret key for session management
SECRET_KEY = os.getenv("SECRET_KEY", "sinabung-secret-key-change-me")

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'mahameru-terminal-be', 'logs')

SERVICE_PORTS_MAPPING = {
    "news_service.py": [5101, 5102, 5103, 5104, 5105],
    "backup_service.py": [5004],
    "sentiment_service.py": [5008],
    "entity_service.py": [5005],
    "ta_service.py": [5007],
    "deep_ta_service.py": [5200],
    "research_service.py": [5202],
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
    "dashboard_service.py": [8000],
    "bond_service.py": [8145],
    "volatility_service.py": [8155],
    "options_service.py": [8165],
    "capital_flow_service.py": [8175],
    "corporate_intel_service.py": [8185],
    "regime_service.py": [8195],
    "esg_service.py": [8190],
    "macro_economics_service.py": [8205],
    "supply_chain_service.py": [8210],
    "entity_correlation_service.py": [8200],
    "copilot_gateway.py": [8500],
    "vite_frontend": [5151],
    "sinabung_monitoring": [9000]
}

# Reverse mapping: Port -> Log file name
PORT_TO_LOG = {}
for py_file, ports in SERVICE_PORTS_MAPPING.items():
    log_name = py_file.replace('.py', '.log')
    for p in ports:
        PORT_TO_LOG[p] = log_name

_ALL_BE_PORTS = {
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
    5202: "Research Service API",
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
    8145: "Bond Intelligence",
    8155: "Volatility Engine",
    8165: "Options Intel",
    8175: "Capital Flows",
    8185: "Corporate Intel",
    8195: "Regime Intelligence",
    8190: "ESG Monitoring",
    8205: "Macro Economics",
    8210: "Supply Chain Intel",
    8170: "Bot Telegram (MAHAMERU)",
    8200: "Entity Correlation",
    8500: "Mahameru Copilot AI",
    9000: "Sinabung Monitoring (Self)",
}

DEV_ESSENTIAL_PORTS = [5006, 8092, 8200, 8097, 8098, 8093, 8094, 5151, 5202, 8170, 8500]

BE_PORTS = {k: v for k, v in _ALL_BE_PORTS.items() if k in DEV_ESSENTIAL_PORTS} if DEV_MODE else _ALL_BE_PORTS

FE_PORTS = {
    5151: "Vite SolidJS FE"
}

IMPORTANT_TABLES = [
    "article", "ais_history", "global_conflicts", "global_trade_alerts",
    "government_facilities", "military_facilities", "power_plants",
    "oil_refineries", "datacenter_hub", "mines_data", "offshore_platforms",
    "petroleum_terminals", "oil_trades"
]
