"""
Enhanced security module with comprehensive protections.
"""
import os
import re
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Centralized security operations."""
    
    # Strict filename validation
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
    
    # Allowed MIME types
    ALLOWED_EXTENSIONS = {
        '.html', '.htm', '.css', '.js', '.json', '.txt', '.md',
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico',
        '.woff', '.woff2', '.ttf', '.otf', '.eot',
        '.xml', '.pdf', '.mp3', '.mp4', '.webm', '.ogg'
    }
    
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate Ed25519 keypair.
        
        Returns:
            (private_key_bytes, public_key_bytes)
        """
        try:
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
            
            logger.info("Generated new Ed25519 keypair")
            return private_bytes, public_bytes
            
        except Exception as e:
            logger.error("Keypair generation failed: %s", e)
            raise

    @staticmethod
    def get_public_key(private_key: bytes) -> bytes:
        """
        Derive public key from a private key.
        """
        try:
            priv_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
            pub_key_obj = priv_key_obj.public_key()
            return pub_key_obj.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        except Exception as e:
            logger.error("Failed to derive public key: %s", e)
            raise

    @staticmethod
    def derive_site_id(public_key: bytes) -> str:
        """Derive site ID from public key (SHA256)."""
        return hashlib.sha256(public_key).hexdigest()
    
    @staticmethod
    def sanitize_path(user_path: str, base_dir: Path) -> Optional[Path]:
        """
        CRITICAL: Prevent directory traversal.
        
        Defense in depth:
        1. Path normalization
        2. Component validation
        3. Resolution check
        4. Extension whitelist
        """
        if not base_dir.is_absolute():
            raise ValueError("base_dir must be absolute")

        # Block absolute paths (Unix and Windows)
        if user_path.startswith('/') or user_path.startswith('\\') or re.match(r'^[a-zA-Z]:\\', user_path):
            return None
        
        # Normalize and strip
        user_path = user_path.strip().strip('/\\')
        
        if not user_path:
            return None
        
        # Check for null bytes
        if '\x00' in user_path:
            logger.warning("Null byte in path: %s", repr(user_path))
            return None
        
        # URL decode (prevent encoding attacks)
        try:
            from urllib.parse import unquote
            user_path = unquote(user_path)
        except:
            pass
        
        # Split and validate each component
        parts = user_path.replace('\\', '/').split('/')
        for part in parts:
            if part in ('', '.', '..'):
                logger.warning("Invalid path component: %s", part)
                return None
            if not SecurityManager.SAFE_FILENAME_PATTERN.match(part):
                logger.warning("Unsafe filename pattern: %s", part)
                return None
        
        # Reconstruct path
        requested_path = base_dir / Path(*parts)
        
        # Resolve symlinks and relative paths
        try:
            resolved = requested_path.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            logger.warning("Path resolution failed: %s", e)
            return None
        
        # CRITICAL: Ensure within base_dir
        try:
            resolved.relative_to(base_dir.resolve())
        except ValueError:
            logger.warning("Path escape attempt: %s -> %s", user_path, resolved)
            return None
        
        # Validate extension
        if resolved.suffix.lower() not in SecurityManager.ALLOWED_EXTENSIONS:
            logger.warning("Blocked extension: %s", resolved.suffix)
            return None
        
        return resolved
    
    @staticmethod
    def validate_site_id(site_id: str) -> bool:
        """Validate site ID format (64 hex chars)."""
        if not isinstance(site_id, str):
            return False
        if len(site_id) != 64:
            return False
        try:
            int(site_id, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def secure_delete(filepath: Path, passes: int = 3):
        """
        Securely delete file by overwriting.
        
        Args:
            filepath: File to delete
            passes: Number of overwrite passes
        """
        try:
            if not filepath.exists():
                return
            
            file_size = filepath.stat().st_size
            
            with open(filepath, 'ba+') as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            filepath.unlink()
            logger.info("Securely deleted: %s", filepath)
            
        except Exception as e:
            logger.error("Secure delete failed for %s: %s", filepath, e)
    
    @staticmethod
    def encrypt_private_key(private_key: bytes, password: str) -> bytes:
        """
        Encrypt private key with password (AES-256-GCM).
        
        Args:
            private_key: Raw private key bytes
            password: User password
            
        Returns:
            Encrypted key (nonce + tag + ciphertext)
        """
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        
        # Derive key from password
        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        # Encrypt with AES-256-GCM
        nonce = secrets.token_bytes(12)
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(private_key) + encryptor.finalize()
        
        # Return: salt + nonce + tag + ciphertext
        return salt + nonce + encryptor.tag + ciphertext
    
    @staticmethod
    def decrypt_private_key(encrypted_key: bytes, password: str) -> bytes:
        """Decrypt private key."""
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        
        # Extract components
        salt = encrypted_key[:16]
        nonce = encrypted_key[16:28]
        tag = encrypted_key[28:44]
        ciphertext = encrypted_key[44:]
        
        # Derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()