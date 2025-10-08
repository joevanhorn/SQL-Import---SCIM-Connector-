# Entitlements Guide

Complete guide for using entitlements with the SCIM 2.0 connector.

---

## Overview

Entitlements allow you to import user roles, groups, and permissions from your SQL database into Okta for Identity Governance.

### What are Entitlements?

Entitlements represent access rights that can be assigned to users:
- **Roles** - Administrator, Manager, User
- **Groups** - Finance, HR, IT departments
- **Permissions** - CreateUser, ViewReports, EditConfig
- **Custom** - Any application-specific access rights

---

## Requirements

### Prerequisites
- ✅ SCIM 2.0 connector (`scim2_app.py`)
- ✅ Okta Provisioning Agent 2.1.0 or later
- ✅ Early Access feature: "On-premises provisioning and entitlements" enabled
- ✅ SQL Server with entitlement tables

### Enable Early Access Feature

1. Log in to **Okta Admin Console**
2. Navigate to **Settings** → **Features**
3. Click **Early Access** tab
4. Find **"On-premises provisioning and entitlements"**
5. Click **Enable**
6. ✅ Activated immediately!

---

## Database Setup

### Step 1: Create Entitlement Tables

Run the SQL script: `database/entitlements_schema.sql`

```sql
-- Creates 2 tables:
-- 1. entitlements - stores available entitlements
-- 2. user_entitlements - maps users to entitlements
```

Or create manually:

```sql
-- Entitlements table
CREATE TABLE entitlements (
    id VARCHAR(50) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    display VARCHAR(255),
    type VARCHAR(50) DEFAULT 'default',
    description VARCHAR(500)
);

-- User-Entitlement mapping
CREATE TABLE user_entitlements (
    user_id VARCHAR(50) NOT NULL,
    entitlement_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, entitlement_id),
    FOREIGN KEY (entitlement_id) REFERENCES entitlements(id)
);
```

### Step 2: Insert Sample Entitlements

```sql
-- Sample roles
INSERT INTO entitlements (id, value, display, type) VALUES
('role-admin', 'Administrator', 'System Administrator', 'role'),
('role-manager', 'Manager', 'Department Manager', 'role'),
('role-user', 'User', 'Standard User', 'role');

-- Sample groups
INSERT INTO entitlements (id, value, display, type) VALUES
('group-finance', 'Finance', 'Finance Department', 'group'),
('group-hr', 'HR', 'Human Resources', 'group'),
('group-it', 'IT', 'IT Department', 'group');

-- Sample permissions
INSERT INTO entitlements (id, value, display, type) VALUES
('perm-create-user', 'CreateUser', 'Create User', 'permission'),
('perm-view-reports', 'ViewReports', 'View Reports', 'permission');
```

### Step 3: Assign Entitlements to Users

```sql
-- Give user '1' admin role and IT group
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('1', 'role-admin'),
('1', 'group-it'),
('1', 'perm-create-user');

-- Give user '2' manager role and finance group
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('2', 'role-manager'),
('2', 'group-finance'),
('2', 'perm-view-reports');
```

---

## Configuration

### Configure Column Mappings

Edit `.env` file:

```env
# Entitlement Tables
SQL_ENTITLEMENTS_TABLE=entitlements
SQL_USER_ENTITLEMENTS_TABLE=user_entitlements

# Entitlement Column Mappings
ENTITLEMENT_COLUMN_ID=id
ENTITLEMENT_COLUMN_VALUE=value
ENTITLEMENT_COLUMN_DISPLAY=display
ENTITLEMENT_COLUMN_TYPE=type
```

### Custom Table/Column Names

If your tables have different names:

```env
# Custom table names
SQL_ENTITLEMENTS_TABLE=app_roles
SQL_USER_ENTITLEMENTS_TABLE=user_roles_mapping

# Custom column names
ENTITLEMENT_COLUMN_ID=role_id
ENTITLEMENT_COLUMN_VALUE=role_name
ENTITLEMENT_COLUMN_DISPLAY=role_display_name
ENTITLEMENT_COLUMN_TYPE=role_category
```

---

## Testing

### Start SCIM 2.0 Server

