import pandas as pd
from db import get_connection, _sql

conn = get_connection()
print('conn', type(conn))
try:
    query = _sql("SELECT u.id, COALESCE(s.name, f.name, u.username) as display_name, u.username, u.role FROM users u LEFT JOIN students s ON u.id = s.id LEFT JOIN faculty f ON u.id = f.id")
    print('query:', query)
    df = pd.read_sql_query(query, conn)
    print('df head:')
    print(df.head())
    print('dtypes:')
    print(df.dtypes)
    print('rows', len(df))
except Exception as e:
    print('err', e)
finally:
    conn.close()
