"""
Site downloading and synchronization.
Handles fetching ZedNet sites from the DHT and keeping them updated.
"""
import libtorrent as lt
from pathlib import Path
from typing import Optional, Dict, Callable
import logging
import time
from .security import SecurityManager
from .storage import SiteStorage

logger = logging.getLogger(__name__)

class SiteDownloader:
    """
    Downloads and monitors ZedNet sites.
    """
    
    def __init__(self, session: lt.session, storage: SiteStorage):
        self.session = session
        self.storage = storage
        self.active_downloads: Dict[str, Dict] = {}
        self.update_callbacks: Dict[str, Callable] = {}
    
    def add_site(self, site_id: str, auto_update: bool = True) -> bool:
        """
        Add a site to track and download.
        
        Args:
            site_id: ZedNet site ID (public key hash)
            auto_update: Automatically download updates
            
        Returns:
            True if site added successfully
        """
        logger.info("Adding site: %s", site_id)
        
        # Validate site ID
        if not SecurityManager.validate_site_id(site_id):
            logger.error("Invalid site ID format: %s", site_id)
            return False
        
        # Check if already tracking
        if site_id in self.active_downloads:
            logger.warning("Site already being tracked: %s", site_id)
            return True
        
        try:
            # Lookup site in DHT
            info_hash = self._lookup_site_in_dht(site_id)
            
            if info_hash is None:
                logger.error("Site not found in DHT: %s", site_id)
                return False
            
            # Start download
            self._start_download(site_id, info_hash, auto_update)
            
            return True
            
        except Exception as e:
            logger.error("Failed to add site %s: %s", site_id, e)
            return False
    
    def _lookup_site_in_dht(self, site_id: str) -> Optional[lt.sha1_hash]:
        """
        Look up site's current info hash in DHT using BEP 46.
        
        Args:
            site_id: Site identifier (public key hash)
            
        Returns:
            Current torrent info hash or None
        """
        try:
            # Convert site_id back to public key
            # Note: We need to store public keys in metadata
            metadata = self.storage.load_site_metadata(site_id)
            
            if not metadata or 'public_key' not in metadata:
                logger.error("No public key found for site: %s", site_id)
                return None
            
            public_key_hex = metadata['public_key']
            public_key_bytes = bytes.fromhex(public_key_hex)
            
            # DHT get mutable item (BEP 46)
            # This retrieves the latest signed info_hash
            
            # Create callback for DHT response
            result = {'info_hash': None, 'received': False}
            
            def dht_callback(item):
                if item and 'v' in item:
                    # Decode bencode value
                    value = lt.bdecode(item['v'])
                    if 'ih' in value:
                        result['info_hash'] = lt.sha1_hash(value['ih'])
                        result['received'] = True
            
            # Get from DHT
            self.session.dht_get_item(public_key_bytes, dht_callback)
            
            # Wait for response (with timeout)
            timeout = 30  # seconds
            start_time = time.time()
            
            while not result['received'] and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                # Process DHT alerts
                self.session.wait_for_alert(100)
                alerts = self.session.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.dht_mutable_item_alert):
                        dht_callback({
                            'v': alert.item,
                            'sig': alert.signature,
                            'k': alert.key
                        })
            
            if not result['received']:
                logger.warning("DHT lookup timeout for site: %s", site_id)
                return None
            
            logger.info("Found site in DHT: %s", site_id)
            return result['info_hash']
            
        except Exception as e:
            logger.error("DHT lookup failed for %s: %s", site_id, e)
            return None
    
    def _start_download(self, site_id: str, info_hash: lt.sha1_hash,
                       auto_update: bool):
        """
        Start downloading site content.
        
        Args:
            site_id: Site identifier
            info_hash: Torrent info hash
            auto_update: Monitor for updates
        """
        # Create save directory
        save_path = self.storage.get_site_content_dir(site_id)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Add torrent
        params = lt.add_torrent_params()
        params.info_hash = info_hash
        params.save_path = str(save_path)
        
        # Flags
        params.flags |= lt.torrent_flags.auto_managed
        params.flags |= lt.torrent_flags.duplicate_is_error
        
        handle = self.session.add_torrent(params)
        
        # Store download info
        self.active_downloads[site_id] = {
            'handle': handle,
            'info_hash': info_hash,
            'auto_update': auto_update,
            'started_at': time.time()
        }
        
        # Start monitoring for updates if enabled
        if auto_update:
            self._monitor_for_updates(site_id)
        
        logger.info("Started downloading site: %s", site_id)
    
    def _monitor_for_updates(self, site_id: str):
        """
        Monitor DHT for site updates.
        
        Args:
            site_id: Site to monitor
        """
        # This should run in a background thread
        import threading
        
        def update_checker():
            while site_id in self.active_downloads:
                try:
                    # Check DHT every 5 minutes
                    time.sleep(300)
                    
                    if site_id not in self.active_downloads:
                        break
                    
                    # Look up current version
                    current_hash = self._lookup_site_in_dht(site_id)
                    
                    if current_hash is None:
                        continue
                    
                    # Compare with our version
                    our_hash = self.active_downloads[site_id]['info_hash']
                    
                    if current_hash != our_hash:
                        logger.info("Update detected for site: %s", site_id)
                        # Download new version
                        self._update_site(site_id, current_hash)
                        
                        # Call update callback if registered
                        if site_id in self.update_callbacks:
                            self.update_callbacks[site_id](site_id, current_hash)
                
                except Exception as e:
                    logger.error("Update check failed for %s: %s", site_id, e)
        
        thread = threading.Thread(target=update_checker, daemon=True)
        thread.start()
    
    def _update_site(self, site_id: str, new_info_hash: lt.sha1_hash):
        """
        Update site to new version.
        
        Args:
            site_id: Site identifier
            new_info_hash: New torrent info hash
        """
        logger.info("Updating site %s to new version", site_id)
        
        # Remove old torrent
        old_handle = self.active_downloads[site_id]['handle']
        self.session.remove_torrent(old_handle)
        
        # Start downloading new version
        self._start_download(
            site_id,
            new_info_hash,
            auto_update=self.active_downloads[site_id]['auto_update']
        )
    
    def remove_site(self, site_id: str, delete_files: bool = False):
        """
        Stop tracking a site.
        
        Args:
            site_id: Site to remove
            delete_files: Delete downloaded content
        """
        if site_id not in self.active_downloads:
            logger.warning("Site not being tracked: %s", site_id)
            return
        
        # Remove torrent
        handle = self.active_downloads[site_id]['handle']
        
        if delete_files:
            self.session.remove_torrent(handle, lt.options_t.delete_files)
        else:
            self.session.remove_torrent(handle)
        
        del self.active_downloads[site_id]
        
        logger.info("Removed site: %s (deleted files: %s)", site_id, delete_files)
    
    def get_download_status(self, site_id: str) -> Optional[Dict]:
        """Get download progress for a site."""
        if site_id not in self.active_downloads:
            return None
        
        handle = self.active_downloads[site_id]['handle']
        status = handle.status()
        
        return {
            'state': str(status.state),
            'progress': status.progress * 100,  # Percentage
            'download_rate': status.download_rate / 1024,  # KB/s
            'upload_rate': status.upload_rate / 1024,  # KB/s
            'num_peers': status.num_peers,
            'num_seeds': status.num_seeds,
            'total_download': status.total_download,
            'total_upload': status.total_upload,
        }
    
    def register_update_callback(self, site_id: str, callback: Callable):
        """
        Register callback for site updates.
        
        Args:
            site_id: Site to monitor
            callback: Function called when update detected
                     Signature: callback(site_id: str, new_hash: sha1_hash)
        """
        self.update_callbacks[site_id] = callback
        logger.info("Registered update callback for site: %s", site_id)