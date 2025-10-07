# Quick Start Guide

Get the Okta SCIM SQL Connector running in under 15 minutes.

## Prerequisites

- [ ] Windows Server (or Windows 10/11 for testing)
- [ ] Python 3.7+ installed
- [ ] SQL Server with user data
- [ ] Okta tenant with OPP Agent installed
- [ ] Administrator access

---

## Step 1: Download and Setup (5 minutes)

### Clone Repository

```powershell
# Clone the repository
git clone https://github.com/your-org/okta-scim-sql-connector.git
cd okta-scim-sql-connector
```

### Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Database Connection (3 minutes)

### Create Configuration File

```powershell
# Copy example configuration
Copy-Item .env.example .env

# Edit configuration
notepad .env
```

### Minimum Required Configuration

Update these values in `.env`:

```env
# Database connection
DB_SERVER=your-sql-server.company.com
DB_NAME=YourDatabase
DB_USERNAME=your_username
DB_PASSWORD=your_password

# SQL table name
SQL_TABLE=users

# Column mappings (adjust to match YOUR database)
DB_COLUMN_ID=id
DB_COLUMN_USERNAME=email
DB_COLUMN_EMAIL=email
DB_COLUMN_FIRST_NAME=first_name
DB_COLUMN_LAST_NAME=last_name

# SCIM credentials (use strong password)
SCIM_USERNAME=okta_import
SCIM_PASSWORD=ChangeThisToAStrongPassword123!

# Server settings
SERVER_PORT=8080  # Use 8080 for testing, 443 for production
```

### Verify Your SQL Table

Make sure you know your actual table and column names:

```sql
-- Run this in SQL Server Management Studio
SELECT TOP 5 * FROM users;

-- Get exact column names
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users';
```

---

## Step 3: Test Database Connection (2 minutes)

### Create Test Script

Create `test_db_connection.py`:

```python
import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

print("Testing database connection...")
print(f"Server: {os.getenv('DB_SERVER')}")
print(f"Database: {os.getenv('DB_NAME')}")

conn_str = (
    f"DRIVER={{{os.getenv('DB_DRIVER')}}};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_NAME')};"
    f"UID={os.getenv('DB_USERNAME')};"
    f"PWD={os.getenv('DB_PASSWORD')}"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Test query
    table = os.getenv('SQL_TABLE', 'users')
    cursor.execute(f"SELECT TOP 5 * FROM {table}")
    
    print("\n✅ Database connection successful!")
    print(f"\nFirst 5 rows from '{table}' table:")
    print("-" * 80)
    
    # Get column names
    columns = [column[0] for column in cursor.description]
    print(" | ".join(columns))
    print("-" * 80)
    
    # Print rows
    for row in cursor.fetchall():
        print(" | ".join(str(x) for x in row))
    
    conn.close()
    print("\n✅ Test completed successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting tips:")
    print("1. Check SQL Server allows remote connections")
    print("2. Verify firewall allows port 1433")
    print("3. Confirm SQL Server authentication is enabled")
    print("4. Double-check credentials in .env file")
```

### Run Test

```powershell
python test_db_connection.py
```

**Expected Output:**
```
✅ Database connection successful!

First 5 rows from 'users' table:
--------------------------------------------------------------------------------
id | username | email | first_name | last_name
--------------------------------------------------------------------------------
1 | john.doe@company.com | john.doe@company.com | John | Doe
...
```

---

## Step 4: Start SCIM Server (1 minute)

### Start Server

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\activate

# Start server
python inbound_app.py
```

**Expected Output:**
```
Starting SCIM server on 0.0.0.0:8080
Database: your-sql-server.company.com/YourDatabase
Table: users
Authentication: okta_import
 * Running on http://0.0.0.0:8080
```

### Test Health Endpoint

Open a new PowerShell window:

```powershell
# Test health endpoint
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("okta_import:YourPassword"))
$headers = @{ "Authorization" = "Basic $creds" }

Invoke-RestMethod -Uri "http://localhost:8080/health" -Headers $headers
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-06T12:00:00Z"
}
```

---

## Step 5: Test SCIM Endpoints (2 minutes)

### Test User List

```powershell
# Get first 5 users
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("okta_import:YourPassword"))
$headers = @{ "Authorization" = "Basic $creds" }

