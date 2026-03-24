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
        # Use autocommit by default for DDL robustness on serverless PG backends
        conn.autocommit = True
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


def migrate_sqlite_to_postgres():
    """Copy local SQLite schema rows into Postgres/Neon if both are present."""
    if not USE_POSTGRES:
        return

    if not os.path.exists(DB_PATH):
        return

    local_conn = sqlite3.connect(DB_PATH)
    local_conn.row_factory = sqlite3.Row
    local_cur = local_conn.cursor()

    remote_conn = get_connection()
    remote_cur = remote_conn.cursor()

    # 1) Migrate students
    student_map = {}
    local_cur.execute("SELECT id,name,roll,email,class_level FROM students")
    for row in local_cur.fetchall():
        local_id = row['id']
        local_roll = row['roll']

        remote_cur.execute("SELECT id FROM students WHERE roll=%s", (local_roll,))
        existing = remote_cur.fetchone()
        if existing:
            student_map[local_id] = existing['id'] if isinstance(existing, dict) else existing[0]
        else:
            remote_cur.execute(
                "INSERT INTO students (name,roll,email,class_level) VALUES (%s,%s,%s,%s) RETURNING id",
                (row['name'], row['roll'], row['email'], row['class_level']),
            )
            new_id = remote_cur.fetchone()['id'] if USE_POSTGRES else remote_cur.lastrowid
            student_map[local_id] = new_id

    # 2) Migrate faculty
    faculty_map = {}
    local_cur.execute("SELECT id,name,department,email FROM faculty")
    for row in local_cur.fetchall():
        local_id = row['id']
        remote_cur.execute("SELECT id FROM faculty WHERE name=%s", (row['name'],))
        existing = remote_cur.fetchone()
        if existing:
            faculty_map[local_id] = existing['id'] if isinstance(existing, dict) else existing[0]
        else:
            remote_cur.execute(
                "INSERT INTO faculty (name,department,email) VALUES (%s,%s,%s) RETURNING id",
                (row['name'], row['department'], row['email']),
            )
            faculty_map[local_id] = remote_cur.fetchone()['id']

    # 3) Migrate subjects
    subject_map = {}
    local_cur.execute("SELECT id,name,code,faculty_id,class_level FROM subjects")
    for row in local_cur.fetchall():
        local_id = row['id']
        remote_cur.execute("SELECT id FROM subjects WHERE code=%s", (row['code'],))
        existing = remote_cur.fetchone()
        if existing:
            subject_map[local_id] = existing['id'] if isinstance(existing, dict) else existing[0]
        else:
            faculty_old = row['faculty_id']
            faculty_new = faculty_map.get(faculty_old)
            remote_cur.execute(
                "INSERT INTO subjects (name,code,faculty_id,class_level) VALUES (%s,%s,%s,%s) RETURNING id",
                (row['name'], row['code'], faculty_new, row['class_level']),
            )
            subject_map[local_id] = remote_cur.fetchone()['id']

    # 4) Migrate attendance
    local_cur.execute("SELECT student_id,subject_id,date,time,lecture_number,status FROM attendance")
    for row in local_cur.fetchall():
        s_new = student_map.get(row['student_id'])
        sub_new = subject_map.get(row['subject_id'])
        if not s_new or not sub_new:
            continue

        remote_cur.execute(
            "SELECT 1 FROM attendance WHERE student_id=%s AND subject_id=%s AND date=%s AND COALESCE(time,'')=%s AND COALESCE(lecture_number,0)=%s AND status=%s",
            (s_new, sub_new, row['date'], row['time'] or '', row['lecture_number'] or 0, row['status']),
        )
        if not remote_cur.fetchone():
            remote_cur.execute(
                "INSERT INTO attendance (student_id,subject_id,date,time,lecture_number,status) VALUES (%s,%s,%s,%s,%s,%s)",
                (s_new, sub_new, row['date'], row['time'], row['lecture_number'], row['status']),
            )

    # 5) Migrate LER
    local_cur.execute("SELECT faculty_id,subject_id,date,lecture_number,syllabus_covered_pct,present_count,absent_rolls FROM ler")
    for row in local_cur.fetchall():
        f_new = faculty_map.get(row['faculty_id'])
        sub_new = subject_map.get(row['subject_id'])
        if not f_new or not sub_new:
            continue

        remote_cur.execute(
            "SELECT 1 FROM ler WHERE faculty_id=%s AND subject_id=%s AND date=%s AND COALESCE(lecture_number,0)=%s",
            (f_new, sub_new, row['date'], row['lecture_number'] or 0),
        )
        if not remote_cur.fetchone():
            remote_cur.execute(
                "INSERT INTO ler (faculty_id,subject_id,date,lecture_number,syllabus_covered_pct,present_count,absent_rolls) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (f_new, sub_new, row['date'], row['lecture_number'], row['syllabus_covered_pct'], row['present_count'], row['absent_rolls']),
            )

    remote_conn.commit()
    remote_conn.close()
    local_conn.close()


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

        # If we're now on Postgres and local DB file exists, migrate existing local data
        migrate_sqlite_to_postgres()

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
