import subprocess
import psutil
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from config import BE_PORTS, FE_PORTS, DEV_MODE
from services.monitoring import get_process_info, get_error_counts, get_disk_usage, purge_all_logs
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
    if target == 'be':
        return os.path.join(os.path.dirname(__file__), '..', '..', 'mahameru-terminal-be')
    return os.path.join(os.path.dirname(__file__), '..')

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

@api.route('/api/pm2-action/<action>/<int:app_id>', methods=['POST'])
def pm2_action(action, app_id):
    if action not in ['start', 'stop', 'restart', 'delete', 'reload']:
        return jsonify({"status": "error", "message": "Invalid action"}), 400
    try:
        result = subprocess.run(
            ['npx', 'pm2', action, str(app_id)],
            capture_output=True, text=True, check=True, shell=True
        )
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500

@api.route('/api/clear-logs/<int:app_id>', methods=['POST'])
def clear_logs(app_id):
    try:
        result = subprocess.run(
            ['npx', 'pm2', 'flush', str(app_id)],
            capture_output=True, text=True, check=True, shell=True
        )
        return jsonify({"status": "success", "output": "Logs flushed for ID " + str(app_id)})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500


# ─── System Maintenance ──────────────────────────────────────────────────────

@api.route('/api/disk-usage')
def disk_usage():
    stats = get_disk_usage()
    return jsonify(stats)

@api.route('/api/purge-logs', methods=['POST'])
def purge_logs_action():
    res = purge_all_logs()
    return jsonify(res)


# ─── PM2 Operations ─────────────────────────────────────────────────────────

@api.route('/api/pm2-reload/<int:app_id>', methods=['POST'])
def pm2_reload(app_id):
    try:
        result = subprocess.run(
            ['npx', 'pm2', 'reload', str(app_id)],
            capture_output=True, text=True, check=True
        )
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.stderr}), 500


@api.route('/api/logs/<int:port>')
def stream_logs(port):
    from config import PORT_TO_LOG, LOGS_DIR
    import os
    import time
    
    log_name = PORT_TO_LOG.get(port)
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
    return current_app.response_class(generate(), mimetype='text/event-stream')


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
