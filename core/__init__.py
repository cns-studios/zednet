"""
ZedNet Core Package

Security-critical components for cryptography, P2P networking,
and content management.
"""

__version__ = "0.1.0-alpha"
__author__ = "ZedNet Contributors"

# Import main classes for easier access
from .security import SecurityManager
from .publisher import SitePublisher
from .downloader import SiteDownloader
from .storage import SiteStorage
from .vpn_check import VPNChecker
from .killswitch import KillSwitch
from .audit_log import AuditLogger
from .content_scanner import ContentScanner, ContentReporter
from .app_controller import AppController

__all__ = [
    # Security
    'SecurityManager',
    
    # P2P
    'SitePublisher',
    'SiteDownloader',
    
    # Storage
    'SiteStorage',
    
    # Network Security
    'VPNChecker',
    'KillSwitch',
    
    # Monitoring
    'AuditLogger',
    'ContentScanner',
    'ContentReporter',
    
    # Main Controller
    'AppController',
]