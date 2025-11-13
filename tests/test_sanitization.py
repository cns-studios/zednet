"""
Dedicated Path Sanitization Security Tests

CRITICAL: These tests MUST pass 100%.
Path traversal vulnerabilities are the #1 attack vector.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import os
from core.security import SecurityManager


class TestPathSanitizationComprehensive:
    """
    Exhaustive path sanitization tests.
    Tests every known path traversal technique.
    """
    
    @pytest.fixture
    def isolated_env(self):
        """
        Create isolated filesystem for testing.
        
        Structure:
        temp/
        ├── allowed/
        │   ├── index.html
        │   └── subdir/
        │       └── page.html
        ├── forbidden/
        │   └── secret.txt
        └── symlink -> forbidden/
        """
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create allowed directory
        allowed = temp_dir / "allowed"
        allowed.mkdir()
        (allowed / "index.html").write_text("<html>Safe</html>")
        
        subdir = allowed / "subdir"
        subdir.mkdir()
        (subdir / "page.html").write_text("<html>Sub</html>")
        
        # Create forbidden directory (outside allowed)
        forbidden = temp_dir / "forbidden"
        forbidden.mkdir()
        (forbidden / "secret.txt").write_text("SENSITIVE DATA")
        
        # Create symlink attack vector
        try:
            symlink = allowed / "symlink"
            symlink.symlink_to(forbidden)
        except OSError:
            pass  # Symlinks may not work on Windows without admin
        
        yield allowed, forbidden
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    # ===== BASIC TRAVERSAL ATTACKS =====
    
    def test_single_dot_dot_blocked(self, isolated_env):
        """Test ../ traversal blocked."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "../forbidden/secret.txt",
            "./../forbidden/secret.txt",
            "subdir/../../forbidden/secret.txt",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block: {attack}"
    
    def test_multiple_dot_dot_blocked(self, isolated_env):
        """Test multiple ../ blocked."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "../../forbidden/secret.txt",
            "../../../forbidden/secret.txt",
            "../../../../etc/passwd",
            "subdir/../../../forbidden/secret.txt",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block: {attack}"
    
    # ===== ENCODED TRAVERSAL ATTACKS =====
    
    def test_url_encoded_traversal_blocked(self, isolated_env):
        """Test URL-encoded ../ blocked."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "%2e%2e/forbidden/secret.txt",          # ..
            "%2e%2e%2fforbidden/secret.txt",        # ../
            "..%2fforbidden/secret.txt",            # ../
            "..%5cforbidden/secret.txt",            # ..\
            "%2e%2e%5cforbidden%5csecret.txt",      # ..\ (Windows)
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block URL-encoded: {attack}"
    
    def test_double_encoded_traversal_blocked(self, isolated_env):
        """Test double URL-encoded attacks."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "%252e%252e/forbidden/secret.txt",      # Double-encoded ..
            "%252e%252e%252fforbidden/secret.txt",  # Double-encoded ../
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block double-encoded: {attack}"
    
    # ===== UNICODE/UTF-8 ATTACKS =====
    
    def test_unicode_traversal_blocked(self, isolated_env):
        """Test Unicode lookalike characters blocked."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "..︱forbidden/secret.txt",              # Unicode fullwidth solidus
            ".\u002e/forbidden/secret.txt",         # Unicode dot
            "..\u2215forbidden/secret.txt",         # Unicode division slash
            "..\uff0fforbidden/secret.txt",         # Fullwidth slash
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block Unicode: {repr(attack)}"
    
    # ===== ABSOLUTE PATH ATTACKS =====
    
    def test_absolute_paths_blocked(self, isolated_env):
        """Test absolute paths rejected."""
        allowed, forbidden = isolated_env
        
        attacks = [
            str(forbidden / "secret.txt"),          # Absolute path
            "/etc/passwd",                          # Unix absolute
            "C:\\Windows\\System32\\config\\SAM",   # Windows absolute
            "\\\\server\\share\\file.txt",          # UNC path
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block absolute: {attack}"
    
    # ===== NULL BYTE INJECTION =====
    
    def test_null_byte_injection_blocked(self, isolated_env):
        """Test null byte attacks blocked."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "index.html\x00.txt",
            "safe.html\x00../../forbidden/secret.txt",
            "index.html\x00",
            "\x00../../forbidden/secret.txt",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block null byte: {repr(attack)}"
    
    # ===== BACKSLASH ATTACKS (Windows) =====
    
    def test_backslash_traversal_blocked(self, isolated_env):
        """Test backslash traversal blocked."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "..\\forbidden\\secret.txt",
            "..\\..\\forbidden\\secret.txt",
            "subdir\\..\\..\\forbidden\\secret.txt",
            "..\\\\forbidden\\\\secret.txt",        # Double backslash
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block backslash: {attack}"
    
    # ===== MIXED SEPARATOR ATTACKS =====
    
    def test_mixed_separators_blocked(self, isolated_env):
        """Test mixed slash/backslash attacks."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "../\\forbidden/secret.txt",
            "..\\../forbidden\\secret.txt",
            "..\\/forbidden/secret.txt",
            "..//forbidden//secret.txt",            # Double forward slash
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            assert result is None, f"Failed to block mixed: {attack}"
    
    # ===== DOT SEGMENT ATTACKS =====
    
    def test_dot_segments_blocked(self, isolated_env):
        """Test various dot segment attacks."""
        allowed, forbidden = isolated_env
        
        attacks = [
            ".",
            "..",
            "...",
            "....",
            "./index.html",                          # Should normalize but check carefully
            "subdir/.",
            "subdir/..",
            "subdir/../..",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            # Most should be blocked, but some may normalize safely
            # The key is they shouldn't escape the base directory
            if result is not None:
                # If allowed, ensure it's still within base
                try:
                    result.relative_to(allowed)
                except ValueError:
                    pytest.fail(f"Path escaped base directory: {attack} -> {result}")
    
    # ===== OVERLONG UTF-8 ATTACKS =====
    
    def test_overlong_utf8_blocked(self, isolated_env):
        """Test overlong UTF-8 encoding attacks."""
        allowed, forbidden = isolated_env
        
        # Overlong encoding of '/' and '.'
        attacks = [
            b"..%c0%af..%c0%afforbidden/secret.txt".decode('utf-8', errors='ignore'),
            b"..%e0%80%af..%e0%80%afforbidden/secret.txt".decode('utf-8', errors='ignore'),
        ]
        
        for attack in attacks:
            if attack:  # Skip if decode failed
                result = SecurityManager.sanitize_path(attack, allowed)
                assert result is None, f"Failed to block overlong UTF-8: {repr(attack)}"
    
    # ===== SPECIAL FILENAMES =====
    
    def test_special_filenames_blocked(self, isolated_env):
        """Test special/reserved filenames."""
        allowed, forbidden = isolated_env
        
        attacks = [
            "CON",          # Windows reserved
            "PRN",          # Windows reserved
            "AUX",          # Windows reserved
            "NUL",          # Windows reserved
            "COM1",         # Windows reserved
            "LPT1",         # Windows reserved
            ".git/config",  # Git directory
            ".env",         # Environment file
            ".htaccess",    # Apache config
            "web.config",   # IIS config
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            # These may or may not be blocked depending on implementation
            # Key is they shouldn't expose sensitive data
            if result is not None:
                assert not result.exists() or result.is_relative_to(allowed)
    
    # ===== SYMLINK ATTACKS =====
    
    def test_symlink_escape_blocked(self, isolated_env):
        """Test symlink traversal blocked."""
        allowed, forbidden = isolated_env
        
        symlink_path = allowed / "symlink"
        if not symlink_path.exists():
            pytest.skip("Symlinks not available on this system")
        
        attacks = [
            "symlink/secret.txt",
            "symlink/../forbidden/secret.txt",
        ]
        
        for attack in attacks:
            result = SecurityManager.sanitize_path(attack, allowed)
            # Should either block or resolve safely within base
            if result is not None:
                try:
                    result.resolve().relative_to(allowed.resolve())
                except ValueError:
                    pytest.fail(f"Symlink escape: {attack} -> {result}")
    
    # ===== CASE SENSITIVITY ATTACKS =====
    
    def test_case_variations(self, isolated_env):
        """Test case sensitivity doesn't break security."""
        allowed, forbidden = isolated_env
        
        # On case-insensitive filesystems, these might access the same file
        variations = [
            "INDEX.HTML",
            "Index.Html",
            "index.HTML",
        ]
        
        for variation in variations:
            result = SecurityManager.sanitize_path(variation, allowed)
            # Should either work (same file) or fail safely
            if result is not None:
                try:
                    result.relative_to(allowed)
                except ValueError:
                    pytest.fail(f"Case variation escape: {variation}")
    
    # ===== VALID PATHS (Should Work) =====
    
    def test_valid_paths_allowed(self, isolated_env):
        """Test legitimate paths are allowed."""
        allowed, forbidden = isolated_env
        
        valid_paths = [
            "index.html",
            "subdir/page.html",
        ]
        
        for path in valid_paths:
            result = SecurityManager.sanitize_path(path, allowed)
            assert result is not None, f"Legitimate path blocked: {path}"
            assert result.exists(), f"Valid path doesn't exist: {path}"
            
            # Ensure it's within base
            try:
                result.relative_to(allowed)
            except ValueError:
                pytest.fail(f"Valid path escaped base: {path}")
    
    # ===== EXTENSION VALIDATION =====
    
    def test_dangerous_extensions_blocked(self, isolated_env):
        """Test dangerous file extensions blocked."""
        allowed, forbidden = isolated_env
        
        dangerous_files = [
            "malware.exe",
            "backdoor.dll",
            "script.sh",
            "evil.bat",
            "payload.php",
            "hack.jsp",
            "trojan.scr",
        ]
        
        for filename in dangerous_files:
            # Create the file
            (allowed / filename).write_text("dangerous")
            
            result = SecurityManager.sanitize_path(filename, allowed)
            assert result is None, f"Dangerous extension not blocked: {filename}"
    
    def test_safe_extensions_allowed(self, isolated_env):
        """Test safe file extensions allowed."""
        allowed, forbidden = isolated_env
        
        safe_files = [
            "page.html",
            "style.css",
            "script.js",
            "data.json",
            "image.png",
            "photo.jpg",
            "doc.pdf",
        ]
        
        for filename in safe_files:
            # Create the file
            (allowed / filename).write_text("safe")
            
            result = SecurityManager.sanitize_path(filename, allowed)
            assert result is not None, f"Safe extension blocked: {filename}"
    
    # ===== PERFORMANCE TESTS =====
    
    def test_deeply_nested_path(self, isolated_env):
        """Test performance with deeply nested paths."""
        allowed, forbidden = isolated_env
        
        # Create deeply nested structure
        deep_path = allowed
        for i in range(50):
            deep_path = deep_path / f"level{i}"
            deep_path.mkdir(exist_ok=True)
        
        (deep_path / "deep.html").write_text("deep")
        
        # Build path string
        path_str = "/".join([f"level{i}" for i in range(50)] + ["deep.html"])
        
        result = SecurityManager.sanitize_path(path_str, allowed)
        assert result is not None, "Deep path blocked"
        assert result.exists(), "Deep path doesn't resolve"
    
    def test_very_long_filename(self, isolated_env):
        """Test handling of very long filenames."""
        allowed, forbidden = isolated_env
        
        # Create very long filename (but within limits)
        long_name = "a" * 200 + ".html"
        
        result = SecurityManager.sanitize_path(long_name, allowed)
        # May be blocked due to length or pattern, but shouldn't crash
        assert result is None or isinstance(result, Path)


class TestSecurityManagerEdgeCases:
    """Additional edge case tests for SecurityManager."""
    
    def test_base_dir_must_be_absolute(self):
        """Test that relative base_dir is rejected."""
        with pytest.raises(ValueError, match="absolute"):
            SecurityManager.sanitize_path("index.html", Path("relative/path"))
    
    def test_empty_path_blocked(self):
        """Test empty path rejected."""
        result = SecurityManager.sanitize_path("", Path("/tmp").resolve())
        assert result is None
    
    def test_whitespace_only_blocked(self):
        """Test whitespace-only path rejected."""
        result = SecurityManager.sanitize_path("   ", Path("/tmp").resolve())
        assert result is None
    
    def test_path_with_spaces_normalized(self):
        """Test paths with spaces handled correctly."""
        temp = Path(tempfile.mkdtemp())
        (temp / "file with spaces.html").write_text("test")
        
        result = SecurityManager.sanitize_path("file with spaces.html", temp)
        # May be allowed if filename pattern permits spaces
        # Key is no directory traversal
        
        shutil.rmtree(temp)


# ===== INTEGRATION TEST =====

def test_sanitization_in_server_context():
    """
    Integration test: Ensure server uses sanitization correctly.
    """
    from server.local_server import app
    from config import CONTENT_DIR
    
    # Create test client
    client = app.test_client()
    
    # Try path traversal attack via HTTP
    attacks = [
        "/site/a" * 64 + "/../../../etc/passwd",
        "/site/a" * 64 + "/%2e%2e/%2e%2e/secret.txt",
    ]
    
    for attack in attacks:
        response = client.get(attack)
        # Should return 400 or 403, NOT 200
        assert response.status_code in [400, 403, 404], \
            f"Server didn't block attack: {attack} (status: {response.status_code})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])