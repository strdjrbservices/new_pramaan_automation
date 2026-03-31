import os
import threading
import shutil
import time
from flask import Flask, render_template, request, jsonify, send_from_directory  # pyre-ignore
from werkzeug.utils import secure_filename  # pyre-ignore
from automation import run_automation  # pyre-ignore
from automation_revised import run_revised_automation  # pyre-ignore
from automation_fastapp import run_fastapp_automation  # pyre-ignore
from utils import NEW_FILES_REVISED_PATH, OLD_FILES_REVISED_PATH, HTML_FILES_PATH, LOG_FILES_PATH, DOWNLOAD_PATH, PROCESSED_FILES_PATH, ERROR_FILES_PATH, FULL_FILE_PATH, PAUSE_LOCK_FILE, TERMINATION_LOCK_FILE, logger, IS_PRODUCTION  # pyre-ignore

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(DOWNLOAD_PATH, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper for folder paths
FOLDER_MAP = {
    'new_revised': NEW_FILES_REVISED_PATH,
    'old_revised': OLD_FILES_REVISED_PATH,
    'html_ref': HTML_FILES_PATH,
    'logs': LOG_FILES_PATH,
    'processed': PROCESSED_FILES_PATH,
    'errors': ERROR_FILES_PATH,
    'full_file': FULL_FILE_PATH
}

# Strict Validation Rules
VALID_EXTENSIONS = {
    'html_ref': ['.html'],
    'new_revised': ['_revised.pdf'],
    'old_revised': ['.pdf'],
    'processed': ['.pdf', '.xlsx'],
    'logs': ['.log', '.xlsx', '.html'],
    'errors': ['.png', '.pdf'],
    'full_file': ['.pdf']
}

def is_allowed_file(filename, folder_key):
    exts = VALID_EXTENSIONS.get(folder_key, ['.pdf'])
    filename_lower = filename.lower()
    
    
    for ext in exts:
        if filename_lower.endswith(ext.lower()):
            return True
    return False

@app.route('/api/files/upload/<folder_key>', methods=['POST'])
def generic_upload_to_folder(folder_key):
    path = FOLDER_MAP.get(folder_key)
    if not path: return jsonify({"error": "Invalid folder destination"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No data stream found"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename received"}), 400

    if not is_allowed_file(file.filename, folder_key):
        req = ", ".join(VALID_EXTENSIONS.get(folder_key, ['.pdf']))
        return jsonify({"error": f"Validation Failure: Destination {folder_key} requires {req} format"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(path, filename)
    file.save(save_path)
    
    return jsonify({"message": f"Successfully stored {filename} in {folder_key.upper()} repository"})

@app.route('/api/files/<folder_key>', methods=['GET'])
def list_generic_files(folder_key):
    path = FOLDER_MAP.get(folder_key)
    if not path or not os.path.exists(path):
        return jsonify([])
    files = sorted([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    return jsonify(files)

@app.route('/api/files/<folder_key>/download/<filename>', methods=['GET'])
def download_generic_file(folder_key, filename):
    path = FOLDER_MAP.get(folder_key)
    if not path: return jsonify({"error": "Invalid folder"}), 400
    filename = secure_filename(filename)
    return send_from_directory(path, filename, as_attachment=True)

@app.route('/api/files/<folder_key>', methods=['DELETE'])
def clear_generic_folder(folder_key):
    path = FOLDER_MAP.get(folder_key)
    if not path: return jsonify({"error": "Invalid folder"}), 400
    for f in os.listdir(path):
        os.remove(os.path.join(path, f))
    return jsonify({"message": f"Purged all records in {folder_key}"})

@app.route('/api/pause', methods=['POST'])
def toggle_pause():
    if PAUSE_LOCK_FILE.exists():
        os.remove(PAUSE_LOCK_FILE)
        return jsonify({"paused": False, "message": "Resumed"})
    else:
        PAUSE_LOCK_FILE.touch()
        return jsonify({"paused": True, "message": "Paused"})

@app.route('/api/kill', methods=['POST'])
def kill_automation():
    global automation_status
    automation_status["is_running"] = False
    automation_status["error"] = "Process hard-terminated by user."
    with open(TERMINATION_LOCK_FILE, "w") as f:
        f.write("KILL")
    return jsonify({"message": "Engine sequence killed and termination signal sent."})

@app.route('/api/files/logs', methods=['GET'])
def list_log_files():
    files = []
    if os.path.exists(LOG_FILES_PATH):
        files = sorted(
            [f for f in os.listdir(LOG_FILES_PATH) if os.path.isfile(os.path.join(LOG_FILES_PATH, f))],
            key=lambda x: os.path.getmtime(os.path.join(LOG_FILES_PATH, x)),
            reverse=True
        )
    return jsonify(files)

@app.route('/api/files/logs/download/<filename>', methods=['GET'])
def download_log_file(filename):
    filename = secure_filename(filename)
    return send_from_directory(LOG_FILES_PATH, filename, as_attachment=True)

@app.route('/api/logs/active/content', methods=['GET'])
def get_active_log_content():
    global automation_status
    log_path = automation_status.get("log_file") # This is expected to be a full path or a relative one to LOG_FILES_PATH
    if not log_path:
        return jsonify({"content": "", "filename": None})
    
    
    if not os.path.exists(log_path):
        log_path = os.path.join(LOG_FILES_PATH, os.path.basename(log_path))
        
    if not os.path.exists(log_path):
        return jsonify({"content": "", "filename": None})
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content, "filename": os.path.basename(log_path)})
    except Exception as e:
        return jsonify({"content": f"Error reading log: {str(e)}", "filename": os.path.basename(log_path)})

@app.route('/api/logs/file/content/<path:filename>', methods=['GET'])
def get_log_file_content(filename):
    filename = secure_filename(filename)
    log_path = os.path.join(LOG_FILES_PATH, filename)
    if not os.path.exists(log_path):
        return jsonify({"error": "File not found"}), 404
        
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Global state to track automation logs
automation_status: dict[str, str | bool | None | int] = {
    "is_running": False,
    "log_file": None,
    "error": None,
    "batch_total": 0,
    "batch_current": 0
}

def update_active_log(path):
    global automation_status
    automation_status["log_file"] = path

logger.on_log_file_change = update_active_log

def execute_playwright_background(file_path, username, password):
    global automation_status
    automation_status["is_running"] = True
    automation_status["error"] = None
    
    # Initialize session log file
    log_path = logger.start_file_logging(os.path.basename(file_path))
    automation_status["log_file"] = log_path
    
    if os.path.exists(TERMINATION_LOCK_FILE):
        os.remove(TERMINATION_LOCK_FILE)

    try:
        # Calls our previously built automation script
        run_automation(file_path, username, password)
    except Exception as e:
        automation_status["error"] = str(e)
    finally:
        automation_status["is_running"] = False

def execute_fastapp_background(username, password, mode='full_file', download_pref='appr_id'):
    global automation_status
    automation_status["is_running"] = True
    automation_status["error"] = None
    automation_status["batch_total"] = 0
    automation_status["batch_current"] = 0
    
    # Initialize session log file
    log_path = logger.start_file_logging("fastapp_check")
    automation_status["log_file"] = log_path

    if os.path.exists(TERMINATION_LOCK_FILE):
        os.remove(TERMINATION_LOCK_FILE)

    try:
        logger.info("--- Starting FastApp Independent Process ---")
        # Map UI mode to FastApp automation mode
        fa_mode = 'update_review' if mode == 'update_review' else 'full_file'
        run_fastapp_automation(username, password, mode=fa_mode, download_pref=download_pref)
        logger.success("--- FastApp Process Completed ---")
    except Exception as e:
        automation_status["error"] = str(e)
        logger.error(f"FastApp Process Failed: {str(e)}")
    finally:
        automation_status["is_running"] = False

def execute_automation_batch(filenames, username, password, mode='revised'):
    global automation_status
    automation_status["is_running"] = True
    automation_status["batch_total"] = int(len(filenames))
    automation_status["batch_current"] = 0
    automation_status["error"] = None
    
    # Initialize a batch init log
    logger.start_file_logging("batch_init")
    
    if os.path.exists(TERMINATION_LOCK_FILE):
        os.remove(TERMINATION_LOCK_FILE)

    # 0. Initial Summary Logs
    try:
        processed_count = len([f for f in os.listdir(PROCESSED_FILES_PATH) if os.path.isfile(os.path.join(PROCESSED_FILES_PATH, f))])
        logger.info(f"Found {processed_count} processed files in log.")
        search_path = FULL_FILE_PATH if mode == 'full' else NEW_FILES_REVISED_PATH
        logger.info(f"Found {len(filenames)} PDF file(s) to process in '{search_path}': {', '.join(filenames)}")
    except Exception:
        pass

    for filename in filenames:
        current_idx = int(automation_status["batch_current"] or 0)
        automation_status["batch_current"] = current_idx + 1
        filename = secure_filename(filename)
        
        # Decide search path based on mode
        if mode == 'full':
            source_path = os.path.join(FULL_FILE_PATH, filename)
        else:
            source_path = os.path.join(NEW_FILES_REVISED_PATH, filename)
        
        # 1. Skip already processed files
        processed_path = os.path.join(PROCESSED_FILES_PATH, filename)
        if os.path.exists(processed_path):
            logger.info(f"Skipping already processed file: {filename}")
            continue

        if not os.path.exists(source_path):
            logger.warning(f"File not found: {filename}. It might have been moved or deleted.")
            continue

        # 2. Retry Logic (One retry if first attempt fails)
        success = False
        attempts = 2
        for i in range(attempts):
            try:
                attempt_num = i + 1
                if i == 0:
                    # Clean log for each file at start of its workflow
                    logger.start_file_logging(filename)
                
                if i > 0:
                    logger.warning(f"RETRY ATTEMPT {attempt_num} for: {filename}")
                else:
                    logger.info(f"\n--- Starting workflow for: {filename} ---")
                
                if mode == 'full':
                    run_automation(source_path, username, password)
                else:
                    new_pdf = source_path
                    base_name = os.path.splitext(filename)[0]
                    if base_name.lower().endswith("_revised"):
                        base_name = base_name[:-8]
                    
                    old_pdf_candidates = [f"{base_name}.pdf", filename]
                    old_pdf = None
                    for cand in old_pdf_candidates:
                        p = os.path.join(OLD_FILES_REVISED_PATH, cand)
                        if os.path.exists(p):
                            old_pdf = p
                            break
                    
                    html_candidates = [f"{base_name}.html", os.path.splitext(filename)[0] + ".html"]
                    html_path = None
                    for cand in html_candidates:
                        p = os.path.join(HTML_FILES_PATH, cand)
                        if os.path.exists(p):
                            html_path = p
                            break
                    
                    run_revised_automation(new_pdf, old_pdf, html_path, username, password)
                success = True
                logger.success(f"Successfully processed: {filename}")
                break

            except Exception as e:
                logger.error(f"Attempt {i+1} failed for {filename}: {str(e)}")
                if i < attempts - 1:
                    logger.info("Conditioning for retry (5.0s cool-down)...")
                    time.sleep(5)
                else:
                    automation_status["error"] = f"CRITICAL: Final failure for {filename} after {attempts} attempts."

        # 3. Move file based on result
        try:
            if success:
                shutil.move(source_path, processed_path)
                logger.info(f"\n--- Finished workflow for: {filename} ---")
                logger.info(f"Moved processed file to: {processed_path}")
            else:
                error_path = os.path.join(ERROR_FILES_PATH, filename)
                shutil.move(source_path, error_path)
                logger.warning(f"--- FAILED workflow for: {filename} ---")
                logger.warning(f"Moved failed file to: {error_path}")
        except Exception as move_err:
            logger.error(f"Failed to move file {filename}: {str(move_err)}")

    logger.info("\n✅ Batch processing cycle completed. Checking for new files...")
    automation_status["is_running"] = False
    automation_status["batch_total"] = 0
    automation_status["batch_current"] = 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    global automation_status
    if automation_status["is_running"]:
        return jsonify({"error": "An automation process is already running."}), 400
        
    if 'pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        username = request.form.get('username')
        password = request.form.get('password')

        # Start background automation thread
        # Storing only - NO automatic start
        # thread = threading.Thread(target=execute_playwright_background, args=(file_path, username, password))
        # thread.start()

        return jsonify({"message": f"File {filename} uploaded and stored. Ready for manual review launch."})
        
    return jsonify({"error": "Invalid file format. Please upload a PDF."}), 400

@app.route('/api/upload_revised', methods=['POST'])
def upload_revised_files():
    global automation_status
    if automation_status["is_running"]:
        return jsonify({"error": "An automation process is already running."}), 400

    if 'new_pdf' not in request.files:
        return jsonify({"error": "Missing new_pdf file."}), 400

    new_pdf = request.files['new_pdf']
    old_pdf = request.files.get('old_pdf')
    html_file = request.files.get('html_file')

    if new_pdf.filename == '':
        return jsonify({"error": "No selected file in new_pdf field."}), 400

    if new_pdf:
        new_pdf_name = secure_filename(new_pdf.filename)
        new_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], new_pdf_name)
        new_pdf.save(new_pdf_path)

        old_pdf_path = None
        if old_pdf and old_pdf.filename != '':
            old_pdf_name = secure_filename(old_pdf.filename)
            old_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], old_pdf_name)
            old_pdf.save(old_pdf_path)
        
        html_path = None
        if html_file and html_file.filename != '':
            html_name = secure_filename(html_file.filename)
            html_path = os.path.join(app.config['UPLOAD_FOLDER'], html_name)
            html_file.save(html_path)

        username = request.form.get('username')
        password = request.form.get('password')

        # Storing only - NO automatic start
        # thread = threading.Thread(target=execute_automation_batch, args=([new_pdf_name], username, password, mode))
        # thread.start()

        return jsonify({"message": f"Successfully stored {new_pdf_name}. Automation must be launched manually from the dashboard."})

    return jsonify({"error": "Invalid file format."}), 400

