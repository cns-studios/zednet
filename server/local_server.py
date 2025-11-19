"""
Production-hardened local web server.
"""
from flask import Flask, send_file, abort, render_template, request
from pathlib import Path
from core.security import SecurityManager
from core.audit_log import AuditLogger
from core.storage import SiteStorage
import logging
import json
from functools import wraps
import time
import asyncio
import requests

logger = logging.getLogger(__name__)

app = None

# Global instances (injected at startup)
audit_logger: AuditLogger = None
content_dir: Path = None
storage: SiteStorage = None
directory_info_hash: str = None
app_controller = None

# Rate limiting
request_times = {}
RATE_LIMIT = 100  # requests per minute

def create_app():
    global app
    app = Flask(__name__)
    app.config['DEBUG'] = False
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max request

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
        """Serve dashboard."""
        from config import VERSION, LOCAL_PORT
        
        # TODO: Get actual VPN status
        return render_template(
            "index.html",
            version=VERSION,
            port=LOCAL_PORT,
            vpn_status="CHECK GUI",
            status_class="warning"
        )


    @app.route('/directory_info_hash')
    @rate_limit
    def get_directory_info_hash():
        """Returns the info-hash of the latest site directory torrent."""
        if directory_info_hash:
            return directory_info_hash
        else:
            # 503 Service Unavailable
            abort(503, "Directory info-hash is not yet available.")


    @app.route('/register', methods=['GET', 'POST'])
    @rate_limit
    def register_site():
        """Handle site registration."""
        if request.method == 'POST':
            site_name = request.form.get('site_name')
            info_hash = request.form.get('info_hash')

            if not site_name or not info_hash:
                abort(400, "Site name and info-hash are required.")

            # For now, just log the submission
            logger.info(f"New site submission: {site_name} ({info_hash})")

            # Store the submission
            submission = {'site_name': site_name, 'info_hash': info_hash, 'status': 'pending'}
            submissions_file = Path(storage.data_dir) / 'submissions.json'
            try:
                with open(submissions_file, 'r+') as f:
                    submissions = json.load(f)
                    submissions.append(submission)
                    f.seek(0)
                    json.dump(submissions, f, indent=4)
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Error saving submission: {e}")
                abort(500, "Could not save submission.")

            return "Site submitted for review."
        
        return render_template("register.html")


    @app.route('/admin')
    @rate_limit
    def admin_panel():
        """Display the admin panel."""
        submissions_file = Path(storage.data_dir) / 'submissions.json'
        try:
            with open(submissions_file, 'r') as f:
                submissions = json.load(f)
        except (IOError, json.JSONDecodeError):
            submissions = []
        
        pending_submissions = [s for s in submissions if s.get('status') == 'pending']
        
        return render_template("admin.html", submissions=pending_submissions)


    @app.route('/admin/approve', methods=['POST'])
    @rate_limit
    def approve_submission():
        """Approve a site submission."""
        info_hash = request.form.get('info_hash')
        if not info_hash:
            abort(400, "Info-hash is required.")

        logger.info(f"Approving submission: {info_hash}")

        # Update submissions file
        submissions_file = Path(storage.data_dir) / 'submissions.json'
        try:
            with open(submissions_file, 'r+') as f:
                submissions = json.load(f)
                for sub in submissions:
                    if sub.get('info_hash') == info_hash:
                        sub['status'] = 'approved'
                        break
                f.seek(0)
                json.dump(submissions, f, indent=4)
        except (IOError, json.JSONDecodeError):
            abort(500, "Could not update submissions.")

        # Add to sites.json
        sites_file = Path(storage.data_dir) / 'sites.json'
        try:
            with open(sites_file, 'r+') as f:
                sites = json.load(f)
                # Find the submission to get the site name
                site_name = "Unknown"
                with open(submissions_file, 'r') as sf:
                    submissions = json.load(sf)
                    for sub in submissions:
                        if sub.get('info_hash') == info_hash:
                            site_name = sub.get('site_name')
                            break

                sites.append({'site_name': site_name, 'info_hash': info_hash})
                f.seek(0)
                json.dump(sites, f, indent=4)
        except (IOError, json.JSONDecodeError):
            abort(500, "Could not add site to directory.")

        # Republish the directory
        if app_controller and app_controller.publisher:
            new_info_hash = app_controller.run_async_and_wait(app_controller.publisher.publish_directory())
            if new_info_hash:
                app_controller.directory_info_hash = new_info_hash
                global directory_info_hash
                directory_info_hash = new_info_hash
                logger.info(f"Directory updated. New info-hash: {new_info_hash}")

        return "Site approved."


    @app.route('/admin/reject', methods=['POST'])
    @rate_limit
    def reject_submission():
        """Reject a site submission."""
        info_hash = request.form.get('info_hash')
        if not info_hash:
            abort(400, "Info-hash is required.")

        logger.info(f"Rejecting submission: {info_hash}")

        # Update submissions file
        submissions_file = Path(storage.data_dir) / 'submissions.json'
        try:
            with open(submissions_file, 'r+') as f:
                submissions = json.load(f)
                for sub in submissions:
                    if sub.get('info_hash') == info_hash:
                        sub['status'] = 'rejected'
                        break
                f.seek(0)
                json.dump(submissions, f, indent=4)
        except (IOError, json.JSONDecodeError):
            abort(500, "Could not update submissions.")

        return "Site rejected."


    @app.route('/search')
    @app.route('/pages')
    @rate_limit
    def view_directory():
        """Fetch and display the site directory."""
        if not directory_info_hash:
            abort(503, "Directory info-hash is not yet available.")
        
        dir_info_hash = directory_info_hash

        if not app_controller or not app_controller.downloader:
            abort(503, "Downloader not available.")

        # Download the directory torrent
        try:
            dir_content = app_controller.run_async_and_wait(app_controller.downloader.download_directory(dir_info_hash))
            if not dir_content:
                abort(404, "Directory content not found.")

            sites = json.loads(dir_content)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Could not parse directory content: {e}")
            abort(500, "Could not parse directory content.")
        except Exception as e:
            logger.error(f"Error downloading directory: {e}")
            abort(500, "Error downloading directory.")

        return render_template("directory.html", sites=sites)


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

    return app


def initialize_server(audit_log: AuditLogger, content_directory: Path, controller):
    """Initialize server with dependencies."""
    global audit_logger, content_dir, storage, directory_info_hash, app_controller
    audit_logger = audit_log
    content_dir = content_directory
    storage = controller.storage
    directory_info_hash = controller.directory_info_hash
    app_controller = controller


def run_server(host='127.0.0.1', port=9999):
    """Run the server."""
    global app
    if not app:
        app = create_app()
    app.run(host=host, port=port, threaded=True, debug=False)