```bash
python scim2_app.py
```

Expected output:
```
Starting SCIM 2.0 server with Entitlements on 0.0.0.0:443
Database: your-server/YourDatabase
User Table: users
Entitlement Table: entitlements
User-Entitlement Table: user_entitlements
Authentication: okta_import

⚠️  SCIM 2.0 with Entitlements - Requirements:
   • Okta Provisioning Agent 2.1.0 or later
   • Early Access: On-premises provisioning and entitlements

✨ Features:
   • User provisioning with entitlements
   • Entitlement discovery
   • Identity Governance integration
```

### Test Entitlement Endpoints

```powershell
# Get credentials from .env
$user = "okta_import"
$pass = "your_password"
$creds = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${user}:${pass}"))
$headers = @{ "Authorization" = "Basic $creds" }

# 1. List all entitlements
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Entitlements" -Headers $headers | ConvertTo-Json -Depth 5

# 2. Get specific entitlement
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Entitlements/role-admin" -Headers $headers | ConvertTo-Json -Depth 5

# 3. Get user with entitlements
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Users/1" -Headers $headers | ConvertTo-Json -Depth 5
```

### Expected User Response

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "1",
  "userName": "john.doe@company.com",
  "name": {
    "givenName": "John",
    "familyName": "Doe"
  },
  "emails": [...],
  "active": true,
  "entitlements": [
    {
      "value": "Administrator",
      "type": "role",
      "display": "System Administrator"
    },
    {
      "value": "IT",
      "type": "group",
      "display": "IT Department"
    },
    {
      "value": "CreateUser",
      "type": "permission",
      "display": "Create User"
    }
  ]
}
```

### Expected Entitlements List Response

```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
  "totalResults": 8,
  "startIndex": 1,
  "itemsPerPage": 8,
  "Resources": [
    {
      "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Entitlement"],
      "id": "role-admin",
      "value": "Administrator",
      "display": "System Administrator",
      "type": "role"
    },
    ...
  ]
}
```

---

## Okta Configuration

### Configure OPP Agent

1. Open **Okta On-Premises Provisioning Agent**
2. Click **Settings** → Configure application
3. **SCIM Base URL:** `https://your-server:443/scim/v2`
4. **Authentication:** Basic Auth
   - Username: (from .env SCIM_USERNAME)
   - Password: (from .env SCIM_PASSWORD)
5. Click **Test Connection** → Should succeed
6. **Save configuration**

### Import Users with Entitlements

1. In OPP Agent, click **Import**
2. Select **Import Now**
3. Wait for import to complete
4. Review imported users

### Verify in Okta Admin Console

1. Go to **Directory** → **People**
2. Click on an imported user
3. Go to **Applications** tab
4. Click on your on-premises app
5. **View entitlements** assigned to user

---

## Entitlement Types

### Standard Types

| Type | Description | Example Use Case |
|------|-------------|------------------|
| **role** | Job role or position | Administrator, Manager, User |
| **group** | Department or team | Finance, HR, Sales |
| **permission** | Specific access right | CreateUser, ViewReports |
| **default** | Generic entitlement | Custom application access |

### Custom Types

You can define custom entitlement types:

```sql
INSERT INTO entitlements (id, value, display, type) VALUES
('app-license-premium', 'Premium', 'Premium License', 'license'),
('app-feature-analytics', 'Analytics', 'Analytics Feature', 'feature');
```

---

## Common Use Cases

### Use Case 1: Role-Based Access Control (RBAC)

```sql
-- Create roles
INSERT INTO entitlements (id, value, display, type) VALUES
('role-admin', 'Administrator', 'System Admin', 'role'),
('role-power-user', 'PowerUser', 'Power User', 'role'),
('role-basic-user', 'BasicUser', 'Basic User', 'role');

-- Assign to users
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('1', 'role-admin'),      -- User 1 is admin
('2', 'role-power-user'), -- User 2 is power user
('3', 'role-basic-user'); -- User 3 is basic user
```

### Use Case 2: Department-Based Groups

