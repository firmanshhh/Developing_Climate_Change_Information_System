from flask import (
    Flask, render_template, send_from_directory, send_file,
    request, redirect, url_for, session, flash
)
from werkzeug.utils import secure_filename
import os
import shutil
import re
from io import BytesIO
import zipfile
from config import BLOCKED_PATHS
import pandas as pd
import json
from config import BLOCKED_PATHS

# ========================
# 🔧 KONFIGURASI APLIKASI
# ========================
app = Flask(__name__)
app.secret_key = 'ccis_bmkg_strong_secret_key_2025'

ADMIN_USERS = {
    'admin': 'password123',
    'bmkg': 'climate2025'
}

ROOT_FOLDER = os.path.abspath('./files')
os.makedirs(ROOT_FOLDER, exist_ok=True)


# ========================
# 🧠 FUNGSI BANTU (HELPER)
# ========================

def is_admin():
    return session.get('user_role') == 'admin'

def is_safe_path(base, path):
    """Cegah path traversal"""
    try:
        base_real = os.path.realpath(base)
        path_real = os.path.realpath(os.path.join(base, path))
        return path_real.startswith(base_real + os.sep) or path_real == base_real
    except Exception:
        return False

def contains_blocked_path(filepath):
    """Cek apakah path mengandung folder/file sensitif"""
    if not filepath:
        return False
    parts = [part for part in filepath.split('/') if part]
    return any(part in BLOCKED_PATHS for part in parts)

def get_directory_contents(folder_path, show_blocked=False):
    """Ambil isi folder, sembunyikan item sensitif jika bukan admin"""
    if not os.path.exists(folder_path):
        return None, "📁 Folder tidak ditemukan."
    if not os.path.isdir(folder_path):
        return None, "❌ Path bukan folder."

    items = []
    try:
        for name in os.listdir(folder_path):
            if name.startswith('.') and not show_blocked:
                continue
            if name in BLOCKED_PATHS and not show_blocked:
                continue

            item_path = os.path.join(folder_path, name)
            if os.path.isfile(item_path):
                stat = os.stat(item_path)
                items.append({
                    'name': name,
                    'is_file': True,
                    'is_dir': False,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                })
            else:
                items.append({
                    'name': name,
                    'is_file': False,
                    'is_dir': True,
                    'size': None,
                    'mtime': os.stat(item_path).st_mtime
                })
        return items, None
    except PermissionError:
        return None, "🔒 Akses ditolak."
    except Exception as e:
        return None, f"Error: {str(e)}"

def get_icon_class(filename):
    if '.' not in filename:
        return 'files'
    ext = filename.split('.')[-1].lower()
    icons = {
        'pdf': 'pdf', 'txt': 'txt', 'log': 'txt',
        'zip': 'zip', 'rar': 'zip', '7z': 'zip', 'tar': 'zip', 'gz': 'zip',
        'jpg': 'jpg', 'jpeg': 'jpg', 'png': 'png', 'gif': 'png', 'webp': 'png', 'svg': 'svg',
        'doc': 'doc', 'docx': 'doc', 'odt': 'doc',
        'xls': 'xlsx', 'xlsx': 'xlsx', 'ods': 'xlsx', 'csv': 'csv',
        'ppt': 'ppt', 'pptx': 'ppt',
        'mp3': 'mp3', 'wav': 'mp3', 'ogg': 'mp3',
        'mp4': 'mp4', 'webm': 'mp4', 'avi': 'mp4', 'mkv': 'mp4',
        'py': 'files', 'js': 'js', 'html': 'html', 'css': 'css', 'json': 'json', 'xml': 'xml',
        'ai': 'files', 'psd': 'files'
    }
    return icons.get(ext, 'files')


