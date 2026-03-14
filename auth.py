from db import get_connection, _sql
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str, role: str):
    # normalize username to avoid accidental spaces or case issues
    uname = username.strip().lower()
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(_sql("INSERT INTO users (username,password,role) VALUES (?,?,?)"),
                  (uname, hash_password(password), role))
        conn.commit()
    except Exception as e:
        raise e
    finally:
        conn.close()


def validate_login(username: str, password: str):
    uname = username.strip().lower()
    conn = get_connection()
    c = conn.cursor()
    c.execute(_sql("SELECT * FROM users WHERE username=?"), (uname,))
    user = c.fetchone()
    conn.close()
    if user and user["password"] == hash_password(password):
        return dict(user)
    return None
