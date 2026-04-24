import os
import shutil
import zipfile
import tarfile
import mimetypes
from functools import wraps
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file, session
from ftplib import FTP, error_perm
from config import FM_ROOT_PATH, FM_PASSWORD

filemanager = Blueprint('filemanager', __name__)


# ─── Auth Guard ─────────────────────────────────────────────────────────────

def fm_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('fm_authenticated'):
            return jsonify({'error': 'Unauthorized. Please authenticate first.'}), 401
        return f(*args, **kwargs)
    return decorated


def safe_path(rel_path: str) -> str:
    """Resolve path safely within FM_ROOT_PATH to prevent directory traversal."""
    base = os.path.realpath(FM_ROOT_PATH)
    target = os.path.realpath(os.path.join(base, rel_path.lstrip('/')))
    if not target.startswith(base):
        raise PermissionError("Access denied: path traversal attempt detected.")
    return target


# ─── Authentication ─────────────────────────────────────────────────────────

@filemanager.route('/api/fm/login', methods=['POST'])
def fm_login():
    data = request.json or {}
    pwd = data.get('password', '')
    if pwd == FM_PASSWORD:
        session['fm_authenticated'] = True
        return jsonify({'status': 'success', 'message': 'Authenticated'})
    return jsonify({'status': 'error', 'message': 'Invalid password'}), 401


@filemanager.route('/api/fm/logout', methods=['POST'])
def fm_logout():
    session.pop('fm_authenticated', None)
    return jsonify({'status': 'success'})


@filemanager.route('/api/fm/status')
def fm_status():
    return jsonify({'authenticated': bool(session.get('fm_authenticated'))})


# ─── Browse ──────────────────────────────────────────────────────────────────

@filemanager.route('/api/fm/browse')
@fm_login_required
def fm_browse():
    rel = request.args.get('path', '')
    try:
        abs_path = safe_path(rel)
        if not os.path.isdir(abs_path):
            return jsonify({'error': 'Not a directory'}), 400

        items = []
        for entry in sorted(os.scandir(abs_path), key=lambda e: (not e.is_dir(), e.name.lower())):
            stat = entry.stat(follow_symlinks=False)
            items.append({
                'name': entry.name,
                'path': os.path.join(rel, entry.name).replace('\\', '/'),
                'is_dir': entry.is_dir(),
                'size': stat.st_size if not entry.is_dir() else None,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'ext': os.path.splitext(entry.name)[1].lower() if not entry.is_dir() else '',
            })

        parent = os.path.dirname(rel.rstrip('/')) if rel and rel != '/' else None
        return jsonify({'path': rel or '/', 'parent': parent, 'items': items})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Download ────────────────────────────────────────────────────────────────

@filemanager.route('/api/fm/download')
@fm_login_required
def fm_download():
    rel = request.args.get('path', '')
    try:
        abs_path = safe_path(rel)
        if not os.path.isfile(abs_path):
            return jsonify({'error': 'Not a file'}), 400
        mime, _ = mimetypes.guess_type(abs_path)
        return send_file(abs_path, as_attachment=True, mimetype=mime or 'application/octet-stream')
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Upload ──────────────────────────────────────────────────────────────────

@filemanager.route('/api/fm/upload', methods=['POST'])
@fm_login_required
def fm_upload():
    rel = request.form.get('path', '')
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files provided'}), 400
    try:
        dest_dir = safe_path(rel)
        if not os.path.isdir(dest_dir):
            return jsonify({'error': 'Destination is not a directory'}), 400
        saved = []
        for f in files:
            if f.filename:
                dest = os.path.join(dest_dir, os.path.basename(f.filename))
                f.save(dest)
                saved.append(f.filename)
        return jsonify({'status': 'success', 'uploaded': saved})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Delete ──────────────────────────────────────────────────────────────────

@filemanager.route('/api/fm/delete', methods=['POST'])
@fm_login_required
def fm_delete():
    rel = request.json.get('path', '')
    try:
        abs_path = safe_path(rel)
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        elif os.path.isfile(abs_path):
            os.remove(abs_path)
        else:
            return jsonify({'error': 'Path does not exist'}), 404
        return jsonify({'status': 'success'})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Rename / Move ───────────────────────────────────────────────────────────

@filemanager.route('/api/fm/rename', methods=['POST'])
@fm_login_required
def fm_rename():
    data = request.json or {}
    src_rel = data.get('path', '')
    new_name = data.get('new_name', '')
    try:
        src = safe_path(src_rel)
        dest = os.path.join(os.path.dirname(src), os.path.basename(new_name))
        dest = os.path.realpath(dest)
        if not dest.startswith(os.path.realpath(FM_ROOT_PATH)):
            raise PermissionError("Access denied.")
        os.rename(src, dest)
        return jsonify({'status': 'success'})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Create Directory ────────────────────────────────────────────────────────

