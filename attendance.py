import streamlit as st
from db import get_connection, _sql
import pandas as pd
from datetime import date, datetime, time


def mark_attendance(subject_id, lecture_date=None, lecture_time=None, lecture_number=None):
    # ensure integer and validate
    try:
        subject_id = int(subject_id)
    except (ValueError, TypeError):
        st.error(f"Invalid subject ID: {subject_id}")
        return
    
    if subject_id <= 0:
        st.error("Subject ID must be positive")
        return
    
    conn = get_connection()
    c = conn.cursor()
    # get subject class_level by id
    c.execute(_sql("SELECT class_level FROM subjects WHERE id=?"), (subject_id,))
    res = c.fetchone()
    if not res:
        st.error("Subject not found")
        conn.close()
        return
    cls = res['class_level'] if isinstance(res, dict) else res[0]

    # Normalize lecture metadata for attendance entries
    if lecture_date is None:
        lecture_date = date.today()
    elif isinstance(lecture_date, str):
        try:
            lecture_date = date.fromisoformat(lecture_date)
        except Exception:
            lecture_date = date.today()
    elif not isinstance(lecture_date, date):
        lecture_date = date.today()
    lecture_date_str = str(lecture_date)

    if lecture_time is None:
        lecture_time = datetime.now().time()
    elif isinstance(lecture_time, str):
        try:
            lecture_time = time.fromisoformat(lecture_time)
        except Exception:
            lecture_time = datetime.now().time()
    elif not isinstance(lecture_time, time):
        lecture_time = datetime.now().time()
    lecture_time_str = lecture_time.strftime("%H:%M:%S")

    if lecture_number is None:
        lecture_number = 1
    else:
        try:
            lecture_number = int(lecture_number)
            if lecture_number < 1:
                lecture_number = 1
        except Exception:
            lecture_number = 1

    # DEBUG: Show what we're looking for
    try:
        with st.expander("🔍 Debug Info"):
            st.write(f"Subject Class Level: {cls}")
            # Show all students in database
            c.execute(_sql("SELECT COUNT(*) as cnt FROM students"))
            total_count = c.fetchone()
            total_students = total_count['cnt'] if isinstance(total_count, dict) else total_count[0]
            st.write(f"Total students in DB: {total_students}")
            
            c.execute(_sql("SELECT DISTINCT class_level FROM students"))
            classes = c.fetchall()
            class_list = []
            for r in classes:
                if isinstance(r, dict):
                    class_list.append(r.get('class_level', 'N/A'))
                else:
                    class_list.append(r[0] if len(r) > 0 else 'N/A')
            st.write(f"Classes in DB: {class_list}")
    except Exception as e:
        st.warning(f"Debug info error: {e}")
    
    # get students in that class (if class defined) using cursor
    student_rows = []
    if cls and str(cls).strip():
        c.execute(_sql("SELECT id,name,roll FROM students WHERE class_level=?"), (str(cls).strip(),))
        student_rows = c.fetchall()
        if not student_rows:
            st.warning(f"No students found for class '{cls}'. Showing all students instead.")
            c.execute(_sql("SELECT id,name,roll FROM students ORDER BY name"))
            student_rows = c.fetchall()
    else:
        st.warning("Subject has no class assigned; showing all students")
        c.execute(_sql("SELECT id,name,roll FROM students ORDER BY name"))
        student_rows = c.fetchall()
    
    if not student_rows:
        st.error("❌ No students found in database. Please upload student list in Admin → Students")
        conn.close()
        return

    # Convert results to a list of dicts for rendering
    students_data = []
    for row in student_rows:
        row_dict = row if isinstance(row, dict) else {
            'id': row[0],
            'name': row[1],
            'roll': row[2]
        }
        students_data.append(row_dict)
    
    status = {}
    try:
        with st.form("attendance_form"):
            st.write("Tick checkbox for present students. Unticked will be marked absent.")
            for student in students_data:
                # Ensure the student dict has required keys
                sid = student.get('id') if isinstance(student, dict) else None
                name = student.get('name') if isinstance(student, dict) else None
                roll = student.get('roll') if isinstance(student, dict) else None
                if sid is None or name is None or roll is None:
                    continue

                key = f"stu_{sid}"
                checked = st.checkbox(f"{name} ({roll})", key=key)
                status[sid] = 'present' if checked else 'absent'

            # Always include submit button so Streamlit doesn't warn
            submitted = st.form_submit_button("Submit")
            if submitted:
                try:
                    inserted_count = 0
                    for student_id, stat in status.items():
                        c.execute(_sql("INSERT INTO attendance (student_id,subject_id,date,time,lecture_number,status) VALUES (?,?,?,?,?,?)"),
                                  (student_id, subject_id, lecture_date_str, lecture_time_str, lecture_number, stat))
                        inserted_count += 1
                    
                    # Commit the transaction
                    conn.commit()
                    
                    # Verify insertion by querying back immediately
                    c.execute(_sql("SELECT COUNT(*) as cnt FROM attendance WHERE subject_id=? AND date=? AND time=? AND lecture_number=?"), 
                             (subject_id, lecture_date_str, lecture_time_str, lecture_number))
                    verify_row = c.fetchone()
                    verify_count = verify_row['cnt'] if isinstance(verify_row, dict) else verify_row[0]
                    
                    st.success(f"✅ Attendance recorded successfully for {inserted_count} students (verified: {verify_count} records for {lecture_date_str} {lecture_time_str}, lecture {lecture_number})")
                except Exception as e:
                    try:
                        conn.rollback()
                    except:
                        pass
                    st.error(f"❌ Failed to save attendance: {str(e)}")
                    import traceback
                    st.error(f"Details: {traceback.format_exc()}")
    except Exception as e:
        st.error(f"Failed to render attendance form: {e}")
    finally:
        conn.close()
