#!/usr/bin/env python3
"""
Windows Service Wrapper for Okta SCIM SQL Connector
Allows the SCIM server to run as a Windows Service

Installation:
    python service_wrapper.py install

Start Service:
    python service_wrapper.py start

Stop Service:
    python service_wrapper.py stop

Remove Service:
    python service_wrapper.py remove

Note: Must be run as Administrator
"""

import os
import sys
import time
import logging
from pathlib import Path

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    print("Error: pywin32 is required. Install with: pip install pywin32")
    sys.exit(1)

# Service configuration
SERVICE_NAME = "OktaSCIMConnector"
SERVICE_DISPLAY_NAME = "Okta SCIM SQL Connector"
SERVICE_DESCRIPTION = "SCIM server for importing users from SQL Server to Okta"

# Determine which SCIM version to run (default: SCIM 1.1)
SCIM_VERSION = os.getenv('SCIM_VERSION', '1.1')
SCIM_SCRIPT = 'scim2_app.py' if SCIM_VERSION == '2.0' else 'inbound_app.py'


class OktaSCIMService(win32serviceutil.ServiceFramework):
    """Windows Service for Okta SCIM Connector"""
    
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    
    def __init__(self, args):
        """Initialize the service"""
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure service logging"""
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / 'service.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('OktaSCIMService')
    
    def SvcStop(self):
        """Stop the service"""
        self.logger.info('Stopping Okta SCIM Service...')
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
        
    def SvcDoRun(self):
        """Run the service"""
        self.logger.info(f'Starting Okta SCIM Service (Version: SCIM {SCIM_VERSION})...')
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.main()
        except Exception as e:
            self.logger.error(f'Service error: {str(e)}', exc_info=True)
            servicemanager.LogErrorMsg(f'Service failed: {str(e)}')
    
    def main(self):
        """Main service logic"""
        self.logger.info(f'Loading SCIM server from {SCIM_SCRIPT}...')
        
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        scim_script_path = script_dir / SCIM_SCRIPT
        
        if not scim_script_path.exists():
            error_msg = f'SCIM script not found: {scim_script_path}'
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Change to script directory
        os.chdir(script_dir)
        
        # Load environment variables from .env file if it exists
        env_file = script_dir / '.env'
        if env_file.exists():
            self.logger.info('Loading environment variables from .env')
            self.load_env_file(env_file)
        else:
            self.logger.warning('.env file not found, using system environment variables')
        
        # Import and run the SCIM app
        try:
            # Add current directory to Python path
            sys.path.insert(0, str(script_dir))
            
            # Import the appropriate SCIM module
            if SCIM_VERSION == '2.0':
                import scim2_app as scim_app
            else:
                import inbound_app as scim_app
            
            self.logger.info('Starting SCIM server...')
            
            # Run the server in a separate thread so we can monitor the stop event
            import threading
            server_thread = threading.Thread(target=self.run_server, args=(scim_app,))
            server_thread.daemon = True
            server_thread.start()
            
            # Wait for stop signal
            while self.running:
                if win32event.WaitForSingleObject(self.stop_event, 5000) == win32event.WAIT_OBJECT_0:
                    break
            
            self.logger.info('Service stopped')
            
        except ImportError as e:
            error_msg = f'Failed to import SCIM module: {str(e)}'
            self.logger.error(error_msg)
            raise ImportError(error_msg)
        except Exception as e:
            error_msg = f'Error running SCIM server: {str(e)}'
            self.logger.error(error_msg, exc_info=True)
            raise
    
    def run_server(self, scim_app):
        """Run the SCIM server"""
        try:
            # The SCIM app should have a main() or run() function
            if hasattr(scim_app, 'main'):
                scim_app.main()
            elif hasattr(scim_app, 'app'):
                # If it's a Flask app, run it
                port = int(os.getenv('PORT', 8080))
                scim_app.app.run(host='0.0.0.0', port=port)
            else:
                self.logger.error('SCIM module has no main() function or app object')
        except Exception as e:
            self.logger.error(f'Server error: {str(e)}', exc_info=True)
    
    def load_env_file(self, env_file):
        """Load environment variables from .env file"""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
        except Exception as e:
            self.logger.error(f'Error loading .env file: {str(e)}')


def main():
    """Main entry point for service management"""
    if len(sys.argv) == 1:
        # No arguments - running as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(OktaSCIMService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Command line arguments - install/remove/etc
        win32serviceutil.HandleCommandLine(OktaSCIMService)


if __name__ == '__main__':
    main()
