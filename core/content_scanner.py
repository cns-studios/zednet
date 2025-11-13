"""
Content scanning and violation reporting.
Scans for known malware hashes and provides user reporting mechanism.
"""
import hashlib
from pathlib import Path
from typing import Set, Optional, Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class ContentScanner:
    """
    Scans downloaded content for known threats.
    Uses hash-based detection and file analysis.
    """
    
    def __init__(self, blocklist_file: Path):
        self.blocklist_file = blocklist_file
        self.blocked_hashes: Set[str] = set()
        self.quarantine_dir: Optional[Path] = None
        self._load_blocklist()
    
    def _load_blocklist(self):
        """Load known malware/illegal content hashes."""
        if self.blocklist_file.exists():
            try:
                with open(self.blocklist_file, 'r') as f:
                    data = json.load(f)
                    self.blocked_hashes = set(data.get('blocked_hashes', []))
                logger.info("Loaded %d blocked hashes", len(self.blocked_hashes))
            except Exception as e:
                logger.error("Failed to load blocklist: %s", e)
    
    def _save_blocklist(self):
        """Save blocklist to disk."""
        try:
            with open(self.blocklist_file, 'w') as f:
                json.dump({
                    'blocked_hashes': list(self.blocked_hashes),
                    'version': 1
                }, f)
        except Exception as e:
            logger.error("Failed to save blocklist: %s", e)
    
    def scan_file(self, filepath: Path) -> Dict[str, any]:
        """
        Scan individual file for threats.
        
        Args:
            filepath: Path to file
            
        Returns:
            {
                'safe': bool,
                'hash': str,
                'threat_type': str or None,
                'size': int
            }
        """
        try:
            # Calculate SHA256
            sha256 = hashlib.sha256()
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            file_hash = sha256.hexdigest()
            
            # Check against blocklist
            is_blocked = file_hash in self.blocked_hashes
            
            result = {
                'safe': not is_blocked,
                'hash': file_hash,
                'threat_type': 'BLOCKLISTED' if is_blocked else None,
                'size': filepath.stat().st_size
            }
            
            # Additional heuristics
            if filepath.suffix.lower() in ['.exe', '.dll', '.so', '.dylib']:
                result['warning'] = 'Executable file detected'
            
            return result
            
        except Exception as e:
            logger.error("Error scanning file %s: %s", filepath, e)
            return {
                'safe': False,
                'error': str(e),
                'threat_type': 'SCAN_ERROR'
            }
    
    def scan_directory(self, directory: Path) -> Dict[str, any]:
        """
        Scan entire directory.
        
        Returns:
            {
                'total_files': int,
                'threats_found': int,
                'threats': List[Dict],
                'total_size': int
            }
        """
        threats = []
        total_files = 0
        total_size = 0
        
        for filepath in directory.rglob('*'):
            if filepath.is_file():
                total_files += 1
                result = self.scan_file(filepath)
                total_size += result.get('size', 0)
                
                if not result['safe']:
                    threats.append({
                        'file': str(filepath.relative_to(directory)),
                        'hash': result['hash'],
                        'threat_type': result.get('threat_type'),
                        'size': result.get('size', 0)
                    })
                    logger.warning("Threat detected: %s (%s)", filepath, result['threat_type'])
        
        return {
            'total_files': total_files,
            'threats_found': len(threats),
            'threats': threats,
            'total_size': total_size
        }
    
    def add_to_blocklist(self, file_hash: str, reason: str = "user_report"):
        """Add hash to blocklist."""
        self.blocked_hashes.add(file_hash)
        self._save_blocklist()
        logger.info("Added hash to blocklist: %s (reason: %s)", file_hash[:16], reason)
    
    def quarantine_file(self, filepath: Path, reason: str):
        """Move file to quarantine."""
        if not self.quarantine_dir:
            logger.error("Quarantine directory not set")
            return False
        
        try:
            self.quarantine_dir.mkdir(exist_ok=True, mode=0o700)
            quarantine_path = self.quarantine_dir / f"{hashlib.sha256(str(filepath).encode()).hexdigest()[:16]}_{filepath.name}"
            filepath.rename(quarantine_path)
            logger.warning("Quarantined file: %s -> %s (reason: %s)", filepath, quarantine_path, reason)
            return True
        except Exception as e:
            logger.error("Failed to quarantine file %s: %s", filepath, e)
            return False


class ContentReporter:
    """
    User reporting mechanism for illegal/harmful content.
    """
    
    def __init__(self, reports_file: Path):
        self.reports_file = reports_file
        self.reports: List[Dict] = []
        self._load_reports()
    
    def _load_reports(self):
        """Load existing reports."""
        if self.reports_file.exists():
            try:
                with open(self.reports_file, 'r') as f:
                    self.reports = json.load(f)
            except Exception as e:
                logger.error("Failed to load reports: %s", e)
    
    def _save_reports(self):
        """Save reports to disk."""
        try:
            with open(self.reports_file, 'w') as f:
                json.dump(self.reports, f, indent=2)
        except Exception as e:
            logger.error("Failed to save reports: %s", e)
    
    def submit_report(self, site_id: str, reason: str, details: str = "") -> str:
        """
        Submit content violation report.
        
        Args:
            site_id: ZedNet site ID
            reason: Violation type (e.g., 'malware', 'illegal', 'csam')
            details: Additional details
            
        Returns:
            report_id: Unique report identifier
        """
        import uuid
        from datetime import datetime
        
        report_id = str(uuid.uuid4())
        report = {
            'id': report_id,
            'timestamp': datetime.utcnow().isoformat(),
            'site_id': site_id,
            'reason': reason,
            'details': details,
            'status': 'pending'
        }
        
        self.reports.append(report)
        self._save_reports()
        
        logger.warning("Content report submitted: %s for site %s (reason: %s)", 
                      report_id, site_id, reason)
        
        return report_id
    
    def get_reports_for_site(self, site_id: str) -> List[Dict]:
        """Get all reports for a specific site."""
        return [r for r in self.reports if r['site_id'] == site_id]