@app.route('/api/start_stored_revised', methods=['POST'])
def start_stored_revised_automation():
    global automation_status
    if automation_status["is_running"]:
        return jsonify({"error": "An automation process is already running."}), 400

    data = request.get_json()
    filename = data.get('filename')
    username = data.get('username')
    password = data.get('password')
    mode = data.get('mode', 'revised')

    if not filename:
        return jsonify({"error": "No filename selected."}), 400

    # The background function will handle searching for matching old files
    thread = threading.Thread(target=execute_automation_batch, args=([filename], username, password, mode))
    thread.start()

    return jsonify({"message": f"Automation started for stored file: {filename}. Missing files will be automatically matched if in Revised mode."})

@app.route('/api/start_batch_stored_revised', methods=['POST'])
def start_batch_stored_revised_automation():
    global automation_status
    if automation_status["is_running"]:
        return jsonify({"error": "An automation process is already running."}), 400

    data = request.get_json()
    filenames = data.get('filenames', [])
    username = data.get('username')
    password = data.get('password')
    mode = data.get('mode', 'revised')

    if not filenames:
        return jsonify({"error": "No filenames selected."}), 400

    thread = threading.Thread(target=execute_automation_batch, args=(filenames, username, password, mode))
    thread.start()

    return jsonify({"message": f"Batch automation started for {len(filenames)} files in {mode} mode."})

