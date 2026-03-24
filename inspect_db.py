from db import get_connection, _sql

conn = get_connection()
c = conn.cursor()

row = c.execute(_sql('SELECT COUNT(*) FROM attendance')).fetchone()
print('attendance count', row[0] if row else None)

rows = c.execute(_sql('SELECT date,status,student_id,subject_id FROM attendance ORDER BY id DESC LIMIT 10')).fetchall()
print('attendance last 10 count', len(rows))
for r in rows:
    if isinstance(r, dict):
        print(r)
    else:
        print(tuple(r))

row = c.execute(_sql('SELECT COUNT(*) FROM ler')).fetchone()
print('ler count', row[0] if row else None)

rows = c.execute(_sql('SELECT date,faculty_id,subject_id,present_count,absent_rolls FROM ler ORDER BY id DESC LIMIT 10')).fetchall()
print('ler last 10 count', len(rows))
for r in rows:
    if isinstance(r, dict):
        print(r)
    else:
        print(tuple(r))

conn.close()
