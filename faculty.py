import streamlit as st
from db import get_connection, _sql
import pandas as pd
from attendance import mark_attendance


def faculty_portal(user):
    st.title(f"Faculty Portal - {user['username']}")
    menu = ["Take Attendance","View Attendance","Timetable"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Take Attendance":
        take_attendance(user)
    elif choice == "View Attendance":
        view_attendance(user)
    elif choice == "Timetable":
        show_timetable()


def take_attendance(user):
    st.subheader("Take Attendance")
    conn = get_connection()
    # determine the correct faculty.id stored in faculty table
    fid = None
    try:
        uid = int(user.get('id'))
    except Exception:
        uid = None
    if uid is not None:
        # try matching by user id first
        row = conn.execute(_sql("SELECT id FROM faculty WHERE id=?"), (uid,)).fetchone()
        if row:
            fid = row[0]
    if fid is None:
        # fallback: match by username (case-insensitive)
        uname = user.get('username', '').strip().lower()
        row = conn.execute(_sql("SELECT id FROM faculty WHERE LOWER(name)=?"), (uname,)).fetchone()
        if row:
            fid = row[0]
    # retrieve subjects for this faculty
    if fid is not None:
        df = pd.read_sql_query(
            _sql("SELECT s.id,s.name,s.class_level FROM subjects s WHERE s.faculty_id=?"),
            conn, params=(fid,))
    else:
        df = pd.DataFrame()
    conn.close()

    if df.empty:
        st.info("You have no subjects assigned. Ask admin to add some.")
        return

    # build dropdown labels including class
    subject_label = None
    if not df.empty:
        labels = df.apply(lambda r: f"{r['name']} ({r.get('class_level','')})", axis=1)
        sel = st.selectbox("Subject", labels)
        # map back to id
        idx = labels.tolist().index(sel)
        subject_id = df.iloc[idx]['id']
    else:
        subject_id = None
    subject = subject_id
    if 'selected_subject' not in st.session_state:
        st.session_state.selected_subject = None

    if st.button("Load students") and subject is not None:
        st.session_state.selected_subject = subject

    # if a subject has been loaded, display attendance form
    if st.session_state.selected_subject:
        mark_attendance(st.session_state.selected_subject)


def view_attendance(user):
    st.subheader("Attendance Records")
    conn = get_connection()
    df = pd.read_sql_query(
        _sql("SELECT a.date,s.name as student,s.class_level as class,sub.name as subject,a.status FROM attendance a "
             "JOIN students s ON a.student_id=s.id "
             "JOIN subjects sub ON a.subject_id=sub.id"), conn)
    conn.close()
    st.dataframe(df)


def show_timetable():
    st.subheader("Timetable")
    conn = get_connection()
    df = pd.read_sql_query(_sql("SELECT day,hour,s.name AS subject FROM timetable t LEFT JOIN subjects s ON t.subject_id=s.id"), conn)
    conn.close()
    st.dataframe(df)
