"""
Secure file storage and key management.
"""
from pathlib import Path
from typing import Optional
import json
import logging
from .security import SecurityManager

logger = logging.getLogger(__name__)

class SiteStorage:
    """
    Manages secure storage of sites, keys, and metadata.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.keys_dir = data_dir / 'keys'
        self.content_dir = data_dir / 'sites'
        self.metadata_dir = data_dir / 'metadata'
        
        # Create directories
        for d in [self.keys_dir, self.content_dir, self.metadata_dir]:
            d.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    def save_private_key(self, site_id: str, private_key: bytes,
                        password: Optional[str] = None) -> Path:
        """
        Save private key (encrypted if password provided).
        
        Args:
            site_id: Site identifier
            private_key: Raw private key bytes
            password: Optional encryption password
            
        Returns:
            Path to saved key file
        """
        key_file = self.keys_dir / f"{site_id}.key"
        
        if password:
            # Encrypt key
            encrypted_key = SecurityManager.encrypt_private_key(private_key, password)
            key_file.write_bytes(encrypted_key)
            logger.info("Saved encrypted private key: %s", key_file)
        else:
            # Save raw (NOT RECOMMENDED)
            key_file.write_bytes(private_key)
            logger.warning("Saved UNENCRYPTED private key: %s", key_file)
        
        # Set restrictive permissions
        key_file.chmod(0o600)
        
        return key_file
    
    def load_private_key(self, key_file: Path,
                        password: Optional[str] = None) -> bytes:
        """
        Load private key (decrypt if password provided).
        
        Args:
            key_file: Path to key file
            password: Decryption password
            
        Returns:
            Raw private key bytes
        """
        if not key_file.exists():
            raise FileNotFoundError(f"Key file not found: {key_file}")
        
        key_data = key_file.read_bytes()
        
        if password:
            # Decrypt
            try:
                private_key = SecurityManager.decrypt_private_key(key_data, password)
                logger.info("Decrypted private key: %s", key_file)
                return private_key
            except Exception as e:
                logger.error("Failed to decrypt key: %s", e)
                raise ValueError("Incorrect password or corrupted key")
        else:
            # Return raw
            return key_data
    
    def save_site_metadata(self, site_id: str, metadata: dict):
        """Save site metadata."""
        metadata_file = self.metadata_dir / f"{site_id}.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Saved metadata for site: %s", site_id)
    
    def load_site_metadata(self, site_id: str) -> Optional[dict]:
        """Load site metadata."""
        metadata_file = self.metadata_dir / f"{site_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load metadata for %s: %s", site_id, e)
            return None
    
    def get_site_content_dir(self, site_id: str) -> Path:
        """Get content directory for a site."""
        return self.content_dir / site_id
    
    def list_sites(self) -> list:
        """List all tracked sites."""
        sites = []
        
        for metadata_file in self.metadata_dir.glob('*.json'):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    sites.append(metadata)
            except Exception as e:
                logger.error("Failed to load %s: %s", metadata_file, e)
        
        return sites
    
    def delete_site(self, site_id: str, delete_key: bool = False):
        """
        Delete site data.
        
        Args:
            site_id: Site to delete
            delete_key: Also delete private key (DANGEROUS)
        """
        # Delete metadata
        metadata_file = self.metadata_dir / f"{site_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            logger.info("Deleted metadata: %s", site_id)
        
        # Delete content
        content_dir = self.get_site_content_dir(site_id)
        if content_dir.exists():
            import shutil
            shutil.rmtree(content_dir)
            logger.info("Deleted content: %s", site_id)
        
        # Delete key if requested
        if delete_key:
            key_file = self.keys_dir / f"{site_id}.key"
            if key_file.exists():
                SecurityManager.secure_delete(key_file)
                logger.warning("DELETED PRIVATE KEY: %s (IRREVERSIBLE)", site_id)