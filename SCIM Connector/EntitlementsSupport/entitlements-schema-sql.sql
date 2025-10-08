-- =========================================
-- Okta SCIM Connector - Entitlements Schema
-- =========================================
-- This script creates the tables needed for entitlement support
-- Run this script in your SQL Server database

-- =========================================
-- 1. Entitlements Table
-- =========================================
-- Stores the available entitlements (roles, groups, permissions)

CREATE TABLE entitlements (
    id VARCHAR(50) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    display VARCHAR(255),
    type VARCHAR(50) DEFAULT 'default',
    description VARCHAR(500),
    created_date DATETIME DEFAULT GETDATE(),
    modified_date DATETIME DEFAULT GETDATE()
);

-- Create indexes for better performance
CREATE INDEX idx_entitlements_value ON entitlements(value);
CREATE INDEX idx_entitlements_type ON entitlements(type);

-- =========================================
-- 2. User-Entitlements Mapping Table
-- =========================================
-- Maps users to their entitlements (many-to-many relationship)

CREATE TABLE user_entitlements (
    user_id VARCHAR(50) NOT NULL,
    entitlement_id VARCHAR(50) NOT NULL,
    assigned_date DATETIME DEFAULT GETDATE(),
    PRIMARY KEY (user_id, entitlement_id),
    FOREIGN KEY (entitlement_id) REFERENCES entitlements(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_user_entitlements_user ON user_entitlements(user_id);
CREATE INDEX idx_user_entitlements_entitlement ON user_entitlements(entitlement_id);

-- =========================================
-- Sample Data (Optional)
-- =========================================
-- Uncomment to insert sample entitlements

/*
-- Sample Roles
INSERT INTO entitlements (id, value, display, type, description) VALUES
('role-admin', 'Administrator', 'System Administrator', 'role', 'Full system access'),
('role-manager', 'Manager', 'Department Manager', 'role', 'Management access'),
('role-user', 'User', 'Standard User', 'role', 'Standard access'),
('role-readonly', 'ReadOnly', 'Read Only User', 'role', 'Read-only access');

-- Sample Groups
INSERT INTO entitlements (id, value, display, type, description) VALUES
('group-finance', 'Finance', 'Finance Department', 'group', 'Finance department group'),
('group-hr', 'HR', 'Human Resources', 'group', 'HR department group'),
('group-it', 'IT', 'IT Department', 'group', 'IT department group'),
('group-sales', 'Sales', 'Sales Department', 'group', 'Sales department group');

-- Sample Permissions
INSERT INTO entitlements (id, value, display, type, description) VALUES
('perm-create-user', 'CreateUser', 'Create User', 'permission', 'Can create new users'),
('perm-delete-user', 'DeleteUser', 'Delete User', 'permission', 'Can delete users'),
('perm-view-reports', 'ViewReports', 'View Reports', 'permission', 'Can view reports'),
('perm-edit-config', 'EditConfig', 'Edit Configuration', 'permission', 'Can edit system configuration');

-- Sample User-Entitlement Mappings
-- Assuming you have users with IDs 1, 2, 3 in your users table
INSERT INTO user_entitlements (user_id, entitlement_id) VALUES
('1', 'role-admin'),
('1', 'group-it'),
('1', 'perm-create-user'),
('1', 'perm-delete-user'),
('2', 'role-manager'),
('2', 'group-finance'),
('2', 'perm-view-reports'),
('3', 'role-user'),
('3', 'group-sales');
*/

-- =========================================
-- Verification Queries
-- =========================================
-- Run these queries to verify the setup

-- Check entitlements table
-- SELECT * FROM entitlements;

-- Check user-entitlement mappings
-- SELECT * FROM user_entitlements;

-- Get entitlements for a specific user
-- SELECT e.* 
-- FROM entitlements e
-- INNER JOIN user_entitlements ue ON e.id = ue.entitlement_id
-- WHERE ue.user_id = '1';

-- Get users with a specific entitlement
-- SELECT u.*, e.value as entitlement
-- FROM users u
-- INNER JOIN user_entitlements ue ON u.id = ue.user_id
-- INNER JOIN entitlements e ON ue.entitlement_id = e.id
-- WHERE e.id = 'role-admin';

-- Count entitlements by type
-- SELECT type, COUNT(*) as count
-- FROM entitlements
-- GROUP BY type;

-- =========================================
-- Cleanup (Optional)
-- =========================================
-- Uncomment to drop tables if needed

/*
DROP TABLE IF EXISTS user_entitlements;
DROP TABLE IF EXISTS entitlements;
*/

-- =========================================
-- Notes
-- =========================================
-- 1. User IDs in user_entitlements must match IDs in your users table
-- 2. The 'type' column can be: role, group, permission, or custom values
-- 3. The 'display' column is optional but recommended for better UI display
-- 4. Adjust VARCHAR lengths based on your needs
-- 5. Consider adding audit columns (created_by, modified_by) if needed