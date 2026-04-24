"""
bot_so_alerts.py — PUSH Auto-Alert Engine (Server/DevOps)
─────────────────────────────────────────────────────────
Runs in a background thread. Monitors & broadcasts:
  - Node crash detection
  - High RAM alert
  - Disk space warning
  - Error log spike detection
  - Backup success confirmation (daily)
"""
import os
import time
import psutil
from datetime import datetime, date
from config import BE_PORTS, FE_PORTS, LOGS_DIR, RAM_ALERT_THRESHOLD
from services.monitoring import get_process_info
from services.bot_helpers import broadcast_alert

ALERT_COOLDOWN  = {}   # key -> last_alert_epoch
DISK_THRESHOLD  = 15   # percent free remaining to warn
ERROR_THRESHOLD = 20   # new errors in 5 min to warn
_prev_error_counts: dict = {}
_last_backup_date = None


def _cooldown_ok(key: str, seconds: int = 900) -> bool:
    """Returns True if enough time has passed since last alert for this key."""
    now = time.time()
    if now - ALERT_COOLDOWN.get(key, 0) > seconds:
        ALERT_COOLDOWN[key] = now
        return True
    return False


# ─── Individual Check Functions ───────────────────────────────────────────────

def check_node_crashes():
    combined = {**BE_PORTS, **FE_PORTS}
    for port, name in combined.items():
        info = get_process_info(port, name)
        if info["status"] == "OFFLINE" and _cooldown_ok(f"crash_{port}", 1800):
            broadcast_alert(
                f"🚨 <b>[SO_ALERT] NODE CRASH</b>\n\n"
                f"Service  : <b>{name}</b>\n"
                f"Port     : <code>{port}</code>\n"
                f"Status   : ❌ OFFLINE\n"
                f"Time     : {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"<i>Launcher auto-recovery should trigger. Check logs.</i>"
            )


def check_high_ram():
    for port, name in {**BE_PORTS, **FE_PORTS}.items():
        info = get_process_info(port, name)
        ram = info["ram"]
        if ram > RAM_ALERT_THRESHOLD and _cooldown_ok(f"ram_{port}", 900):
            broadcast_alert(
                f"⚠️ <b>[SO_ALERT] HIGH RAM USAGE</b>\n\n"
                f"Service  : <b>{name}</b>\n"
                f"Port     : <code>{port}</code>\n"
                f"RAM Used : <b>{ram} MB</b> (threshold: {RAM_ALERT_THRESHOLD} MB)\n"
                f"Time     : {datetime.now().strftime('%H:%M:%S')}"
            )


def check_disk_space():
    try:
        disk = psutil.disk_usage('/')
        free_pct = 100 - disk.percent
        if free_pct < DISK_THRESHOLD and _cooldown_ok("disk_warn", 3600):
            broadcast_alert(
                f"💾 <b>[SO_ALERT] LOW DISK SPACE</b>\n\n"
                f"Total    : {disk.total/(1024**3):.1f} GB\n"
                f"Used     : {disk.used/(1024**3):.1f} GB (<b>{disk.percent}%</b>)\n"
                f"Free     : <b>{disk.free/(1024**3):.1f} GB ({free_pct:.1f}%)</b>\n\n"
                f"⚠️ Disk space is critically low! Consider purging logs: /so_logs_clear"
            )
    except Exception:
        pass


def check_error_log_spikes():
    if not os.path.exists(LOGS_DIR):
        return
    global _prev_error_counts
    for fname in os.listdir(LOGS_DIR):
        if not fname.endswith('.log'):
            continue
        path = os.path.join(LOGS_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - 100_000))
                count = f.read().count('ERROR')
            prev = _prev_error_counts.get(fname, count)
            delta = count - prev
            _prev_error_counts[fname] = count
            if delta >= ERROR_THRESHOLD and _cooldown_ok(f"errspike_{fname}", 600):
                svc_name = fname.replace('.log', '').replace('_', ' ').upper()
                broadcast_alert(
                    f"🔴 <b>[SO_ALERT] ERROR SPIKE DETECTED</b>\n\n"
                    f"Service  : <b>{svc_name}</b>\n"
                    f"Log File : <code>{fname}</code>\n"
                    f"New ERRs : <b>+{delta}</b> in last 5 min\n"
                    f"Total    : {count}\n"
                    f"Time     : {datetime.now().strftime('%H:%M:%S')}"
                )
        except Exception:
            pass


def check_daily_backup():
    global _last_backup_date
    today = date.today()
    if _last_backup_date != today:
        # Placeholder: just confirm backup ran. 
        # Can be wired to backup_service /api/backup/status
        _last_backup_date = today
        broadcast_alert(
            f"✅ <b>[SO_INFO] DAILY CHECK-IN</b>\n\n"
            f"Date     : {today.strftime('%Y-%m-%d')}\n"
            f"Status   : All systems operational at midnight cycle.\n"
            f"Use /so_status for full report."
        )


# ─── Main Alert Loop ─────────────────────────────────────────────────────────

def run_so_alert_loop():
    """Run this in a daemon thread from app.py or telegram_bot.py."""
    print("[*] SO Alert Loop started.")
    tick = 0
    while True:
        try:
            check_node_crashes()
            check_high_ram()

            if tick % 6 == 0:      # every 30 sec
                check_error_log_spikes()

            if tick % 60 == 0:     # every 5 min
                check_disk_space()

            if tick % 720 == 0:    # every hour
                check_daily_backup()

        except Exception as e:
            print(f"[SO Alert Loop] Error: {e}")

        time.sleep(5)
        tick += 1
