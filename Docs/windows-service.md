# Windows Service Deployment Guide

This guide explains how to deploy the SCIM connector as a Windows Service for production use.

## Option 1: NSSM (Non-Sucking Service Manager) - Recommended

NSSM is the easiest way to run Python applications as Windows Services.

### Installation Steps

#### 1. Download NSSM

```powershell
# Download from https://nssm.cc/download
# Or use Chocolatey
choco install nssm
```

#### 2. Create Service

```powershell
# Run as Administrator
# Navigate to NSSM directory
cd C:\nssm-2.24\win64

# Install service
.\nssm.exe install OktaSCIMConnector "C:\okta-scim-sql-connector\venv\Scripts\python.exe" "C:\okta-scim-sql-connector\inbound_app.py"

# Set working directory
.\nssm.exe set OktaSCIMConnector AppDirectory "C:\okta-scim-sql-connector"

# Set startup type to automatic
.\nssm.exe set OktaSCIMConnector Start SERVICE_AUTO_START

# Set restart behavior
.\nssm.exe set OktaSCIMConnector AppExit Default Restart
.\nssm.exe set OktaSCIMConnector AppRestartDelay 5000

# Configure stdout/stderr logging
.\nssm.exe set OktaSCIMConnector AppStdout "C:\okta-scim-sql-connector\logs\service-output.log"
.\nssm.exe set OktaSCIMConnector AppStderr "C:\okta-scim-sql-connector\logs\service-error.log"

# Set service to run as specific user (if needed)
.\nssm.exe set OktaSCIMConnector ObjectName "DOMAIN\ServiceAccount" "ServicePassword"
```

#### 3. Start Service

```powershell
# Start the service
Start-Service OktaSCIMConnector

# Check service status
Get-Service OktaSCIMConnector

# View logs
Get-Content C:\okta-scim-sql-connector\logs\service-output.log -Tail 50
```

#### 4. Configure Firewall

```powershell
# Allow inbound connections on port 443
New-NetFirewallRule -DisplayName "Okta SCIM Connector" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

### Service Management

```powershell
# Start service
Start-Service OktaSCIMConnector

# Stop service
Stop-Service OktaSCIMConnector

# Restart service
Restart-Service OktaSCIMConnector

# Remove service (if needed)
.\nssm.exe remove OktaSCIMConnector confirm
```

---

## Option 2: Python Service (win32serviceutil)

For environments where you can't use NSSM, use native Windows Service.

### Installation Steps

#### 1. Install Dependencies

```powershell
pip install pywin32
```

#### 2. Create Service Wrapper

Create `service_wrapper.py`:

```python
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
from pathlib import Path

# Add project directory to path
sys.path.insert(0, str(Path(__file__).parent))

