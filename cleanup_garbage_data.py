"""
Comprehensive cleanup script to remove all garbage/placeholder rows from database.
This handles rows where column names were accidentally stored as data values.
"""

from db import get_connection, _sql

def cleanup_garbage_data():
    conn = get_connection()
    c = conn.cursor()
    
    print("🧹 Starting comprehensive garbage data cleanup...")
    
    # List of keywords that indicate garbage/header rows
    garbage_values = ['date', 'subject', 'status', 'roll', 'student', 'class', 'name', 'faculty', 
                      'class_level', 'lecture_number', 'syllabus_covered_pct', 'present_count', 
                      'absent_rolls', 'null', 'n/a', 'none', '']
    
    # === ATTENDANCE TABLE CLEANUP ===
    print("\n📋 Cleaning attendance table...")
    
    # Delete rows where date is a garbage value (case-insensitive)
    for val in garbage_values:
        c.execute(_sql("DELETE FROM attendance WHERE LOWER(CAST(date AS TEXT)) = ?"), (val.lower(),))
        if c.rowcount > 0:
            print(f"  ✓ Deleted {c.rowcount} rows where date='{val}'")
    
    # Delete rows where status is a garbage value
    for val in garbage_values:
        c.execute(_sql("DELETE FROM attendance WHERE LOWER(status) = ?"), (val.lower(),))
        if c.rowcount > 0:
            print(f"  ✓ Deleted {c.rowcount} rows where status='{val}'")
    
    # Delete rows where date is NULL or empty
    c.execute(_sql("DELETE FROM attendance WHERE date IS NULL OR date = ''"))
    if c.rowcount > 0:
        print(f"  ✓ Deleted {c.rowcount} rows where date is NULL/empty")
    
    # Delete rows where status is NULL or empty
    c.execute(_sql("DELETE FROM attendance WHERE status IS NULL OR status = ''"))
    if c.rowcount > 0:
        print(f"  ✓ Deleted {c.rowcount} rows where status is NULL/empty")
    
    # === STUDENTS TABLE CLEANUP ===
    print("\n👥 Cleaning students table...")
    
    # Delete rows where class_level is a garbage value
    for val in ['class', 'class_level', 'null', 'n/a', 'none']:
        c.execute(_sql("DELETE FROM students WHERE LOWER(class_level) = ?"), (val.lower(),))
        if c.rowcount > 0:
            print(f"  ✓ Deleted {c.rowcount} rows where class_level='{val}'")
    
    # Delete rows where class_level is NULL or empty
    c.execute(_sql("DELETE FROM students WHERE class_level IS NULL OR class_level = ''"))
    if c.rowcount > 0:
        print(f"  ✓ Deleted {c.rowcount} rows where class_level is NULL/empty")
    
    # === LER TABLE CLEANUP ===
    print("\n📊 Cleaning LER (Lecture Engagement Register) table...")
    
    # Delete rows where date is a garbage value
    for val in garbage_values:
        c.execute(_sql("DELETE FROM ler WHERE LOWER(CAST(date AS TEXT)) = ?"), (val.lower(),))
        if c.rowcount > 0:
            print(f"  ✓ Deleted {c.rowcount} rows where date='{val}'")
    
    # Delete rows where date is NULL
    c.execute(_sql("DELETE FROM ler WHERE date IS NULL OR date = ''"))
    if c.rowcount > 0:
        print(f"  ✓ Deleted {c.rowcount} rows where date is NULL/empty")
    
    # === SUBJECTS TABLE CLEANUP ===
    print("\n📚 Cleaning subjects table...")
    
    # Delete rows where name is a garbage value
    for val in ['subject', 'name', 'null', 'n/a', 'none']:
        c.execute(_sql("DELETE FROM subjects WHERE LOWER(name) = ?"), (val.lower(),))
        if c.rowcount > 0:
            print(f"  ✓ Deleted {c.rowcount} rows where name='{val}'")
    
    conn.commit()
    
    # === VERIFICATION ===
    print("\n✔️ Verification - Row counts after cleanup:")
    
    c.execute(_sql("SELECT COUNT(*) FROM attendance"))
    att_count = c.fetchone()
    att_count = att_count[0] if not isinstance(att_count, dict) else att_count['COUNT(*)']
    print(f"  • Attendance records: {att_count}")
    
    c.execute(_sql("SELECT COUNT(*) FROM students"))
    stu_count = c.fetchone()
    stu_count = stu_count[0] if not isinstance(stu_count, dict) else stu_count['COUNT(*)']
    print(f"  • Student records: {stu_count}")
    
    c.execute(_sql("SELECT COUNT(*) FROM ler"))
    ler_count = c.fetchone()
    ler_count = ler_count[0] if not isinstance(ler_count, dict) else ler_count['COUNT(*)']
    print(f"  • LER records: {ler_count}")
    
    c.execute(_sql("SELECT COUNT(*) FROM subjects"))
    sub_count = c.fetchone()
    sub_count = sub_count[0] if not isinstance(sub_count, dict) else sub_count['COUNT(*)']
    print(f"  • Subject records: {sub_count}")
    
    conn.close()
    print("\n✅ Cleanup completed successfully!")

if __name__ == "__main__":
    cleanup_garbage_data()
