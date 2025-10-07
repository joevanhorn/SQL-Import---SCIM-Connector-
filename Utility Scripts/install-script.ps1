# Okta SCIM SQL Connector - Automated Installation Script
# Run this script as Administrator for best results

param(
    [switch]$SkipPythonCheck = $false,
    [switch]$SkipDatabaseTest = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Okta SCIM SQL Connector - Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   Some features (like port 443) may not work" -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Check Python Installation
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Green

if (-not $SkipPythonCheck) {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            
            if ($major -ge 3 -and $minor -ge 7) {
                Write-Host "   ✅ Python $($matches[0]) detected" -ForegroundColor Green
            } else {
                Write-Host "   ❌ Python 3.7+ required. Found: $($matches[0])" -ForegroundColor Red
                Write-Host "   Please install Python 3.7 or higher from python.org" -ForegroundColor Red
                exit 1
            }
        }
    } catch {
        Write-Host "   ❌ Python not found" -ForegroundColor Red
        Write-Host "   Please install Python 3.7+ from https://www.python.org/downloads/" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   ⏭️  Skipped Python check" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Create Virtual Environment
Write-Host "[2/6] Creating virtual environment..." -ForegroundColor Green

if (Test-Path "venv") {
    Write-Host "   ⚠️  Virtual environment already exists" -ForegroundColor Yellow
    $response = Read-Host "   Delete and recreate? (y/n)"
    if ($response -eq 'y') {
        Remove-Item -Recurse -Force "venv"
        python -m venv venv
        Write-Host "   ✅ Virtual environment recreated" -ForegroundColor Green
    } else {
        Write-Host "   ⏭️  Using existing virtual environment" -ForegroundColor Yellow
    }
} else {
    python -m venv venv
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
}

Write-Host ""

# Step 3: Install Dependencies
Write-Host "[3/6] Installing dependencies..." -ForegroundColor Green

& "venv\Scripts\pip.exe" install -r requirements.txt --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Create Configuration File
Write-Host "[4/6] Creating configuration file..." -ForegroundColor Green

if (Test-Path ".env") {
    Write-Host "   ⚠️  .env file already exists" -ForegroundColor Yellow
    Write-Host "   ⏭️  Skipping to avoid overwriting configuration" -ForegroundColor Yellow
} else {
    Copy-Item ".env.example" ".env"
    Write-Host "   ✅ Created .env from template" -ForegroundColor Green
    Write-Host ""
    Write-Host "   ⚠️  IMPORTANT: Edit .env file with your configuration:" -ForegroundColor Yellow
    Write-Host "      - Database connection details" -ForegroundColor White
    Write-Host "      - Column mappings" -ForegroundColor White
    Write-Host "      - SCIM credentials" -ForegroundColor White
    Write-Host ""
}

Write-Host ""

# Step 5: Create Logs Directory
Write-Host "[5/6] Creating logs directory..." -ForegroundColor Green

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Host "   ✅ Logs directory created" -ForegroundColor Green
} else {
    Write-Host "   ⏭️  Logs directory already exists" -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Test Database Connection (Optional)
Write-Host "[6/6] Testing database connection..." -ForegroundColor Green

if ($SkipDatabaseTest) {
    Write-Host "   ⏭️  Skipped database test" -ForegroundColor Yellow
} else {
    if (Test-Path ".env") {
        Write-Host "   Testing connection..." -ForegroundColor White
        
        $testResult = & "venv\Scripts\python.exe" test_db_connection.py 2>&1
        
        if ($testResult -match "✅") {
            Write-Host "   ✅ Database connection successful" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Database connection test failed" -ForegroundColor Yellow
            Write-Host "   This is normal if you haven't configured .env yet" -ForegroundColor White
            Write-Host ""
            Write-Host "   To test later, run:" -ForegroundColor White
            Write-Host "   python test_db_connection.py" -ForegroundColor Cyan
        }
    } else {
        Write-Host "   ⏭️  Skipped (no .env file)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Next Steps
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Configure your database connection:" -ForegroundColor White
Write-Host "   notepad .env" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Test database connection:" -ForegroundColor White
Write-Host "   venv\Scripts\activate" -ForegroundColor Cyan
Write-Host "   python test_db_connection.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Start SCIM server:" -ForegroundColor White
Write-Host "   venv\Scripts\activate" -ForegroundColor Cyan
Write-Host "   python inbound_app.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Configure Okta OPP Agent:" -ForegroundColor White
Write-Host "   SCIM Base URL: http://your-server:8080/scim/v2" -ForegroundColor Cyan
Write-Host "   Authentication: Basic (use credentials from .env)" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   Quick Start: docs\QUICK_START.md" -ForegroundColor White
Write-Host "   Troubleshooting: docs\TROUBLESHOOTING.md" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Useful Commands:" -ForegroundColor Cyan
Write-Host "   Test health check:" -ForegroundColor White
Write-Host "   curl http://localhost:8080/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "   View logs:" -ForegroundColor White
Write-Host "   Get-Content logs\scim_server.log -Tail 50" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator for port 443 reminder
if (-not $isAdmin) {
    Write-Host "⚠️  Reminder: For production (port 443), run as Administrator" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "✅ Ready to go! See docs\QUICK_START.md for detailed instructions." -ForegroundColor Green
Write-Host ""