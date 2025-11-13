"""
Optional VPN detection (NOT ENFORCEABLE - UI WARNING ONLY).
"""
import socket
import requests
from typing import Optional

class VPNChecker:
    """
    Attempts to detect VPN usage.
    WARNING: Easily bypassable. Use only for user warnings.
    """
    
    # Use multiple services for redundancy
    IP_CHECK_SERVICES = [
        'https://api.ipify.org?format=json',
        'https://ifconfig.me/ip',
    ]
    
    @staticmethod
    def get_public_ip() -> Optional[str]:
        """
        Get public IP address.
        
        Returns:
            IP address string or None on failure
        """
        for service in VPNChecker.IP_CHECK_SERVICES:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    # Handle both JSON and plain text responses
                    try:
                        return response.json()['ip']
                    except:
                        return response.text.strip()
            except:
                continue
        return None
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """Check if IP is in private ranges."""
        try:
            parts = [int(p) for p in ip.split('.')]
            if parts[0] == 10:
                return True
            if parts[0] == 172 and 16 <= parts[1] <= 31:
                return True
            if parts[0] == 192 and parts[1] == 168:
                return True
            if parts[0] == 127:
                return True
            return False
        except:
            return True  # Assume private on parse failure
    
    @classmethod
    def check_vpn_status(cls) -> dict:
        """
        Check if VPN appears active.
        
        Returns:
            {
                'appears_safe': bool,
                'public_ip': str or None,
                'warning': str or None
            }
        """
        public_ip = cls.get_public_ip()
        
        if public_ip is None:
            return {
                'appears_safe': False,
                'public_ip': None,
                'warning': 'Cannot determine public IP. Network issue or VPN blocking detection.'
            }
        
        if cls.is_private_ip(public_ip):
            return {
                'appears_safe': False,
                'public_ip': public_ip,
                'warning': 'You appear to be on a local network without VPN protection.'
            }
        
        # We have a public IP, but can't verify it's a VPN
        return {
            'appears_safe': True,  # Assume user knows what they're doing
            'public_ip': public_ip,
            'warning': 'Public IP detected. Ensure VPN is active if anonymity is required.'
        }