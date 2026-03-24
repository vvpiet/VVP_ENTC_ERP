"""
Setup and verification script for College ERP database configuration.
Ensures Postgres/Neon environment variables are properly set.
"""

import os
import sys

def setup_postgres_env():
    """Guide user through setting up Postgres environment variables."""
    print("\n" + "=" * 70)
    print("COLLEGE ERP - POSTGRES/NEON ENVIRONMENT SETUP")
    print("=" * 70)
    
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    
    if db_url:
        print(f"\n✅ Database URL is SET")
        print(f"   Backend: {"Postgres/Neon" if db_url else "SQLite"}")
        return True
    else:
        print(f"\n❌ Database URL is NOT SET")
        print(f"\nTo connect to Postgres/Neon, set one of these environment variables:")
        print("""
Option 1: DATABASE_URL
   Example: postgresql://user:password@host:port/database?sslmode=require

Option 2: NEON_DATABASE_URL
   Example: Add this directly from your Neon console
   
Commands to set (choose ONE):

Windows PowerShell:
   $env:NEON_DATABASE_URL = "your_database_url_here"
   
Windows CMD:
   set NEON_DATABASE_URL=your_database_url_here
   
Windows Environment Variables (Persistent):
   1. Open System Properties → Environment Variables
   2. Click "New" under "User variables"
   3. Variable name: NEON_DATABASE_URL
   4. Variable value: your_database_url_here
   5. Click OK and restart your terminal/Streamlit

After setting the variable, restart your Streamlit app:
   streamlit run app.py

Then verify with:
   python diagnose_postgres.py
        """)
        return False

def check_database_connection():
    """Test connection to the configured database."""
    from db import get_connection, get_db_info, USE_POSTGRES
    
    db_info = get_db_info()
    backend = db_info.get('backend', 'unknown')
    
    print(f"\n📡 Current Backend: {backend.upper()}")
    
    if backend == 'sqlite':
        print(f"   Path: {db_info.get('path')}")
    else:
        print(f"   URL: {db_info.get('url')}")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Test query
        cur.execute("SELECT 1" + (" as test" if USE_POSTGRES else ""))
        conn.close()
        
        print(f"\n✅ Database connection: SUCCESSFUL")
        return True
    except Exception as e:
        print(f"\n❌ Database connection: FAILED")
        print(f"   Error: {str(e)}")
        return False

def main():
    print("\n" + "=" * 70)
    print("COLLEGE ERP - DATABASE VERIFICATION")
    print("=" * 70)
    
    # Check environment setup
    env_ok = setup_postgres_env()
    
    # Try to connect
    if env_ok:
        conn_ok = check_database_connection()
        if conn_ok:
            print(f"\n✅ Database is properly configured and accessible")
            print(f"\n   Attendance and LER data will be saved to Postgres/Neon")
        else:
            print(f"\n⚠️  Database URL is set but connection failed")
            print(f"   Please check:")
            print(f"   • Database URL is correct")
            print(f"   • Network connection to database")
            print(f"   • Database credentials")
            print(f"   • SSL certificate requirements")
    else:
        print(f"\n⚠️  DATABASE_URL/NEON_DATABASE_URL is not set")
        print(f"   Currently using SQLite (college.db)")
        print(f"\n   To use Postgres/Neon:")
        print(f"   1. Set one of the environment variables above")
        print(f"   2. Restart your terminal")
        print(f"   3. Run: streamlit run app.py")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()