@filemanager.route('/api/fm/mkdir', methods=['POST'])
@fm_login_required
def fm_mkdir():
    data = request.json or {}
    rel = data.get('path', '')
    name = data.get('name', '')
    try:
        parent = safe_path(rel)
        new_dir = os.path.join(parent, os.path.basename(name))
        os.makedirs(new_dir, exist_ok=True)
        return jsonify({'status': 'success'})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Zip / Compress ──────────────────────────────────────────────────────────

@filemanager.route('/api/fm/zip', methods=['POST'])
@fm_login_required
def fm_zip():
    data = request.json or {}
    paths = data.get('paths', [])      # list of relative paths
    dest_rel = data.get('dest', '')    # destination dir
    archive_name = data.get('name', 'archive.zip')

    try:
        dest_dir = safe_path(dest_rel)
        archive_path = os.path.join(dest_dir, os.path.basename(archive_name))
        if not archive_path.endswith('.zip'):
            archive_path += '.zip'

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for rel in paths:
                abs_p = safe_path(rel)
                if os.path.isfile(abs_p):
                    zf.write(abs_p, os.path.basename(abs_p))
                elif os.path.isdir(abs_p):
                    for root, _, files in os.walk(abs_p):
                        for file in files:
                            fp = os.path.join(root, file)
                            arcname = os.path.relpath(fp, os.path.dirname(abs_p))
                            zf.write(fp, arcname)
        return jsonify({'status': 'success', 'archive': os.path.basename(archive_path)})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Extract ─────────────────────────────────────────────────────────────────

@filemanager.route('/api/fm/extract', methods=['POST'])
@fm_login_required
def fm_extract():
    data = request.json or {}
    rel = data.get('path', '')
    dest_rel = data.get('dest', os.path.dirname(data.get('path', '')))

    try:
        src = safe_path(rel)
        dest = safe_path(dest_rel)
        os.makedirs(dest, exist_ok=True)

        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src, 'r') as zf:
                zf.extractall(dest)
        elif tarfile.is_tarfile(src):
            with tarfile.open(src, 'r:*') as tf:
                tf.extractall(dest)
        else:
            return jsonify({'error': 'Unsupported archive format (.zip, .tar, .tar.gz, .tgz only)'}), 400

        return jsonify({'status': 'success', 'extracted_to': dest_rel or '/'})
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── FTP Connect / Browse ────────────────────────────────────────────────────

@filemanager.route('/api/fm/ftp/connect', methods=['POST'])
@fm_login_required
def ftp_connect():
    data = request.json or {}
    host = data.get('host', '')
    port = int(data.get('port', 21))
    user = data.get('user', 'anonymous')
    pwd  = data.get('password', '')
    try:
        ftp = FTP()
        ftp.connect(host, port, timeout=10)
        ftp.login(user, pwd)
        welcome = ftp.getwelcome()
        ftp.quit()
        # Store credentials in session for subsequent FTP operations
        session['ftp_creds'] = {'host': host, 'port': port, 'user': user, 'password': pwd}
        return jsonify({'status': 'success', 'welcome': welcome})
    except error_perm as e:
        return jsonify({'error': f'FTP Auth Error: {e}'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@filemanager.route('/api/fm/ftp/browse')
@fm_login_required
def ftp_browse():
    creds = session.get('ftp_creds')
    if not creds:
        return jsonify({'error': 'No FTP session. Connect first.'}), 400
    path = request.args.get('path', '/')
    try:
        ftp = FTP()
        ftp.connect(creds['host'], creds['port'], timeout=10)
        ftp.login(creds['user'], creds['password'])
        ftp.cwd(path)
        items = []
        def parse_line(line):
            parts = line.split(None, 8)
            if len(parts) < 9:
                return
            is_dir = parts[0].startswith('d')
            name = parts[8]
            size = int(parts[4]) if not is_dir else None
            items.append({'name': name, 'path': path.rstrip('/') + '/' + name, 'is_dir': is_dir, 'size': size})
        ftp.retrlines('LIST', parse_line)
        ftp.quit()
        parent = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
        return jsonify({'path': path, 'parent': parent, 'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@filemanager.route('/api/fm/ftp/download')
@fm_login_required
def ftp_download():
    creds = session.get('ftp_creds')
    if not creds:
        return jsonify({'error': 'No FTP session.'}), 400
    ftp_path = request.args.get('path', '')
    filename = os.path.basename(ftp_path)
    tmp_path = os.path.join('/tmp', filename)
    try:
        ftp = FTP()
        ftp.connect(creds['host'], creds['port'], timeout=30)
        ftp.login(creds['user'], creds['password'])
        with open(tmp_path, 'wb') as f:
            ftp.retrbinary(f'RETR {ftp_path}', f.write)
        ftp.quit()
        return send_file(tmp_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@filemanager.route('/api/fm/ftp/disconnect', methods=['POST'])
@fm_login_required
def ftp_disconnect():
    session.pop('ftp_creds', None)
    return jsonify({'status': 'success'})
