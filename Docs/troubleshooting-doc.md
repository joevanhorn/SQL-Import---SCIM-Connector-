# Troubleshooting Guide

## Common Issues and Solutions

### 1. Schema Version Mismatch Error

**Error Message:**
```
Error while downloading all users: Exception in deserializing the User Json String.
Error message=Resource 'User' is malformed: 'urn:scim:schemas:core:1.0' must be declared in the schemas attribute.
```

**Root Cause:**  
Okta OPP Agent expects SCIM 1.1 format (without schemas arrays), but the server was returning SCIM 2.0 format.

**Solution:**  
Ensure you're using the latest version of `inbound_app.py` which uses SCIM 1.1 format (no `schemas` field in responses).

**Verification:**
```powershell
# Test that responses don't include schemas field
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("okta_import:YourPassword"))
$headers = @{ "Authorization" = "Basic $creds" }
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Users?count=1" -Headers $headers
```

---

### 2. Port 443 Permission Denied

**Error Message:**
```
OSError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
```

**Root Cause:**  
Ports below 1024 (including 443) require Administrator privileges on Windows.

**Solution:**  
Run PowerShell as Administrator:
1. Right-click PowerShell
2. Select "Run as Administrator"
3. Navigate to project directory
4. Activate virtual environment
5. Run `python inbound_app.py`

**Alternative:**  
Use port 8080 for testing:
```env
SERVER_PORT=8080
```

Then update OPP Agent URL to: `http://your-server:8080/scim/v2`

---

### 3. Database Connection Failures

**Error Message:**
```
pyodbc.OperationalError: ('08001', '[08001] [Microsoft][ODBC SQL Server Driver]...')
```

**Common Causes and Solutions:**

#### A. SQL Server Not Accepting Remote Connections
```sql
-- Enable TCP/IP protocol in SQL Server Configuration Manager
-- Restart SQL Server service after enabling
```

#### B. Firewall Blocking Connection
```powershell
# Windows Firewall - Allow SQL Server port
New-NetFirewallRule -DisplayName "SQL Server" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow
```

#### C. SQL Server Authentication Not Enabled
```sql
-- Enable Mixed Mode Authentication in SQL Server
-- Properties → Security → SQL Server and Windows Authentication mode
-- Restart SQL Server
```

#### D. Wrong Connection String Format
```env
# Correct format for SQL Server
DB_DRIVER=SQL Server
DB_SERVER=server.domain.com
DB_NAME=DatabaseName
DB_USERNAME=username
DB_PASSWORD=password

# For SQL Server Express with instance name
DB_SERVER=server.domain.com\\SQLEXPRESS
```

#### E. Database User Permissions
```sql
-- Grant SELECT permission to connector user
USE YourDatabase;
CREATE LOGIN sql_readonly_user WITH PASSWORD = 'SecurePassword123!';
CREATE USER sql_readonly_user FOR LOGIN sql_readonly_user;
GRANT SELECT ON users TO sql_readonly_user;
```

---

### 4. No Users Returned (Empty Response)

**Error Message:**
```json
{
  "totalResults": 0,
  "Resources": []
}
```

**Troubleshooting Steps:**

#### Step 1: Verify Table Has Data
```sql
SELECT COUNT(*) FROM users;
SELECT TOP 5 * FROM users;
```

#### Step 2: Check Table Name
```env
# Make sure SQL_TABLE matches your actual table name
SQL_TABLE=users  # Case-sensitive on some systems
```

#### Step 3: Verify Column Mappings
```powershell
# Test database connection script
python test_db_connection.py
```

#### Step 4: Check Column Names Match
```sql
-- Get actual column names
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'users';
```

Update `.env` to match exact column names:
```env
DB_COLUMN_ID=UserID  # Match exact casing
DB_COLUMN_EMAIL=EmailAddress
```

---

### 5. Authentication Failures

**Error Message:**
```
401 Unauthorized
```

**Solutions:**

#### A. Verify SCIM Credentials
```powershell
# Test with correct credentials
$user = "okta_import"
$pass = "SecureImportPassword123!"
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${user}:${pass}"))
$headers = @{ "Authorization" = "Basic $creds" }
Invoke-RestMethod -Uri "http://localhost:443/health" -Headers $headers
```

#### B. Check .env File Loaded
```python
# Add debug print in inbound_app.py
print(f"SCIM Username: {SCIM_USERNAME}")
print(f"SCIM Password: {'*' * len(SCIM_PASSWORD)}")
```

#### C. Verify OPP Agent Configuration
- Check credentials in OPP Agent match `.env` file exactly
- Ensure no extra spaces in username/password

---

### 6. OPP Agent Cannot Connect to SCIM Server

**Error in OPP Agent Logs:**
```
Connection refused
```

**Solutions:**

#### A. Verify Server is Running
```powershell
# Check if server is listening
netstat -an | findstr :443
```