# ========================
# 🔑 AUTHENTICATION ROUTES
# ========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in ADMIN_USERS and ADMIN_USERS[username] == password:
            session.update({
                'logged_in': True,
                'username': username,
                'user_role': 'admin'
            })
            return redirect(url_for('browse'))
        else:
            flash('Username atau password salah.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('browse'))


# ========================
# 🏠 PUBLIC & STATIC ROUTES
# ========================

@app.route('/')
def home():
    return redirect(url_for('browse'))

# ========================
# 🌦️ CLIMPACT ROUTES
# ========================
@app.route('/climpact')
def climpact():
    return render_template('climpact.html')

@app.route('/climpact/preview', methods=['POST'])
def climpact_preview():
    if 'station_file' not in request.files:
        flash('File tidak dipilih.', 'error')
        return redirect(url_for('climpact'))

    file = request.files['station_file']
    if file.filename == '':
        flash('File tidak dipilih.', 'error')
        return redirect(url_for('climpact'))

    # Simpan sementara
    filename = secure_filename(file.filename)
    filepath = os.path.join('uploads', filename)
    file.save(filepath)

    try:
        df = pd.read_csv(filepath, sep=';')
        required_cols = ['DATA_TIMESTAMP', 'NAME', 'CURRENT_LATITUDE', 'CURRENT_LONGITUDE', 'tmin', 'tmax', 'ch', 'YEAR']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Kolom '{col}' tidak ditemukan dalam file.")

        # Konversi tanggal
        df['date'] = pd.to_datetime(df['DATA_TIMESTAMP'], format='%d/%m/%Y', errors='coerce')
        if df['date'].isnull().any():
            raise ValueError("Format tanggal DATA_TIMESTAMP tidak valid. Harus DD/MM/YYYY.")

        # Ambil metadata
        first_row = df.iloc[0]
        station_name = str(first_row['NAME']).strip()
        lat = float(first_row['CURRENT_LATITUDE'])
        lon = float(first_row['CURRENT_LONGITUDE'])

        if not (-90 <= lat <= 90):
            raise ValueError("Latitude harus antara -90 dan 90.")
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude harus antara -180 dan 180.")

        # Tentukan rentang tahun
        data_min_year = int(df['YEAR'].min())
        data_max_year = int(df['YEAR'].max())

        # Ambil input manual (boleh kosong)
        start_year = request.form.get('start_year', '').strip() or None
        end_year = request.form.get('end_year', '').strip() or None

        # Validasi manual input
        use_start = int(start_year) if start_year is not None else None
        use_end = int(end_year) if end_year is not None else None

        if use_start is not None and use_end is not None:
            if use_start > use_end:
                raise ValueError("Start Year tidak boleh lebih besar dari End Year.")
            if use_start < data_min_year or use_end > data_max_year:
                raise ValueError(
                    f"Periode manual ({use_start}–{use_end}) harus dalam rentang data ({data_min_year}–{data_max_year})."
                )
            final_start = use_start
            final_end = use_end
        else:
            final_start = data_min_year
            final_end = data_max_year

        # Filter data
        df = df[(df['YEAR'] >= final_start) & (df['YEAR'] <= final_end)]
        if df.empty:
            raise ValueError("Tidak ada data dalam periode yang ditentukan.")

        # Siapkan data untuk plot
        dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
        tmax = df['tmax'].where(pd.notnull(df['tmax']), None).tolist()
        tmin = df['tmin'].where(pd.notnull(df['tmin']), None).tolist()
        pr = df['ch'].where(pd.notnull(df['ch']), None).tolist()

        # Simpan file sementara dengan ID unik
        temp_id = f"{os.path.splitext(filename)[0]}_{int(pd.Timestamp.now().timestamp())}"
        temp_path = os.path.join('uploads', temp_id + '.csv')
        os.rename(filepath, temp_path)

        return render_template(
            'climpact_preview.html',
            temp_file=temp_id + '.csv',
            station_name=station_name,
            latitude=lat,
            longitude=lon,
            has_temp=('tmax' in df.columns and 'tmin' in df.columns),
            has_rain=('ch' in df.columns),
            year_range=f"{data_min_year}–{data_max_year}",
            data_start_year=data_min_year,
            data_end_year=data_max_year,
            start_year=start_year,
            end_year=end_year,
            dates_json=json.dumps(dates),
            tmax_json=json.dumps(tmax),
            tmin_json=json.dumps(tmin),
            pr_json=json.dumps(pr)
        )

    except Exception as e:
        flash(f"Error saat membaca file: {str(e)}", 'error')
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect(url_for('climpact'))

@app.route('/climpact/process', methods=['POST'])
def climpact_process():
    temp_file = request.form.get('temp_file')
    if not temp_file:
        flash('File sementara tidak ditemukan.', 'error')
        return redirect(url_for('climpact'))

    filepath = os.path.join('uploads', temp_file)
    if not os.path.exists(filepath):
        flash('File sementara telah kadaluarsa.', 'error')
        return redirect(url_for('climpact'))

    start_year = request.form.get('start_year', '').strip() or None
    end_year = request.form.get('end_year', '').strip() or None

    try:
        from utils.climpact_processor import process_climpact_data
        result_df, metadata = process_climpact_data(filepath, start_year, end_year)

        result_filename = f"{metadata['station_name'].replace(' ', '_')}_indices.csv"
        result_path = os.path.join('uploads', result_filename)
        result_df.to_csv(result_path)

        # Hapus file sementara
        os.remove(filepath)

        return render_template(
            'climpact_result.html',
            result_df=result_df,
            metadata=metadata,
            result_filename=result_filename
        )

    except Exception as e:
        flash(f"Error saat memproses data: {str(e)}", 'error')
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect(url_for('climpact'))

@app.route('/climpact/generate-template')
def generate_template():
    from io import StringIO
    import csv
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        'DATA_TIMESTAMP', 'WMO_ID', 'NAME', 'CURRENT_LATITUDE', 'CURRENT_LONGITUDE',
        'tave', 'tmin', 'tmax', 'ch', 'YEAR', 'MONTH', 'DAY'
    ])
    writer.writerow([
        '01/01/1981', '96001', 'Stasiun Meteorologi Maimun Saleh', '5.87655', '95.33785',
        '27.1', '23.0', '28.3', '0', '1981', '1', '1'
    ])
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='climpact_template.csv'
    )

