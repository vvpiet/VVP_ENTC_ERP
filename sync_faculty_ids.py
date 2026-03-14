import sqlite3

conn = sqlite3.connect('d:/college_erp/college.db')
c = conn.cursor()
# match faculty.name (case insensitive) to users.username
for row in c.execute("SELECT f.id,f.name FROM faculty f"):
    fid, fname = row
    cur = c.execute("SELECT id FROM users WHERE LOWER(username)=?", (fname.strip().lower(),))
    res = cur.fetchone()
    if res:
        uid = res[0]
        if uid != fid:
            print(f"Updating faculty id {fid} -> {uid} for name {fname}")
            c.execute("UPDATE faculty SET id=? WHERE id=?", (uid, fid))
            # also update subjects referencing the old id
            c.execute("UPDATE subjects SET faculty_id=? WHERE faculty_id=?", (uid, fid))
conn.commit()
conn.close()
print('sync completed')
