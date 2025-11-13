"""
Security primitives for ZedNet.
All cryptographic operations and input validation.
"""
import os
import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class SecurityManager:
    """Handles all cryptographic operations and input validation."""
    
    # Only allow alphanumeric and basic web file extensions
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
    ALLOWED_EXTENSIONS = {
        '.html', '.css', '.js', '.json', '.txt', 
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
        '.woff', '.woff2', '.ttf'
    }
    
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate Ed25519 keypair for ZedNet identity.
        
        Returns:
            (private_key_bytes, public_key_bytes)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return private_bytes, public_bytes
    
    @staticmethod
    def derive_site_id(public_key: bytes) -> str:
        """
        Derive human-readable site ID from public key.
        
        Args:
            public_key: Raw Ed25519 public key bytes
            
        Returns:
            Hex-encoded SHA256 hash (64 chars)
        """
        return hashlib.sha256(public_key).hexdigest()
    
    @staticmethod
    def sanitize_path(user_path: str, base_dir: Path) -> Optional[Path]:
        """
        CRITICAL: Prevent directory traversal attacks.
        
        Args:
            user_path: User-supplied path component
            base_dir: Allowed base directory (must be absolute)
            
        Returns:
            Resolved safe path or None if invalid
        """
        if not base_dir.is_absolute():
            raise ValueError("base_dir must be absolute path")
        
        # Remove leading/trailing slashes and normalize
        user_path = user_path.strip('/\\')
        
        # Split path and validate each component
        parts = user_path.split('/')
        for part in parts:
            # Reject dangerous patterns
            if part in ('', '.', '..'):
                return None
            if not SecurityManager.SAFE_FILENAME_PATTERN.match(part):
                return None
        
        # Reconstruct and resolve
        requested_path = base_dir / user_path
        try:
            resolved = requested_path.resolve()
        except (OSError, RuntimeError):
            return None
        
        # CRITICAL: Ensure resolved path is within base_dir
        try:
            resolved.relative_to(base_dir)
        except ValueError:
            return None
        
        # Validate file extension
        if resolved.suffix.lower() not in SecurityManager.ALLOWED_EXTENSIONS:
            return None
        
        return resolved
    
    @staticmethod
    def validate_site_id(site_id: str) -> bool:
        """
        Validate ZedNet site ID format.
        
        Args:
            site_id: Hex-encoded hash string
            
        Returns:
            True if valid format
        """
        if not isinstance(site_id, str):
            return False
        if len(site_id) != 64:  # SHA256 hex = 64 chars
            return False
        try:
            int(site_id, 16)
            return True
        except ValueError:
            return False