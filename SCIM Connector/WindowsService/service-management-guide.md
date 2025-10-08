# Windows Service Management Guide

Complete guide for installing, configuring, and managing the Okta SCIM Connector as a Windows Service.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Service Management](#service-management)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

---

## Prerequisites

### Required
- Windows Server 2016+ or Windows 10+
- Python 3.7 or higher
- Administrator privileges
- SQL Server connectivity
- `.env` file configured (copy from `.env.example`)

### Optional
- Okta OPP Agent installed (for production use)

---

## Installation

### Option 1: Automated Installation (Recommended)

**SCIM 1.1 (Standard - Works with all Okta tenants)**
```powershell
# Run PowerShell as Administrator
.\install_service.ps1 -AutoStart
```

**SCIM 2.0 (Requires Okta Feature Flag)**
```powershell
# Run PowerShell as Administrator
.\install_service.ps1 -ScimVersion "2.0" -AutoStart
```

### Option 2: Manual Installation

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set SCIM version (optional, defaults to 1.1)
$env:SCIM_VERSION = "1.1"  # or "2.0"

# 3. Install service
python service_wrapper.py install

# 4. Start service
Start-Service OktaSCIMConnector
```

---

## Service Management

### Start the Service
```powershell
Start-Service OktaSCIMConnector
```

### Stop the Service
```powershell
Stop-Service OktaSCIMConnector
```

### Restart the Service
```powershell
Restart-Service OktaSCIMConnector
```

### Check Service Status
```powershell
Get-Service OktaSCIMConnector

# Detailed status
Get-Service OktaSCIMConnector | Format-List *
```

### Configure Startup Type
```powershell
# Automatic (starts on boot)
Set-Service OktaSCIMConnector -StartupType Automatic

# Manual (must be started manually)
Set-Service OktaSCIMConnector -StartupType Manual

# Disabled
Set-Service OktaSCIMConnector -StartupType Disabled
```

---

## Monitoring

### View Service Logs
```powershell
# View last 50 lines
Get-Content logs\service.log -Tail 50

# View last 50 lines and follow new entries
Get-Content logs\service.log -Tail 50 -Wait

# View all logs
Get-Content logs\service.log
```

### Check Service Health
```powershell
# Test SCIM endpoint
Invoke-WebRequest -Uri "http://localhost:8080/scim/v1/Users" -Headers @{Authorization="Basic <your-base64-token>"}

# Or use the monitoring script
.\scripts\monitor_health.ps1
```

### Windows Event Viewer
1. Open Event Viewer (`eventvwr.msc`)
2. Navigate to: **Windows Logs → Application**
3. Filter by Source: **OktaSCIMConnector**

---

## Switching SCIM Versions

To switch between SCIM 1.1 and 2.0:

```powershell
# 1. Stop the service
Stop-Service OktaSCIMConnector

# 2. Uninstall
.\install_service.ps1 -Uninstall

# 3. Reinstall with new version
.\install_service.ps1 -ScimVersion "2.0" -AutoStart
```

Or manually:
```powershell
# Set environment variable (system-wide)
[System.Environment]::SetEnvironmentVariable("SCIM_VERSION", "2.0", "Machine")

# Restart service
Restart-Service OktaSCIMConnector
```

---

## Troubleshooting

### Service Won't Start

**Check Python Installation**
```powershell
python --version
# Should show Python 3.7+
```

**Check Dependencies**
```powershell
pip list | Select-String "pywin32|Flask|pyodbc"
```

**Check Configuration**
```powershell
# Verify .env file exists
Test-Path .env

# View .env contents (careful - contains passwords!)
Get-Content .env
```

**Check Logs**
```powershell
Get-Content logs\service.log -Tail 100
```

### Service Starts but Crashes

**Check Database Connection**
```powershell
python test_db_connection.py
```

**Check Port Availability**
```powershell
# Check if port 8080 or 443 is in use
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 443 -ErrorAction SilentlyContinue
```

**Verify SCIM Script Exists**
```powershell
# For SCIM 1.1
Test-Path inbound_app.py

# For SCIM 2.0
Test-Path scim2_app.py
```

### Permission Errors

**Firewall Issues**
```powershell
# Add firewall rule for port 8080
New-NetFirewallRule -DisplayName "Okta SCIM Connector" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow

# For port 443 (HTTPS)
New-NetFirewallRule -DisplayName "Okta SCIM Connector HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
```

**Service Account Permissions**
The service runs under the Local System account by default. To use a different account:

```powershell
$cred = Get-Credential
Set-Service OktaSCIMConnector -Credential $cred
```

### Common Errors

| Error | Solution |
|-------|----------|
| `pywin32 not found` | Install: `pip install pywin32` |
| `.env file not found` | Copy `.env.example` to `.env` and configure |
| `SQL Server connection failed` | Check connection string in `.env` |
| `Port already in use` | Change `PORT` in `.env` or stop conflicting service |
| `Service fails to start` | Check `logs\service.log` for details |

---

## Uninstallation

### Using Install Script (Recommended)
```powershell
.\install_service.ps1 -Uninstall
```

### Manual Uninstallation
```powershell
# 1. Stop service
Stop-Service OktaSCIMConnector

# 2. Remove service
python service_wrapper.py remove

# 3. Clean up environment variable (optional)
[System.Environment]::SetEnvironmentVariable("SCIM_VERSION", $null, "Machine")
```

### Complete Cleanup
```powershell
# Remove service
.\install_service.ps1 -Uninstall

# Remove logs (optional)
Remove-Item logs\*.log

# Remove virtual environment (optional)
Remove-Item venv -Recurse -Force
```

---

## Advanced Configuration

### Running on Port 443 (HTTPS)

⚠️ **Important**: Port 443 requires Administrator privileges

1. Update `.env`:
   ```
   PORT=443
   ```

2. Restart service:
   ```powershell
   Restart-Service OktaSCIMConnector
   ```

### Service Recovery Options

Configure automatic restart on failure:

```powershell
sc.exe failure OktaSCIMConnector reset= 86400 actions= restart/60000/restart/60000/restart/60000

# Explanation:
# - reset=86400: Reset failure count after 24 hours
# - restart/60000: Restart after 60 seconds (can specify 3 times)
```

### Scheduled Service Restarts

To restart the service daily at 3 AM:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-Command Restart-Service OktaSCIMConnector"
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
Register-ScheduledTask -TaskName "Restart SCIM Service" -Action $action -Trigger $trigger -RunLevel Highest
```

---

## Best Practices

### Production Deployment

1. ✅ **Use SCIM 1.1** unless you have confirmed SCIM 2.0 feature flag is enabled
2. ✅ **Configure automatic startup** (`Set-Service -StartupType Automatic`)
3. ✅ **Enable failure recovery** (restart on failure)
4. ✅ **Monitor logs regularly** (set up log rotation if needed)
5. ✅ **Test database connectivity** before starting service
6. ✅ **Configure firewall rules** for required ports
7. ✅ **Backup .env file** securely (contains credentials)
8. ✅ **Document your configuration** (SQL tables, column mappings, etc.)

### Security

1. 🔒 **Secure .env file** - Restrict permissions to Administrators only
2. 🔒 **Use strong SCIM credentials** - Generate random passwords for SCIM_USERNAME/PASSWORD
3. 🔒 **Enable SSL/TLS** if exposing externally (use reverse proxy)
4. 🔒 **Rotate credentials regularly** - Update SCIM and database passwords periodically
5. 🔒 **Monitor access logs** - Review `logs/service.log` for unauthorized access attempts

### Monitoring

1. 📊 **Set up alerts** for service failures
2. 📊 **Monitor resource usage** (CPU, memory, disk)
3. 📊 **Track import statistics** (users synced, errors)
4. 📊 **Regular health checks** using `monitor_health.ps1`

---

## Quick Reference

### One-Liners

```powershell
# Install and start SCIM 1.1
.\install_service.ps1 -AutoStart

# Install and start SCIM 2.0
.\install_service.ps1 -ScimVersion "2.0" -AutoStart

# Check service status
Get-Service OktaSCIMConnector | Select-Object Name, Status, StartType

# View recent logs
Get-Content logs\service.log -Tail 50

# Restart service
Restart-Service OktaSCIMConnector

# Uninstall
.\install_service.ps1 -Uninstall

# Test endpoint
Invoke-WebRequest -Uri "http://localhost:8080/health"
```

---

## Need Help?

- **Logs**: Check `logs\service.log` for detailed error messages
- **Event Viewer**: Windows Logs → Application → Source: OktaSCIMConnector
- **Configuration**: Review `.env` file for correct settings
- **Documentation**: See README.md and docs/ folder
- **Support**: Contact your Okta Solutions Engineer

---

## Changelog

- **v1.0** - Initial Windows Service support
- **v1.1** - Added SCIM 2.0 version support
- **v1.2** - Added automated installation script