#### B. Check Network Connectivity
```powershell
# From OPP Agent machine
Test-NetConnection -ComputerName your-server -Port 443
```

#### C. Firewall Rules
```powershell
# Allow inbound connections on port 443
New-NetFirewallRule -DisplayName "SCIM Server" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

#### D. Verify URL in OPP Agent
```
Correct: https://your-server:443/scim/v2
Incorrect: https://your-server/scim/v2 (missing port)
Incorrect: https://your-server:443/ (missing /scim/v2)
```

---

### 7. SSL/TLS Certificate Errors

**Error Message:**
```
SSL certificate verification failed
```

**Solutions:**

#### A. Use HTTP for Testing
```
http://your-server:8080/scim/v2
```

#### B. Generate Self-Signed Certificate
```powershell
# Generate certificate
New-SelfSignedCertificate -DnsName "your-server" -CertStoreLocation Cert:\LocalMachine\My
```

#### C. Configure Flask with SSL
```python
# In inbound_app.py
app.run(
    host=SERVER_HOST,
    port=SERVER_PORT,
    ssl_context=('cert.pem', 'key.pem')
)
```

---

### 8. Data Type Conversion Errors

**Error Message:**
```
TypeError: Object of type 'datetime' is not JSON serializable
```

**Solution:**  
Ensure datetime fields are converted to ISO format in `map_sql_to_scim()`:

```python
# Correct conversion
"created": datetime.utcnow().isoformat() + "Z"

# For database datetime fields
if isinstance(value, datetime):
    value = value.isoformat() + "Z"
```

---

### 9. Pagination Issues

**Symptoms:**
- Only first page of users imported
- Duplicate users
- Missing users

**Solutions:**

#### A. Verify Pagination Logic
```python
# Check OFFSET calculation
offset = start_index - 1  # SCIM uses 1-based indexing
```

#### B. Test Pagination
```powershell
# First page
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Users?startIndex=1&count=10"

# Second page
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Users?startIndex=11&count=10"
```

#### C. Ensure Stable Ordering
```sql
-- Always ORDER BY a unique column
ORDER BY id
```

---

### 10. Performance Issues (Slow Imports)

**Symptoms:**
- Import takes hours
- OPP Agent times out

**Solutions:**

#### A. Add Database Indexes
```sql
CREATE INDEX idx_users_id ON users(id);
CREATE INDEX idx_users_email ON users(email);
```

#### B. Optimize Query
```sql
-- Use specific columns instead of SELECT *
SELECT id, username, email, first_name, last_name
FROM users
ORDER BY id
OFFSET @offset ROWS
FETCH NEXT @count ROWS ONLY;
```

#### C. Increase Pagination Size
```python
# In get_users() function
count = int(request.args.get('count', 200))  # Default 200 instead of 100
```

#### D. Database Connection Pooling
Already configured in pyodbc connection settings.

---

## Debugging Tips

### Enable Debug Logging

```python
# In inbound_app.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Run in debug mode
app.run(host=SERVER_HOST, port=SERVER_PORT, debug=True)
```

### Test Individual Components

```python
# test_db_connection.py
import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

conn_str = f"DRIVER={{SQL Server}};SERVER={os.getenv('DB_SERVER')};DATABASE={os.getenv('DB_NAME')};UID={os.getenv('DB_USERNAME')};PWD={os.getenv('DB_PASSWORD')}"

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 5 * FROM users")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Error: {e}")
```

### Monitor OPP Agent Logs

Location: `C:\ProgramData\Okta\Okta On-Premises Provisioning Agent\logs\`

Look for:
- Connection attempts
- SCIM requests/responses
- Error messages

### Use Postman/cURL for Testing

```bash
# Test health endpoint
curl -u okta_import:password http://localhost:443/health

# Test user list
curl -u okta_import:password http://localhost:443/scim/v2/Users?count=5

# Test specific user
curl -u okta_import:password http://localhost:443/scim/v2/Users/123
```

---

## Getting Help

If you continue to experience issues:

1. **Check logs** - Review both SCIM server output and OPP Agent logs
2. **Verify configuration** - Double-check `.env` file settings
3. **Test connectivity** - Ensure network connectivity between components
4. **Simplify** - Test with minimal data first, then scale up
5. **Contact support** - Open a GitHub issue with logs and configuration (redact credentials)

---

## Useful SQL Queries for Troubleshooting

```sql
-- Check total user count
SELECT COUNT(*) as TotalUsers FROM users;

-- Check for NULL values in key columns
SELECT 
    COUNT(*) as Total,
    SUM(CASE WHEN id IS NULL THEN 1 ELSE 0 END) as NullIds,
    SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) as NullEmails
FROM users;

-- Check for duplicate IDs
SELECT id, COUNT(*) as Count
FROM users
GROUP BY id
HAVING COUNT(*) > 1;

-- Check for duplicate emails
SELECT email, COUNT(*) as Count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- View sample data
SELECT TOP 10 * FROM users;

-- Check column data types
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'users';
```