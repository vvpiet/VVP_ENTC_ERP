import streamlit as st
from db import get_connection, _sql
import pandas as pd
from datetime import date


def mark_attendance(subject_id):
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
        return
    cls = res['class_level'] if isinstance(res, dict) else res[0]
    
    # get students in that class (if class defined) using cursor
    if cls:
        c.execute(_sql("SELECT id,name,roll FROM students WHERE class_level=?"), (cls,))
    else:
        st.warning("Subject has no class assigned; showing all students")
        c.execute(_sql("SELECT id,name,roll FROM students"))
    
    student_rows = c.fetchall()
    
    # Convert rows to dicts
    students_data = []
    for row in student_rows:
        row_dict = row if isinstance(row, dict) else {
            'id': row[0],
            'name': row[1],
            'roll': row[2]
        }
        students_data.append(row_dict)
    
    status = {}
    with st.form("attendance_form"):
        st.write("Tick checkbox for present students. Unticked will be marked absent.")
        for student in students_data:
            key = f"stu_{student['id']}"
            checked = st.checkbox(f"{student['name']} ({student['roll']})", key=key)
            status[student['id']] = 'present' if checked else 'absent'
        submitted = st.form_submit_button("Submit")
        if submitted:
            for student_id, stat in status.items():
                c.execute(_sql("INSERT INTO attendance (student_id,subject_id,date,status) VALUES (?,?,?,?)"),
                          (student_id, subject_id, str(date.today()), stat))
            conn.commit()
            st.success("Attendance recorded")
    conn.close()