@app.route('/climpact/download/<filename>')
def download_climpact_result(filename):
    return send_from_directory('uploads', filename, as_attachment=True)


# ========================
# 📁 FILE BROWSER & MANAJEMEN FILE
# ========================

@app.route('/files/')
@app.route('/files/<path:filepath>')
def browse(filepath=""):
    if not is_safe_path(ROOT_FOLDER, filepath):
        return "🚫 Akses ditolak.", 403
    if contains_blocked_path(filepath) and not is_admin():
        return "🚫 Akses ditolak.", 403

    target_path = os.path.join(ROOT_FOLDER, filepath)
    if os.path.isdir(target_path):
        items, error = get_directory_contents(target_path, show_blocked=is_admin())
        icon_map = {
            item['name']: 'folder' if item['is_dir'] else get_icon_class(item['name'])
            for item in (items or [])
        }

        parent_path = None
        clean_path = filepath.strip('/')
        if clean_path:
            parent = os.path.dirname(clean_path)
            parent_path = parent if parent else None

        return render_template(
            'ftp.html',
            items=items,
            current_path=filepath,
            parent_path=parent_path,
            error=error,
            icon_map=icon_map,
            is_admin=is_admin()
        )

    elif os.path.isfile(target_path):
        filename = os.path.basename(target_path)
        if filename in BLOCKED_PATHS and not is_admin():
            return "🚫 Akses ditolak.", 403
        return send_from_directory(os.path.dirname(target_path), filename)

    else:
        return "📁 Tidak ditemukan.", 404


@app.route('/files/<path:filepath>/download-zip')
def download_zip(filepath):
    if not is_safe_path(ROOT_FOLDER, filepath) or (contains_blocked_path(filepath) and not is_admin()):
        return "🚫 Akses ditolak.", 403

    target_path = os.path.join(ROOT_FOLDER, filepath)
    if not os.path.isdir(target_path):
        return "📁 Folder tidak ditemukan.", 404

    memory = BytesIO()
    try:
        with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(target_path):
                if not is_admin():
                    dirs[:] = [d for d in dirs if d not in BLOCKED_PATHS]
                    files = [f for f in files if f not in BLOCKED_PATHS]
                for f in files:
                    full_path = os.path.join(root, f)
                    arcname = os.path.relpath(full_path, target_path)
                    zf.write(full_path, arcname)
        memory.seek(0)
        folder_name = os.path.basename(target_path.rstrip('/'))
        return send_file(
            memory,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{folder_name}.zip"
        )
    except Exception as e:
        return f"❌ Gagal membuat ZIP: {str(e)}", 500


