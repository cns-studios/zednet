"""
Site publishing using BEP 46 (Mutable Torrents).
Handles creating and updating ZedNet sites.
"""
import libtorrent as lt
from pathlib import Path
from typing import Optional, Dict, List
import logging
import json
import time
from .security import SecurityManager
from .storage import SiteStorage

logger = logging.getLogger(__name__)

class SitePublisher:
    """
    Publishes and updates ZedNet sites using BEP 46 mutable torrents.
    """
    
    def __init__(self, session: lt.session, storage: SiteStorage):
        self.session = session
        self.storage = storage
        self.active_sites: Dict[str, Dict] = {}
    
    def create_site(self, site_name: str, content_dir: Path, 
                   password: Optional[str] = None) -> Dict[str, str]:
        """
        Create a new ZedNet site.
        
        Args:
            site_name: Human-readable site name
            content_dir: Directory containing site files
            password: Optional password to encrypt private key
            
        Returns:
            {
                'site_id': str,
                'public_key': str (hex),
                'private_key_file': str (path)
            }
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
    
    def publish_site(self, site_id: str, content_dir: Path,
                    private_key_file: Path, password: Optional[str] = None) -> bool:
        """
        Publish or update a site using BEP 46.
        
        Args:
            site_id: ZedNet site identifier
            content_dir: Directory with site content
            private_key_file: Path to encrypted private key
            password: Password to decrypt private key
            
        Returns:
            True if published successfully
        """
        logger.info("Publishing site: %s", site_id)
        
        try:
            # Load private key
            private_key = self.storage.load_private_key(
                private_key_file, password
            )
            
            # Create torrent from directory
            torrent_info = self._create_torrent(content_dir)
            
            # Get info hash
            info_hash = torrent_info.info_hash()
            
            # Create mutable torrent item for DHT (BEP 46)
            self._publish_to_dht(
                site_id=site_id,
                info_hash=info_hash,
                private_key=private_key,
                torrent_info=torrent_info
            )
            
            # Start seeding
            self._start_seeding(site_id, content_dir, torrent_info)
            
            # Update metadata
            metadata = self.storage.load_site_metadata(site_id)
            metadata['version'] += 1
            metadata['last_updated'] = time.time()
            metadata['info_hash'] = str(info_hash)
            self.storage.save_site_metadata(site_id, metadata)
            
            logger.info("Site published successfully: %s", site_id)
            return True
            
        except Exception as e:
            logger.error("Failed to publish site %s: %s", site_id, e)
            return False
    
    def _create_torrent(self, content_dir: Path) -> lt.torrent_info:
        """
        Create torrent from directory.
        
        Args:
            content_dir: Directory to create torrent from
            
        Returns:
            libtorrent torrent_info object
        """
        # Create file storage
        fs = lt.file_storage()
        
        # Add all files
        lt.add_files(fs, str(content_dir))
        
        # Create torrent
        t = lt.create_torrent(fs)
        
        # Set piece size (256KB)
        t.set_piece_size(256 * 1024)
        
        # Generate pieces
        lt.set_piece_hashes(t, str(content_dir.parent))
        
        # Add tracker (optional, we primarily use DHT)
        # t.add_tracker("udp://tracker.example.com:6881")
        
        # Create torrent_info
        torrent_data = lt.bencode(t.generate())
        torrent_info = lt.torrent_info(torrent_data)
        
        logger.info("Created torrent with %d files, %d pieces",
                   fs.num_files(), torrent_info.num_pieces())
        
        return torrent_info
    
    def _publish_to_dht(self, site_id: str, info_hash: lt.sha1_hash,
                       private_key: bytes, torrent_info: lt.torrent_info):
        """
        Publish mutable torrent to DHT using BEP 46.
        
        Args:
            site_id: ZedNet site ID (derived from public key)
            info_hash: Torrent info hash
            private_key: Ed25519 private key for signing
            torrent_info: Torrent metadata
        """
        try:
            # BEP 46: Mutable items in DHT
            # The public key hash is the DHT key
            # The value is the signed info_hash
            
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            
            # Reconstruct private key object
            private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
            public_key_obj = private_key_obj.public_key()
            
            # Prepare mutable item value
            # Format: info_hash as bencode
            value = {
                'ih': bytes(info_hash),  # info hash
                'v': 1,  # version
                't': int(time.time())  # timestamp
            }
            
            value_bytes = lt.bencode(value)
            
            # Sign the value
            signature = private_key_obj.sign(value_bytes)
            
            # Get public key bytes
            public_key_bytes = public_key_obj.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Put mutable item to DHT
            # Note: libtorrent's Python bindings for BEP 46 may vary by version
            # This is a simplified representation
            
            # For libtorrent 2.0+:
            item = {
                'v': value_bytes,
                'k': public_key_bytes,
                'sig': signature,
                'salt': b'',  # Optional salt
                'seq': 1  # Sequence number (increment on updates)
            }
            
            # Put to DHT (this API may need adjustment based on libtorrent version)
            self.session.dht_put_item(
                public_key_bytes,
                value_bytes,
                signature
            )
            
            logger.info("Published site to DHT: %s", site_id)
            
        except Exception as e:
            logger.error("Failed to publish to DHT: %s", e)
            raise
    
    def _start_seeding(self, site_id: str, content_dir: Path,
                      torrent_info: lt.torrent_info):
        """
        Start seeding the site content.
        
        Args:
            site_id: ZedNet site ID
            content_dir: Directory containing files
            torrent_info: Torrent metadata
        """
        # Add torrent to session
        params = lt.add_torrent_params()
        params.ti = torrent_info
        params.save_path = str(content_dir.parent)
        params.seed_mode = True  # Already have all data
        
        handle = self.session.add_torrent(params)
        
        # Store handle
        self.active_sites[site_id] = {
            'handle': handle,
            'content_dir': content_dir,
            'torrent_info': torrent_info
        }
        
        logger.info("Started seeding site: %s", site_id)
    
    def stop_seeding(self, site_id: str):
        """Stop seeding a site."""
        if site_id in self.active_sites:
            handle = self.active_sites[site_id]['handle']
            self.session.remove_torrent(handle)
            del self.active_sites[site_id]
            logger.info("Stopped seeding site: %s", site_id)
    
    def get_site_status(self, site_id: str) -> Optional[Dict]:
        """Get seeding status for a site."""
        if site_id not in self.active_sites:
            return None
        
        handle = self.active_sites[site_id]['handle']
        status = handle.status()
        
        return {
            'state': str(status.state),
            'progress': status.progress,
            'download_rate': status.download_rate,
            'upload_rate': status.upload_rate,
            'num_peers': status.num_peers,
            'num_seeds': status.num_seeds,
        }