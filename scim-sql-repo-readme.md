# Okta SCIM Connector for SQL Database Import

A Python-based SCIM 1.1 server that enables Okta to import users from SQL Server databases using the On-Premises Provisioning (OPP) Agent.

## Overview

This connector provides **inbound provisioning** from SQL Server to Okta. The SCIM server acts as a bridge between your SQL database and Okta's OPP Agent, allowing you to import users with flexible column mapping.

### Architecture

```
SQL Database → SCIM Server (this app) → Okta OPP Agent → Okta Tenant
```

## 🔄 Two Versions Available

This repository includes both SCIM 1.1 and SCIM 2.0 implementations:

| Version | File | Use Case |
|---------|------|----------|
| **SCIM 1.1** | `inbound_app.py` | ✅ **Default** - Works with all Okta tenants |
| **SCIM 2.0** | `scim2_app.py` | ⚠️ Requires OPP Agent 2.1.0+ and Early Access feature |

**Not sure which to use?** Start with SCIM 1.1 (`inbound_app.py`)

**SCIM 2.0 Requirements:**
- Okta Provisioning Agent 2.1.0 or later
- Early Access feature enabled (self-service, no support ticket needed)
- See [Enable Instructions](https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm)

See [SCIM Version Comparison](docs/SCIM_VERSION_COMPARISON.md) for detailed differences.

## Features

- ✅ **Two SCIM versions**: SCIM 1.1 (default) and SCIM 2.0 (requires OPP Agent 2.1.0+)
- ✅ SCIM 1.1 protocol compliance (compatible with all OPP Agent versions)
- ✅ SCIM 2.0 protocol compliance (requires OPP Agent 2.1.0+ and self-service EA feature)
- ✅ Flexible SQL column mapping via environment variables
- ✅ Support for pagination and filtering
- ✅ Health check endpoint for monitoring
- ✅ Basic authentication for SCIM endpoints
- ✅ Configurable user attributes (name, email, active status, etc.)
- ✅ Supports any SQL Server database schema

## Prerequisites

- Windows Server (or Linux with Python 3.7+)
- SQL Server database with user data
- Okta tenant with OPP Agent installed
- Python 3.7 or higher
- Administrator access (for running on port 443)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/okta-scim-sql-connector.git
cd okta-scim-sql-connector
```

### 2. Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Edit `.env` with your SQL Server and column mapping details.

### 4. Run the Server

```bash
# Run SCIM 1.1 server (default - recommended)
python inbound_app.py

# OR run SCIM 2.0 server (requires feature flag from Okta Support)
python scim2_app.py

# Run on port 443 (production) - requires Administrator
# Run PowerShell as Administrator first
python inbound_app.py  # or scim2_app.py
```

**Which version?** See [SCIM Version Comparison](docs/SCIM_VERSION_COMPARISON.md)

### 5. Configure Okta OPP Agent

1. Open Okta OPP Agent configuration
2. Set SCIM Base URL: `https://your-server:443/scim/v2`
3. Set Authentication: Basic Auth
   - Username: (value from `SCIM_USERNAME` in .env)
   - Password: (value from `SCIM_PASSWORD` in .env)
4. Test connection
5. Import users

## Configuration

### Database Connection

Configure your SQL Server connection in `.env`:

```env
DB_DRIVER=SQL Server
DB_SERVER=your-sql-server.company.com
DB_NAME=YourDatabase
DB_USERNAME=sql_user
DB_PASSWORD=your_password
```

### Column Mapping

Map your SQL columns to SCIM attributes:

```env
# Required Fields
DB_COLUMN_ID=user_id
DB_COLUMN_USERNAME=email
DB_COLUMN_EMAIL=email

# Optional Fields
DB_COLUMN_FIRST_NAME=first_name
DB_COLUMN_LAST_NAME=last_name
DB_COLUMN_DISPLAY_NAME=display_name
DB_COLUMN_ACTIVE=is_active
DB_COLUMN_EXTERNAL_ID=employee_id
```

### SCIM Authentication

Set credentials for OPP Agent authentication:

```env
SCIM_USERNAME=okta_import
SCIM_PASSWORD=SecureImportPassword123!
```

### Server Settings

```env
SERVER_HOST=0.0.0.0
SERVER_PORT=443
```

## Database Schema Examples

The connector supports various database schemas. See `docs/examples/` for:

- HR System schema
- Active Directory export schema
- Payroll system schema
- Custom database schema

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scim/v2/Users` | GET | List all users |
| `/scim/v2/Users?startIndex={n}&count={n}` | GET | Paginated user list |
| `/scim/v2/Users/{id}` | GET | Get specific user |
| `/scim/v2/ServiceProviderConfig` | GET | SCIM capabilities |
| `/health` | GET | Health check |

## Troubleshooting

### Common Issues

**1. Schema Version Mismatch Error**

```
Error: 'urn:scim:schemas:core:1.0' must be declared
```

**Solution**: The connector now uses SCIM 1.1 format (no schemas arrays in responses). Make sure you're using the latest version.

**2. Port 443 Requires Administrator**

```
Error: Permission denied
```

**Solution**: Run PowerShell as Administrator before starting the server.

**3. Database Connection Fails**

```
Error: Connection refused
```

**Solution**: Check:
- SQL Server allows remote connections
- Firewall rules allow connection
- SQL Server authentication is enabled
- Credentials are correct

**4. No Users Returned**

**Solution**: Check:
- SQL query in code matches your table name
- Column mappings in `.env` are correct
- Users exist in the database

### Enable Debug Logging

Edit `inbound_app.py` and set:

```python
app.run(host=SERVER_HOST, port=SERVER_PORT, debug=True)
```

## Testing

### Test Database Connection

```python
python test_db_connection.py
```

### Test SCIM Endpoint

```powershell
# PowerShell
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("okta_import:SecureImportPassword123!"))
$headers = @{ "Authorization" = "Basic $creds" }

Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Users?count=5" -Headers $headers | ConvertTo-Json -Depth 5
```

### Test Health Check

```bash
curl http://localhost:443/health
```

## Production Deployment

### Windows Service

See `docs/deployment/windows-service.md` for instructions on running as a Windows Service.

### Security Considerations

1. Use HTTPS in production (configure SSL certificate)
2. Use strong SCIM credentials
3. Restrict network access to OPP Agent only
4. Use SQL Server accounts with read-only access
5. Enable SQL Server encryption
6. Regularly rotate credentials

### Performance Tuning

- Adjust pagination size in code (default: 100)
- Optimize SQL query with proper indexes
- Consider database connection pooling
- Monitor memory usage for large user sets

## Project Structure

```
okta-scim-sql-connector/
├── inbound_app.py              # Main SCIM server
├── requirements.txt            # Python dependencies
├── .env.example               # Example configuration
├── README.md                  # This file
├── LICENSE                    # License file
├── docs/
│   ├── deployment/
│   │   ├── windows-service.md
│   │   └── ssl-setup.md
│   ├── examples/
│   │   ├── hr-system-schema.md
│   │   ├── ad-export-schema.md
│   │   └── custom-schema.md
│   └── troubleshooting.md
└── tests/
    ├── test_db_connection.py
    └── test_scim_endpoints.py
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or questions:
- Open a GitHub issue
- Contact your Okta Solutions Engineering team
- Check Okta documentation: https://help.okta.com

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built for Okta Solutions Engineers to demonstrate SQL database import capabilities.

---

**Version:** 1.0.0  
**Last Updated:** October 2025  
**Maintainer:** Okta Solutions Engineering