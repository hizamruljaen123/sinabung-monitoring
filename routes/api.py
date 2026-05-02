import subprocess
import psutil
import os
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from config import BE_PORTS, FE_PORTS, DEV_MODE
from services.monitoring import (
    get_process_info, get_error_counts, get_disk_usage, 
    purge_all_logs, start_environment, stop_environment
)
from services.database import get_db_connection, get_table_counts, serialize_row

api = Blueprint('api', __name__)


# ─── Main Page ──────────────────────────────────────────────────────────────

@api.route('/')
def index():
    return render_template('index.html', DEV_MODE=DEV_MODE)


# ─── Stats Endpoint ──────────────────────────────────────────────────────────

@api.route('/api/stats')
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
    system_cpu = psutil.cpu_percent(interval=0.1)
    system_ram = psutil.virtual_memory()

    return jsonify({
        "services": all_stats,
        "total_cpu": round(system_cpu, 1),
        "total_ram": round(system_ram.used / (1024 ** 3), 2),
        "total_ram_capacity": round(system_ram.total / (1024 ** 3), 1),
        "ram_percent": system_ram.percent,
        "db_counts": db_counts,
        "time": datetime.now().strftime("%H:%M:%S"),
        "dev_mode": DEV_MODE
    })


# ─── Git Operations ──────────────────────────────────────────────────────────

def get_cwd(target):
    import os
    base = os.path.join(os.path.dirname(__file__), '..', '..')
    if target == 'be':
        return os.path.normpath(os.path.join(base, 'mahameru-terminal-be'))
    if target == 'fe':
        return os.path.normpath(os.path.join(base, 'mahameru-terminal-fe'))
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

@api.route('/api/git-pull', methods=['POST'])
def git_pull():
    target = request.args.get('target', 'fe')
    cwd = get_cwd(target)
    try:
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True, cwd=cwd)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500


@api.route('/api/git-stash', methods=['POST'])
def git_stash():
    target = request.args.get('target', 'fe')
    cwd = get_cwd(target)
    try:
        result = subprocess.run(['git', 'stash'], capture_output=True, text=True, check=True, cwd=cwd)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500


# ─── Extra Operations ────────────────────────────────────────────────────────

@api.route('/api/npm-install', methods=['POST'])
def npm_install():
    target = request.args.get('target', 'fe')
    cwd = get_cwd(target)
    try:
        result = subprocess.run(['npm', 'install'], capture_output=True, text=True, check=True, cwd=cwd, shell=True)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500

@api.route('/api/build', methods=['POST'])
def build():
    target = request.args.get('target', 'fe')
    cwd = get_cwd(target)
    try:
        # Assuming npm run build
        result = subprocess.run(['npm', 'run', 'build'], capture_output=True, text=True, check=True, cwd=cwd, shell=True)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500

