#!/usr/bin/env python3
"""
Database Connection Test Utility
Tests SQL Server connectivity and displays sample data
"""

import pyodbc
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.WHITE}{text}{Colors.END}")

def test_connection():
    """Test database connection and display sample data"""
    
    print_header("Okta SCIM SQL Connector - Database Connection Test")
    
    # Get configuration from environment
    db_driver = os.getenv('DB_DRIVER', 'SQL Server')
    db_server = os.getenv('DB_SERVER')
    db_name = os.getenv('DB_NAME')
    db_username = os.getenv('DB_USERNAME')
    db_password = os.getenv('DB_PASSWORD')
    table_name = os.getenv('SQL_TABLE', 'users')
    
    # Display configuration (hide password)
    print_info(f"Configuration:")
    print_info(f"  Driver:   {db_driver}")
    print_info(f"  Server:   {db_server}")
    print_info(f"  Database: {db_name}")
    print_info(f"  Username: {db_username}")
    print_info(f"  Password: {'*' * len(db_password) if db_password else '(not set)'}")
    print_info(f"  Table:    {table_name}")
    print()
    
    # Check for missing configuration
    if not all([db_server, db_name, db_username, db_password]):
        print_error("Missing required configuration in .env file")
        print_info("\nRequired environment variables:")
        print_info("  - DB_SERVER")
        print_info("  - DB_NAME")
        print_info("  - DB_USERNAME")
        print_info("  - DB_PASSWORD")
        print_info("\nPlease edit your .env file and try again.")
        return False
    
    # Build connection string
    conn_str = (
        f"DRIVER={{{db_driver}}};"
        f"SERVER={db_server};"
        f"DATABASE={db_name};"
        f"UID={db_username};"
        f"PWD={db_password}"
    )
    
    try:
        print_info("Connecting to database...")
        conn = pyodbc.connect(conn_str, timeout=10)
        print_success("Database connection established!")
        print()
        
        cursor = conn.cursor()
        
        # Test 1: Get row count
        print_info(f"Test 1: Counting rows in '{table_name}' table...")
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            print_success(f"Found {row_count:,} total rows")
            print()
        except pyodbc.Error as e:
            print_error(f"Failed to count rows: {e}")
            print_warning(f"Table '{table_name}' may not exist")
            print_info("\nTo list all tables, run this SQL:")
            print_info("  SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            conn.close()
            return False
        
        # Test 2: Get column information
        print_info(f"Test 2: Retrieving column information...")
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        if columns:
            print_success(f"Found {len(columns)} columns:")
            print()
            print_info(f"{'Column Name':<30} {'Data Type':<20} {'Max Length':<15} {'Nullable'}")
            print_info("-" * 80)
            for col in columns:
                col_name, data_type, max_len, nullable = col
                max_len_str = str(max_len) if max_len else 'N/A'
                print_info(f"{col_name:<30} {data_type:<20} {max_len_str:<15} {nullable}")
            print()
        
        # Test 3: Get sample data
        print_info(f"Test 3: Retrieving sample data (first 5 rows)...")
        cursor.execute(f"SELECT TOP 5 * FROM {table_name}")
        
        rows = cursor.fetchall()
        column_names = [column[0] for column in cursor.description]
        
        if rows:
            print_success(f"Retrieved {len(rows)} sample rows")
            print()
            
            # Print column headers
            header = " | ".join([f"{name:<20}" for name in column_names])
            print_info(header)
            print_info("-" * len(header))
            
            # Print data rows
            for row in rows:
                row_str = " | ".join([f"{str(val):<20}"[:20] for val in row])
                print_info(row_str)
            print()
        else:
            print_warning("Table is empty (0 rows)")
            print()
        
        # Test 4: Verify column mappings
        print_info("Test 4: Verifying column mappings from .env...")
        
        mappings = {
            'ID': os.getenv('DB_COLUMN_ID'),
            'Username': os.getenv('DB_COLUMN_USERNAME'),
            'Email': os.getenv('DB_COLUMN_EMAIL'),
            'First Name': os.getenv('DB_COLUMN_FIRST_NAME'),
            'Last Name': os.getenv('DB_COLUMN_LAST_NAME'),
            'Display Name': os.getenv('DB_COLUMN_DISPLAY_NAME'),
            'Active': os.getenv('DB_COLUMN_ACTIVE'),
            'External ID': os.getenv('DB_COLUMN_EXTERNAL_ID'),
        }
        
        column_names_lower = [col.lower() for col in column_names]
        mapping_issues = []
        
        for scim_field, db_column in mappings.items():
            if db_column:
                if db_column.lower() in column_names_lower:
                    print_success(f"{scim_field:<15} → {db_column} (✓ exists)")
                else:
                    print_error(f"{scim_field:<15} → {db_column} (✗ NOT FOUND)")
                    mapping_issues.append(f"Column '{db_column}' not found in table")
            else:
                print_info(f"{scim_field:<15} → (not configured)")
        
        print()
        
        # Test 5: Test SCIM query
        print_info("Test 5: Testing SCIM-style query...")
        
        id_col = os.getenv('DB_COLUMN_ID', 'id')
        try:
            cursor.execute(f"""
                SELECT TOP 3 *
                FROM {table_name}
                ORDER BY {id_col}
            """)
            
            scim_rows = cursor.fetchall()
            print_success(f"SCIM query successful! Retrieved {len(scim_rows)} rows")
            print()
        except pyodbc.Error as e:
            print_error(f"SCIM query failed: {e}")
            print_warning(f"Check that DB_COLUMN_ID ('{id_col}') is correct in .env")
            print()
        
        # Close connection
        conn.close()
        
        # Final summary
        print_header("Test Summary")
        
        if mapping_issues:
            print_warning("Column Mapping Issues Found:")
            for issue in mapping_issues:
                print_error(f"  - {issue}")
            print()
            print_info("Update your .env file to fix these mappings.")
            print()
            return False
        else:
            print_success("All tests passed!")
            print()
            print_info("Next steps:")
            print_info("  1. Review column mappings above")
            print_info("  2. Start SCIM server: python inbound_app.py")
            print_info("  3. Test health check: curl http://localhost:8080/health")
            print_info("  4. Configure Okta OPP Agent")
            print()
            return True
        
    except pyodbc.InterfaceError as e:
        print_error(f"Database driver error: {e}")
        print()
        print_info("Troubleshooting:")
        print_info("  - Verify ODBC Driver for SQL Server is installed")
        print_info("  - Check DB_DRIVER setting in .env")
        print_info("  - Install driver: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
        return False
        
    except pyodbc.OperationalError as e:
        print_error(f"Connection failed: {e}")
        print()
        print_info("Troubleshooting:")
        print_info("  - Verify DB_SERVER is correct and reachable")
        print_info("  - Check if SQL Server allows remote connections")
        print_info("  - Verify firewall allows port 1433")
        print_info("  - Confirm SQL Server authentication is enabled")
        print_info("  - Test: Test-NetConnection -ComputerName <server> -Port 1433")
        return False
        
    except pyodbc.Error as e:
        print_error(f"Database error: {e}")
        print()
        print_info("Check your database configuration in .env file")
        return False
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

if __name__ == '__main__':
    try:
        success = test_connection()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        print_warning("Test cancelled by user")
        exit(130)