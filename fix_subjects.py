import sqlite3
conn = sqlite3.connect('d:/college_erp/college.db')
c = conn.cursor()
c.execute("UPDATE subjects SET faculty_id = CAST(faculty_id AS INTEGER) WHERE typeof(faculty_id) = 'blob'")
conn.commit()
print('updated', c.rowcount)
conn.close()
