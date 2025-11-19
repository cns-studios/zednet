"""
ZedNet Main Application Entry Point (Updated)
"""
import sys
import logging
from pathlib import Path
import threading

# Configure logging
from config import LOGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'zednet.log', encoding='utf-8'),
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
        print(terms_file.read_text(encoding='utf-8'))
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
        DATA_DIR, CONTENT_DIR, LOGS_DIR, LOCAL_HOST, LOCAL_PORT,
        ENABLE_KILL_SWITCH, REQUIRE_VPN_CHECK
    )
    from core.audit_log import AuditLogger
    from core.killswitch import KillSwitch
    from core.vpn_check import VPNChecker
    from core.app_controller import AppController
    from server.local_server import initialize_server, run_server
    
    # Initialize audit logger
    audit_logger = AuditLogger(LOGS_DIR)
    logger.info("Audit logging initialized")
    
    # Check VPN status
    kill_switch_enabled = ENABLE_KILL_SWITCH
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
            else:
                kill_switch_enabled = False
    
    # Initialize application controller
    logger.info("Initializing application controller...")
    controller = AppController(DATA_DIR)
    
    if not controller.initialize():
        logger.error("Failed to initialize application")
        sys.exit(1)
    
    # Emergency shutdown callback
    def emergency_shutdown():
        """Emergency shutdown callback."""
        logger.critical("EMERGENCY SHUTDOWN TRIGGERED")
        logger.critical("Stopping all network activity...")
        controller.shutdown()
        logger.critical("Network activity stopped. Restart with VPN to continue.")
    
    # Start kill switch
    if kill_switch_enabled:
        logger.info("Starting VPN kill switch...")
        kill_switch = KillSwitch(check_interval=30, audit_logger=audit_logger)
        kill_switch.start(emergency_shutdown)
    
    # Initialize and start web server
    logger.info("Starting local web server on %s:%d", LOCAL_HOST, LOCAL_PORT)
    initialize_server(audit_logger, CONTENT_DIR, controller)
    
    server_thread = threading.Thread(
        target=run_server,
        args=(LOCAL_HOST, LOCAL_PORT),
        daemon=True
    )
    server_thread.start()
    
    logger.info("="*70)
    logger.info("ZedNet is running")
    logger.info("Local server: http://%s:%d", LOCAL_HOST, LOCAL_PORT)
    logger.info("="*70)
    
    # Start GUI
    try:
        # Import tkinter here to catch TclError if it occurs
        import tkinter
        from gui.interface import ZedNetGUI
        
        logger.info("Starting GUI...")
        gui = ZedNetGUI(controller)
        gui.run()
        
    except (ImportError, tkinter.TclError) as e:
        logger.warning("GUI not available (%s), running in headless mode.", e)
        logger.info("Press Ctrl+C to stop.")
        
        try:
            # Keep main thread alive
            server_thread.join()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
    
    # Cleanup
    controller.shutdown()
    if ENABLE_KILL_SWITCH:
        kill_switch.stop()
    logger.info("Goodbye")


if __name__ == '__main__':
    main()