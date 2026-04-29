import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import Binary
from psycopg2 import Binary
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Database connection
def get_db_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# Create tables
def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            email VARCHAR(100)
        );
        CREATE TABLE IF NOT EXISTS classes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            class_id INTEGER REFERENCES classes(id)
        );
        CREATE TABLE IF NOT EXISTS faculty_subjects (
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            PRIMARY KEY (faculty_id, subject_id)
        );
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            roll_no VARCHAR(50) UNIQUE NOT NULL,
            prn VARCHAR(100),
            name VARCHAR(100) NOT NULL,
            class_id INTEGER REFERENCES classes(id)
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            subject_id INTEGER REFERENCES subjects(id),
            faculty_id INTEGER REFERENCES users(id),
            date DATE NOT NULL,
            time TIME NOT NULL,
            present BOOLEAN NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lecture_engagement (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            date DATE NOT NULL,
            topic_covered TEXT,
            lecture_number INTEGER,
            syllabus_percent DECIMAL(5,2),
            total_present INTEGER,
            total_absent INTEGER,
            absent_roll_numbers TEXT[]
        );
        CREATE TABLE IF NOT EXISTS faculty_resources (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            file_name VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            file_data BYTEA NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resources (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            file_name VARCHAR(255) NOT NULL,
            file_data BYTEA NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS gradecards (
            id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            semester VARCHAR(20),
            course VARCHAR(50),
            pdf_file BYTEA NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, semester)
        );
        CREATE TABLE IF NOT EXISTS mcq_tests (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            title VARCHAR(255) NOT NULL,
            proctor_notes TEXT,
            proctored BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS mcq_test_questions (
            id SERIAL PRIMARY KEY,
            test_id INTEGER REFERENCES mcq_tests(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option CHAR(1) NOT NULL,
            marks INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS mcq_test_attempts (
            id SERIAL PRIMARY KEY,
            test_id INTEGER REFERENCES mcq_tests(id) ON DELETE CASCADE,
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            score INTEGER,
            total_marks INTEGER,
            percent NUMERIC(5,2),
            passed BOOLEAN,
            proctor_notes TEXT
        );
        CREATE TABLE IF NOT EXISTS mcq_test_answers (
            id SERIAL PRIMARY KEY,
            attempt_id INTEGER REFERENCES mcq_test_attempts(id) ON DELETE CASCADE,
            question_id INTEGER REFERENCES mcq_test_questions(id),
            selected_option CHAR(1),
            is_correct BOOLEAN
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()


def ensure_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("ALTER TABLE lecture_engagement ADD COLUMN IF NOT EXISTS absent_roll_numbers TEXT[]")
    cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS prn VARCHAR(100)")
    cur.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS attendance_student_id_fkey")
    cur.execute("ALTER TABLE attendance ADD CONSTRAINT attendance_student_id_fkey FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE")
    cur.execute("ALTER TABLE gradecards DROP CONSTRAINT IF EXISTS gradecards_student_id_fkey")
    cur.execute("ALTER TABLE gradecards ADD CONSTRAINT gradecards_student_id_fkey FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE")
    cur.execute("ALTER TABLE mcq_test_attempts DROP CONSTRAINT IF EXISTS mcq_test_attempts_student_id_fkey")
    cur.execute("ALTER TABLE mcq_test_attempts ADD CONSTRAINT mcq_test_attempts_student_id_fkey FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE")
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gradecards (
            id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            semester VARCHAR(20),
            course VARCHAR(50),
            pdf_file BYTEA NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, semester)
        );
        CREATE TABLE IF NOT EXISTS mcq_tests (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            title VARCHAR(255) NOT NULL,
            proctor_notes TEXT,
            proctored BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS mcq_test_questions (
            id SERIAL PRIMARY KEY,
            test_id INTEGER REFERENCES mcq_tests(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option CHAR(1) NOT NULL,
            marks INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS mcq_test_attempts (
            id SERIAL PRIMARY KEY,
            test_id INTEGER REFERENCES mcq_tests(id) ON DELETE CASCADE,
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            score INTEGER,
            total_marks INTEGER,
            percent NUMERIC(5,2),
            passed BOOLEAN,
            proctor_notes TEXT
        );
        CREATE TABLE IF NOT EXISTS mcq_test_answers (
            id SERIAL PRIMARY KEY,
            attempt_id INTEGER REFERENCES mcq_test_attempts(id) ON DELETE CASCADE,
            question_id INTEGER REFERENCES mcq_test_questions(id),
            selected_option CHAR(1),
            is_correct BOOLEAN
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

# User functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, password, role, name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    hashed = hash_password(password)
    cur.execute('INSERT INTO users (username, password_hash, role, name, email) VALUES (%s, %s, %s, %s, %s)',
                (username, hashed, role, name, email))
    conn.commit()
    cur.close()
    conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user and check_password(password, user['password_hash']):
        return user
    return None

# Other functions will be added as needed

# Faculty resource functions
def upload_resource(faculty_id, subject_id, file_name, file_data, resource_type):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO resources (faculty_id, subject_id, file_name, file_data, resource_type) VALUES (%s, %s, %s, %s, %s)",
        (faculty_id, subject_id, file_name, file_data, resource_type)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_faculty_resources(faculty_id, subject_id=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if subject_id:
            cur.execute('SELECT id, file_name, resource_type, uploaded_date FROM faculty_resources WHERE faculty_id = %s AND subject_id = %s ORDER BY uploaded_date DESC',
                        (faculty_id, subject_id))
        else:
            cur.execute('SELECT id, file_name, resource_type, uploaded_date, s.name as subject_name FROM faculty_resources fr LEFT JOIN subjects s ON fr.subject_id = s.id WHERE fr.faculty_id = %s ORDER BY fr.uploaded_date DESC',
                        (faculty_id,))
        resources = cur.fetchall()
        cur.close()
        conn.close()
        return resources if resources else []
    except Exception as e:
        print(f"Error getting faculty resources: {e}")
        return []


def store_lecture_engagement(faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO lecture_engagement (faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers))
    conn.commit()
    cur.close()
    conn.close()


def get_student_resources(roll_no):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT r.id, r.file_name, r.resource_type, s.name as subject_name, r.uploaded_date, r.file_data "
        "FROM resources r "
        "JOIN subjects s ON r.subject_id = s.id "
        "JOIN students st ON st.class_id = s.class_id "
        "WHERE st.roll_no = %s "
        "ORDER BY r.uploaded_date DESC",
        (roll_no,)
    )
    resources = cur.fetchall()
    cur.close()
    conn.close()
    return resources if resources else []


def delete_resource(resource_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM faculty_resources WHERE id = %s', (resource_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_resource_file(resource_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT file_name, file_data, file_type FROM faculty_resources WHERE id = %s', (resource_id,))
    resource = cur.fetchone()
    cur.close()
    conn.close()
    return resource

def save_gradecard(student_id, pdf_data, semester, course):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO gradecards (student_id, semester, course, pdf_file)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (student_id, semester)
           DO UPDATE SET pdf_file = EXCLUDED.pdf_file, course = EXCLUDED.course, generated_at = CURRENT_TIMESTAMP''',
        (student_id, semester, course, psycopg2.Binary(pdf_data))
    )
    conn.commit()
    cur.close()
    conn.close()


def get_gradecard(student_id, semester=None):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if semester:
        cur.execute('SELECT pdf_file, semester, course, generated_at FROM gradecards WHERE student_id = %s AND semester = %s', (student_id, semester))
    else:
        cur.execute('SELECT pdf_file, semester, course, generated_at FROM gradecards WHERE student_id = %s ORDER BY generated_at DESC LIMIT 1', (student_id,))
    gradecard = cur.fetchone()
    if gradecard and gradecard.get('pdf_file') is not None:
        pdf_file = gradecard['pdf_file']
        if isinstance(pdf_file, memoryview):
            gradecard['pdf_file'] = pdf_file.tobytes()
        elif isinstance(pdf_file, bytearray):
            gradecard['pdf_file'] = bytes(pdf_file)
    cur.close()
    conn.close()
    return gradecard


def get_student_id_by_roll_no(roll_no):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM students WHERE roll_no = %s', (roll_no,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def create_mcq_test(faculty_id, subject_id, title, proctor_notes, proctored=True):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO mcq_tests (faculty_id, subject_id, title, proctor_notes, proctored) VALUES (%s, %s, %s, %s, %s) RETURNING id',
        (faculty_id, subject_id, title, proctor_notes, proctored)
    )
    test_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return test_id


def add_mcq_question(test_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks=1):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO mcq_test_questions (test_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (test_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_faculty_tests(faculty_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT t.id, t.title, t.proctor_notes, t.created_at, s.name as subject_name, c.name as class_name FROM mcq_tests t JOIN subjects s ON t.subject_id = s.id JOIN classes c ON s.class_id = c.id WHERE t.faculty_id = %s ORDER BY t.created_at DESC',
        (faculty_id,)
    )
    tests = cur.fetchall()
    cur.close()
    conn.close()
    return tests


def get_test_with_questions(test_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT t.id, t.title, t.proctor_notes, t.proctored, s.name as subject_name, c.name as class_name, u.name as faculty_name FROM mcq_tests t JOIN subjects s ON t.subject_id = s.id JOIN classes c ON s.class_id = c.id JOIN users u ON t.faculty_id = u.id WHERE t.id = %s',
        (test_id,)
    )
    test = cur.fetchone()
    cur.execute(
        'SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option, marks FROM mcq_test_questions WHERE test_id = %s ORDER BY id',
        (test_id,)
    )
    questions = cur.fetchall()
    cur.close()
    conn.close()
    return {'test': test, 'questions': questions}


def get_student_tests(roll_no):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT t.id, t.title, t.proctor_notes, t.created_at, s.name as subject_name, u.name as faculty_name FROM mcq_tests t JOIN subjects s ON t.subject_id = s.id JOIN users u ON t.faculty_id = u.id JOIN students st ON st.class_id = s.class_id WHERE st.roll_no = %s ORDER BY t.created_at DESC',
        (roll_no,)
    )
    tests = cur.fetchall()
    cur.close()
    conn.close()
    return tests


def submit_student_test_attempt(test_id, roll_no, answers, score, total_marks, percent, passed, proctor_notes=None):
    student_id = get_student_id_by_roll_no(roll_no)
    if not student_id:
        raise ValueError('Student not found')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO mcq_test_attempts (test_id, student_id, finished_at, score, total_marks, percent, passed, proctor_notes) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s) RETURNING id',
        (test_id, student_id, score, total_marks, percent, passed, proctor_notes)
    )
    attempt_id = cur.fetchone()[0]
    for answer in answers:
        cur.execute(
            'INSERT INTO mcq_test_answers (attempt_id, question_id, selected_option, is_correct) VALUES (%s, %s, %s, %s)',
            (attempt_id, answer['question_id'], answer['selected_option'], answer['is_correct'])
        )
    conn.commit()
    cur.close()
    conn.close()
    return attempt_id


def get_student_test_attempts(roll_no):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT a.id, a.test_id, a.score, a.total_marks, a.percent, a.passed, a.finished_at, t.title, s.name as subject_name FROM mcq_test_attempts a JOIN mcq_tests t ON a.test_id = t.id JOIN subjects s ON t.subject_id = s.id JOIN students st ON a.student_id = st.id WHERE st.roll_no = %s ORDER BY a.finished_at DESC',
        (roll_no,)
    )
    attempts = cur.fetchall()
    cur.close()
    conn.close()
    return attempts


def get_mcq_test_results():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT a.id as attempt_id, t.title as test_title, s.name as subject_name, st.roll_no as student_roll_no, st.name as student_name, u.name as faculty_name, a.score, a.total_marks, a.percent, a.passed, a.finished_at, t.proctor_notes '
        'FROM mcq_test_attempts a '
        'JOIN mcq_tests t ON a.test_id = t.id '
        'JOIN subjects s ON t.subject_id = s.id '
        'JOIN users u ON t.faculty_id = u.id '
        'JOIN students st ON a.student_id = st.id '
        'ORDER BY a.finished_at DESC'
    )
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

# Student management functions
def get_all_students():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT s.id, s.roll_no, s.prn, s.name, c.name as class_name FROM students s JOIN classes c ON s.class_id = c.id ORDER BY s.roll_no')
    students = cur.fetchall()
    cur.close()
    conn.close()
    return students

def update_student(student_id, roll_no, prn, name, class_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM classes WHERE name = %s', (class_name,))
    class_id = cur.fetchone()[0]
    cur.execute('UPDATE students SET roll_no = %s, prn = %s, name = %s, class_id = %s WHERE id = %s',
                (roll_no, prn, name, class_id, student_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Delete all related student records first to satisfy foreign key constraints.
    cur.execute('DELETE FROM attendance WHERE student_id = %s', (student_id,))
    cur.execute('DELETE FROM gradecards WHERE student_id = %s', (student_id,))
    cur.execute('DELETE FROM mcq_test_answers WHERE attempt_id IN (SELECT id FROM mcq_test_attempts WHERE student_id = %s)', (student_id,))
    cur.execute('DELETE FROM mcq_test_attempts WHERE student_id = %s', (student_id,))
    # Delete student
    cur.execute('DELETE FROM students WHERE id = %s', (student_id,))
    conn.commit()
    cur.close()
    conn.close()