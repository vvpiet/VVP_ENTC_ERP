from db import get_connection, _sql

conn = get_connection()
cur_fac = conn.cursor()
cur_fac.execute(_sql("SELECT id,name FROM faculty"))
fac_rows = cur_fac.fetchall()
print('faculty rows:', fac_rows)
try:
    fac_options = [""] + [r['name'] for r in fac_rows]
    print('fac_options:', fac_options)
except Exception as e:
    print('error building fac_options:', e)
finally:
    conn.close()
