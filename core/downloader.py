"""
Site downloading and synchronization using aiotorrent.
"""
import asyncio
from typing import Optional, Dict, Callable
import logging
from .security import SecurityManager
from .storage import SiteStorage
import aiotorrent
from aiotorrent import Torrent
from fastbencode import bdecode, bencode
import os

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
                logger.warning(f"DHT lookup failed for site {site_id}. Cannot add.")
                return False
            
            await self._start_download(site_id, info_hash, auto_update)
            return True
        except Exception as e:
            logger.error(f"Failed to add site {site_id}: {e}", exc_info=True)
            return False

    async def _lookup_site_in_dht(self, site_id: str) -> Optional[bytes]:
        """
        Look up site's current info hash in DHT using BEP 46. This is a placeholder.
        """
        metadata = self.storage.load_site_metadata(site_id)
        if not metadata or 'public_key' not in metadata:
            logger.error(f"Missing metadata or public key for site {site_id}")
            return None

        public_key = bytes.fromhex(metadata['public_key'])
        logger.info(f"BEP 46 Lookup for public key: {public_key.hex()} (Placeholder)")

        # Placeholder: a real implementation would query the DHT.
        # aiotorrent does not support BEP46 directly.
        return os.urandom(20)

    async def _start_download(self, site_id: str, info_hash: bytes, auto_update: bool):
        """
        Start downloading site content.
        """
        save_path = self.storage.get_site_content_dir(site_id)
        save_path.mkdir(parents=True, exist_ok=True)
        
        dummy_torrent_path = save_path / "metadata.torrent"
        dummy_torrent_data = {
            b'info': {
                b'name': site_id.encode(),
                b'piece length': 2**18,
                b'pieces': b'',
                b'files': [{b'path': [b'placeholder.txt'], b'length': 0}]
            }
        }
        with open(dummy_torrent_path, 'wb') as f:
            f.write(bencode(dummy_torrent_data))

        torrent = Torrent(str(dummy_torrent_path))
        
        self.active_downloads[site_id] = {
            'torrent': torrent,
            'auto_update': auto_update
        }
        logger.info(f"Started downloading site: {site_id}")

        await torrent.init(dht_enabled=True)
        # Placeholder: a real implementation would download files.
        # for file in torrent.files:
        #     await torrent.download(file, save_path=save_path)
        logger.info(f"Placeholder: Download for site {site_id} is complete.")

    def get_site_status(self, site_id: str) -> Optional[Dict]:
        """Get download progress for a site."""
        if site_id in self.active_downloads:
            torrent = self.active_downloads[site_id]['torrent']
            return {
                "state": "Downloading",
                "progress": getattr(torrent, 'progress', 0),
            }
        
        metadata = self.storage.load_site_metadata(site_id)
        if metadata and 'download_path' in metadata:
            return {"state": "Downloaded"}
        return None

    def remove_site(self, site_id: str, delete_files: bool = False):
        """Remove a site."""
        if site_id in self.active_downloads:
            del self.active_downloads[site_id]
            logger.info(f"Removed site from downloader: {site_id}")

        if delete_files:
            self.storage.delete_site(site_id)
