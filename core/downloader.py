"""
Site downloading and synchronization using aiotorrent.
"""
import asyncio
from typing import Optional, Dict, Callable
import logging
from .security import SecurityManager
from .storage import SiteStorage
import aiotorrent
from .torrent import ZedNetTorrent as Torrent
from fastbencode import bdecode

logger = logging.getLogger(__name__)

class SiteDownloader:
    """
    Downloads and monitors ZedNet sites.
    """
    
    def __init__(self, storage: SiteStorage):
        self.storage = storage
        self.active_downloads: Dict[str, Dict] = {}
        self.update_callbacks: Dict[str, Callable] = {}

    async def add_site(self, site_id: str, auto_update: bool = True) -> bool:
        """
        Add a site to track and download.
        """
        try:
            info_hash = await self._lookup_site_in_dht(site_id)
            if info_hash is None:
                return False
            
            await self._start_download(site_id, info_hash, auto_update)
            return True
        except Exception as e:
            logger.error("Failed to add site %s: %s", site_id, e)
            return False

    async def _lookup_site_in_dht(self, site_id: str) -> Optional[bytes]:
        """
        Look up site's current info hash in DHT using BEP 46.
        """
        metadata = self.storage.load_site_metadata(site_id)
        public_key = bytes.fromhex(metadata['public_key'])

        # TODO: Implement BEP 46 lookup
        # This will require a custom DHT client that can handle mutable gets.
        # For now, we'll just return a dummy info_hash.
        logger.info("BEP 46 Lookup for public key: %s", public_key.hex())

        # This is a placeholder. A real implementation would need to
        # query the DHT for the mutable item.
        # dht_server = aiotorrent.DHTServer()
        # await dht_server.start()
        # value = await dht_server.get(public_key)
        # await dht_server.stop()
        # if value:
        #     data = bdecode(value)
        #     return data.get(b'ih')

        return None

    async def _start_download(self, site_id: str, info_hash: bytes, auto_update: bool):
        """
        Start downloading site content.
        """
        save_path = self.storage.get_site_content_dir(site_id)
        save_path.mkdir(parents=True, exist_ok=True)
        
        torrent = Torrent(info_hash=info_hash)
        await torrent.init(dht_enabled=True)
        
        self.active_downloads[site_id] = {
            'torrent': torrent,
            'auto_update': auto_update
        }
        logger.info("Started downloading site: %s", site_id)

        for file in torrent.files:
            await torrent.download(file, save_path=save_path)

    def get_site_status(self, site_id: str) -> Optional[Dict]:
        """Get download progress for a site."""
        if site_id not in self.active_downloads:
            return None
        
        torrent = self.active_downloads[site_id]['torrent']
        return {
            "progress": torrent.progress,
        }

    def remove_site(self, site_id: str, delete_files: bool = False):
        """Remove a site."""
        if site_id in self.active_downloads:
            del self.active_downloads[site_id]
            logger.info("Removed site from downloader: %s", site_id)

        if delete_files:
            self.storage.delete_site(site_id)
