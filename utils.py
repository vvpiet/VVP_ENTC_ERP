from db import get_connection, _sql


def check_alerts_threshold(threshold=75):
    conn = get_connection()
    c = conn.cursor()
    # compute attendance percentage per student-subject
    query = '''
    SELECT a.student_id, sub.id as subject_id,
           SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)*100.0/COUNT(*) as pct
    FROM attendance a
    JOIN subjects sub ON a.subject_id=sub.id
    GROUP BY a.student_id, sub.id
    '''
    # psycopg2's cursor.execute() returns None (unlike sqlite3), so call execute separately
    c.execute(query)
    for row in c:
        student_id, subject_id, pct = row
        if pct < threshold:
            msg = f"Attendance below {threshold}%: {pct:.1f}%"
            # avoid creating duplicate alerts for same student/subject
            exists = c.execute(_sql("SELECT 1 FROM alerts WHERE student_id=? AND subject_id=? AND message=?"),
                               (student_id, subject_id, msg)).fetchone()
            if not exists:
                c.execute(_sql("INSERT INTO alerts (student_id,subject_id,message) VALUES (?,?,?)"),
                          (student_id, subject_id, msg))
    conn.commit()
    conn.close()
