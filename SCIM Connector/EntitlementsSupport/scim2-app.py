#!/usr/bin/env python3
"""
Okta SCIM 2.0 Connector with Entitlements for SQL Server User Import
Enables Okta OPP Agent to import users AND entitlements from any SQL Server database

⚠️ REQUIREMENTS:
   - Okta Provisioning Agent version 2.1.0 or later
   - Early Access feature "On-premises provisioning and entitlements" enabled
   - Enable at: Admin Console → Settings → Features → Early Access
   - See: https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm

FEATURES:
   - User provisioning with entitlements
   - Entitlement discovery
   - Support for roles, groups, permissions
   - Identity Governance integration

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

# SQL Table names
SQL_TABLE = os.getenv('SQL_TABLE', 'users')
SQL_ENTITLEMENTS_TABLE = os.getenv('SQL_ENTITLEMENTS_TABLE', 'entitlements')
SQL_USER_ENTITLEMENTS_TABLE = os.getenv('SQL_USER_ENTITLEMENTS_TABLE', 'user_entitlements')

# Entitlement column mappings
ENTITLEMENT_COLUMN_ID = os.getenv('ENTITLEMENT_COLUMN_ID', 'id')
ENTITLEMENT_COLUMN_VALUE = os.getenv('ENTITLEMENT_COLUMN_VALUE', 'value')
ENTITLEMENT_COLUMN_DISPLAY = os.getenv('ENTITLEMENT_COLUMN_DISPLAY', 'display')
ENTITLEMENT_COLUMN_TYPE = os.getenv('ENTITLEMENT_COLUMN_TYPE', 'type')

# SCIM 2.0 Schema URNs
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
ENTERPRISE_USER_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
ENTITLEMENT_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Entitlement"
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

def get_user_entitlements(user_id, conn):
    """Get entitlements for a specific user"""
    try:
        cursor = conn.cursor()
        
        # Query to get entitlements for user
        query = f"""
            SELECT e.{ENTITLEMENT_COLUMN_ID}, e.{ENTITLEMENT_COLUMN_VALUE}, 
                   e.{ENTITLEMENT_COLUMN_DISPLAY}, e.{ENTITLEMENT_COLUMN_TYPE}
            FROM {SQL_ENTITLEMENTS_TABLE} e
            INNER JOIN {SQL_USER_ENTITLEMENTS_TABLE} ue 
                ON e.{ENTITLEMENT_COLUMN_ID} = ue.entitlement_id
            WHERE ue.user_id = ?
        """
        
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        
        entitlements = []
        for row in rows:
            entitlement = {
                "value": row[1],  # entitlement value
                "type": row[3] if row[3] else "default"  # entitlement type
            }
            
            # Add display name if available
            if row[2]:  # display name
                entitlement["display"] = row[2]
            
            entitlements.append(entitlement)
        
        return entitlements
    except Exception as e:
        # If entitlement tables don't exist or error occurs, return empty list
        print(f"Warning: Could not fetch entitlements for user {user_id}: {e}")
        return []

def map_entitlement_to_scim(row, column_names):
    """Map SQL row to SCIM 2.0 entitlement format"""
    col_dict = {name: idx for idx, name in enumerate(column_names)}
    
    entitlement = {
        "schemas": [ENTITLEMENT_SCHEMA],
        "id": str(row[col_dict[ENTITLEMENT_COLUMN_ID]]) if ENTITLEMENT_COLUMN_ID in col_dict else "",
        "value": row[col_dict[ENTITLEMENT_COLUMN_VALUE]] if ENTITLEMENT_COLUMN_VALUE in col_dict else "",
        "type": row[col_dict[ENTITLEMENT_COLUMN_TYPE]] if ENTITLEMENT_COLUMN_TYPE in col_dict else "default",
        "meta": {
            "resourceType": "Entitlement",
            "created": datetime.utcnow().isoformat() + "Z",
            "lastModified": datetime.utcnow().isoformat() + "Z",
            "location": f"/scim/v2/Entitlements/{row[col_dict[ENTITLEMENT_COLUMN_ID]]}" if ENTITLEMENT_COLUMN_ID in col_dict else ""
        }
    }
    
    # Add optional display name
    if ENTITLEMENT_COLUMN_DISPLAY in col_dict and row[col_dict[ENTITLEMENT_COLUMN_DISPLAY]]:
        entitlement["display"] = row[col_dict[ENTITLEMENT_COLUMN_DISPLAY]]
    
    return entitlement

def map_sql_to_scim_v2(row, column_names, conn=None):
    """Map SQL row to SCIM 2.0 user format with entitlements"""
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
    
    # Add entitlements if connection provided
    if conn and DB_COLUMN_ID in col_dict:
        user_id = str(row[col_dict[DB_COLUMN_ID]])
        entitlements = get_user_entitlements(user_id, conn)
        if entitlements:
            user["entitlements"] = entitlements
    
    return user

@app.route('/scim/v2/Users', methods=['GET'])
@auth.login_required
def get_users():
    """Get list of users with pagination support and entitlements (SCIM 2.0)"""
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
        
        # Map to SCIM 2.0 format with entitlements
        resources = [map_sql_to_scim_v2(row, column_names, conn) for row in rows]
        
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
    """Get a specific user by ID with entitlements (SCIM 2.0)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {SQL_TABLE} WHERE {DB_COLUMN_ID} = ?"
        cursor.execute(query, (user_id,))
        
        row = cursor.fetchone()
        column_names = [column[0] for column in cursor.description]
        
        if not row:
            conn.close()
            return jsonify({
                "schemas": [ERROR_SCHEMA],
                "status": "404",
                "detail": "User not found"
            }), 404
        
        user = map_sql_to_scim_v2(row, column_names, conn)
        conn.close()
        
        return jsonify(user), 200
        
    except Exception as e:
        return jsonify({
            "schemas": [ERROR_SCHEMA],
            "status": "500",
            "detail": str(e)
        }), 500

