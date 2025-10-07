#!/usr/bin/env python3
"""
Okta SCIM 2.0 Connector for SQL Server User Import
Enables Okta OPP Agent to import users from any SQL Server database

⚠️ REQUIREMENTS:
   - Okta Provisioning Agent version 2.1.0 or later
   - Early Access feature "On-premises provisioning and entitlements" enabled
   - Enable at: Admin Console → Settings → Features → Early Access
   - See: https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm

For standard OPP Agent installations (< 2.1.0), use inbound_app.py (SCIM 1.1) instead.
"""

from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
import pyodbc
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
auth = HTTPBasicAuth()

# Configuration from environment variables
DB_DRIVER = os.getenv('DB_DRIVER', 'SQL Server')
DB_SERVER = os.getenv('DB_SERVER')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# SCIM Authentication
SCIM_USERNAME = os.getenv('SCIM_USERNAME', 'okta_import')
SCIM_PASSWORD = os.getenv('SCIM_PASSWORD')

# Column mappings - customize based on your database schema
DB_COLUMN_ID = os.getenv('DB_COLUMN_ID', 'id')
DB_COLUMN_USERNAME = os.getenv('DB_COLUMN_USERNAME', 'username')
DB_COLUMN_EMAIL = os.getenv('DB_COLUMN_EMAIL', 'email')
DB_COLUMN_FIRST_NAME = os.getenv('DB_COLUMN_FIRST_NAME', 'first_name')
DB_COLUMN_LAST_NAME = os.getenv('DB_COLUMN_LAST_NAME', 'last_name')
DB_COLUMN_DISPLAY_NAME = os.getenv('DB_COLUMN_DISPLAY_NAME', 'display_name')
DB_COLUMN_ACTIVE = os.getenv('DB_COLUMN_ACTIVE', 'active')
DB_COLUMN_EXTERNAL_ID = os.getenv('DB_COLUMN_EXTERNAL_ID', 'external_id')

# Server configuration
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', '443'))

# SQL Table name
SQL_TABLE = os.getenv('SQL_TABLE', 'users')

# SCIM 2.0 Schema URNs
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
ENTERPRISE_USER_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
LIST_RESPONSE_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"

@auth.verify_password
def verify_password(username, password):
    """Verify SCIM authentication credentials"""
    return username == SCIM_USERNAME and password == SCIM_PASSWORD

def get_db_connection():
    """Create database connection"""
    conn_str = (
        f'DRIVER={{{DB_DRIVER}}}; '
        f'SERVER={DB_SERVER}; '
        f'DATABASE={DB_NAME}; '
        f'UID={DB_USERNAME}; '
        f'PWD={DB_PASSWORD}'
    )
    return pyodbc.connect(conn_str)

def map_sql_to_scim_v2(row, column_names):
    """Map SQL row to SCIM 2.0 user format"""
    # Get column indices
    col_dict = {name: idx for idx, name in enumerate(column_names)}
    
    # Build SCIM 2.0 user object (WITH schemas array)
    user = {
        "schemas": [USER_SCHEMA, ENTERPRISE_USER_SCHEMA],
        "id": str(row[col_dict[DB_COLUMN_ID]]) if DB_COLUMN_ID in col_dict else "",
        "userName": row[col_dict[DB_COLUMN_USERNAME]] if DB_COLUMN_USERNAME in col_dict else "",
        "name": {
            "givenName": row[col_dict[DB_COLUMN_FIRST_NAME]] if DB_COLUMN_FIRST_NAME in col_dict else "",
            "familyName": row[col_dict[DB_COLUMN_LAST_NAME]] if DB_COLUMN_LAST_NAME in col_dict else "",
            "formatted": f"{row[col_dict[DB_COLUMN_FIRST_NAME]]} {row[col_dict[DB_COLUMN_LAST_NAME]]}" if DB_COLUMN_FIRST_NAME in col_dict and DB_COLUMN_LAST_NAME in col_dict else ""
        },
        "emails": [
            {
                "value": row[col_dict[DB_COLUMN_EMAIL]] if DB_COLUMN_EMAIL in col_dict else "",
                "type": "work",
                "primary": True
            }
        ],
        "active": bool(row[col_dict[DB_COLUMN_ACTIVE]]) if DB_COLUMN_ACTIVE in col_dict else True,
        "meta": {
            "resourceType": "User",
            "created": datetime.utcnow().isoformat() + "Z",
            "lastModified": datetime.utcnow().isoformat() + "Z",
            "location": f"/scim/v2/Users/{row[col_dict[DB_COLUMN_ID]]}" if DB_COLUMN_ID in col_dict else ""
        }
    }
    
    # Add optional fields
    if DB_COLUMN_DISPLAY_NAME in col_dict and row[col_dict[DB_COLUMN_DISPLAY_NAME]]:
        user["displayName"] = row[col_dict[DB_COLUMN_DISPLAY_NAME]]
    
    if DB_COLUMN_EXTERNAL_ID in col_dict and row[col_dict[DB_COLUMN_EXTERNAL_ID]]:
        user["externalId"] = str(row[col_dict[DB_COLUMN_EXTERNAL_ID]])
    
    return user

