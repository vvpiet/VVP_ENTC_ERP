from db import get_connection, _sql

conn = get_connection()
cur = conn.cursor()
try:
    query = _sql("SELECT u.id, COALESCE(s.name, f.name, u.username) as display_name, u.username, u.role FROM users u LEFT JOIN students s ON u.id = s.id LEFT JOIN faculty f ON u.id = f.id")
    print('query:', query)
    cur.execute(query)
    rows = cur.fetchmany(10)
    for r in rows:
        print(dict(r))
except Exception as e:
    print('err', e)
finally:
    conn.close()