@api.route('/api/terminal/run', methods=['POST'])
def terminal_run():
    """Execute arbitrary shell commands in a target directory."""
    data = request.json
    target = data.get('target', 'be')
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({"status": "error", "message": "No command provided"}), 400
        
    cwd = get_cwd(target)
    
    try:
        # Run command with shell=True to support pipes, etc.
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return jsonify({
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Command timed out after 120s"}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/api/env-config/get', methods=['GET'])
def get_env_config():
    """Read the .env file for a target."""
    target = request.args.get('target', 'be')
    cwd = get_cwd(target)
    env_path = os.path.join(cwd, '.env')
    
    if not os.path.exists(env_path):
        return jsonify({"status": "error", "message": ".env file not found"}), 404
        
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"status": "success", "content": content})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/api/env-config/save', methods=['POST'])
def save_env_config():
    """Overwrite the .env file for a target."""
    data = request.json
    target = data.get('target', 'be')
    content = data.get('content', '')
    
    cwd = get_cwd(target)
    env_path = os.path.join(cwd, '.env')
    
    try:
        # Backup existing .env before overwrite
        if os.path.exists(env_path):
            backup_path = f"{env_path}.bak"
            import shutil
            shutil.copy2(env_path, backup_path)
            
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"status": "success", "message": ".env saved and backed up."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/api/pm2-action/<action>/<app_id>', methods=['POST'])
def pm2_action(action, app_id):
    if action not in ['start', 'stop', 'restart', 'delete', 'reload']:
        return jsonify({"status": "error", "message": "Invalid action"}), 400
    
    # Check for self-reload/restart
    current_pm2_id = os.environ.get('pm_id')
    is_self = current_pm2_id and str(app_id) == str(current_pm2_id)
    
    # Use single string commands for shell=True on Windows
    cmd = f"pm2 {action} {app_id}"
    npx_cmd = f"npx pm2 {action} {app_id}"
    
    try:
        if is_self and action in ['reload', 'restart']:
            # Run in background to allow response to finish
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({"status": "success", "message": f"Self-{action} initiated. System will restart."})
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
        return jsonify({"status": "success", "output": result.stdout})
    except Exception:
        try:
            if is_self and action in ['reload', 'restart']:
                subprocess.Popen(npx_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return jsonify({"status": "success", "message": f"Self-{action} initiated via npx."})
            result = subprocess.run(npx_cmd, capture_output=True, text=True, check=True, shell=True)
            return jsonify({"status": "success", "output": result.stdout})
        except subprocess.CalledProcessError as e:
            return jsonify({
                "status": "error", 
                "message": "PM2 Command Failed",
                "output": e.stderr or e.stdout
            }), 500
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/api/clear-logs/<app_id>', methods=['POST'])
def clear_logs(app_id):
    try:
        cmd = f"pm2 flush {app_id}"
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
        return jsonify({"status": "success", "output": f"Logs flushed for {app_id}"})
    except Exception:
        try:
            npx_cmd = f"npx pm2 flush {app_id}"
            result = subprocess.run(npx_cmd, capture_output=True, text=True, check=True, shell=True)
            return jsonify({"status": "success", "output": f"Logs flushed for {app_id} via npx"})
        except subprocess.CalledProcessError as e:
            return jsonify({"status": "error", "output": e.stderr}), 500


# ─── System Maintenance ──────────────────────────────────────────────────────

@api.route('/api/disk-usage')
def disk_usage():
    stats = get_disk_usage()
    return jsonify(stats)

@api.route('/api/bot-history')
def bot_history():
    """Retrieve recent bot activity logs."""
    from services.bot_cache import get_full_history
    history = get_full_history(limit=100)
    
    formatted = []
    for row in history:
        formatted.append({
            "id": row[0],
            "chat_id": row[1],
            "message_id": row[2],
            "sent_at": row[3],
            "sent_date": row[4]
        })
    return jsonify(formatted)

@api.route('/api/purge-logs', methods=['POST'])
def purge_logs_action():
    res = purge_all_logs()
    return jsonify(res)


# ─── Environment Management ──────────────────────────────────────────────────

@api.route('/api/env/start/<env_name>', methods=['POST'])
def env_start(env_name):
    if env_name == "main":
        return jsonify({"status": "error", "message": "Main environment cannot be controlled via web switch for safety."}), 403
    res = start_environment(env_name)
    return jsonify(res)

@api.route('/api/env/stop/<env_name>', methods=['POST'])
def env_stop(env_name):
    if env_name == "main":
        return jsonify({"status": "error", "message": "Main environment cannot be controlled via web switch for safety."}), 403
    res = stop_environment(env_name)
    return jsonify(res)


# ─── PM2 Operations ─────────────────────────────────────────────────────────

@api.route('/api/pm2-reload/<app_id>', methods=['POST'])
def pm2_reload(app_id):
    return pm2_action('reload', app_id)


@api.route('/api/logs/<int:port>')
def stream_logs(port):
    from config import PORT_TO_LOG, LOGS_DIR
    import os
    import time
    
    log_name = PORT_TO_LOG.get(port)
    
    # Handle UI Aliases (0 = Backend Core, 1 = Frontend UI)
    if port == 0: log_name = "dashboard_service.log"
    if port == 1: log_name = "vite_frontend.log"

    if not log_name:
        return "Log file not mapped", 404
    
    log_path = os.path.join(LOGS_DIR, log_name)
    
    def generate():
        if not os.path.exists(log_path):
            yield f"data: [SYSTEM] Waiting for log file: {log_name}...\n\n"
            while not os.path.exists(log_path):
                time.sleep(1)
        
        # Read the last 50 lines first
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                # Seek back roughly 50 lines
                f.seek(max(0, size - 5000)) 
                lines = f.readlines()
                for line in lines[-50:]:
                    yield f"data: {line.strip()}\n\n"
        except: pass

        # Tail the file
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                yield f"data: {line.strip()}\n\n"

    from flask import current_app
    resp = current_app.response_class(generate(), mimetype='text/event-stream')
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


# ─── Database Manager ────────────────────────────────────────────────────────

@api.route('/api/db/tables')
def list_db_tables():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB Connection Failed"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        return jsonify(tables)
    finally:
        conn.close()


@api.route('/api/db/schema/<table_name>')
def get_table_schema(table_name):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB Connection Failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE {table_name}")
        return jsonify(cursor.fetchall())
    finally:
        conn.close()


@api.route('/api/db/data/<table_name>')
def get_table_data(table_name):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB Connection Failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT COUNT(*) as total FROM {table_name}")
        total = cursor.fetchone()['total']

        cursor.execute(f"SELECT * FROM {table_name} LIMIT %s OFFSET %s", (per_page, offset))
        data = [serialize_row(row) for row in cursor.fetchall()]

        return jsonify({
            "data": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        })
    finally:
        conn.close()


@api.route('/api/db/data/<table_name>', methods=['POST'])
def create_record(table_name):
    data = request.json
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    values = tuple(data.values())

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        return jsonify({"status": "success", "id": cursor.lastrowid})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        conn.close()


@api.route('/api/db/data/<table_name>/<id_col>/<id_val>', methods=['PUT'])
def update_record(table_name, id_col, id_val):
    data = request.json
    set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
    values = tuple(data.values()) + (id_val,)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {id_col} = %s", values)
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        conn.close()


@api.route('/api/db/data/<table_name>/<id_col>/<id_val>', methods=['DELETE'])
def delete_record(table_name, id_col, id_val):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE {id_col} = %s", (id_val,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        conn.close()
