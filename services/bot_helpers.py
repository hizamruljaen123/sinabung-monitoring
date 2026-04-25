"""
bot_helpers.py
─────────────────────────────────────────────
Shared utilities for all Telegram bot modules:
- send_message / send_typed
- broadcast_alert (used by push modules)
- Port registry for Mahameru services
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# ─── Path Map for Mahameru Backend Services ───────────────────────────────────
MAHAMERU_PATHS = {
    "crypto":       "/crypto",
    "crypto_stream":"/ws/crypto",
    "ta":           "/ta",
    "deep_ta":      "/deep-ta",
    "news":         "/news",
    "sentiment":    "/sentiment",
    "entity":       "/entity",
    "forex":        "/forex",
    "commodity":    "/commodity",
    "market":       "/market",
    "ais":          "/ais",
    "oil_refinery": "/refinery",
    "oil_trade":    "/oil-trade",
    "port":         "/port",
    "mines":        "/mines",
    "disaster":     "/disaster",
    "geo":          "/geo",
    "conflict":     "/conflict",
    "military":     "/military",
    "gov_facility": "/government",
    "vessel":       "/vessel",
    "datacenter":   "/datacenter",
    "infrastructure":"/infra",
    "dashboard":    "/dashboard",
}

# ─── Message Tracking (Persistent SQLite) ──────────────────────────────────────
from services.bot_cache import save_message
import hashlib

LAST_MESSAGE_HASH = {} # chat_id -> md5_hash

def _get_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def _api(service: str, path: str = ""):
    base_path = MAHAMERU_PATHS.get(service, f"/{service}")
    return f"https://api.asetpedia.online{base_path}{path}"

import threading
import time

def delete_message(chat_id, message_id, token):
    """Helper to delete a message after a delay."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
            timeout=5
        )
    except: pass

def send_message(chat_id, text, parse_mode="HTML", auto_delete_seconds=None):
    """Send a Telegram message, optionally scheduling it for deletion."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    # Deduplication: Prevent sending the exact same message twice in a row
    msg_hash = _get_hash(text)
    if LAST_MESSAGE_HASH.get(chat_id) == msg_hash:
        # If it's an alert, maybe we want to skip. 
        # But if it's a command response, usually user wants to see it.
        # However, "pesan ganda" usually happens with alerts or reloader bugs.
        return None
    
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=8
        )
        if resp.status_code == 200:
            LAST_MESSAGE_HASH[chat_id] = msg_hash
            msg_data = resp.json().get("result", {})
            msg_id = msg_data.get("message_id")
            
            if auto_delete_seconds and msg_id:
                threading.Timer(auto_delete_seconds, delete_message, [chat_id, msg_id, TELEGRAM_BOT_TOKEN]).start()
            
            # Always track for manual /so_clear_history
            save_message(chat_id, msg_id)
            
            return msg_id
    except Exception as e:
        print(f"[Bot] send_message error: {e}")
    return None

def broadcast_alert(text, parse_mode="HTML"):
    """Broadcast an auto-alert to the configured TELEGRAM_CHAT_ID."""
    if not TELEGRAM_CHAT_ID:
        return
    send_message(TELEGRAM_CHAT_ID, text, parse_mode)

def safe_get(url, timeout=8):
    """HTTP GET with error handling. Returns dict or None."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[Bot] safe_get error {url}: {e}")
    return None

def fmt_number(n):
    """Format big numbers nicely."""
    if n is None:
        return "N/A"
    if abs(n) >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:.4f}"
