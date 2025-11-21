"""
Security-hardened configuration with legal compliance.
"""
from pathlib import Path
import os

# Version
VERSION = "0.1.0-alpha"
BUILD_DATE = "2025"

# Base directories
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / 'data'
CONTENT_DIR = DATA_DIR / 'sites'
KEYS_DIR = DATA_DIR / 'keys'
LOGS_DIR = DATA_DIR / 'logs'
QUARANTINE_DIR = DATA_DIR / 'quarantine'

# Create directories with secure permissions
for d in [DATA_DIR, CONTENT_DIR, KEYS_DIR, LOGS_DIR, QUARANTINE_DIR]:
    d.mkdir(exist_ok=True, mode=0o700)

# Server settings
LOCAL_HOST = '127.0.0.1'
LOCAL_PORT = 9999

# Security settings
REQUIRE_VPN_CHECK = True       # Check VPN before starting
VPN_CHECK_INTERVAL = 30        # Seconds between VPN checks
ENABLE_KILL_SWITCH = True      # Emergency shutdown on VPN loss
FORCE_ENCRYPTION = True        # Require encrypted P2P (MANDATORY)
ENABLE_AUDIT_LOG = True        # Cannot be disabled

# Content security
ENABLE_CONTENT_SCANNING = True
MAX_FILE_SIZE_MB = 100         # Per file limit
MAX_SITE_SIZE_MB = 500         # Per site limit
MAX_SITES = 100                # Maximum tracked sites
BLOCKED_EXTENSIONS = {
    '.exe', '.dll', '.so', '.dylib', '.app',  # Executables
    '.bat', '.cmd', '.sh', '.ps1',            # Scripts
    '.zip', '.rar', '.7z', '.tar', '.gz',     # Archives (optional)
}

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 100
MAX_BANDWIDTH_MBPS = 10

# libtorrent settings
DHT_BOOTSTRAP_NODES = [
    ('router.bittorrent.com', 6881),
    ('dht.transmissionbt.com', 6881),
    ('router.utorrent.com', 6881),
]

# Tor integration (optional future feature)
ENABLE_TOR = os.environ.get('ZEDNET_TOR', 'false').lower() == 'true'
TOR_PROXY = '127.0.0.1:9050'

# Legal
TERMS_ACCEPTED = DATA_DIR / '.terms_accepted'
LEGAL_JURISDICTION = "UNKNOWN"  # User must set