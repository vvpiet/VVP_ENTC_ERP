import os
import sqlite3
from sqlite3 import Connection

DB_PATH = "college.db"

# Use DATABASE_URL/NEON_DATABASE_URL if set for remote Postgres/Neon deployment
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)


def get_db_info() -> dict:
    """Return info about the active database backend."""
    if USE_POSTGRES:
        redacted = DATABASE_URL
        if "@" in redacted:
            userpart, hostpart = redacted.split("@", 1)
            redacted = "<hidden>@" + hostpart
        return {"backend": "postgres", "url": redacted}
    return {"backend": "sqlite", "path": DB_PATH}


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
        # Enable autocommit to ensure changes are flushed to database immediately
        # This is especially important for Neon's serverless connections
        conn.autocommit = False  # Use explicit commits for now
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


def execute_query(sql: str, params=None):
    """Execute a query and return results as list of dicts."""
    conn = get_connection()
    c = conn.cursor()
    try:
        if params:
            c.execute(_sql(sql), params)
        else:
            c.execute(_sql(sql))
        
        # For SELECT queries, fetch all rows
        if sql.strip().upper().startswith('SELECT'):
            results = c.fetchall()
            conn.close()
            return results
        else:
            conn.commit()
            conn.close()
            return None
    except Exception as e:
        conn.close()
        raise e


def initialize_db():
    conn = get_connection()
    c = conn.cursor()

    # For Postgres, enable autocommit to avoid transaction abort on DDL failures
    if USE_POSTGRES:
        conn.autocommit = True

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
            time TEXT,
            lecture_number INTEGER,
            status TEXT CHECK(status IN ('present','absent')),
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''' )

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

        c.execute('''
        CREATE TABLE IF NOT EXISTS ler (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            lecture_number INTEGER,
            syllabus_covered_pct INTEGER,
            present_count INTEGER,
            absent_rolls TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(faculty_id) REFERENCES faculty(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        # Add academic_year column if it doesn't exist
        c.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='students' AND column_name='academic_year') THEN
                ALTER TABLE students ADD COLUMN academic_year INTEGER;
            END IF;
        END $$;
        """)

        # Add attendance columns for manual date/time/lecture no. if missing
        # Use DO $$ to safely add columns if not exist
        c.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='attendance' AND column_name='time') THEN
                ALTER TABLE attendance ADD COLUMN time TEXT;
            END IF;
        END $$;
        """)
        c.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='attendance' AND column_name='lecture_number') THEN
                ALTER TABLE attendance ADD COLUMN lecture_number INTEGER;
            END IF;
        END $$;
        """)

        # Ensure we commit DDL in Postgres right away so tables don't disappear if
        # a later statement fails (e.g. ALTER/UPDATE during migrations).
        conn.commit()

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
            time TEXT,
            lecture_number INTEGER,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS ler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            lecture_number INTEGER,
            syllabus_covered_pct INTEGER,
            present_count INTEGER,
            absent_rolls TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(faculty_id) REFERENCES faculty(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            due_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
        ''')

        # Ensure we commit DDL in SQLite so tables persist even if later
        # schema-migration steps fail.
        conn.commit()

    # add missing columns if upgrading existing db
    try:
        c.execute(_sql("ALTER TABLE students ADD COLUMN class_level TEXT"))
    except Exception:
        pass
    try:
        c.execute(_sql("ALTER TABLE subjects ADD COLUMN class_level TEXT"))
    except Exception:
        pass
    try:
        c.execute(_sql("ALTER TABLE attendance ADD COLUMN time TEXT"))
    except Exception:
        pass
    try:
        c.execute(_sql("ALTER TABLE attendance ADD COLUMN lecture_number INTEGER"))
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
