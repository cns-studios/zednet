"""
Production-hardened local web server.
"""
from flask import Flask, send_file, abort, render_template, request, flash, redirect, url_for
from pathlib import Path
import requests
from dotenv import load_dotenv
import os
import threading
from core.security import SecurityManager
from core.audit_log import AuditLogger
from core.storage import SiteStorage
import logging
from functools import wraps
import time
import json

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
SITES_JSON_URL = os.getenv("SITES_JSON_URL")
SUBMIT_SITE_URL = os.getenv("SUBMIT_SITE_URL")


app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['DEBUG'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max request
app.config['SECRET_KEY'] = 'a_secure_random_secret_key_for_flashing' # In a real app, use a proper secret

# Global instances (injected at startup)
audit_logger: AuditLogger = None
content_dir: Path = None
storage: SiteStorage = None
app_controller = None # Injected AppController instance
last_sites_json_update_status = "Not yet run."

def fetch_and_update_sites_json():
    """Fetches the sites.json from the central repository and updates the local copy."""
    global last_sites_json_update_status
    if not SITES_JSON_URL:
        last_sites_json_update_status = "Error: SITES_JSON_URL is not set in .env file."
        logger.error(last_sites_json_update_status)
        return

    try:
        logger.info("Fetching public sites list from %s", SITES_JSON_URL)
        response = requests.get(SITES_JSON_URL, timeout=15)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes

        sites_data = response.json()
        sites_file = storage.data_dir / "sites.json"
        with open(sites_file, 'w', encoding='utf-8') as f:
            json.dump(sites_data, f, indent=2)

        last_sites_json_update_status = f"Successfully updated at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        logger.info("Successfully updated sites.json")

    except requests.exceptions.RequestException as e:
        last_sites_json_update_status = f"Error: Failed to fetch from API. Using local copy. Details: {e}"
        logger.error(last_sites_json_update_status)
    except json.JSONDecodeError as e:
        last_sites_json_update_status = f"Error: Failed to parse JSON from API. Using local copy. Details: {e}"
        logger.error(last_sites_json_update_status)
    except IOError as e:
        last_sites_json_update_status = f"Error: Failed to write to local sites.json. Details: {e}"
        logger.error(last_sites_json_update_status)


def periodic_sites_json_updater():
    """Runs the updater function in a loop every 5 minutes."""
    while True:
        fetch_and_update_sites_json()
        time.sleep(300) # 300 seconds = 5 minutes

# Rate limiting
request_times = {}
RATE_LIMIT = 100  # requests per minute

def rate_limit(f):
    """Rate limiting decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Clean old entries
        if client_ip in request_times:
            request_times[client_ip] = [
                t for t in request_times[client_ip] 
                if current_time - t < 60
            ]
        else:
            request_times[client_ip] = []
        
        # Check limit
        if len(request_times[client_ip]) >= RATE_LIMIT:
            if audit_logger:
                audit_logger.log_security_violation('RATE_LIMIT', {
                    'ip': client_ip,
                    'endpoint': request.endpoint
                })
            abort(429, "Rate limit exceeded")
        
        request_times[client_ip].append(current_time)
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/')
@rate_limit
def dashboard():
    """Serve the main dashboard."""
    if not app_controller:
        abort(503, "Controller not initialized")

    return render_template(
        "dashboard.html",
        p2p_status=app_controller.is_p2p_online(),
        vpn_status=app_controller.get_vpn_status(),
        my_sites_count=len(app_controller.get_my_sites()),
        downloaded_sites_count=len(app_controller.get_downloads()),
        my_sites=app_controller.get_my_sites(),
        sites_json_status=last_sites_json_update_status
    )

def _get_public_sites():
    """Helper to load and return the public sites list."""
    # In a future step, this will fetch from a URL. For now, read from disk.
    sites_file = storage.data_dir / "sites.json"
    if not sites_file.exists():
        return []
    try:
        with open(sites_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read or parse sites.json: {e}")
        return []

@app.route('/sites')
@rate_limit
def list_sites():
    """Serve a list of all public sites."""
    sites = _get_public_sites()
    return render_template("sites.html", sites=sites)


@app.route('/search')
@rate_limit
def search_sites():
    """Serve the search page and handle search queries."""
    query = request.args.get('q', '').strip().lower()
    sites = _get_public_sites()

    if query:
        results = [
            site for site in sites
            if query in site.get('name', '').lower()
        ]
    else:
        results = [] # Don't show results on initial page load

    return render_template("search.html", sites=results, query=query)


@app.route('/add-site', methods=['GET', 'POST'])
@rate_limit
def add_site():
    """Handle site submission form."""
    if request.method == 'POST':
        if not app_controller:
            abort(503, "Controller not initialized")

        site_name = request.form.get('site_name')
        site_id = request.form.get('site_id')
        description = request.form.get('description')

        if not all([site_name, site_id, description]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_site'))

        # New: Submit to the central API
        if not SUBMIT_SITE_URL:
            flash('Error: SUBMIT_SITE_URL is not configured in the .env file.', 'danger')
            return redirect(url_for('add_site'))

        try:
            payload = {
                "name": site_name,
                "site_id": site_id,
                "description": description
            }
            response = requests.post(SUBMIT_SITE_URL, json=payload, timeout=15)
            response.raise_for_status() # Check for HTTP errors

            if response.status_code == 201:
                flash('Your site has been submitted to the public index!', 'success')
            else:
                flash(f"Received an unexpected status from the API: {response.status_code}", 'warning')

        except requests.exceptions.RequestException as e:
            flash(f"There was an error submitting your site: {e}", 'danger')

        return redirect(url_for('add_site'))

    return render_template('add_site.html')


@app.route('/site/<site_id>/<path:filepath>')
@rate_limit
def serve_site(site_id: str, filepath: str):
    """
    Serve file from ZedNet site with maximum security.
    """
    client_ip = request.remote_addr
    
    # Validate site ID
    if not SecurityManager.validate_site_id(site_id):
        if audit_logger:
            audit_logger.log_security_violation('INVALID_SITE_ID', {
                'site_id': site_id,
                'client_ip': client_ip
            })
        abort(400, "Invalid site ID format")

    # Determine base directory
    metadata = storage.load_site_metadata(site_id)
    if metadata and 'content_path' in metadata:
        # It's one of our own sites, serve from original path
        site_dir = Path(metadata['content_path'])
    else:
        # It's a downloaded site
        site_dir = content_dir / site_id
    
    if not site_dir.exists():
        if audit_logger:
            audit_logger.log_file_access(site_id, filepath, False, client_ip)
        abort(404, "Site not found - not downloaded or path is invalid")
    
    # CRITICAL: Sanitize path
    safe_path = SecurityManager.sanitize_path(filepath, site_dir)
    
    if safe_path is None:
        if audit_logger:
            audit_logger.log_security_violation('PATH_TRAVERSAL_ATTEMPT', {
                'site_id': site_id,
                'filepath': filepath,
                'client_ip': client_ip
            })
        logger.warning("Path traversal blocked: %s/%s from %s", site_id, filepath, client_ip)
        abort(403, "Invalid file path")
    
    # Check file exists
    if not safe_path.exists():
        if audit_logger:
            audit_logger.log_file_access(site_id, filepath, False, client_ip)
        abort(404, "File not found")
    
    if not safe_path.is_file():
        if audit_logger:
            audit_logger.log_security_violation('DIRECTORY_ACCESS_ATTEMPT', {
                'site_id': site_id,
                'filepath': filepath,
                'client_ip': client_ip
            })
        abort(403, "Not a file")
    
    # Log successful access
    if audit_logger:
        audit_logger.log_file_access(site_id, filepath, True, client_ip)
    
    # Serve file
    try:
        return send_file(safe_path)
    except Exception as e:
        logger.error("Error serving %s: %s", safe_path, e)
        abort(500, "Error serving file")


@app.errorhandler(429)
def rate_limit_handler(e):
    """Handle rate limiting."""
    return "Rate limit exceeded. Please slow down.", 429


@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal errors without leaking info."""
    logger.error("Internal server error: %s", e)
    return "Internal server error", 500


def initialize_server(controller, audit_log: AuditLogger, content_directory: Path, site_storage: SiteStorage):
    """Initialize server with dependencies."""
    global app_controller, audit_logger, content_dir, storage
    app_controller = controller
    audit_logger = audit_log
    content_dir = content_directory
    storage = site_storage

    # Start the background thread for updating sites.json
    updater_thread = threading.Thread(target=periodic_sites_json_updater, daemon=True)
    updater_thread.start()


def run_server(host='127.0.0.1', port=9999):
    """Run the server."""
    app.run(host=host, port=port, threaded=True, debug=False)