@app.route('/api/start_fastapp', methods=['POST'])
def start_fastapp_automation():
    global automation_status
    if automation_status["is_running"]:
        return jsonify({"error": "An automation process is already running."}), 400

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    mode = data.get('mode', 'full_file')
    download_pref = data.get('downloadPref', 'appr_id')

    thread = threading.Thread(target=execute_fastapp_background, args=(username, password, mode, download_pref))
    thread.start()

    return jsonify({"message": "FastApp Independent automation sequence started."})

@app.route('/api/status', methods=['GET'])
def get_status():
    global automation_status
    return jsonify(automation_status)

@app.route('/api/files/new_revised', methods=['GET'])
def list_new_revised_files():
    files = []
    if os.path.exists(NEW_FILES_REVISED_PATH):
        for f in os.listdir(NEW_FILES_REVISED_PATH):
            if os.path.isfile(os.path.join(NEW_FILES_REVISED_PATH, f)):
                files.append(f)
    return jsonify(files)

@app.route('/api/files/new_revised/<filename>', methods=['DELETE'])
def delete_new_revised_file(filename):
    filename = secure_filename(filename)
    file_path = os.path.join(NEW_FILES_REVISED_PATH, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"File {filename} deleted."})
    return jsonify({"error": "File not found."}), 404

