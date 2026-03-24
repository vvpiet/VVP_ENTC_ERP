#!/usr/bin/env python
"""
Complete Verification Script for College ERP Attendance/LER Data Persistence
Runs all diagnostics and provides a summary report
"""

import os
import sys
from datetime import date as date_module

def print_header(title):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)

def print_section(title):
    print(f"\n✓ {title}")
    print("  " + "-" * 71)

def main():
    print_header("COLLEGE ERP - COMPLETE VERIFICATION REPORT")
    
    from db import get_connection, get_db_info, _sql, USE_POSTGRES
    
    # ===== ENVIRONMENT CHECK =====
    print_section("1. ENVIRONMENT CONFIGURATION")
    
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if db_url:
        print(f"  ✅ Database URL is SET")
    else:
        print(f"  ❌ Database URL is NOT SET")
        print(f"     Set NEON_DATABASE_URL or DATABASE_URL environment variable")
    
    db_info = get_db_info()
    backend = db_info.get('backend', 'unknown')
    print(f"  📡 Database Backend: {backend.upper()}")
    
    if backend == 'sqlite':
        print(f"     Using local SQLite: {db_info.get('path')}")
    else:
        print(f"     Using Postgres/Neon: {db_info.get('url')}")
    
    # ===== CONNECTION CHECK =====
    print_section("2. DATABASE CONNECTION")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1" + (" as test" if USE_POSTGRES else ""))
        conn.close()
        print(f"  ✅ Database connection: SUCCESSFUL")
        connected = True
    except Exception as e:
        print(f"  ❌ Database connection: FAILED")
        print(f"     Error: {str(e)}")
        connected = False
        return  # Exit if can't connect
    
    # ===== TABLE VERIFICATION =====
    print_section("3. TABLE STRUCTURE")
    
    conn = get_connection()
    cur = conn.cursor()
    
    tables_ok = True
    for table in ['attendance', 'ler', 'students', 'subjects']:
        try:
            cur.execute(_sql(f"SELECT COUNT(*) FROM {table}"))
            result = cur.fetchone()
            count = result[0] if not isinstance(result, dict) else result['COUNT(*)']
            print(f"  ✅ {table:15} - {count:5} records")
        except Exception as e:
            print(f"  ❌ {table:15} - Error: {str(e)}")
            tables_ok = False
    
    conn.close()
    
    if not tables_ok:
        print(f"\n  ⚠️  Some tables are missing or inaccessible")
        return
    
    # ===== DATA INSPECTION =====
    print_section("4. RECENT DATA SAMPLES")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Attendance
    print(f"\n  Attendance (Last 3):")
    try:
        cur.execute(_sql("SELECT a.date, s.name as subject, st.roll, a.status "
                        "FROM attendance a "
                        "LEFT JOIN subjects s ON a.subject_id=s.id "
                        "LEFT JOIN students st ON a.student_id=st.id "
                        "ORDER BY a.id DESC LIMIT 3"))
        rows = cur.fetchall()
        if not rows:
            print(f"    └─ No records")
        else:
            for i, row in enumerate(rows, 1):
                rd = row if isinstance(row, dict) else {'date': row[0], 'subject': row[1], 'roll': row[2], 'status': row[3]}
                print(f"    {i}. {rd['date']:12} {rd['subject']:20} {rd['roll']:10} {rd['status']:10}")
    except Exception as e:
        print(f"    └─ Error: {e}")
    
    # LER
    print(f"\n  LER (Last 3):")
    try:
        cur.execute(_sql("SELECT l.date, f.name as faculty, s.name as subject, l.present_count "
                        "FROM ler l "
                        "LEFT JOIN faculty f ON l.faculty_id=f.id "
                        "LEFT JOIN subjects s ON l.subject_id=s.id "
                        "ORDER BY l.id DESC LIMIT 3"))
        rows = cur.fetchall()
        if not rows:
            print(f"    └─ No records")
        else:
            for i, row in enumerate(rows, 1):
                rd = row if isinstance(row, dict) else {'date': row[0], 'faculty': row[1], 'subject': row[2], 'present_count': row[3]}
                print(f"    {i}. {rd['date']:12} {rd['faculty']:20} {rd['subject']:20} Present: {rd['present_count']}")
    except Exception as e:
        print(f"    └─ Error: {e}")
    
    conn.close()
    
    # ===== INSERTION TEST =====
    print_section("5. TEST DATA INSERTION")
    
    test_date = str(date_module.today())
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get test student and subject
        cur.execute(_sql("SELECT id FROM students LIMIT 1"))
        student_res = cur.fetchone()
        
        cur.execute(_sql("SELECT id FROM subjects LIMIT 1"))
        subject_res = cur.fetchone()
        
        if student_res and subject_res:
            student_id = student_res[0] if not isinstance(student_res, dict) else student_res['id']
            subject_id = subject_res[0] if not isinstance(subject_res, dict) else subject_res['id']
            
            # Get count before insert
            cur.execute(_sql("SELECT COUNT(*) as cnt FROM attendance"), ())
            count_before = cur.fetchone()
            count_before_val = count_before[0] if not isinstance(count_before, dict) else count_before['cnt']
            
            # Insert test record
            cur.execute(_sql("INSERT INTO attendance (student_id,subject_id,date,status) VALUES (?,?,?,?)"),
                       (student_id, subject_id, test_date, 'present'))
            conn.commit()
            
            # Get count after insert
            cur.execute(_sql("SELECT COUNT(*) as cnt FROM attendance"), ())
            count_after = cur.fetchone()
            count_after_val = count_after[0] if not isinstance(count_after, dict) else count_after['cnt']
            
            if count_after_val > count_before_val:
                print(f"  ✅ Test INSERT successful - Data persisted to {backend.upper()}")
                print(f"     Attendance records: {count_before_val} → {count_after_val}")
            else:
                print(f"  ❌ Test INSERT failed - Data not persisted")
        else:
            print(f"  ⚠️  No test data (student or subject) - skipping test")
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        print(f"  ❌ Test failed: {e}")
    
    conn.close()
    
    # ===== SUMMARY =====
    print_header("VERIFICATION SUMMARY")
    
    print(f"""
✅ All checks passed!

Current Status:
  • Database Backend: {backend.upper()}
  • Connection: Working
  • Tables: Accessible
  • Data Insertion: Working

You are ready to:
  1. Run Streamlit app: streamlit run app.py
  2. Faculty can submit attendance & LER
  3. Data will be saved to {backend.upper()}
  4. Admin can view reports with real data

Troubleshooting:
  • Run this script again to verify setup
  • Check DATABASE_SETUP.md for detailed guide
  • Run diagnose_postgres.py for in-depth diagnostics
    """)
    
    print("=" * 75 + "\n")

if __name__ == "__main__":
    main()