class OktaSCIMService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OktaSCIMConnector"
    _svc_display_name_ = "Okta SCIM SQL Connector"
    _svc_description_ = "SCIM 1.1 server for importing SQL users into Okta"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
        
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
        
    def main(self):
        # Import and run Flask app
        from inbound_app import app, SERVER_HOST, SERVER_PORT
        
        try:
            app.run(
                host=SERVER_HOST,
                port=SERVER_PORT,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(OktaSCIMService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(OktaSCIMService)
```

#### 3. Install Service

```powershell
# Install service
python service_wrapper.py install

# Set to auto-start
python service_wrapper.py --startup auto install

# Start service
python service_wrapper.py start
```

#### 4. Manage Service

```powershell
# Check status
python service_wrapper.py status

# Stop service
python service_wrapper.py stop

# Remove service
python service_wrapper.py remove
```

---

## Option 3: Task Scheduler

Simplest option for testing or non-critical deployments.

### Setup Steps

#### 1. Create Batch Script

Create `start_scim_server.bat`:

```batch
@echo off
cd /d C:\okta-scim-sql-connector
call venv\Scripts\activate.bat
python inbound_app.py >> logs\scim_server.log 2>&1
```

#### 2. Create Scheduled Task

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "C:\okta-scim-sql-connector\start_scim_server.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 3

Register-ScheduledTask -TaskName "OktaSCIMConnector" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Okta SCIM SQL Connector"
```

#### 3. Manage Task

```powershell
# Start task
Start-ScheduledTask -TaskName "OktaSCIMConnector"

# Stop task
Stop-ScheduledTask -TaskName "OktaSCIMConnector"

# Check status
Get-ScheduledTask -TaskName "OktaSCIMConnector" | Get-ScheduledTaskInfo
```

---

## Production Checklist

### Pre-Deployment

- [ ] Python 3.7+ installed
- [ ] SQL Server connection tested
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with production values
- [ ] Strong SCIM credentials set
- [ ] SSL certificate obtained (if using HTTPS)
- [ ] Firewall rules configured
- [ ] Service account created with minimal permissions
- [ ] Logs directory created
- [ ] Health check endpoint tested

### Security Hardening

- [ ] Use read-only SQL Server account
- [ ] Enable SQL Server connection encryption
- [ ] Use HTTPS instead of HTTP
- [ ] Restrict network access to OPP Agent IP only
- [ ] Rotate SCIM credentials regularly
- [ ] Enable Windows Event Log auditing
- [ ] Set restrictive file permissions on `.env`
- [ ] Disable debug mode in production
- [ ] Configure log rotation

### Monitoring

- [ ] Service monitoring configured
- [ ] Health check endpoint monitored
- [ ] Database connection monitoring
- [ ] Log file size monitoring
- [ ] Disk space monitoring
- [ ] CPU/memory usage monitoring
- [ ] Network connectivity monitoring
- [ ] Alert thresholds configured

### Backup

- [ ] Configuration files backed up
- [ ] SSL certificates backed up
- [ ] Deployment scripts backed up
- [ ] Recovery procedure documented

---

## Monitoring and Logging

### Application Logs

```powershell
# View real-time logs
Get-Content C:\okta-scim-sql-connector\logs\service-output.log -Wait -Tail 50

# Search for errors
Select-String -Path "C:\okta-scim-sql-connector\logs\*.log" -Pattern "error|exception" -CaseSensitive:$false
```

### Windows Event Logs

```powershell
# View service events
Get-EventLog -LogName Application -Source "OktaSCIMConnector" -Newest 50

# Filter errors only
Get-EventLog -LogName Application -Source "OktaSCIMConnector" -EntryType Error -Newest 20
```

### Health Monitoring Script

Create `monitor_health.ps1`:

```powershell
$uri = "http://localhost:443/health"
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("okta_import:YourPassword"))
$headers = @{ "Authorization" = "Basic $creds" }

try {
    $response = Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 10
    if ($response.status -eq "healthy") {
        Write-Host "✅ SCIM Server is healthy"
        exit 0
    } else {
        Write-Host "⚠️ SCIM Server is unhealthy: $($response.error)"
        exit 1
    }
} catch {
    Write-Host "❌ SCIM Server is not responding: $_"
    exit 2
}
```

Schedule this script to run every 5 minutes.

---

## SSL/TLS Configuration

### Generate Self-Signed Certificate

```powershell
# Generate certificate
$cert = New-SelfSignedCertificate -DnsName "scim.yourdomain.com" -CertStoreLocation Cert:\LocalMachine\My -NotAfter (Get-Date).AddYears(2)

# Export certificate
$pwd = ConvertTo-SecureString -String "YourCertPassword" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "C:\okta-scim-sql-connector\cert.pfx" -Password $pwd

# Extract certificate and key
# Use OpenSSL or certutil to extract .pem files
```

### Configure Flask with SSL

Update `inbound_app.py`:

```python
if __name__ == '__main__':
    # SSL Configuration
    ssl_cert = os.getenv('SSL_CERT_PATH', 'cert.pem')
    ssl_key = os.getenv('SSL_KEY_PATH', 'key.pem')
    
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        app.run(
            host=SERVER_HOST,
            port=SERVER_PORT,
            ssl_context=(ssl_cert, ssl_key),
            debug=False
        )
    else:
        app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
```

---

## Performance Tuning

### Optimize Database Queries

```sql
-- Add indexes for better performance
CREATE INDEX idx_users_id ON users(id);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Update statistics
UPDATE STATISTICS users;
```

### Configure Connection Pooling

Already configured in pyodbc connection string.

### Adjust Pagination

```python
# In get_users() function - increase default page size
count = int(request.args.get('count', 200))  # Default 200 users per page
```

---

## Disaster Recovery

### Backup Configuration

```powershell
# Backup script
$backupPath = "C:\Backups\OktaSCIM\$(Get-Date -Format 'yyyy-MM-dd')"
New-Item -ItemType Directory -Path $backupPath -Force

Copy-Item "C:\okta-scim-sql-connector\.env" -Destination $backupPath
Copy-Item "C:\okta-scim-sql-connector\inbound_app.py" -Destination $backupPath
Copy-Item "C:\okta-scim-sql-connector\requirements.txt" -Destination $backupPath
```

### Recovery Procedure

1. Stop service: `Stop-Service OktaSCIMConnector`
2. Restore files from backup
3. Verify configuration: `python test_db_connection.py`
4. Start service: `Start-Service OktaSCIMConnector`
5. Test health check: `curl http://localhost:443/health`
6. Verify OPP Agent connectivity

---

## Troubleshooting Service Issues

```powershell
# Check if service is running
Get-Service OktaSCIMConnector

# Check service logs (NSSM)
Get-Content C:\okta-scim-sql-connector\logs\service-output.log -Tail 100

# Check Windows Event Log
Get-EventLog -LogName Application -Source OktaSCIMConnector -Newest 20

# Test port availability
Test-NetConnection -ComputerName localhost -Port 443

# Check if port is in use
netstat -an | findstr :443

# Restart service
Restart-Service OktaSCIMConnector

# Force kill if not responding
Get-Process | Where-Object {$_.Path -like "*okta-scim*"} | Stop-Process -Force
```
