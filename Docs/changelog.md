# Changelog

All notable changes to the Okta SCIM SQL Connector will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-10-06

### Added
- SCIM 2.0 version (`scim2_app.py`) for OPP Agent 2.1.0+ with Early Access features
- Full SCIM 2.0 protocol compliance with schema declarations
- Additional SCIM 2.0 endpoints: `/Schemas` and `/ResourceTypes`
- Support for Okta Identity Governance and entitlements
- SCIM Version Comparison documentation
- Version-specific troubleshooting guide
- Self-service enablement instructions for SCIM 2.0

### Documentation
- SCIM Version Comparison Guide (`docs/SCIM_VERSION_COMPARISON.md`)
- Version-Specific Troubleshooting (`docs/VERSION_TROUBLESHOOTING.md`)
- Updated README with version selection guidance
- Early Access self-service enablement instructions
- OPP Agent 2.1.0+ requirements documentation

### Notes
- SCIM 1.1 (`inbound_app.py`) remains the default and recommended version
- SCIM 2.0 (`scim2_app.py`) requires OPP Agent 2.1.0 or later
- SCIM 2.0 requires self-service Early Access feature "On-premises provisioning and entitlements"
- No Okta Support ticket needed for SCIM 2.0 - self-service enablement
- Both versions use the same configuration file (`.env`)
- No breaking changes to existing SCIM 1.1 implementation

---

## [1.0.0] - 2025-10-06

### Added
- Initial release of Okta SCIM SQL Connector
- SCIM 1.1 server implementation for Okta OPP Agent compatibility
- SQL Server database support with pyodbc
- Flexible column mapping via environment variables
- Basic authentication for SCIM endpoints
- Pagination support for large user datasets
- Health check endpoint for monitoring
- `/scim/v2/Users` endpoint (GET all users, GET by ID)
- `/scim/v2/ServiceProviderConfig` endpoint
- Comprehensive README with setup instructions
- Quick Start guide for 15-minute setup
- Detailed troubleshooting documentation
- Windows Service deployment guide (NSSM and native)
- Multiple database schema examples (HR, AD, Payroll)
- Database connection test utility
- Automated installation script (PowerShell)
- Health monitoring script
- Example configuration file (.env.example)
- MIT License

### Fixed
- Schema version mismatch error with Okta OPP Agent
  - Changed from SCIM 2.0 to SCIM 1.1 format
  - Removed `schemas` arrays from all responses
  - Fixed ListResponse format to match SCIM 1.1 spec
  - Updated ServiceProviderConfig to use SCIM 1.1 property names

### Documentation
- Complete README with architecture overview
- Installation and configuration guide
- API endpoint documentation
- Troubleshooting guide covering 10+ common issues
- Production deployment checklist
- SSL/TLS setup guide
- Multiple database schema examples
- Architecture and data flow diagrams
- Security best practices
- Performance tuning recommendations

### Scripts
- `install.ps1` - Automated installation and setup
- `test_db_connection.py` - Database connectivity tester
- `start_server.bat` - Quick server launcher
- `monitor_health.ps1` - Health check monitoring
- `service_wrapper.py` - Windows Service wrapper

---

## [Unreleased]

### Planned Features
- Support for additional databases (PostgreSQL, MySQL, Oracle)
- Group provisioning support
- Docker containerization
- Automated testing suite
- Web UI for configuration
- Metrics and monitoring dashboard
- Incremental sync (delta imports)

### Known Issues
- None at this time

---

## Version History Summary

- **1.1.0** (2025-10-06) - Added SCIM 2.0 version with feature flag support
- **1.0.0** (2025-10-06) - Initial release with SCIM 1.1 support and comprehensive documentation

---

## How to Upgrade

### From Development Version to 1.0.0

If you were using a development version before the official 1.0.0 release:

1. **Backup your configuration**
   ```bash
   cp .env .env.backup
   ```

2. **Update repository**
   ```bash
   git pull origin main
   ```

3. **Update dependencies**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **Review `.env.example`** for any new configuration options

5. **Test connection**
   ```bash
   python test_db_connection.py
   ```

6. **Restart service**
   ```bash
   # If running as Windows Service
   Restart-Service OktaSCIMConnector
   
   # If running manually
   python inbound_app.py
   ```

---

## Release Notes Format

Each release will include:

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features that will be removed in future versions
- **Removed** - Features that have been removed
- **Fixed** - Bug fixes
- **Security** - Security vulnerability fixes

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

When contributing, please:
1. Add your changes to the "Unreleased" section
2. Follow the format: `- Description of change (#PR-number)`
3. Categorize under appropriate heading (Added, Changed, Fixed, etc.)

Example:
```markdown
## [Unreleased]

### Added
- PostgreSQL database support (#123)
- Group provisioning endpoints (#124)

### Fixed
- Pagination bug with special characters in username (#125)
```

---

## Support

For issues or questions:
- Open a [GitHub issue](https://github.com/your-org/okta-scim-sql-connector/issues)
- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Contact Okta Solutions Engineering team