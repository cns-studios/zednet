"""
Main application controller - coordinates all components.
"""
import libtorrent as lt
from pathlib import Path
import logging
from typing import Dict, List, Optional

from .security import SecurityManager
from .storage import SiteStorage
from .publisher import SitePublisher
from .downloader import SiteDownloader
from .vpn_check import VPNChecker
from .p2p_engine import P2PEngine

logger = logging.getLogger(__name__)

class AppController:
    """
    Main application controller.
    Coordinates all ZedNet components.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        
        # Initialize components
        self.storage = SiteStorage(data_dir)
        self.p2p_engine = P2PEngine(data_dir / 'sites')
        self.session: Optional[lt.session] = None
        
        # Will be initialized after P2P engine starts
        self.publisher: Optional[SitePublisher] = None
        self.downloader: Optional[SiteDownloader] = None
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if successful
        """
        logger.info("Initializing application controller...")
        
        # Initialize P2P engine
        if not self.p2p_engine.initialize(force_encryption=True):
            logger.error("Failed to initialize P2P engine")
            return False
        
        self.session = self.p2p_engine.session
        
        # Initialize publisher and downloader
        self.publisher = SitePublisher(self.session, self.storage)
        self.downloader = SiteDownloader(self.session, self.storage)
        
        logger.info("Application controller initialized successfully")
        return True
    
    def shutdown(self):
        """Shutdown all components."""
        logger.info("Shutting down application controller...")
        
        if self.p2p_engine:
            self.p2p_engine.shutdown()
        
        logger.info("Application controller shutdown complete")
    
    # Site creation methods
    
    def create_site(self, site_name: str, content_dir: Path,
                   password: Optional[str] = None) -> Dict:
        """Create a new site."""
        if not self.publisher:
            raise RuntimeError("Publisher not initialized")
        
        return self.publisher.create_site(site_name, content_dir, password)
    
    def publish_site(self, site_id: str, content_dir: Path,
                    private_key_file: Path, password: Optional[str] = None) -> bool:
        """Publish or update a site."""
        if not self.publisher:
            raise RuntimeError("Publisher not initialized")
        
        return self.publisher.publish_site(
            site_id, content_dir, private_key_file, password
        )
    
    def stop_seeding_site(self, site_id: str):
        """Stop seeding a site."""
        if self.publisher:
            self.publisher.stop_seeding(site_id)
    
    # Site downloading methods
    
    def add_site(self, site_id: str, auto_update: bool = True) -> bool:
        """Add a site to download."""
        if not self.downloader:
            raise RuntimeError("Downloader not initialized")
        
        return self.downloader.add_site(site_id, auto_update)
    
    def remove_site(self, site_id: str, delete_files: bool = False):
        """Remove a site."""
        if self.downloader:
            self.downloader.remove_site(site_id, delete_files)
    
    # Status methods
    
    def get_vpn_status(self) -> Dict:
        """Get current VPN status."""
        return VPNChecker.check_vpn_status()
    
    def is_p2p_online(self) -> bool:
        """Check if P2P engine is online."""
        return self.p2p_engine.is_online if self.p2p_engine else False
    
    def get_my_sites(self) -> List[Dict]:
        """Get list of my published sites."""
        sites = self.storage.list_sites()
        return [s for s in sites if 'public_key' in s]
    
    def get_downloads(self) -> List[Dict]:
        """Get list of downloading sites."""
        if not self.downloader:
            return []
        
        downloads = []
        for site_id in list(self.downloader.active_downloads.keys()):
            status = self.downloader.get_download_status(site_id)
            if status:
                status['site_id'] = site_id
                downloads.append(status)
        
        return downloads
    
    def get_site_status(self, site_id: str) -> Optional[Dict]:
        """Get status for a specific site."""
        if self.publisher:
            status = self.publisher.get_site_status(site_id)
            if status:
                return status
        
        if self.downloader:
            status = self.downloader.get_download_status(site_id)
            if status:
                return status
        
        return None