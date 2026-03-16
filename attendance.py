import streamlit as st
from db import get_connection, _sql
import pandas as pd
from datetime import date


def mark_attendance(subject_id):
    # ensure integer
    try:
        subject_id = int(subject_id)
    except Exception:
        pass
    conn = get_connection()
    c = conn.cursor()
    # get subject class_level by id
    c.execute(_sql("SELECT class_level FROM subjects WHERE id=?"), (subject_id,))
    res = c.fetchone()
    if not res:
        st.error("Subject not found")
        return
    cls = res[0]
    # get students in that class (if class defined)
    if cls:
        students = pd.read_sql_query(_sql("SELECT id,name,roll FROM students WHERE class_level=?"), conn, params=(cls,))
    else:
        st.warning("Subject has no class assigned; showing all students")
        students = pd.read_sql_query(_sql("SELECT id,name,roll FROM students"), conn)
    status = {}
    with st.form("attendance_form"):
        st.write("Tick checkbox for present students. Unticked will be marked absent.")
        for idx, row in students.iterrows():
            key = f"stu_{row['id']}"
            checked = st.checkbox(f"{row['name']} ({row['roll']})", key=key)
            status[row['id']] = 'present' if checked else 'absent'
        submitted = st.form_submit_button("Submit")
        if submitted:
            for student_id, stat in status.items():
                c.execute(_sql("INSERT INTO attendance (student_id,subject_id,date,status) VALUES (?,?,?,?)"),
                          (student_id, subject_id, str(date.today()), stat))
            conn.commit()
            st.success("Attendance recorded")
    conn.close()
