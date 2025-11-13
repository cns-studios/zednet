"""
Sandboxed local web server with strict path validation.
"""
from flask import Flask, send_file, abort, render_template_string
from pathlib import Path
from core.security import SecurityManager
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Disable Flask debug mode in production
app.config['DEBUG'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True

# Simple dashboard HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ZedNet Local Node</title>
    <style>
        body { font-family: monospace; max-width: 800px; margin: 50px auto; }
        .warning { color: red; font-weight: bold; }
        .safe { color: green; }
    </style>
</head>
<body>
    <h1>ZedNet Local Node</h1>
    <p class="{{ status_class }}">VPN Status: {{ vpn_status }}</p>
    <p>Access sites at: <code>http://127.0.0.1:9999/site/&lt;SITE_ID&gt;/index.html</code></p>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Serve local dashboard."""
    # TODO: Integrate actual VPN status
    return render_template_string(
        DASHBOARD_HTML,
        vpn_status="UNKNOWN (Check GUI)",
        status_class="warning"
    )

@app.route('/site/<site_id>/<path:filepath>')
def serve_site(site_id: str, filepath: str):
    """
    Serve file from ZedNet site with strict security.
    
    Args:
        site_id: ZedNet site identifier
        filepath: Requested file path
    """
    # Validate site ID format
    if not SecurityManager.validate_site_id(site_id):
        logger.warning("Invalid site ID format: %s", site_id)
        abort(400, "Invalid site ID format")
    
    # Construct base directory for this site
    from config import CONTENT_DIR
    site_dir = CONTENT_DIR / site_id
    
    if not site_dir.exists():
        logger.warning("Site not found: %s", site_id)
        abort(404, "Site not downloaded")
    
    # CRITICAL: Sanitize and validate path
    safe_path = SecurityManager.sanitize_path(filepath, site_dir)
    
    if safe_path is None:
        logger.warning("Path traversal attempt: %s -> %s", site_id, filepath)
        abort(403, "Invalid file path")
    
    if not safe_path.exists():
        logger.warning("File not found: %s", safe_path)
        abort(404, "File not found")
    
    if not safe_path.is_file():
        logger.warning("Not a file: %s", safe_path)
        abort(403, "Not a file")
    
    # Serve file
    try:
        return send_file(safe_path)
    except Exception as e:
        logger.error("Error serving file %s: %s", safe_path, e)
        abort(500, "Error serving file")

def run_server(host='127.0.0.1', port=9999):
    """Run the local server."""
    app.run(host=host, port=port, threaded=True)