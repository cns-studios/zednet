"""
Main application controller - coordinates all components.
"""
import asyncio
from pathlib import Path
import logging
from typing import Dict, List, Optional
import aiotorrent

from .security import SecurityManager
from .storage import SiteStorage
from .publisher import SitePublisher
from .downloader import SiteDownloader
from .vpn_check import VPNChecker

logger = logging.getLogger(__name__)

class AppController:
    """
    Main application controller.
    Coordinates all ZedNet components.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.storage = SiteStorage(data_dir)
        self.publisher: Optional[SitePublisher] = None
        self.downloader: Optional[SiteDownloader] = None
        self._online = False

    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if successful
        """
        logger.info("Initializing application controller...")
        
        try:
            self.publisher = SitePublisher(self.storage)
            self.downloader = SiteDownloader(self.storage)
            self._online = True
            logger.info("Application controller initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize application controller: {e}")
            return False

    def shutdown(self):
        """Shutdown all components."""
        logger.info("Shutting down application controller...")
        if self._online:
            # aiotorrent client doesn't have an explicit shutdown,
            # but we can stop all torrents.
            if self.publisher:
                for site_id in list(self.publisher.active_sites.keys()):
                    self.publisher.stop_seeding(site_id)
            if self.downloader:
                for site_id in list(self.downloader.active_downloads.keys()):
                    self.downloader.remove_site(site_id)
            self._online = False
        logger.info("Application controller shutdown complete")

    # Site creation methods
    
    async def create_site(self, site_name: str, content_dir: Path,
                   password: Optional[str] = None) -> Dict:
        """Create a new site."""
        if not self.publisher:
            raise RuntimeError("Publisher not initialized")
        
        return self.publisher.create_site(site_name, content_dir, password)
    
    async def publish_site(self, site_id: str, password: Optional[str] = None) -> bool:
        """Publish or update a site."""
        if not self.publisher:
            raise RuntimeError("Publisher not initialized")
        
        metadata = self.storage.load_site_metadata(site_id)
        if not metadata:
            raise ValueError(f"Site not found: {site_id}")

        content_dir = Path(metadata['content_path'])
        private_key_file = self.storage.keys_dir / f"{site_id}.key"

        return await self.publisher.publish_site(
            site_id, content_dir, private_key_file, password
        )
    
    def stop_seeding_site(self, site_id: str):
        """Stop seeding a site."""
        if self.publisher:
            self.publisher.stop_seeding(site_id)
    
    # Site downloading methods
    
    async def add_site(self, site_id: str, auto_update: bool = True) -> bool:
        """Add a site to download."""
        if not self.downloader:
            raise RuntimeError("Downloader not initialized")
        
        return await self.downloader.add_site(site_id, auto_update)
    
    def remove_site(self, site_id: str, delete_files: bool = False):
        """Remove a downloaded site."""
        if self.downloader:
            self.downloader.remove_site(site_id, delete_files)

    def delete_my_site(self, site_id: str, delete_key: bool = False):
        """
        Delete one of my sites.
        This stops seeding and deletes all associated data.
        """
        logger.info(f"Deleting my site: {site_id}")
        # Stop seeding if active
        if self.publisher and site_id in self.publisher.active_sites:
            self.publisher.stop_seeding(site_id)

        # Delete from storage
        try:
            self.storage.delete_site(site_id, delete_key)
            logger.info(f"Successfully deleted site data for: {site_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete site {site_id}: {e}", exc_info=True)
            return False
    
    # Status methods
    
    def get_vpn_status(self) -> Dict:
        """Get current VPN status."""
        return VPNChecker.check_vpn_status()
    
    def is_p2p_online(self) -> bool:
        """Check if P2P engine is online."""
        return self._online
    
    def get_my_sites(self) -> List[Dict]:
        """Get list of my published sites."""
        return self.storage.list_sites()
    
    def get_downloads(self) -> List[Dict]:
        """Get list of downloading sites."""
        if not self.downloader:
            return []
        
        downloads = []
        for site_id in list(self.downloader.active_downloads.keys()):
            status = self.downloader.get_site_status(site_id)
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
            status = self.downloader.get_site_status(site_id)
            if status:
                return status
        
        metadata = self.storage.load_site_metadata(site_id)
        if metadata and 'status' in metadata:
            return {"state": metadata['status']}

        return None