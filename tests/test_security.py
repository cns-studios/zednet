"""
CRITICAL SECURITY TESTS - Must pass 100%
Run with: pytest tests/ -v --tb=short
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from core.security import SecurityManager

class TestPathSanitization:
    """Test suite for directory traversal prevention."""
    
    @pytest.fixture
    def test_env(self):
        """Create isolated test environment."""
        temp_dir = Path(tempfile.mkdtemp())
        base_dir = temp_dir / "content"
        base_dir.mkdir()
        
        # Create safe test files
        (base_dir / "index.html").write_text("<html>Safe</html>")
        (base_dir / "subdir").mkdir()
        (base_dir / "subdir" / "page.html").write_text("<html>Sub</html>")
        
        # Create file outside base (attack target)
        attack_target = temp_dir / "secret.txt"
        attack_target.write_text("SENSITIVE DATA")
        
        yield base_dir, attack_target
        
        shutil.rmtree(temp_dir)
    
    def test_safe_path_allowed(self, test_env):
        """Test that safe paths are allowed."""
        base_dir, _ = test_env
        
        result = SecurityManager.sanitize_path("index.html", base_dir)
        assert result is not None
        assert result == base_dir / "index.html"
        
        result = SecurityManager.sanitize_path("subdir/page.html", base_dir)
        assert result is not None
        assert result == base_dir / "subdir" / "page.html"
    
    def test_directory_traversal_blocked(self, test_env):
        """CRITICAL: Block directory traversal attacks."""
        base_dir, attack_target = test_env
        
        # Classic attacks
        attacks = [
            "../secret.txt",
            "../../secret.txt",
            "../../../etc/passwd",
            "subdir/../../secret.txt",
            "./../../secret.txt",
            "subdir/../../../secret.txt",
            "....//....//secret.txt",
            "..\\..\\secret.txt",  # Windows style
            "subdir/..\\..\\secret.txt",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, base_dir)
            assert result is None, f"FAILED to block: {attack}"
    
    def test_absolute_path_blocked(self, test_env):
        """Block absolute path injections."""
        base_dir, attack_target = test_env
        
        attacks = [
            str(attack_target),  # Absolute path
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, base_dir)
            assert result is None, f"FAILED to block absolute path: {attack}"
    
    def test_special_filenames_blocked(self, test_env):
        """Block special filenames and path components."""
        base_dir, _ = test_env
        
        attacks = [
            ".",
            "..",
            "...",
            ".git/config",
            ".env",
            "subdir/.",
            "subdir/..",
            "",
            "//",
            "subdir//file.html",
            "subdir/..///..//secret.txt",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, base_dir)
            assert result is None, f"FAILED to block special filename: {attack}"
    
    def test_null_byte_injection_blocked(self, test_env):
        """Block null byte injection attacks."""
        base_dir, _ = test_env
        
        attacks = [
            "index.html\x00.txt",
            "safe.html\x00../../../etc/passwd",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, base_dir)
            assert result is None, f"FAILED to block null byte: {repr(attack)}"
    
    def test_invalid_extensions_blocked(self, test_env):
        """Block dangerous file extensions."""
        base_dir, _ = test_env
        
        dangerous = [
            "script.php",
            "backdoor.exe",
            "malware.sh",
            "config.ini",
            "data.db",
            "index.asp",
        ]
        
        for filename in dangerous:
            # Create the file to test extension filtering
            (base_dir / filename).write_text("test")
            result = SecurityManager.sanitize_path(filename, base_dir)
            assert result is None, f"FAILED to block extension: {filename}"
    
    def test_unicode_normalization_attacks(self, test_env):
        """Block Unicode-based path traversal."""
        base_dir, _ = test_env
        
        attacks = [
            "..%2Fsecret.txt",
            "..%252Fsecret.txt",
            "%2e%2e%2fsecret.txt",
            "..%5Csecret.txt",  # Backslash
            "..︱..︱secret.txt",  # Unicode lookalikes
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, base_dir)
            assert result is None, f"FAILED to block Unicode attack: {attack}"
    
    def test_nonexistent_file_allowed_in_path(self, test_env):
        """Allow path validation for files that don't exist yet."""
        base_dir, _ = test_env
        
        # Should validate path even if file doesn't exist
        result = SecurityManager.sanitize_path("newfile.html", base_dir)
        assert result is not None
        assert result == base_dir / "newfile.html"


class TestCryptography:
    """Test cryptographic operations."""
    
    def test_keypair_generation(self):
        """Test Ed25519 keypair generation."""
        private_key, public_key = SecurityManager.generate_keypair()
        
        assert len(private_key) == 32  # Ed25519 private key size
        assert len(public_key) == 32   # Ed25519 public key size
        assert private_key != public_key
    
    def test_site_id_derivation(self):
        """Test deterministic site ID generation."""
        _, public_key = SecurityManager.generate_keypair()
        
        site_id1 = SecurityManager.derive_site_id(public_key)
        site_id2 = SecurityManager.derive_site_id(public_key)
        
        assert site_id1 == site_id2  # Deterministic
        assert len(site_id1) == 64   # SHA256 hex
        assert SecurityManager.validate_site_id(site_id1)
    
    def test_site_id_validation(self):
        """Test site ID format validation."""
        # Valid
        assert SecurityManager.validate_site_id("a" * 64)
        assert SecurityManager.validate_site_id("0123456789abcdef" * 4)
        
        # Invalid
        assert not SecurityManager.validate_site_id("short")
        assert not SecurityManager.validate_site_id("z" * 64)  # Invalid hex
        assert not SecurityManager.validate_site_id("a" * 63)  # Wrong length
        assert not SecurityManager.validate_site_id("a" * 65)
        assert not SecurityManager.validate_site_id("")
        assert not SecurityManager.validate_site_id(None)
        assert not SecurityManager.validate_site_id(12345)


class TestInputValidation:
    """Test all user input validation."""
    
    def test_filename_pattern_validation(self):
        """Test filename pattern matching."""
        pattern = SecurityManager.SAFE_FILENAME_PATTERN
        
        # Valid
        assert pattern.match("index.html")
        assert pattern.match("style-main.css")
        assert pattern.match("script_v2.js")
        assert pattern.match("image.png")
        
        # Invalid
        assert not pattern.match("../etc/passwd")
        assert not pattern.match("file;rm -rf /")
        assert not pattern.match("bad|pipe.html")
        assert not pattern.match("bad&cmd.html")
        assert not pattern.match("bad`exec`.html")
        assert not pattern.match("bad$var.html")
        assert not pattern.match("file\x00.html")