$response = Invoke-RestMethod -Uri "http://localhost:8080/scim/v2/Users?count=5" -Headers $headers
$response | ConvertTo-Json -Depth 5
```

**Expected Response:**
```json
{
  "totalResults": 150,
  "startIndex": 1,
  "itemsPerPage": 5,
  "Resources": [
    {
      "id": "1",
      "userName": "john.doe@company.com",
      "name": {
        "givenName": "John",
        "familyName": "Doe"
      },
      "emails": [
        {
          "value": "john.doe@company.com",
          "type": "work",
          "primary": true
        }
      ],
      "active": true
    }
  ]
}
```

### Test Specific User

```powershell
# Get user by ID
$response = Invoke-RestMethod -Uri "http://localhost:8080/scim/v2/Users/1" -Headers $headers
$response | ConvertTo-Json -Depth 5
```

---

## Step 6: Configure Okta OPP Agent (2 minutes)

### Open OPP Agent Configuration

1. Open **Okta On-Premises Provisioning Agent**
2. Click **Settings**
3. Select your provisioning application

### Configure SCIM Connection

| Setting | Value |
|---------|-------|
| **SCIM Base URL** | `http://your-server-ip:8080/scim/v2` |
| **Authentication Type** | Basic Authentication |
| **Username** | `okta_import` (from .env) |
| **Password** | Your SCIM_PASSWORD value |

### Test Connection

1. Click **Test Connection**
2. Should see: "✅ Connection successful"

---

## Step 7: Import Users to Okta (2 minutes)

### Import Users

1. In OPP Agent, click **Import**
2. Select **Import Now**
3. Wait for import to complete
4. Review imported users

### Verify in Okta Admin Console

1. Go to **Directory → People**
2. Filter by your import source
3. Verify users are imported correctly

---

## Troubleshooting Common Issues

### Issue: "Connection refused" in OPP Agent

**Solution:**
```powershell
# Check if server is running
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Check if port is listening
netstat -an | findstr :8080

# Restart server if needed
python inbound_app.py
```

### Issue: "Schema mismatch" error

**Solution:**  
Make sure you're using the latest version of `inbound_app.py` which uses SCIM 1.1 format (no schemas arrays).

### Issue: No users returned

**Solution:**
```powershell
# Verify column mappings in .env match your database
# Run test to see actual column names
python test_db_connection.py
```

### Issue: Database connection fails

**Solution:**
```powershell
# Test SQL Server connectivity
Test-NetConnection -ComputerName your-sql-server -Port 1433

# Check firewall rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*SQL*"}

# Verify SQL Server authentication is enabled
```

---

## Next Steps

Now that you have the connector running:

### For Testing

1. Keep server running in PowerShell window
2. Test with small user imports first
3. Monitor logs for any errors
4. Verify user data mapping is correct

### For Production

1. **Run on port 443**: Update `.env` to `SERVER_PORT=443`
2. **Run as Administrator**: Required for port 443
3. **Deploy as Windows Service**: See `docs/deployment/windows-service.md`
4. **Enable SSL**: See `docs/deployment/ssl-setup.md`
5. **Configure monitoring**: Set up health check monitoring
6. **Secure credentials**: Use strong passwords, rotate regularly

### Additional Documentation

- 📖 **Full README**: `README.md`
- 🔧 **Troubleshooting**: `docs/troubleshooting.md`
- 🚀 **Deployment Guide**: `docs/deployment/windows-service.md`
- 📝 **Schema Examples**: `docs/examples/`

---

## Support

If you encounter issues:

1. Check `docs/troubleshooting.md`
2. Review OPP Agent logs
3. Enable debug mode in `inbound_app.py`
4. Open a GitHub issue with logs (redact credentials)

---

## Summary Checklist

- ✅ Python virtual environment created
- ✅ Dependencies installed
- ✅ `.env` file configured
- ✅ Database connection tested
- ✅ SCIM server started
- ✅ Health check endpoint verified
- ✅ SCIM endpoints tested
- ✅ OPP Agent configured
- ✅ Users imported successfully

**Congratulations! Your SCIM SQL Connector is now running!** 🎉