@app.route('/download-selected')
def download_selected():
    files_param = request.args.getlist('files')
    if not files_param:
        return "❌ Tidak ada file dipilih.", 400

    current_path = request.args.get('path', '').strip('/')
    if not is_safe_path(ROOT_FOLDER, current_path) or (contains_blocked_path(current_path) and not is_admin()):
        return "🚫 Akses ditolak.", 403
    if not is_admin() and any(f in BLOCKED_PATHS for f in files_param):
        return "🚫 Akses ditolak.", 403

    target_dir = os.path.join(ROOT_FOLDER, current_path)
    memory = BytesIO()
    with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in files_param:
            fname_clean = secure_filename(fname)
            if not is_admin() and fname_clean in BLOCKED_PATHS:
                continue
            fpath = os.path.join(target_dir, fname_clean)
            if os.path.isfile(fpath):
                zf.write(fpath, fname_clean)
    memory.seek(0)
    return send_file(
        memory,
        as_attachment=True,
        download_name="selected_files.zip",
        mimetype='application/zip'
    )


# ========================
# ⚙️ ADMIN-ONLY OPERATIONS
# ========================

@app.route('/upload', methods=['POST'])
def upload_files():
    if not is_admin():
        return "🚫 Akses ditolak. Hanya admin.", 403

    path = request.form.get('path', '').strip('/')
    if not is_safe_path(ROOT_FOLDER, path) or contains_blocked_path(path):
        return "❌ Akses ditolak.", 403

    target_dir = os.path.join(ROOT_FOLDER, path)
    os.makedirs(target_dir, exist_ok=True)

    files = request.files.getlist("files")
    if not files or all(f.filename == '' for f in files):
        return "❌ Tidak ada file dipilih.", 400

    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            if filename in BLOCKED_PATHS:
                continue
            file.save(os.path.join(target_dir, filename))
    return "OK"


@app.route('/mkdir', methods=['POST'])
def make_directory():
    if not is_admin():
        return "🚫 Akses ditolak. Hanya admin.", 403

    path = request.form.get('path', '').strip('/')
    folder_name = request.form.get('name', '').strip()

    if not folder_name:
        return "❌ Nama folder tidak boleh kosong.", 400
    if not re.match(r'^[a-zA-Z0-9_\-\.\(\) ]+$', folder_name):
        return "❌ Nama folder mengandung karakter tidak valid.", 400
    if any(c in folder_name for c in ['..', '/', '\\']):
        return "❌ Nama folder tidak aman.", 400
    if folder_name in BLOCKED_PATHS:
        return "❌ Nama folder tidak diizinkan.", 400
    if not is_safe_path(ROOT_FOLDER, path):
        return "🚫 Akses ditolak.", 403

    target_dir = os.path.join(ROOT_FOLDER, path, folder_name)
    if os.path.exists(target_dir):
        return f"❌ Folder '{folder_name}' sudah ada.", 400

    try:
        os.makedirs(target_dir, exist_ok=False)
        return "OK"
    except Exception as e:
        return f"❌ Gagal membuat folder: {str(e)}", 500


@app.route('/delete', methods=['POST'])
def delete_items():
    if not is_admin():
        return "🚫 Akses ditolak. Hanya admin.", 403

    path = request.form.get('path', '').strip('/')
    items = request.form.getlist('items')
    if not items:
        return "❌ Tidak ada item dipilih.", 400
    if not is_safe_path(ROOT_FOLDER, path):
        return "🚫 Akses ditolak.", 403

    target_dir = os.path.join(ROOT_FOLDER, path)
    for name in items:
        name = secure_filename(name)
        if name in BLOCKED_PATHS:
            continue
        item_path = os.path.join(target_dir, name)
        full_path = os.path.realpath(item_path)
        if not full_path.startswith(os.path.realpath(ROOT_FOLDER) + os.sep):
            continue
        try:
            if os.path.isfile(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
        except Exception as e:
            return f"❌ Gagal menghapus '{name}': {str(e)}", 500
    return "OK"


# ========================
# 🚀 ENTRY POINT
# ========================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
