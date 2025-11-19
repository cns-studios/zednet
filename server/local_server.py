"""
Production-hardened local web server.
"""
from flask import Flask, send_file, abort, render_template, request, flash, redirect, url_for
from pathlib import Path
import requests
from core.security import SecurityManager
from core.audit_log import AuditLogger
from core.storage import SiteStorage
import logging
from functools import wraps
import time
import json

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['DEBUG'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max request
app.config['SECRET_KEY'] = 'a_secure_random_secret_key_for_flashing' # In a real app, use a proper secret

# Global instances (injected at startup)
audit_logger: AuditLogger = None
content_dir: Path = None
storage: SiteStorage = None
app_controller = None # Injected AppController instance

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
        my_sites=app_controller.get_my_sites()
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

        # Run the submission in the background
        async def do_submit():
            success = await app_controller.submit_site_for_registration(
                site_name, site_id, description
            )
            if success:
                flash('Your site has been submitted for review!', 'success')
            else:
                flash('There was an error submitting your site. Please try again.', 'danger')

        # This is a simple way to run an async task from a sync Flask route
        # In a more complex app, a task queue like Celery would be better.
        app_controller.loop.call_soon_threadsafe(asyncio.create_task, do_submit())

        # Redirect immediately, feedback will be on the next page load
        flash("Your submission is being processed...", "info")
        return redirect(url_for('add_site'))

    return render_template('add_site.html')


@app.route('/forum', methods=['GET'])
@rate_limit
def forum():
    """Display the forum page."""
    if not app_controller or not app_controller.forum_manager:
        abort(503, "Forum not initialized")

    forum_data = app_controller.forum_manager.get_all_posts()
    return render_template('forum.html', forum_data=forum_data)


@app.route('/forum/new', methods=['POST'])
@rate_limit
def new_forum_post():
    """Handle new post submission."""
    if not app_controller or not app_controller.forum_manager:
        abort(503, "Forum not initialized")

    author = request.form.get('author', 'Anonymous')
    content = request.form.get('content')

    if not content:
        flash("Content is required for a post.", "danger")
    else:
        app_controller.forum_manager.add_post(author, content)
        flash("Your post has been added!", "success")

    return redirect(url_for('forum'))


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


def run_server(host='127.0.0.1', port=9999):
    """Run the server."""
    app.run(host=host, port=port, threaded=True, debug=False)