"""
VPN Kill Switch - Emergency network shutdown.
Monitors VPN status and kills all network activity if VPN drops.
"""
import threading
import time
import logging
from typing import Callable, Optional
from .vpn_check import VPNChecker
from .audit_log import AuditLogger

logger = logging.getLogger(__name__)

class KillSwitch:
    """
    Monitors VPN connection and triggers emergency shutdown.
    """
    
    def __init__(self, check_interval: int = 30, audit_logger: Optional[AuditLogger] = None):
        """
        Args:
            check_interval: Seconds between VPN checks
            audit_logger: Audit logger instance
        """
        self.check_interval = check_interval
        self.audit_logger = audit_logger
        self.is_running = False
        self.is_safe = False
        self.last_known_ip = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.on_emergency_shutdown: Optional[Callable] = None
        self._shutdown_triggered = False
        
    def start(self, on_emergency_shutdown: Callable):
        """
        Start VPN monitoring.
        
        Args:
            on_emergency_shutdown: Callback to execute on VPN loss
        """
        self.on_emergency_shutdown = on_emergency_shutdown
        self.is_running = True
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Kill switch monitoring started (interval: %ds)", self.check_interval)
    
    def stop(self):
        """Stop monitoring."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Kill switch monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            self._check_vpn_status()
            time.sleep(self.check_interval)
    
    def _check_vpn_status(self):
        """Check VPN status and trigger kill switch if needed."""
        try:
            status = VPNChecker.check_vpn_status()
            was_safe = self.is_safe
            self.is_safe = status['appears_safe']
            current_ip = status['public_ip']
            
            # Log status change
            if was_safe != self.is_safe or current_ip != self.last_known_ip:
                logger.warning("VPN status change: %s -> %s (IP: %s)", 
                             was_safe, self.is_safe, current_ip)
                
                if self.audit_logger:
                    self.audit_logger.log_vpn_status_change(
                        was_safe, self.is_safe, current_ip or 'UNKNOWN'
                    )
            
            # Trigger kill switch if VPN appears down
            if not self.is_safe and not self._shutdown_triggered:
                logger.critical("VPN CONNECTION LOST - TRIGGERING EMERGENCY SHUTDOWN")
                self._trigger_emergency_shutdown(status)
            
            self.last_known_ip = current_ip
            
        except Exception as e:
            logger.error("Error checking VPN status: %s", e)
            # Fail-safe: assume unsafe on error
            if self.is_safe:
                logger.critical("VPN check failed - TRIGGERING EMERGENCY SHUTDOWN")
                self._trigger_emergency_shutdown({'error': str(e)})
    
    def _trigger_emergency_shutdown(self, status: dict):
        """Execute emergency shutdown."""
        self._shutdown_triggered = True
        if self.audit_logger:
            self.audit_logger.log_event('EMERGENCY_SHUTDOWN', status)
        
        if self.on_emergency_shutdown:
            try:
                self.on_emergency_shutdown()
            except Exception as e:
                logger.error("Error during emergency shutdown: %s", e)