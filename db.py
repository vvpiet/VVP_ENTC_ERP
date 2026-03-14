import os
import sqlite3
from sqlite3 import Connection

DB_PATH = "college.db"

# Use DATABASE_URL/NEON_DATABASE_URL if set for remote Postgres/Neon deployment
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)


def get_connection() -> Connection:
    """Return a DB connection.

    If DATABASE_URL is set, connect via psycopg2 (Postgres/Neon).
    Otherwise fall back to local SQLite.
    """
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        # return dict-like rows for compatibility
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sql(sql: str) -> str:
    """Normalize parameter placeholders for the active backend."""
    if USE_POSTGRES:
        # Convert sqlite '?' placeholders to psycopg2 '%s'
        return sql.replace("?", "%s")
    return sql


def initialize_db():
    conn = get_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        # Postgres-compatible schema
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','faculty','student'))
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            roll TEXT UNIQUE NOT NULL,
            email TEXT,
            class_level TEXT
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            email TEXT
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            faculty_id INTEGER,
            class_level TEXT,
            FOREIGN KEY(faculty_id) REFERENCES faculty(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT CHECK(status IN ('present','absent')),
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS timetable (
            id SERIAL PRIMARY KEY,
            day TEXT NOT NULL,
            hour INTEGER NOT NULL,
            subject_id INTEGER,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')
    else:
        # SQLite schema
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','faculty','student'))
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll TEXT UNIQUE NOT NULL,
            email TEXT,
            class_level TEXT
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT,
            email TEXT
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            faculty_id INTEGER,
            class_level TEXT,
            FOREIGN KEY(faculty_id) REFERENCES faculty(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT CHECK(status IN ('present','absent')),
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            hour INTEGER NOT NULL,
            subject_id INTEGER,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

    # add missing columns if upgrading existing db
    try:
        c.execute(_sql("ALTER TABLE students ADD COLUMN class_level TEXT"))
    except Exception:
        pass
    try:
        c.execute(_sql("ALTER TABLE subjects ADD COLUMN class_level TEXT"))
    except Exception:
        pass

    # ensure existing usernames are normalized (lowercase, trimmed)
    try:
        c.execute(_sql("UPDATE users SET username=LOWER(TRIM(username))"))
        conn.commit()
    except Exception:
        pass
    conn.close()


if __name__ == "__main__":
    initialize_db()
    print("Database initialized")
