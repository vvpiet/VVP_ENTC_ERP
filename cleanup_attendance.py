from db import get_connection, get_db_info

print('DB backend:', get_db_info())

conn = get_connection()
c = conn.cursor()
q = "DELETE FROM attendance WHERE date IN ('date','subject') OR status IN ('status','subject')"
c.execute(q)
print('attendance deleted', c.rowcount)
conn.commit()
conn.close()

conn = get_connection()
c = conn.cursor()
q = "DELETE FROM students WHERE class_level IN ('class','CLASS')"
c.execute(q)
print('students deleted', c.rowcount)
conn.commit()
conn.close()

print('Cleanup finished')
