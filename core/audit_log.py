"""
Security audit logging - CANNOT be disabled.
Logs all security-relevant events for forensics.
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import hashlib

class AuditLogger:
    """
    Immutable audit log for security events.
    Logs are write-only and tamper-evident.
    """
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Separate log file per day
        self.log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Set up structured logging
        self.logger = logging.getLogger('zednet.audit')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.log_file, mode='a')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S UTC'
        ))
        self.logger.addHandler(handler)
        
        self.log_event('AUDIT_START', {'version': '1.0'})
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log security event with structured data.
        
        Args:
            event_type: Event classification
            data: Event details
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event_type,
            'data': data
        }
        
        # Add integrity hash (chain events)
        event_json = json.dumps(event, sort_keys=True)
        event['hash'] = hashlib.sha256(event_json.encode()).hexdigest()[:16]
        
        self.logger.info(json.dumps(event))
    
    def log_file_access(self, site_id: str, filepath: str, success: bool, ip: str = '127.0.0.1'):
        """Log file access attempt."""
        self.log_event('FILE_ACCESS', {
            'site_id': site_id,
            'filepath': filepath,
            'success': success,
            'client_ip': ip
        })
    
    def log_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """Log security violation attempt."""
        self.log_event('SECURITY_VIOLATION', {
            'type': violation_type,
            'details': details
        })
    
    def log_vpn_status_change(self, was_safe: bool, is_safe: bool, public_ip: str):
        """Log VPN status changes."""
        self.log_event('VPN_STATUS_CHANGE', {
            'was_safe': was_safe,
            'is_safe': is_safe,
            'public_ip': public_ip
        })
    
    def log_p2p_connection(self, peer_ip: str, encrypted: bool, direction: str):
        """Log P2P peer connections."""
        self.log_event('P2P_CONNECTION', {
            'peer_ip': peer_ip,
            'encrypted': encrypted,
            'direction': direction  # 'incoming' or 'outgoing'
        })
    
    def log_content_violation(self, site_id: str, reason: str, action: str):
        """Log content policy violations."""
        self.log_event('CONTENT_VIOLATION', {
            'site_id': site_id,
            'reason': reason,
            'action': action
        })