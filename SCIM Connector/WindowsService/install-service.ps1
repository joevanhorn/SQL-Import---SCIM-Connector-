# Okta SCIM Connector - Windows Service Installation Script
# Must be run as Administrator

<#
.SYNOPSIS
    Installs and configures the Okta SCIM SQL Connector as a Windows Service

.DESCRIPTION
    This script installs the SCIM connector as a Windows Service, configures it,
    and optionally starts it. Supports both SCIM 1.1 and SCIM 2.0 versions.

.PARAMETER ScimVersion
    SCIM version to use: "1.1" (default) or "2.0"

.PARAMETER AutoStart
    Automatically start the service after installation

.PARAMETER Uninstall
    Uninstall the service instead of installing

.EXAMPLE
    .\install_service.ps1
    # Installs SCIM 1.1 service

.EXAMPLE
    .\install_service.ps1 -ScimVersion "2.0" -AutoStart
    # Installs SCIM 2.0 service and starts it

.EXAMPLE
    .\install_service.ps1 -Uninstall
    # Uninstalls the service
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("1.1", "2.0")]
    [string]$ScimVersion = "1.1",
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoStart = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Uninstall = $false
)

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Error "This script must be run as Administrator!"
    Write-Host "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

# Service configuration
$ServiceName = "OktaSCIMConnector"
$ServiceDisplayName = "Okta SCIM SQL Connector"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Okta SCIM Connector Service Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Uninstall mode
if ($Uninstall) {
    Write-Host "Uninstalling service..." -ForegroundColor Yellow
    
    # Check if service exists
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    
    if ($service) {
        # Stop service if running
        if ($service.Status -eq 'Running') {
            Write-Host "Stopping service..." -ForegroundColor Yellow
            Stop-Service -Name $ServiceName -Force
            Start-Sleep -Seconds 2
        }
        
        # Remove service
        Write-Host "Removing service..." -ForegroundColor Yellow
        & python "$ScriptDir\service_wrapper.py" remove
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Service uninstalled successfully!" -ForegroundColor Green
        } else {
            Write-Error "Failed to uninstall service"
            exit 1
        }
    } else {
        Write-Host "Service is not installed" -ForegroundColor Yellow
    }
    
    exit 0
}

# Install mode
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  SCIM Version: $ScimVersion"
Write-Host "  Script Directory: $ScriptDir"
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python is not installed or not in PATH"
    exit 1
}

# Check if virtual environment exists
$venvPath = Join-Path $ScriptDir "venv"
if (-not (Test-Path $venvPath)) {
    Write-Warning "Virtual environment not found at $venvPath"
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# Activate virtual environment and install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
& $activateScript

# Ensure pywin32 is installed
Write-Host "Installing pywin32..." -ForegroundColor Yellow
pip install pywin32 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install pywin32"
    exit 1
}

# Install other requirements
$requirementsFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $requirementsFile) {
    Write-Host "Installing requirements..." -ForegroundColor Yellow
    pip install -r $requirementsFile | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install requirements"
        exit 1
    }
}

Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Check if .env file exists
$envFile = Join-Path $ScriptDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Warning ".env file not found!"
    Write-Host "Please create a .env file with your configuration before starting the service"
    Write-Host "You can copy .env.example to .env and update the values"
}

# Set SCIM version environment variable
$env:SCIM_VERSION = $ScimVersion
[System.Environment]::SetEnvironmentVariable("SCIM_VERSION", $ScimVersion, "Machine")

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($existingService) {
    Write-Host "Service already exists. Removing old installation..." -ForegroundColor Yellow
    
    if ($existingService.Status -eq 'Running') {
        Stop-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 2
    }
    
    & python "$ScriptDir\service_wrapper.py" remove
    Start-Sleep -Seconds 2
}

# Install service
Write-Host "Installing Windows Service..." -ForegroundColor Cyan
& python "$ScriptDir\service_wrapper.py" install

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install service"
    exit 1
}

Write-Host "✓ Service installed successfully!" -ForegroundColor Green

# Configure service for automatic startup
Write-Host "Configuring service..." -ForegroundColor Cyan
Set-Service -Name $ServiceName -StartupType Automatic

# Set service description
$service = Get-WmiObject -Class Win32_Service -Filter "Name='$ServiceName'"
$service.Change($null, $null, $null, $null, $null, $null, $null, $null, $null, $null, "SCIM server for importing users from SQL Server to Okta (Version: SCIM $ScimVersion)")

Write-Host "✓ Service configured" -ForegroundColor Green

# Start service if requested
if ($AutoStart) {
    Write-Host "Starting service..." -ForegroundColor Cyan
    Start-Service -Name $ServiceName
    
    Start-Sleep -Seconds 3
    
    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq 'Running') {
        Write-Host "✓ Service started successfully!" -ForegroundColor Green
    } else {
        Write-Warning "Service failed to start. Check logs for details."
        Write-Host "Log location: $ScriptDir\logs\service.log"
    }
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Name: $ServiceName" -ForegroundColor White
Write-Host "SCIM Version: $ScimVersion" -ForegroundColor White
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  Start:   Start-Service $ServiceName"
Write-Host "  Stop:    Stop-Service $ServiceName"
Write-Host "  Status:  Get-Service $ServiceName"
Write-Host "  Logs:    Get-Content logs\service.log -Tail 50"
Write-Host ""

if (-not $AutoStart) {
    Write-Host "To start the service, run:" -ForegroundColor Yellow
    Write-Host "  Start-Service $ServiceName" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "To uninstall the service, run:" -ForegroundColor Yellow
Write-Host "  .\install_service.ps1 -Uninstall" -ForegroundColor Yellow
Write-Host ""
