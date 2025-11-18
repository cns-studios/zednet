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
from .torrent import ZedNetTorrent as Torrent
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
        
        # Validate content directory
        if not content_dir.exists() or not content_dir.is_dir():
            raise ValueError(f"Invalid content directory: {content_dir}")
        
        # Check for required files
        index_file = content_dir / "index.html"
        if not index_file.exists():
            logger.warning("No index.html found in %s", content_dir)
        
        # Generate keypair
        private_key, public_key = SecurityManager.generate_keypair()
        site_id = SecurityManager.derive_site_id(public_key)
        
        # Save private key
        key_file = self.storage.save_private_key(
            site_id, private_key, password
        )
        
        # Save site metadata
        metadata = {
            'site_id': site_id,
            'site_name': site_name,
            'public_key': public_key.hex(),
            'created_at': time.time(),
            'version': 1,
            'content_hash': None  # Will be set on publish
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
            info_hash = torrent.torrent_info['info_hash']
            
            await self._publish_to_dht(site_id, info_hash, private_key)
            
            await self._start_seeding(site_id, torrent)
            
            # ... (update metadata)
            
            return True
        except Exception as e:
            logger.error("Failed to publish site %s: %s", site_id, e)
            return False

    async def _create_torrent(self, content_dir: Path) -> Torrent:
        """
        Create torrent from directory.
        """
        t = torf.Torrent(path=str(content_dir), trackers=[])
        t.generate()
        
        torrent_path = content_dir.parent / f"{content_dir.name}.torrent"
        t.write(torrent_path)
        
        torrent = Torrent(torrent_path)
        return torrent

    async def _publish_to_dht(self, site_id: str, info_hash: bytes, private_key: bytes):
        """
        Publish mutable torrent to DHT using BEP 46.
        """
        public_key = SecurityManager.get_public_key(private_key)

        metadata = self.storage.load_site_metadata(site_id)
        seq = metadata.get("version", 1)

        value = {"ih": info_hash}
        bencoded_value = bencode(value)

        # TODO: Implement BEP 46 signing and putting
        # This will require a custom DHT client that can handle mutable puts.
        # For now, we'll just log the data.
        logger.info("BEP 46 Data:")
        logger.info("  Public Key: %s", public_key.hex())
        logger.info("  Sequence: %d", seq)
        logger.info("  Value: %s", bencoded_value.hex())

        # This is a placeholder. A real implementation would need to
        # sign the data and send it to the DHT.
        # dht_server = aiotorrent.DHTServer()
        # await dht_server.start()
        # await dht_server.set(public_key, bencoded_value, seq, private_key)
        # await dht_server.stop()

    async def _start_seeding(self, site_id: str, torrent: Torrent):
        """
        Start seeding the site content.
        """
        client = aiotorrent.Client()
        await client.start(torrent)
        self.active_sites[site_id] = {"torrent": torrent, "client": client}
        logger.info("Started seeding site: %s", site_id)

    def get_site_status(self, site_id: str) -> Optional[Dict]:
        """Get status for a specific site."""
        if site_id not in self.active_sites:
            return None

        torrent = self.active_sites[site_id]['torrent']
        return {
            "state": "Seeding",
            "num_peers": len(torrent.peers),
            "upload_rate": 0  # To be implemented
        }

    def stop_seeding(self, site_id: str):
        """Stop seeding a site."""
        if site_id in self.active_sites:
            # aiotorrent doesn't have a clean stop method, so we just drop it
            del self.active_sites[site_id]
            logger.info("Stopped seeding site: %s", site_id)
