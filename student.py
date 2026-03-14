import streamlit as st
from db import get_connection, _sql
import pandas as pd
from reports import generate_student_report


def student_portal(user):
    st.title(f"Student Portal - {user['username']}")
    menu = ["My Attendance","Timetable","Alerts","Get PDF Report"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "My Attendance":
        student_attendance(user)
    elif choice == "Timetable":
        show_timetable()
    elif choice == "Alerts":
        show_alerts(user)
    elif choice == "Get PDF Report":
        generate_student_report(user)


def student_attendance(user):
    conn = get_connection()
    df = pd.read_sql_query(
        _sql("SELECT a.date,sub.name as subject,a.status,s.class_level as class "
             "FROM attendance a "
             "JOIN subjects sub ON a.subject_id=sub.id "
             "JOIN students s ON s.id=a.student_id "
             "JOIN users u ON u.id=a.student_id WHERE u.username=?"), conn, params=(user['username'],))
    # compute percentages
    pct = pd.read_sql_query(
        _sql("SELECT sub.name as subject, s.class_level as class, SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END)*100.0/COUNT(*) as pct "
             "FROM attendance a JOIN subjects sub ON a.subject_id=sub.id "
             "JOIN students s ON s.id=a.student_id "
             "JOIN users u ON u.id=a.student_id WHERE u.username=? GROUP BY sub.name,s.class_level"), conn, params=(user['username'],))
    conn.close()
    st.write("### Records")
    st.dataframe(df)
    st.write("### Percentages")
    st.dataframe(pct)


def show_timetable():
    conn = get_connection()
    df = pd.read_sql_query(_sql("SELECT day,hour,s.name AS subject FROM timetable t LEFT JOIN subjects s ON t.subject_id=s.id"), conn)
    conn.close()
    st.dataframe(df)


def show_alerts(user):
    conn = get_connection()
    df = pd.read_sql_query(
        _sql("SELECT message,created_at FROM alerts a JOIN users u ON u.id=a.student_id WHERE u.username=?"), conn, params=(user['username'],))
    conn.close()
    st.dataframe(df)
