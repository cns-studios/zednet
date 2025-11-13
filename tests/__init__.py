"""
ZedNet Test Suite

Security-critical tests that MUST pass before any release.

Priority:
1. Security tests (path traversal, crypto, input validation)
2. P2P functionality tests
3. Server tests
4. Integration tests
"""

import pytest
import logging

# Configure test logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)

# Test fixtures available to all tests
@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create subdirectories
    (data_dir / "sites").mkdir()
    (data_dir / "keys").mkdir()
    (data_dir / "logs").mkdir()
    (data_dir / "metadata").mkdir()
    
    return data_dir

@pytest.fixture
def mock_vpn_safe(monkeypatch):
    """Mock VPN as safe for testing."""
    from core.vpn_check import VPNChecker
    
    def mock_check():
        return {
            'appears_safe': True,
            'public_ip': '1.2.3.4',
            'warning': None
        }
    
    monkeypatch.setattr(VPNChecker, 'check_vpn_status', lambda: mock_check())

@pytest.fixture
def mock_vpn_unsafe(monkeypatch):
    """Mock VPN as unsafe for testing."""
    from core.vpn_check import VPNChecker
    
    def mock_check():
        return {
            'appears_safe': False,
            'public_ip': '192.168.1.1',
            'warning': 'Private IP detected'
        }
    
    monkeypatch.setattr(VPNChecker, 'check_vpn_status', lambda: mock_check())