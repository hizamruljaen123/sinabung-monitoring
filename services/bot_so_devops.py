"""
bot_so_devops.py — /so_xxxx Command Handlers
─────────────────────────────────────────────
Covers all Sinabung DevOps / Server commands:
  /so_status, /so_cpu, /so_ram, /so_disk,
  /so_db_stats, /so_logs_clear, /so_restart_node,
  /so_backup_now, /so_git_pull, /so_npm_build
"""
import os
import subprocess
import psutil
from datetime import datetime
from config import BE_PORTS, FE_PORTS, LOGS_DIR
from services.monitoring import get_process_info, get_disk_usage
from services.database import get_table_counts
from services.bot_helpers import send_message, _api, safe_get

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'mahameru-terminal-be')
FE_DIR   = os.path.join(os.path.dirname(__file__), '..', '..', 'mahameru-terminal-fe')


# ─── /so_status ───────────────────────────────────────────────────────────────
def handle_so_status(chat_id):
    combined = {**BE_PORTS, **FE_PORTS}
    online, offline = [], []
    for port, name in sorted(combined.items()):
        info = get_process_info(port, name)
        if info["status"] == "ONLINE":
            online.append(f"  ✅ {name[:22]:<22} :{port}")
        else:
            offline.append(f"  ❌ {name[:22]:<22} :{port}")

    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()

    lines = [
        f"🌋 <b>SINABUNG NODE STATUS</b>",
        f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"💻 CPU : {cpu:.1f}%",
        f"🧠 RAM : {ram.used/(1024**3):.2f}/{ram.total/(1024**3):.1f} GB ({ram.percent}%)",
        f"",
        f"<b>ONLINE ({len(online)}):</b>",
        *online,
        f"",
        f"<b>OFFLINE ({len(offline)}):</b>",
        *(offline or ["  —"])
    ]
    send_message(chat_id, "\n".join(lines))


# ─── /so_cpu ──────────────────────────────────────────────────────────────────
def handle_so_cpu(chat_id):
    cpu = psutil.cpu_percent(interval=1.0)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    cores = "\n".join([f"  Core {i}: {v:.1f}%" for i, v in enumerate(per_core)])
    freq_str = f"{freq.current:.0f} MHz" if freq else "N/A"
    msg = (
        f"⚙️ <b>CPU UTILIZATION REPORT</b>\n"
        f"⏱ {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"Total Load : <b>{cpu:.1f}%</b>\n"
        f"Frequency  : {freq_str}\n"
        f"Cores      : {psutil.cpu_count(logical=True)} logical\n\n"
        f"<pre>{cores}</pre>"
    )
    send_message(chat_id, msg)


# ─── /so_ram ──────────────────────────────────────────────────────────────────
def handle_so_ram(chat_id):
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    # Top 5 RAM consumers
    procs = sorted(psutil.process_iter(['pid', 'name', 'memory_info']),
                   key=lambda p: p.info['memory_info'].rss if p.info['memory_info'] else 0,
                   reverse=True)[:5]
    top = "\n".join([
        f"  {p.info['name'][:20]:<20} {p.info['memory_info'].rss/(1024**2):.0f} MB"
        for p in procs if p.info['memory_info']
    ])
    msg = (
        f"🧠 <b>MEMORY ALLOCATION REPORT</b>\n\n"
        f"RAM Used   : {vm.used/(1024**3):.2f} GB / {vm.total/(1024**3):.1f} GB\n"
        f"RAM Free   : {vm.available/(1024**3):.2f} GB\n"
        f"RAM %      : <b>{vm.percent}%</b>\n\n"
        f"Swap Used  : {sw.used/(1024**2):.0f} MB / {sw.total/(1024**2):.0f} MB\n\n"
        f"<b>TOP CONSUMERS:</b>\n<pre>{top}</pre>"
    )
    send_message(chat_id, msg)


