# Okta SCIM SQL Connector - Health Monitoring Script
# Checks the health of the SCIM server and optionally sends alerts

param(
    [string]$ServerUrl = "http://localhost:443",
    [string]$Username = "",
    [string]$Password = "",
    [int]$TimeoutSeconds = 10,
    [switch]$Continuous = $false,
    [int]$IntervalSeconds = 60,
    [string]$LogFile = "logs\health_check.log",
    [switch]$Verbose = $false
)

# Load credentials from .env if not provided
if ([string]::IsNullOrEmpty($Username) -or [string]::IsNullOrEmpty($Password)) {
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^SCIM_USERNAME=(.+)$") {
                $Username = $matches[1]
            }
            if ($_ -match "^SCIM_PASSWORD=(.+)$") {
                $Password = $matches[1]
            }
            if ($_ -match "^SERVER_PORT=(.+)$") {
                $port = $matches[1]
                $ServerUrl = "http://localhost:$port"
            }
        }
    }
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Console output with colors
    switch ($Level) {
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
        "INFO"    { Write-Host $logMessage -ForegroundColor White }
    }
    
    # Write to log file
    if ($LogFile) {
        Add-Content -Path $LogFile -Value $logMessage
    }
}

function Test-SCIMHealth {
    $healthUrl = "$ServerUrl/health"
    
    try {
        # Create basic auth header
        $base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${Username}:${Password}"))
        $headers = @{
            "Authorization" = "Basic $base64Auth"
        }
        
        # Make health check request
        $response = Invoke-RestMethod -Uri $healthUrl -Headers $headers -TimeoutSec $TimeoutSeconds -ErrorAction Stop
        
        # Check response
        if ($response.status -eq "healthy") {
            Write-Log "Health check passed - Server is healthy" -Level "SUCCESS"
            
            if ($Verbose) {
                Write-Log "  Database: $($response.database)" -Level "INFO"
                Write-Log "  Timestamp: $($response.timestamp)" -Level "INFO"
            }
            
            return @{
                Success = $true
                Status = "healthy"
                Message = "Server is healthy"
                Response = $response
            }
        }
        elseif ($response.status -eq "unhealthy") {
            Write-Log "Health check failed - Server is unhealthy" -Level "ERROR"
            Write-Log "  Error: $($response.error)" -Level "ERROR"
            
            return @{
                Success = $false
                Status = "unhealthy"
                Message = $response.error
                Response = $response
            }
        }
        else {
            Write-Log "Health check returned unexpected status: $($response.status)" -Level "WARNING"
            
            return @{
                Success = $false
                Status = "unknown"
                Message = "Unexpected status: $($response.status)"
                Response = $response
            }
        }
    }
    catch [System.Net.WebException] {
        $statusCode = [int]$_.Exception.Response.StatusCode
        
        if ($statusCode -eq 401) {
            Write-Log "Health check failed - Authentication error (401)" -Level "ERROR"
            Write-Log "  Check SCIM_USERNAME and SCIM_PASSWORD in .env" -Level "ERROR"
        }
        else {
            Write-Log "Health check failed - HTTP error: $statusCode" -Level "ERROR"
        }
        
        return @{
            Success = $false
            Status = "error"
            Message = "HTTP error: $statusCode"
            Response = $null
        }
    }
    catch [System.Net.Sockets.SocketException] {
        Write-Log "Health check failed - Cannot connect to server" -Level "ERROR"
        Write-Log "  Check if server is running on $ServerUrl" -Level "ERROR"
        
        return @{
            Success = $false
            Status = "unreachable"
            Message = "Cannot connect to server"
            Response = $null
        }
    }
    catch {
        Write-Log "Health check failed - $($_.Exception.Message)" -Level "ERROR"
        
        if ($Verbose) {
            Write-Log "  Exception Type: $($_.Exception.GetType().FullName)" -Level "ERROR"
            Write-Log "  Stack Trace: $($_.Exception.StackTrace)" -Level "ERROR"
        }
        
        return @{
            Success = $false
            Status = "error"
            Message = $_.Exception.Message
            Response = $null
        }
    }
}

function Test-SCIMEndpoints {
    Write-Log "Testing SCIM endpoints..." -Level "INFO"
    
    # Test users endpoint
    $usersUrl = "$ServerUrl/scim/v2/Users?count=1"
    
    try {
        $base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${Username}:${Password}"))
        $headers = @{
            "Authorization" = "Basic $base64Auth"
        }
        
        $response = Invoke-RestMethod -Uri $usersUrl -Headers $headers -TimeoutSec $TimeoutSeconds -ErrorAction Stop
        
        if ($response.totalResults -ge 0) {
            Write-Log "  Users endpoint working - $($response.totalResults) total users" -Level "SUCCESS"
            return $true
        }
    }
    catch {
        Write-Log "  Users endpoint failed - $($_.Exception.Message)" -Level "ERROR"
        return $false
    }
    
    return $false
}

# Main execution
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SCIM Server Health Monitor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate parameters
if ([string]::IsNullOrEmpty($Username) -or [string]::IsNullOrEmpty($Password)) {
    Write-Host "Error: Missing credentials" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\monitor_health.ps1 -Username <user> -Password <pass>" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or ensure SCIM_USERNAME and SCIM_PASSWORD are set in .env file" -ForegroundColor White
    exit 1
}

Write-Log "Starting health monitoring..." -Level "INFO"
Write-Log "Server URL: $ServerUrl" -Level "INFO"
Write-Log "Username: $Username" -Level "INFO"
Write-Log "Continuous: $Continuous" -Level "INFO"

if ($Continuous) {
    Write-Log "Interval: $IntervalSeconds seconds" -Level "INFO"
}

Write-Host ""

# Main monitoring loop
$consecutiveFailures = 0
$maxConsecutiveFailures = 3

do {
    $result = Test-SCIMHealth
    
    if ($result.Success) {
        $consecutiveFailures = 0
        
        # Optionally test other endpoints
        if ($Verbose) {
            Test-SCIMEndpoints | Out-Null
        }
    }
    else {
        $consecutiveFailures++
        
        if ($consecutiveFailures -ge $maxConsecutiveFailures) {
            Write-Log "ALERT: Server has failed $consecutiveFailures consecutive health checks!" -Level "ERROR"
            
            # Here you could add email/SMS alerting logic
            # Send-MailMessage or Invoke-WebRequest to webhook
        }
    }
    
    # Wait before next check if in continuous mode
    if ($Continuous) {
        Write-Host ""
        Write-Log "Waiting $IntervalSeconds seconds until next check..." -Level "INFO"
        Start-Sleep -Seconds $IntervalSeconds
        Write-Host ""
    }
    
} while ($Continuous)

# Exit with appropriate code
if ($result.Success) {
    Write-Host ""
    Write-Log "Monitoring complete - Server is healthy" -Level "SUCCESS"
    exit 0
}
else {
    Write-Host ""
    Write-Log "Monitoring complete - Server has issues" -Level "ERROR"
    exit 1
}