@app.route('/api/files/new_revised/download/<filename>', methods=['GET'])
def download_new_revised_file(filename):
    filename = secure_filename(filename)
    return send_from_directory(NEW_FILES_REVISED_PATH, filename, as_attachment=True)

@app.route('/api/files/old_revised', methods=['GET'])
def list_old_revised_files():
    files = []
    if os.path.exists(OLD_FILES_REVISED_PATH):
        for f in os.listdir(OLD_FILES_REVISED_PATH):
            if os.path.isfile(os.path.join(OLD_FILES_REVISED_PATH, f)):
                files.append(f)
    return jsonify(files)

@app.route('/api/files/html_ref', methods=['GET'])
def list_html_files():
    files = []
    if os.path.exists(HTML_FILES_PATH):
        for f in os.listdir(HTML_FILES_PATH):
            if os.path.isfile(os.path.join(HTML_FILES_PATH, f)):
                files.append(f)
    return jsonify(files)

@app.route('/api/files/old_revised/download/<filename>', methods=['GET'])
def download_old_revised_file(filename):
    filename = secure_filename(filename)
    return send_from_directory(OLD_FILES_REVISED_PATH, filename, as_attachment=True)

@app.route('/api/files/html_ref/download/<filename>', methods=['GET'])
def download_html_file(filename):
    filename = secure_filename(filename)
    return send_from_directory(HTML_FILES_PATH, filename, as_attachment=True)

if __name__ == '__main__':
    # Running locally on port 5000. 
    # use_reloader=False is critical to prevent crashes when saving uploaded files.
    if not IS_PRODUCTION:
        app.run(debug=True, port=5000, use_reloader=False)
