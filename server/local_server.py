"""
Production-hardened local web server.
"""
from flask import Flask, send_file, abort, render_template_string, request
from pathlib import Path
from core.security import SecurityManager
from core.audit_log import AuditLogger
from core.storage import SiteStorage
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max request

# Global instances (injected at startup)
audit_logger: AuditLogger = None
content_dir: Path = None
storage: SiteStorage = None

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


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZedNet Local Node</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff00;
            padding: 20px;
            line-height: 1.6;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { 
            font-size: 2em; 
            margin-bottom: 20px;
            border-bottom: 2px solid #00ff00;
            padding-bottom: 10px;
        }
        .warning {
            background: #ff0000;
            color: #fff;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            font-weight: bold;
        }
        .safe {
            background: #00ff00;
            color: #000;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            font-weight: bold;
        }
        .info {
            background: #222;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #00ff00;
        }
        code {
            background: #1a1a1a;
            padding: 2px 6px;
            border-radius: 3px;
            color: #00ffff;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #333;
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ ZedNet Local Node v{{ version }}</h1>
        
        <div class="{{ status_class }}">
            🔒 VPN Status: {{ vpn_status }}
        </div>
        
        <div class="info">
            <strong>Local Server:</strong> http://127.0.0.1:{{ port }}<br>
            <strong>Status:</strong> ✓ Online<br>
            <strong>Encryption:</strong> ✓ Enabled (Required)<br>
            <strong>Audit Logging:</strong> ✓ Active
        </div>
        
        <div class="info">
            <h3>⚠️ Security Notice</h3>
            <ul style="margin-left: 20px; margin-top: 10px;">
                <li>Always use a VPN or Tor for anonymity</li>
                <li>This node only serves content locally (127.0.0.1)</li>
                <li>Report illegal content using the GUI</li>
                <li>You are responsible for content you access</li>
            </ul>
        </div>
        
        <div class="info">
            <h3>📡 Access Sites</h3>
            <p>URL Format:</p>
            <code>http://127.0.0.1:{{ port }}/site/&lt;SITE_ID&gt;/index.html</code>
            <p style="margin-top: 10px;">
                <small>Use the GUI application to add sites and browse content.</small>
            </p>
        </div>
        
        <div class="footer">
            ZedNet is experimental software. Use at your own risk.<br>
            Read the Terms of Service and Privacy Policy before use.
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
@rate_limit
def dashboard():
    """Serve dashboard."""
    from config import VERSION, LOCAL_PORT
    
    # TODO: Get actual VPN status
    return render_template_string(
        DASHBOARD_HTML,
        version=VERSION,
        port=LOCAL_PORT,
        vpn_status="CHECK GUI",
        status_class="warning"
    )


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


def initialize_server(audit_log: AuditLogger, content_directory: Path, site_storage: SiteStorage):
    """Initialize server with dependencies."""
    global audit_logger, content_dir, storage
    audit_logger = audit_log
    content_dir = content_directory
    storage = site_storage


def run_server(host='127.0.0.1', port=9999):
    """Run the server."""
    app.run(host=host, port=port, threaded=True, debug=False)