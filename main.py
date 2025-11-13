"""
ZedNet Main Application Entry Point
"""
import sys
import logging
from pathlib import Path
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('data/logs/zednet.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_legal_acceptance():
    """Ensure user has accepted terms."""
    from config import TERMS_ACCEPTED, BASE_DIR
    
    if TERMS_ACCEPTED.exists():
        return True
    
    print("\n" + "="*70)
    print("ZEDNET TERMS OF SERVICE")
    print("="*70)
    
    terms_file = BASE_DIR / 'legal' / 'TERMS_OF_SERVICE.md'
    if terms_file.exists():
        print(terms_file.read_text())
    else:
        print("WARNING: Terms file not found!")
    
    print("\n" + "="*70)
    response = input("Do you accept these terms? (yes/no): ").strip().lower()
    
    if response == 'yes':
        TERMS_ACCEPTED.write_text("accepted")
        return True
    else:
        print("You must accept the terms to use ZedNet.")
        return False


def main():
    """Main application entry point."""
    logger.info("="*70)
    logger.info("ZedNet Starting")
    logger.info("="*70)
    
    # Check legal acceptance
    if not check_legal_acceptance():
        sys.exit(1)
    
    # Import after logging is configured
    from config import (
        CONTENT_DIR, LOGS_DIR, LOCAL_HOST, LOCAL_PORT,
        ENABLE_KILL_SWITCH, REQUIRE_VPN_CHECK
    )
    from core.audit_log import AuditLogger
    from core.killswitch import KillSwitch
    from core.vpn_check import VPNChecker
    from core.p2p_engine import P2PEngine
    from server.local_server import initialize_server, run_server
    
    # Initialize audit logger
    audit_logger = AuditLogger(LOGS_DIR)
    logger.info("Audit logging initialized")
    
    # Check VPN status
    if REQUIRE_VPN_CHECK:
        logger.info("Checking VPN status...")
        vpn_status = VPNChecker.check_vpn_status()
        logger.info("VPN Check: %s", vpn_status)
        
        if not vpn_status['appears_safe']:
            logger.warning("⚠️  WARNING: %s", vpn_status['warning'])
            logger.warning("⚠️  It is STRONGLY RECOMMENDED to use a VPN or Tor")
            response = input("Continue without VPN? (yes/no): ").strip().lower()
            if response != 'yes':
                logger.info("Exiting for VPN setup")
                sys.exit(0)
    
    # Initialize P2P engine
    logger.info("Initializing P2P engine...")
    p2p_engine = P2PEngine(CONTENT_DIR)
    
    def emergency_shutdown():
        """Emergency shutdown callback."""
        logger.critical("EMERGENCY SHUTDOWN TRIGGERED")
        logger.critical("Stopping all network activity...")
        p2p_engine.shutdown()
        logger.critical("Network activity stopped. Restart with VPN to continue.")
    
    if not p2p_engine.initialize(force_encryption=True):
        logger.error("Failed to initialize P2P engine")
        sys.exit(1)
    
    # Start kill switch
    if ENABLE_KILL_SWITCH:
        logger.info("Starting VPN kill switch...")
        kill_switch = KillSwitch(check_interval=30, audit_logger=audit_logger)
        kill_switch.start(emergency_shutdown)
    
    # Initialize and start web server
    logger.info("Starting local web server on %s:%d", LOCAL_HOST, LOCAL_PORT)
    initialize_server(audit_logger, CONTENT_DIR)
    
    server_thread = threading.Thread(
        target=run_server,
        args=(LOCAL_HOST, LOCAL_PORT),
        daemon=True
    )
    server_thread.start()
    
    logger.info("="*70)
    logger.info("ZedNet is running")
    logger.info("Local server: http://%s:%d", LOCAL_HOST, LOCAL_PORT)
    logger.info("Press Ctrl+C to stop")
    logger.info("="*70)
    
    try:
        # Keep main thread alive
        server_thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        p2p_engine.shutdown()
        if ENABLE_KILL_SWITCH:
            kill_switch.stop()
        logger.info("Goodbye")


if __name__ == '__main__':
    main()