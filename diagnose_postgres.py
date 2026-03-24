"""
Diagnostic script to verify attendance and LER data persistence to Postgres/Neon.
Helps identify where data insertion might be failing.
"""

import os
from db import get_connection, get_db_info, _sql, USE_POSTGRES

def diagnose():
    print("=" * 70)
    print("COLLEGE ERP - DATABASE PERSISTENCE DIAGNOSTIC")
    print("=" * 70)
    
    # Check connection info
    db_info = get_db_info()
    print(f"\n📡 Database Backend: {db_info.get('backend').upper()}")
    if db_info.get('backend') == 'postgres':
        print(f"   URL: {db_info.get('url')}")
        print(f"   USE_POSTGRES: {USE_POSTGRES}")
        print(f"   DATABASE_URL: {db_info.get('url') is not None}")
    else:
        print(f"   Path: {db_info.get('path')}")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # === Check Table Structures ===
    print("\n" + "=" * 70)
    print("📋 TABLE STRUCTURE CHECK")
    print("=" * 70)
    
    # Check attendance table
    print("\n✓ Checking 'attendance' table...")
    try:
        cur.execute(_sql("SELECT COUNT(*) as cnt FROM attendance"))
        result = cur.fetchone()
        count = result['cnt'] if isinstance(result, dict) else result[0]
        print(f"  └─ Total attendance records: {count}")
    except Exception as e:
        print(f"  ❌ Error querying attendance: {e}")
    
    # Check ler table
    print("\n✓ Checking 'ler' table...")
    try:
        cur.execute(_sql("SELECT COUNT(*) as cnt FROM ler"))
        result = cur.fetchone()
        count = result['cnt'] if isinstance(result, dict) else result[0]
        print(f"  └─ Total LER records: {count}")
    except Exception as e:
        print(f"  ❌ Error querying ler: {e}")
    
    # === Check Recent Data ===
    print("\n" + "=" * 70)
    print("📊 RECENT DATA CHECK (Last 5 entries)")
    print("=" * 70)
    
    # Recent attendance
    print("\n✓ Last 5 attendance records:")
    try:
        cur.execute(_sql("SELECT a.id, a.date, s.name as subject, st.roll, a.status FROM attendance a "
                        "LEFT JOIN subjects s ON a.subject_id=s.id "
                        "LEFT JOIN students st ON a.student_id=st.id "
                        "ORDER BY a.id DESC LIMIT 5"))
        att_rows = cur.fetchall()
        if not att_rows:
            print("  └─ No attendance records found")
        else:
            for i, row in enumerate(att_rows, 1):
                row_dict = row if isinstance(row, dict) else {
                    'id': row[0],
                    'date': row[1],
                    'subject': row[2],
                    'roll': row[3],
                    'status': row[4]
                }
                print(f"  {i}. ID:{row_dict['id']} Date:{row_dict['date']} "
                      f"Subject:{row_dict['subject']} Roll:{row_dict['roll']} "
                      f"Status:{row_dict['status']}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Recent LER
    print("\n✓ Last 5 LER records:")
    try:
        cur.execute(_sql("SELECT l.id, l.date, f.name as faculty, s.name as subject, "
                        "l.lecture_number, l.present_count FROM ler l "
                        "LEFT JOIN faculty f ON l.faculty_id=f.id "
                        "LEFT JOIN subjects s ON l.subject_id=s.id "
                        "ORDER BY l.id DESC LIMIT 5"))
        ler_rows = cur.fetchall()
        if not ler_rows:
            print("  └─ No LER records found")
        else:
            for i, row in enumerate(ler_rows, 1):
                row_dict = row if isinstance(row, dict) else {
                    'id': row[0],
                    'date': row[1],
                    'faculty': row[2],
                    'subject': row[3],
                    'lecture_number': row[4],
                    'present_count': row[5]
                }
                print(f"  {i}. ID:{row_dict['id']} Date:{row_dict['date']} "
                      f"Faculty:{row_dict['faculty']} Subject:{row_dict['subject']} "
                      f"Lecture:{row_dict['lecture_number']} Present:{row_dict['present_count']}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # === Data Insertion Test ===
    print("\n" + "=" * 70)
    print("🧪 TEST DATA INSERTION")
    print("=" * 70)
    
    from datetime import date as date_module
    test_date = date_module.today()
    
    # Test attendance insertion
    print(f"\n✓ Testing attendance insertion (date: {test_date})...")
    try:
        # Get a student and subject
        cur.execute(_sql("SELECT id FROM students LIMIT 1"))
        student_res = cur.fetchone()
        if student_res:
            student_id = student_res['id'] if isinstance(student_res, dict) else student_res[0]
            
            cur.execute(_sql("SELECT id FROM subjects LIMIT 1"))
            subject_res = cur.fetchone()
            if subject_res:
                subject_id = subject_res['id'] if isinstance(subject_res, dict) else subject_res[0]
                
                # Insert test record
                cur.execute(_sql("INSERT INTO attendance (student_id,subject_id,date,status) VALUES (?,?,?,?)"),
                           (student_id, subject_id, str(test_date), 'present'))
                conn.commit()
                print(f"  ✓ Inserted test attendance record")
                
                # Verify immediately
                cur.execute(_sql("SELECT COUNT(*) as cnt FROM attendance WHERE date=? AND status='present'"),
                           (str(test_date),))
                verify_res = cur.fetchone()
                verify_count = verify_res['cnt'] if isinstance(verify_res, dict) else verify_res[0]
                print(f"  ✓ Verification: {verify_count} matching records found in DB")
                
                if verify_count > 0:
                    print(f"  ✅ Attendance insertion SUCCESSFUL - data persisted to DB")
                else:
                    print(f"  ❌ Attendance insertion FAILED - data not persisted")
        else:
            print("  ⚠️  No test student found - skipping insertion test")
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        print(f"  ❌ Error during test: {e}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("📝 SUMMARY")
    print("=" * 70)
    print("""
If data insertion is failing:
1. Check DATABASE_URL/NEON_DATABASE_URL environment variables are set
2. Verify network connectivity to Postgres/Neon server
3. Check database user has INSERT permissions on tables
4. Ensure SSL certificate validation is working (sslmode='require')
5. Review error messages in Streamlit app for detailed error traces

If test insertion succeeded but app data isn't appearing:
- The app might be using a different database or credentials
- Check that form submissions are being validated correctly
- Look for exception handling that might suppress errors silently
    """)
    print("=" * 70 + "\n")

if __name__ == "__main__":
    diagnose()