# ─── /so_disk ─────────────────────────────────────────────────────────────────
def handle_so_disk(chat_id):
    disk = psutil.disk_usage('/')
    project_stats = get_disk_usage()
    projects_txt = "\n".join([
        f"  {p['name']:<30} {p['size']:>8.1f} MB"
        for p in project_stats
    ])
    # Log dir size
    log_size = sum(
        os.path.getsize(os.path.join(LOGS_DIR, f))
        for f in os.listdir(LOGS_DIR) if f.endswith('.log')
    ) / (1024**2) if os.path.exists(LOGS_DIR) else 0

    msg = (
        f"💾 <b>DISK UTILIZATION REPORT</b>\n\n"
        f"Total   : {disk.total/(1024**3):.1f} GB\n"
        f"Used    : {disk.used/(1024**3):.1f} GB ({disk.percent}%)\n"
        f"Free    : {disk.free/(1024**3):.1f} GB\n\n"
        f"📂 <b>PROJECT SIZES</b> (excl. node_modules/.git):\n"
        f"<pre>{projects_txt}</pre>\n"
        f"📄 Log Dir Size : {log_size:.1f} MB"
    )
    send_message(chat_id, msg)


# ─── /so_db_stats ─────────────────────────────────────────────────────────────
def handle_so_db_stats(chat_id):
    counts = get_table_counts()
    rows = "\n".join([
        f"  {t.replace('_',' '):<28}: {(str(c)+' rows') if c >= 0 else 'ERROR':>10}"
        for t, c in counts.items()
    ])
    msg = f"📊 <b>DATABASE TABLE COUNTS</b>\n\n<pre>{rows}</pre>"
    send_message(chat_id, msg)


# ─── /so_logs_clear ───────────────────────────────────────────────────────────
def handle_so_logs_clear(chat_id):
    from services.monitoring import purge_all_logs
    result = purge_all_logs()
    if result["status"] == "success":
        cleared = "\n".join([f"  ✓ {f}" for f in result["cleared"]])
        send_message(chat_id, f"🗑️ <b>LOG PURGE COMPLETE</b>\n\n<pre>{cleared}</pre>")
    else:
        send_message(chat_id, f"❌ <b>LOG PURGE FAILED</b>\n{result.get('message','')}")


# ─── /so_restart_node <name> ──────────────────────────────────────────────────
def handle_so_restart_node(chat_id, args):
    if not args:
        send_message(chat_id, "⚠️ Usage: <code>/so_restart_node &lt;service_name&gt;</code>\nExample: /so_restart_node ta_service")
        return
    node_name = args[0].strip().lower().replace('.py', '') + '.py'
    script_path = os.path.join(BASE_DIR, node_name)
    if not os.path.exists(script_path):
        send_message(chat_id, f"❌ Service not found: <code>{node_name}</code>")
        return
    # Kill process on its port, then relaunch
    try:
        import sys
        proc = subprocess.Popen([sys.executable, script_path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        send_message(chat_id, f"🔄 <b>Restarted:</b> <code>{node_name}</code>\nNew PID: {proc.pid}")
    except Exception as e:
        send_message(chat_id, f"❌ Failed to restart <code>{node_name}</code>:\n{e}")


# ─── /so_backup_now ───────────────────────────────────────────────────────────
def handle_so_backup_now(chat_id):
    data = safe_get(_api("dashboard", "/api/backup/trigger"))
    if data:
        send_message(chat_id, f"✅ <b>Backup Triggered</b>\n<pre>{str(data)[:500]}</pre>")
    else:
        send_message(chat_id, "⚠️ Backup service did not respond. Check port 5004/8000.")


# ─── /so_git_pull ─────────────────────────────────────────────────────────────
def handle_so_git_pull(chat_id, args):
    target = args[0] if args else "be"
    cwd = BASE_DIR if target == "be" else FE_DIR
    try:
        r = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=cwd, timeout=30)
        out = r.stdout.strip() or r.stderr.strip()
        send_message(chat_id, f"📦 <b>GIT PULL [{target.upper()}]</b>\n<pre>{out[:1000]}</pre>")
    except Exception as e:
        send_message(chat_id, f"❌ Git pull failed: {e}")


# ─── /so_npm_build ────────────────────────────────────────────────────────────
def handle_so_npm_build(chat_id):
    send_message(chat_id, "🏗️ <b>Starting npm build…</b> (this may take a moment)")
    try:
        r = subprocess.run(["npm", "run", "build"], capture_output=True, text=True,
                           cwd=FE_DIR, timeout=120, shell=True)
        out = (r.stdout + r.stderr).strip()
        status = "✅ Build SUCCESS" if r.returncode == 0 else "❌ Build FAILED"
        send_message(chat_id, f"{status}\n<pre>{out[-1500:]}</pre>")
    except Exception as e:
        send_message(chat_id, f"❌ npm build error: {e}")
