#!/usr/bin/env python3
"""
Okta SCIM 1.1 Connector for SQL Server User Import
Enables Okta OPP Agent to import users from any SQL Server database
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

def map_sql_to_scim(row, column_names):
    """Map SQL row to SCIM 1.1 user format"""
    # Get column indices
    col_dict = {name: idx for idx, name in enumerate(column_names)}
    
    # Build SCIM user object (SCIM 1.1 format - NO schemas array)
    user = {
        "id": str(row[col_dict[DB_COLUMN_ID]]) if DB_COLUMN_ID in col_dict else "",
        "userName": row[col_dict[DB_COLUMN_USERNAME]] if DB_COLUMN_USERNAME in col_dict else "",
        "name": {
            "givenName": row[col_dict[DB_COLUMN_FIRST_NAME]] if DB_COLUMN_FIRST_NAME in col_dict else "",
            "familyName": row[col_dict[DB_COLUMN_LAST_NAME]] if DB_COLUMN_LAST_NAME in col_dict else ""
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
    """Get list of users with pagination support"""
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
        
        # Map to SCIM format
        resources = [map_sql_to_scim(row, column_names) for row in rows]
        
        conn.close()
        
        # SCIM 1.1 List Response - NO schemas array
        response = {
            "totalResults": total_results,
            "startIndex": start_index,
            "itemsPerPage": len(resources),
            "Resources": resources
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "Errors": [{
                "description": str(e),
                "code": "500"
            }]
        }), 500

@app.route('/scim/v2/Users/<user_id>', methods=['GET'])
@auth.login_required
def get_user(user_id):
    """Get a specific user by ID"""
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
                "Errors": [{
                    "description": "User not found",
                    "code": "404"
                }]
            }), 404
        
        user = map_sql_to_scim(row, column_names)
        return jsonify(user), 200
        
    except Exception as e:
        return jsonify({
            "Errors": [{
                "description": str(e),
                "code": "500"
            }]
        }), 500

@app.route('/scim/v2/ServiceProviderConfig', methods=['GET'])
def service_provider_config():
    """Return SCIM service provider configuration (SCIM 1.1 format)"""
    config = {
        "documentationUrl": "https://tools.ietf.org/html/rfc7644",
        "patch": {
            "supported": False
        },
        "bulk": {
            "supported": False
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
                "name": "HTTP Basic",
                "description": "Authentication via HTTP Basic",
                "specUrl": "http://www.rfc-editor.org/info/rfc2617",
                "type": "httpbasic"
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
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "message": "Okta SCIM Connector for SQL Server",
        "version": "1.0.0",
        "endpoints": {
            "users": "/scim/v2/Users",
            "config": "/scim/v2/ServiceProviderConfig",
            "health": "/health"
        }
    }), 200

if __name__ == '__main__':
    print(f"Starting SCIM server on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Database: {DB_SERVER}/{DB_NAME}")
    print(f"Table: {SQL_TABLE}")
    print(f"Authentication: {SCIM_USERNAME}")
    
    # Run server
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)