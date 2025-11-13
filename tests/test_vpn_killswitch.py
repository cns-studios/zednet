"""
Test VPN kill switch functionality.
"""
import pytest
from unittest.mock import Mock, patch
from core.vpn_check import VPNChecker
from core.killswitch import KillSwitch

class TestVPNDetection:
    """Test VPN detection logic."""
    
    @patch('core.vpn_check.requests.get')
    def test_public_ip_detection(self, mock_get):
        """Test public IP retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ip': '8.8.8.8'}
        mock_get.return_value = mock_response
        
        ip = VPNChecker.get_public_ip()
        assert ip == '8.8.8.8'
    
    def test_private_ip_detection(self):
        """Test private IP range detection."""
        assert VPNChecker.is_private_ip('192.168.1.1')
        assert VPNChecker.is_private_ip('10.0.0.1')
        assert VPNChecker.is_private_ip('172.16.0.1')
        assert VPNChecker.is_private_ip('127.0.0.1')
        
        assert not VPNChecker.is_private_ip('8.8.8.8')
        assert not VPNChecker.is_private_ip('1.1.1.1')


class TestKillSwitch:
    """Test kill switch emergency shutdown."""
    
    def test_kill_switch_triggers_on_vpn_loss(self):
        """Test that kill switch activates when VPN drops."""
        shutdown_called = {'called': False}
        
        def mock_shutdown():
            shutdown_called['called'] = True
        
        ks = KillSwitch(check_interval=1)
        ks.on_emergency_shutdown = mock_shutdown
        
        # Simulate VPN loss
        with patch.object(VPNChecker, 'check_vpn_status', return_value={
            'appears_safe': False,
            'public_ip': '192.168.1.1',
            'warning': 'VPN disconnected'
        }):
            ks._check_vpn_status()
            assert shutdown_called['called']