```sql
-- Create department groups
INSERT INTO entitlements (id, value, display, type) VALUES
('dept-finance', 'Finance', 'Finance Department', 'group'),
('dept-hr', 'HR', 'Human Resources', 'group'),
('dept-it', 'IT', 'IT Department', 'group'),
('dept-sales', 'Sales', 'Sales Department', 'group');

-- Assign departments to users
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('1', 'dept-it'),      -- User 1 in IT
('2', 'dept-finance'), -- User 2 in Finance
('3', 'dept-sales');   -- User 3 in Sales
```

### Use Case 3: Permission-Based Access

```sql
-- Create granular permissions
INSERT INTO entitlements (id, value, display, type) VALUES
('perm-user-create', 'CreateUser', 'Create Users', 'permission'),
('perm-user-delete', 'DeleteUser', 'Delete Users', 'permission'),
('perm-user-edit', 'EditUser', 'Edit Users', 'permission'),
('perm-report-view', 'ViewReports', 'View Reports', 'permission'),
('perm-report-export', 'ExportReports', 'Export Reports', 'permission');

-- Assign multiple permissions to a user
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('1', 'perm-user-create'),
('1', 'perm-user-edit'),
('1', 'perm-report-view'),
('1', 'perm-report-export');
```

### Use Case 4: Mixed Entitlements

```sql
-- User with role, group, and permissions
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('1', 'role-admin'),          -- Has admin role
('1', 'dept-it'),             -- In IT department
('1', 'perm-user-create'),    -- Can create users
('1', 'perm-user-delete');    -- Can delete users
```

---

## Identity Governance Integration

### Entitlement Discovery

Okta will automatically discover all entitlements from your SQL database:

1. OPP Agent queries `/scim/v2/Entitlements`
2. Okta imports all available entitlements
3. Entitlements become available in Okta IGA

### Access Requests

Users can request entitlements through Okta:

1. User logs into Okta
2. Navigates to **Access Requests**
3. Requests an entitlement (role/group/permission)
4. Manager approves/denies
5. Entitlement provisioned to on-premises app

### Access Reviews

Periodic reviews of user entitlements:

1. Configure access review campaign in Okta
2. Reviewers see which users have which entitlements
3. Reviewers certify or revoke access
4. Changes synced back to SQL database

---

## Advanced Scenarios

### Dynamic Entitlement Assignment

Query from existing database columns:

```sql
-- Create view that maps existing columns to entitlements
CREATE VIEW user_entitlements AS
SELECT 
    id as user_id,
    'role-' + job_title as entitlement_id
FROM users
WHERE job_title IS NOT NULL;

-- User's job_title automatically becomes a role entitlement
```

### Hierarchical Entitlements

```sql
-- Parent-child entitlement relationships
CREATE TABLE entitlement_hierarchy (
    parent_id VARCHAR(50),
    child_id VARCHAR(50),
    FOREIGN KEY (parent_id) REFERENCES entitlements(id),
    FOREIGN KEY (child_id) REFERENCES entitlements(id)
);

-- Example: Admin role includes all manager permissions
INSERT INTO entitlement_hierarchy (parent_id, child_id) VALUES
('role-admin', 'perm-user-create'),
('role-admin', 'perm-user-delete'),
('role-manager', 'perm-user-edit');
```

### Time-Based Entitlements

```sql
-- Add expiration to user entitlements
ALTER TABLE user_entitlements ADD expires_date DATETIME;

-- Assign temporary entitlement
INSERT INTO user_entitlements (user_id, entitlement_id, expires_date) VALUES
('1', 'role-contractor', DATEADD(month, 6, GETDATE()));

-- Query to exclude expired entitlements
SELECT e.* 
FROM entitlements e
INNER JOIN user_entitlements ue ON e.id = ue.entitlement_id
WHERE ue.user_id = '1'
  AND (ue.expires_date IS NULL OR ue.expires_date > GETDATE());
```

---

## Troubleshooting

### Issue: No Entitlements Showing for Users

**Possible Causes:**
1. Entitlement tables don't exist
2. No data in entitlement tables
3. user_entitlements not mapped correctly
4. Early Access feature not enabled

