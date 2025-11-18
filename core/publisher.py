"""
Site publishing using aiotorrent and BEP 46.
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict
import logging
import time
from .security import SecurityManager
from .storage import SiteStorage
import aiotorrent
from aiotorrent import Torrent
from fastbencode import bencode
import torf

logger = logging.getLogger(__name__)

class SitePublisher:
    """
    Publishes and updates ZedNet sites using BEP 46 mutable torrents.
    """
    
    def __init__(self, storage: SiteStorage):
        self.storage = storage
        self.active_sites: Dict[str, Dict] = {}

    def create_site(self, site_name: str, content_dir: Path, password: Optional[str] = None) -> Dict[str, str]:
        """
        Create a new ZedNet site.
        """
        logger.info("Creating new site: %s", site_name)
        
        if not content_dir.exists() or not content_dir.is_dir():
            raise ValueError(f"Invalid content directory: {content_dir}")
        
        index_file = content_dir / "index.html"
        if not index_file.exists():
            logger.warning("No index.html found in %s", content_dir)
        
        private_key, public_key = SecurityManager.generate_keypair()
        site_id = SecurityManager.derive_site_id(public_key)
        
        key_file = self.storage.save_private_key(
            site_id, private_key, password
        )
        
        metadata = {
            'site_id': site_id,
            'site_name': site_name,
            'public_key': public_key.hex(),
            'created_at': time.time(),
            'version': 1,
            'content_hash': None,
            'content_path': str(content_dir),
            'status': 'Ready to Publish'
        }
        
        self.storage.save_site_metadata(site_id, metadata)
        
        logger.info("Site created successfully: %s", site_id)
        
        return {
            'site_id': site_id,
            'public_key': public_key.hex(),
            'private_key_file': str(key_file)
        }

    async def publish_site(self, site_id: str, content_dir: Path, private_key_file: Path, password: Optional[str] = None) -> bool:
        """
        Publish or update a site using BEP 46.
        """
        try:
            private_key = self.storage.load_private_key(private_key_file, password)
            
            torrent = await self._create_torrent(content_dir)
            await torrent.init()
            # Correctly access the info_hash from the torrent_info dictionary
            info_hash = torrent.torrent_info['info_hash']
            
            await self._publish_to_dht(site_id, info_hash, private_key)
            
            await self._start_seeding(site_id, torrent)
            
            # Update metadata
            metadata = self.storage.load_site_metadata(site_id)
            metadata['content_hash'] = info_hash.hex()
            metadata['version'] = metadata.get('version', 1) + 1
            metadata['status'] = 'Seeding'
            self.storage.save_site_metadata(site_id, metadata)

            return True
        except Exception as e:
            logger.error(f"Failed to publish site {site_id}: {e}", exc_info=True)
            return False

    async def _create_torrent(self, content_dir: Path) -> Torrent:
        """
        Create torrent from directory.
        """
        t = torf.Torrent(path=str(content_dir), trackers=[])
        t.generate()
        
        # Using a temporary path for the torrent file
        torrent_path = content_dir.parent / f"{content_dir.name}.torrent"
        t.write(str(torrent_path))
        
        return Torrent(str(torrent_path))

    async def _publish_to_dht(self, site_id: str, info_hash: bytes, private_key: bytes):
        """
        Publish mutable torrent to DHT using BEP 46. This is a placeholder.
        """
        public_key = SecurityManager.get_public_key(private_key)
        metadata = self.storage.load_site_metadata(site_id)
        seq = metadata.get("version", 1)

        value = {b"ih": info_hash}
        bencoded_value = bencode(value)

        logger.info("BEP 46 Data (Placeholder):")
        logger.info(f"  Public Key: {public_key.hex()}")
        logger.info(f"  Sequence: {seq}")
        logger.info(f"  Value: {bencoded_value.hex()}")
        # In a real implementation, this would involve signing and putting to the DHT.
        # aiotorrent library does not support this directly.

    async def _start_seeding(self, site_id: str, torrent: Torrent):
        """
        Start seeding the site content. This is a placeholder.
        """
        self.active_sites[site_id] = {"torrent": torrent, "task": None}
        logger.info(f"Started seeding site: {site_id}")
        # Placeholder: a real implementation would start a long-running seeding task.
        # await torrent.start()

    def get_site_status(self, site_id: str) -> Optional[Dict]:
        """Get status for a specific site."""
        if site_id in self.active_sites:
            torrent = self.active_sites[site_id]['torrent']
            return {
                "state": "Seeding",
                "num_peers": len(getattr(torrent, 'peers', [])),
                "upload_rate": 0
            }

        metadata = self.storage.load_site_metadata(site_id)
        if metadata:
            return {"state": metadata.get('status', 'Unknown')}
        return None

    def stop_seeding(self, site_id: str):
        """Stop seeding a site."""
        if site_id in self.active_sites:
            # Placeholder for stopping the seeding task
            del self.active_sites[site_id]
            logger.info(f"Stopped seeding site: {site_id}")
