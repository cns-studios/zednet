"""
P2P engine with mandatory encryption.
"""
import libtorrent as lt
from pathlib import Path
from typing import Optional, Callable
from .security import SecurityManager
import logging

logger = logging.getLogger(__name__)

class P2PEngine:
    """Manages libtorrent session with security requirements."""
    
    def __init__(self, download_path: Path):
        self.download_path = download_path
        self.session: Optional[lt.session] = None
        self.is_online = False
        
    def initialize(self, force_encryption: bool = True) -> bool:
        """
        Initialize libtorrent session with security settings.
        
        Args:
            force_encryption: Require encrypted connections
            
        Returns:
            True if successful
        """
        try:
            settings = {
                'enable_dht': True,
                'enable_lsd': False,  # Disable local peer discovery
                'enable_upnp': False,  # Don't auto-open ports
                'enable_natpmp': False,
                'anonymous_mode': True,  # Don't send client fingerprint
            }
            
            if force_encryption:
                settings.update({
                    'out_enc_policy': lt.enc_policy.forced,
                    'in_enc_policy': lt.enc_policy.forced,
                    'allowed_enc_level': lt.enc_level.both,
                })
            
            self.session = lt.session(settings)
            
            # Add DHT bootstrap nodes
            from config import DHT_BOOTSTRAP_NODES
            for node, port in DHT_BOOTSTRAP_NODES:
                self.session.add_dht_router(node, port)
            
            self.is_online = True
            logger.info("P2P engine initialized with encryption: %s", force_encryption)
            return True
            
        except Exception as e:
            logger.error("Failed to initialize P2P engine: %s", e)
            return False
    
    def shutdown(self):
        """Safely shutdown session."""
        if self.session:
            self.session.pause()
            self.session = None
            self.is_online = False