**Solution:**
```sql
-- Check if tables exist
SELECT * FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME IN ('entitlements', 'user_entitlements');

-- Check if entitlements exist
SELECT COUNT(*) FROM entitlements;

-- Check if user-entitlement mappings exist
SELECT COUNT(*) FROM user_entitlements;

-- Check specific user's entitlements
SELECT e.* 
FROM entitlements e
INNER JOIN user_entitlements ue ON e.id = ue.entitlement_id
WHERE ue.user_id = '1';
```

### Issue: Error Fetching Entitlements

**Check server logs:**
```
Warning: Could not fetch entitlements for user X: [error message]
```

**Solutions:**
- Verify table names in `.env` match actual tables
- Check foreign key constraints
- Ensure user IDs in user_entitlements match users table
- Verify SQL permissions for entitlement tables

### Issue: Entitlements Not Syncing to Okta

**Verify:**
1. OPP Agent 2.1.0+ installed
2. Early Access feature enabled
3. SCIM 2.0 server running
4. Entitlement endpoints accessible

**Test:**
```powershell
# Test entitlements endpoint
Invoke-RestMethod -Uri "http://localhost:443/scim/v2/Entitlements" -Headers $headers
```

---

## Performance Optimization

### Index Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_user_entitlements_user ON user_entitlements(user_id);
CREATE INDEX idx_user_entitlements_entitlement ON user_entitlements(entitlement_id);
CREATE INDEX idx_entitlements_type ON entitlements(type);
CREATE INDEX idx_entitlements_value ON entitlements(value);
```

### Query Optimization

```sql
-- Update statistics
UPDATE STATISTICS entitlements;
UPDATE STATISTICS user_entitlements;

-- Analyze query plans
SET SHOWPLAN_TEXT ON;
SELECT e.* 
FROM entitlements e
INNER JOIN user_entitlements ue ON e.id = ue.entitlement_id
WHERE ue.user_id = '1';
SET SHOWPLAN_TEXT OFF;
```

---

## Migration Guide

### From Non-Entitlements to Entitlements

If you're upgrading from SCIM 1.1 or basic SCIM 2.0:

1. **Backup your database**
2. **Run entitlements schema SQL**
3. **Populate entitlements table**
4. **Map users to entitlements**
5. **Update .env configuration**
6. **Switch to SCIM 2.0 with entitlements**
7. **Test thoroughly**
8. **Re-import in Okta**

---

## Best Practices

### Naming Conventions
- Use prefixes for IDs: `role-`, `group-`, `perm-`
- Use clear, descriptive values
- Keep display names user-friendly

### Security
- Use read-only database account for SCIM server
- Encrypt entitlement-related data
- Audit entitlement assignments

### Maintenance
- Regularly review entitlements
- Remove unused entitlements
- Keep entitlement descriptions updated
- Document custom entitlement types

---

## Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scim/v2/Entitlements` | GET | List all entitlements |
| `/scim/v2/Entitlements/{id}` | GET | Get specific entitlement |
| `/scim/v2/Users` | GET | List users (with entitlements) |
| `/scim/v2/Users/{id}` | GET | Get user (with entitlements) |

### Database Schema

```sql
entitlements (
    id VARCHAR(50),
    value VARCHAR(255),
    display VARCHAR(255),
    type VARCHAR(50),
    description VARCHAR(500)
)

user_entitlements (
    user_id VARCHAR(50),
    entitlement_id VARCHAR(50)
)
```

### Environment Variables

```env
SQL_ENTITLEMENTS_TABLE=entitlements
SQL_USER_ENTITLEMENTS_TABLE=user_entitlements
ENTITLEMENT_COLUMN_ID=id
ENTITLEMENT_COLUMN_VALUE=value
ENTITLEMENT_COLUMN_DISPLAY=display
ENTITLEMENT_COLUMN_TYPE=type
```

---

## Additional Resources

- [Okta Entitlements Documentation](https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm)
- [SCIM 2.0 with Entitlements](https://developer.okta.com/docs/guides/scim-with-entitlements/main/)
- [Identity Governance](https://help.okta.com/en-us/content/topics/identity-governance/iga.htm)

---

**Entitlements enable powerful Identity Governance capabilities! 🎉**