@app.route('/scim/v2/Entitlements', methods=['GET'])
@auth.login_required
def get_entitlements():
    """Get list of entitlements with pagination support (SCIM 2.0)"""
    try:
        # Pagination parameters
        start_index = int(request.args.get('startIndex', 1))
        count = int(request.args.get('count', 100))
        
        # Calculate SQL OFFSET and FETCH
        offset = start_index - 1
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM {SQL_ENTITLEMENTS_TABLE}")
        total_results = cursor.fetchone()[0]
        
        # Get paginated entitlements
        query = f"""
            SELECT * FROM {SQL_ENTITLEMENTS_TABLE}
            ORDER BY {ENTITLEMENT_COLUMN_ID}
            OFFSET {offset} ROWS
            FETCH NEXT {count} ROWS ONLY
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]
        
        # Map to SCIM 2.0 format
        resources = [map_entitlement_to_scim(row, column_names) for row in rows]
        
        conn.close()
        
        # SCIM 2.0 List Response
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

@app.route('/scim/v2/Entitlements/<entitlement_id>', methods=['GET'])
@auth.login_required
def get_entitlement(entitlement_id):
    """Get a specific entitlement by ID (SCIM 2.0)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {SQL_ENTITLEMENTS_TABLE} WHERE {ENTITLEMENT_COLUMN_ID} = ?"
        cursor.execute(query, (entitlement_id,))
        
        row = cursor.fetchone()
        column_names = [column[0] for column in cursor.description]
        
        conn.close()
        
        if not row:
            return jsonify({
                "schemas": [ERROR_SCHEMA],
                "status": "404",
                "detail": "Entitlement not found"
            }), 404
        
        entitlement = map_entitlement_to_scim(row, column_names)
        return jsonify(entitlement), 200
        
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
        "totalResults": 3,
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
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
                "id": ENTITLEMENT_SCHEMA,
                "name": "Entitlement",
                "description": "Entitlement (Role, Permission, Group)"
            }
        ]
    }
    return jsonify(schemas), 200

@app.route('/scim/v2/ResourceTypes', methods=['GET'])
def get_resource_types():
    """Return SCIM 2.0 resource types"""
    resource_types = {
        "schemas": [LIST_RESPONSE_SCHEMA],
        "totalResults": 2,
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
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Entitlement",
                "name": "Entitlement",
                "endpoint": "/Entitlements",
                "description": "Entitlement (Role, Permission, Group)",
                "schema": ENTITLEMENT_SCHEMA
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
        "message": "Okta SCIM 2.0 Connector with Entitlements for SQL Server",
        "version": "2.0.0",
        "scimVersion": "2.0",
        "features": ["users", "entitlements", "identity-governance"],
        "requirements": {
            "oppAgent": "2.1.0 or later",
            "earlyAccess": "On-premises provisioning and entitlements"
        },
        "enableAt": "Admin Console → Settings → Features → Early Access",
        "documentation": "https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm",
        "endpoints": {
            "users": "/scim/v2/Users",
            "entitlements": "/scim/v2/Entitlements",
            "schemas": "/scim/v2/Schemas",
            "resourceTypes": "/scim/v2/ResourceTypes",
            "config": "/scim/v2/ServiceProviderConfig",
            "health": "/health"
        }
    }), 200

if __name__ == '__main__':
    print(f"Starting SCIM 2.0 server with Entitlements on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Database: {DB_SERVER}/{DB_NAME}")
    print(f"User Table: {SQL_TABLE}")
    print(f"Entitlement Table: {SQL_ENTITLEMENTS_TABLE}")
    print(f"User-Entitlement Table: {SQL_USER_ENTITLEMENTS_TABLE}")
    print(f"Authentication: {SCIM_USERNAME}")
    print(f"\n⚠️  SCIM 2.0 with Entitlements - Requirements:")
    print(f"   • Okta Provisioning Agent 2.1.0 or later")
    print(f"   • Early Access: On-premises provisioning and entitlements")
    print(f"   • Enable at: Admin Console → Settings → Features → Early Access")
    print(f"   • Docs: https://help.okta.com/en-us/content/topics/provisioning/opp/opp-entitlements.htm")
    print(f"\n✨ Features:")
    print(f"   • User provisioning with entitlements")
    print(f"   • Entitlement discovery")
    print(f"   • Identity Governance integration\n")
    
    # Run server
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)