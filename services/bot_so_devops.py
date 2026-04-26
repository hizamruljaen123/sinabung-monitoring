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
from config import BE_PORTS, FE_PORTS, LOGS_DIR, ENVIRONMENTS
from services.monitoring import (
    get_process_info, get_disk_usage, 
    start_environment, stop_environment
)
from services.database import get_table_counts
from services.bot_helpers import send_message, _api, safe_get

# Legacy paths for backward compatibility if needed, but we should use ENVIRONMENTS now
BASE_DIR = ENVIRONMENTS["main"]["be_path"]
FE_DIR   = ENVIRONMENTS["main"]["fe_path"]

def get_env_context(args):
    """
    Extract environment from args. Default to 'main'.
    Returns (env_name, env_config)
    """
    env_name = "main"
    if args and args[0].lower() in ENVIRONMENTS:
        env_name = args[0].lower()
        args.pop(0) # Remove env name from args so remaining args are service names etc.
    return env_name, ENVIRONMENTS[env_name]

# ─── /so_status [env] ─────────────────────────────────────────────────────────
def handle_so_status(chat_id, args=None):
    env_name, env_cfg = get_env_context(args)
    
    # If "main", use the full port mapping. If others, just use their specific ports for now
    # or we can define per-env port mappings in config if needed.
    if env_name == "main":
        combined = {**BE_PORTS, **FE_PORTS}
    else:
        combined = {
            env_cfg["be_port"]: f"BE-{env_name.upper()}",
            env_cfg["fe_port"]: f"FE-{env_name.upper()}"
        }

    online, offline = [], []
    for port, name in sorted(combined.items()):
        info = get_process_info(port, name)
        if info["status"] == "ONLINE":
            online.append(f"  ✅ {name[:22]:<22} :{port}")
        else:
            offline.append(f"  ❌ {name[:22]:<22} :{port}")

    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()

    lines = [
        f"🌋 <b>SINABUNG NODE STATUS ({env_name.upper()})</b>",
        f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"🌐 Domain: {env_cfg['fe_domain']}",
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
    send_message(chat_id, "\n".join(lines[:7]) + f"\n<pre>" + "\n".join(lines[7:]) + "</pre>", auto_delete_seconds=60)


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
    send_message(chat_id, msg, auto_delete_seconds=60)


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
    send_message(chat_id, msg, auto_delete_seconds=60)


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
    send_message(chat_id, msg, auto_delete_seconds=60)


# ─── /so_db_stats ─────────────────────────────────────────────────────────────
def handle_so_db_stats(chat_id):
    counts = get_table_counts()
    rows = "\n".join([
        f"  {t.replace('_',' '):<28}: {(str(c)+' rows') if c >= 0 else 'ERROR':>10}"
        for t, c in counts.items()
    ])
    msg = f"📊 <b>DATABASE TABLE COUNTS</b>\n\n<pre>{rows}</pre>"
    send_message(chat_id, msg, auto_delete_seconds=60)


# ─── /so_logs_clear ───────────────────────────────────────────────────────────
def handle_so_logs_clear(chat_id):
    from services.monitoring import purge_all_logs
    result = purge_all_logs()
    if result["status"] == "success":
        cleared = "\n".join([f"  ✓ {f}" for f in result["cleared"]])
        send_message(chat_id, f"🗑️ <b>LOG PURGE COMPLETE</b>\n\n<pre>{cleared}</pre>", auto_delete_seconds=60)
    else:
        send_message(chat_id, f"❌ <b>LOG PURGE FAILED</b>\n{result.get('message','')}", auto_delete_seconds=60)


# ─── /so_restart_node [env] <name> ─────────────────────────────────────────────
def handle_so_restart_node(chat_id, args):
    if not args:
        send_message(chat_id, "⚠️ Usage: <code>/so_restart_node [env] &lt;service_name&gt;</code>\nExample: /so_restart_node dev ta_service")
        return
    
    env_name, env_cfg = get_env_context(args)
    if not args:
        send_message(chat_id, "⚠️ Please specify a service name.")
        return

    node_name = args[0].strip().lower().replace('.py', '') + '.py'
    
    # If it's a specific env, we might be starting the whole BE/FE or a specific node
    # For now, we assume nodes are in BE path.
    target_dir = env_cfg["be_path"]
    script_path = os.path.join(target_dir, node_name)
    
    if not os.path.exists(script_path):
        send_message(chat_id, f"❌ Service not found in <b>{env_name}</b>: <code>{node_name}</code>\nPath: {script_path}")
        return
    
    # Kill process on its port, then relaunch
    try:
        import sys
        # Note: In production, you'd want to use PM2 or systemd. 
        # This is a basic relaunch for dev/staging.
        proc = subprocess.Popen([sys.executable, script_path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                cwd=target_dir)
        send_message(chat_id, f"🔄 <b>Restarted ({env_name.upper()}):</b> <code>{node_name}</code>\nNew PID: {proc.pid}", auto_delete_seconds=60)
    except Exception as e:
        send_message(chat_id, f"❌ Failed to restart <code>{node_name}</code> in {env_name}:\n{e}", auto_delete_seconds=60)


# ─── /so_backup_now ───────────────────────────────────────────────────────────
def handle_so_backup_now(chat_id):
    data = safe_get(_api("dashboard", "/api/backup/trigger"))
    if data:
        send_message(chat_id, f"✅ <b>Backup Triggered</b>\n<pre>{str(data)[:500]}</pre>", auto_delete_seconds=60)
    else:
        send_message(chat_id, "⚠️ Backup service did not respond. Check port 5004/8000.", auto_delete_seconds=60)


# ─── /so_git_pull [env] [be|fe] ───────────────────────────────────────────────
def handle_so_git_pull(chat_id, args):
    env_name, env_cfg = get_env_context(args)
    target = args[0] if args else "be"
    cwd = env_cfg["be_path"] if target == "be" else env_cfg["fe_path"]
    
    if not os.path.exists(cwd):
        send_message(chat_id, f"❌ Path not found for <b>{env_name}</b>: <code>{cwd}</code>")
        return

    try:
        r = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=cwd, timeout=30)
        out = r.stdout.strip() or r.stderr.strip()
        send_message(chat_id, f"📦 <b>GIT PULL [{env_name.upper()} : {target.upper()}]</b>\n<pre>{out[:1000]}</pre>", auto_delete_seconds=60)
    except Exception as e:
        send_message(chat_id, f"❌ Git pull failed: {e}", auto_delete_seconds=60)


# ─── /so_npm_build [env] ──────────────────────────────────────────────────────
def handle_so_npm_build(chat_id, args):
    env_name, env_cfg = get_env_context(args)
    cwd = env_cfg["fe_path"]
    
    if not os.path.exists(cwd):
        send_message(chat_id, f"❌ FE Path not found for <b>{env_name}</b>: <code>{cwd}</code>")
        return

    send_message(chat_id, f"🏗️ <b>Starting npm build [{env_name.upper()}]…</b> (this may take a moment)")
    try:
        # Use specific port if specified in config for npm run dev or build
        # But npm run build usually doesn't care about port until preview
        r = subprocess.run(["npm", "run", "build"], capture_output=True, text=True,
                           cwd=cwd, timeout=180, shell=True)
        out = (r.stdout + r.stderr).strip()
        status = "✅ Build SUCCESS" if r.returncode == 0 else "❌ Build FAILED"
        send_message(chat_id, f"<b>{status} [{env_name.upper()}]</b>\n<pre>{out[-1500:]}</pre>", auto_delete_seconds=60)
    except Exception as e:
        send_message(chat_id, f"❌ npm build error: {e}", auto_delete_seconds=60)


# ─── /so_start_env [env] ──────────────────────────────────────────────────────
def handle_so_start_env(chat_id, args):
    if not args:
        send_message(chat_id, "⚠️ Usage: <code>/so_start_env &lt;env&gt;</code>\nExample: /so_start_env dev")
        return
    
    env_name, env_cfg = get_env_context(args)
    if env_name == "main":
        send_message(chat_id, "⚠️ <b>MAIN</b> environment should be managed via systemd/pm2 for stability.")
        return

    send_message(chat_id, f"🚀 <b>Starting Environment: {env_name.upper()}</b>\nInitializing BE & FE...")
    
    result = start_environment(env_name)
    if result["status"] == "success":
        send_message(chat_id, f"✅ <b>{env_name.upper()} STARTED</b>\nBE Port: {env_cfg['be_port']}\nFE Port: {env_cfg['fe_port']}", auto_delete_seconds=60)
    else:
        send_message(chat_id, f"❌ Failed to start {env_name}:\n{result['message']}", auto_delete_seconds=60)


# ─── /so_stop_env [env] ───────────────────────────────────────────────────────
def handle_so_stop_env(chat_id, args):
    if not args:
        send_message(chat_id, "⚠️ Usage: <code>/so_stop_env &lt;env&gt;</code>\nExample: /so_stop_env dev")
        return
    
    env_name, env_cfg = get_env_context(args)
    if env_name == "main":
        send_message(chat_id, "⚠️ <b>MAIN</b> environment shutdown restricted for safety.")
        return

    send_message(chat_id, f"🛑 <b>Stopping Environment: {env_name.upper()}</b>\nTerminating all processes...")
    
    result = stop_environment(env_name)
    if result["status"] == "success":
        send_message(chat_id, f"⏹️ <b>{env_name.upper()} STOPPED</b>\nTerminated {result['killed_count']} parent processes and their children.", auto_delete_seconds=60)
    else:
        send_message(chat_id, f"❌ Error during shutdown of {env_name}:\n{result['message']}", auto_delete_seconds=60)


# ─── /so_env ──────────────────────────────────────────────────────────────────
def handle_so_env(chat_id):
    lines = ["🌐 <b>ENVIRONMENT MAPPING</b>\n"]
    for name, cfg in ENVIRONMENTS.items():
        lines.append(f"<b>{name.upper()}:</b>")
        lines.append(f"  • FE: {cfg['fe_domain']} (Port {cfg['fe_port']})")
        lines.append(f"  • BE: {cfg['be_domain']} (Port {cfg['be_port']})")
        lines.append(f"  • DB: <code>{cfg['db']}</code>")
        lines.append("")
    send_message(chat_id, "\n".join(lines), auto_delete_seconds=120)
