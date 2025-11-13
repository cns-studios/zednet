"""
Security-focused configuration.
"""
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / 'data'
CONTENT_DIR = DATA_DIR / 'sites'
KEYS_DIR = DATA_DIR / 'keys'

# Create directories
for d in [DATA_DIR, CONTENT_DIR, KEYS_DIR]:
    d.mkdir(exist_ok=True, mode=0o700)  # Owner-only permissions

# Server settings
LOCAL_HOST = '127.0.0.1'
LOCAL_PORT = 9999

# Security settings
REQUIRE_VPN_WARNING = True  # Show warning, don't block
FORCE_ENCRYPTION = True     # Require encrypted P2P

# libtorrent settings
DHT_BOOTSTRAP_NODES = [
    ('router.bittorrent.com', 6881),
    ('dht.transmissionbt.com', 6881),
]

# Rate limiting (prevent abuse)
MAX_SITES = 100
MAX_SITE_SIZE_MB = 500