@app.route('/scim/v2/Users', methods=['GET'])
@auth.login_required
def get_users():
    """Get list of users with pagination support (SCIM 2.0)"""
    try:
        # Pagination parameters
        start_index = int(request.args.get('startIndex', 1))
        count = int(request.args.get('count', 100))
        
        # Calculate SQL OFFSET and FETCH
        offset = start_index - 1  # SCIM uses 1-based indexing
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM {SQL_TABLE}")
        total_results = cursor.fetchone()[0]
        
        # Get paginated users
        query = f"""
            SELECT * FROM {SQL_TABLE}
            ORDER BY {DB_COLUMN_ID}
            OFFSET {offset} ROWS
            FETCH NEXT {count} ROWS ONLY
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]
        
        # Map to SCIM 2.0 format
        resources = [map_sql_to_scim_v2(row, column_names) for row in rows]
        
        conn.close()
        
        # SCIM 2.0 List Response (WITH schemas array)
        response = {
            "schemas": [LIST_RESPONSE_SCHEMA],
            "totalResults": total_results,
            "startIndex": start_index,
            "itemsPerPage": len(resources),
            "Resources": resources
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "schemas": [ERROR_SCHEMA],
            "status": "500",
            "detail": str(e)
        }), 500

@app.route('/scim/v2/Users/<user_id>', methods=['GET'])
@auth.login_required
def get_user(user_id):
    """Get a specific user by ID (SCIM 2.0)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {SQL_TABLE} WHERE {DB_COLUMN_ID} = ?"
        cursor.execute(query, (user_id,))
        
        row = cursor.fetchone()
        column_names = [column[0] for column in cursor.description]
        
        conn.close()
        
        if not row:
            return jsonify({
                "schemas": [ERROR_SCHEMA],
                "status": "404",
                "detail": "User not found"
            }), 404
        
        user = map_sql_to_scim_v2(row, column_names)
        return jsonify(user), 200
        
    except Exception as e:
        return jsonify({
            "schemas": [ERROR_SCHEMA],
            "status": "500",
            "detail": str(e)
        }), 500

@app.route('/scim/v2/Schemas', methods=['GET'])
def get_schemas():
    """Return SCIM 2.0 schema definitions"""
    schemas = {
        "schemas": [LIST_RESPONSE_SCHEMA],
        "totalResults": 2,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
                "id": USER_SCHEMA,
                "name": "User",
                "description": "User Account"
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
                "id": ENTERPRISE_USER_SCHEMA,
                "name": "EnterpriseUser",
                "description": "Enterprise User"
            }
        ]
    }
    return jsonify(schemas), 200

@app.route('/scim/v2/ResourceTypes', methods=['GET'])
def get_resource_types():
    """Return SCIM 2.0 resource types"""
    resource_types = {
        "schemas": [LIST_RESPONSE_SCHEMA],
        "totalResults": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/Users",
                "description": "User Account",
                "schema": USER_SCHEMA,
                "schemaExtensions": [
                    {
                        "schema": ENTERPRISE_USER_SCHEMA,
                        "required": False
                    }
                ]
            }
        ]
    }
    return jsonify(resource_types), 200

@app.route('/scim/v2/ServiceProviderConfig', methods=['GET'])
def service_provider_config():
    """Return SCIM 2.0 service provider configuration"""
    config = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://tools.ietf.org/html/rfc7644",
        "patch": {
            "supported": False
        },
        "bulk": {
            "supported": False,
            "maxOperations": 0,
            "maxPayloadSize": 0
        },
        "filter": {
            "supported": True,
            "maxResults": 200
        },
        "changePassword": {
            "supported": False
        },
        "sort": {
            "supported": True
        },
        "etag": {
            "supported": False
        },
        "authenticationSchemes": [
            {
                "type": "httpbasic",
                "name": "HTTP Basic",
                "description": "Authentication via HTTP Basic",
                "specUri": "http://www.rfc-editor.org/info/rfc2617",
                "documentationUri": "https://tools.ietf.org/html/rfc7617"
            }
        ]
    }
    return jsonify(config), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "version": "SCIM 2.0",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "version": "SCIM 2.0",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "message": "Okta SCIM 2.0 Connector for SQL Server",
        "version": "2.0.0",
        "scimVersion": "2.0",
        "requirements": {
            "oppAgent": "2.1.0 or later",
            "earlyAccess": "On-premises provisioning and entitlements"
        },
        "enableAt": "Admin Console → Settings → Features → Early Access",
        "documentation": "https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm",
        "endpoints": {
            "users": "/scim/v2/Users",
            "schemas": "/scim/v2/Schemas",
            "resourceTypes": "/scim/v2/ResourceTypes",
            "config": "/scim/v2/ServiceProviderConfig",
            "health": "/health"
        }
    }), 200

if __name__ == '__main__':
    print(f"Starting SCIM 2.0 server on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Database: {DB_SERVER}/{DB_NAME}")
    print(f"Table: {SQL_TABLE}")
    print(f"Authentication: {SCIM_USERNAME}")
    print(f"\n⚠️  SCIM 2.0 Version Requirements:")
    print(f"   • Okta Provisioning Agent 2.1.0 or later")
    print(f"   • Early Access: On-premises provisioning and entitlements")
    print(f"   • Enable at: Admin Console → Settings → Features → Early Access")
    print(f"   • Docs: https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm\n")
    
    # Run server
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)