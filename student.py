import streamlit as st
from db import get_connection, _sql, USE_POSTGRES
import pandas as pd
from reports import generate_student_report


def student_portal(user):
    st.title(f"Student Portal - {user['username']}")
    menu = ["My Attendance","Timetable","Resources","Alerts","Get PDF Report"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "My Attendance":
        student_attendance(user)
    elif choice == "Timetable":
        show_timetable()
    elif choice == "Resources":
        show_resources(user)
    elif choice == "Alerts":
        show_alerts(user)
    elif choice == "Get PDF Report":
        generate_student_report(user)


def student_attendance(user):
    conn = get_connection()
    c = conn.cursor()
    # Cleanup any invalid placeholder rows that sometimes arise from bad imports
    c.execute(_sql("DELETE FROM attendance WHERE date IN ('date','subject') OR status IN ('status','subject') OR date IS NULL OR status IS NULL"))
    conn.commit()

    # Find matching student ID(s) for logged-in user
    c.execute(_sql("SELECT s.id FROM students s LEFT JOIN users u ON u.id=s.id OR u.username=s.roll WHERE u.username=?"), (user['username'],))
    student_rows = c.fetchall()
    student_ids = []
    for row in student_rows:
        student_ids.append(row['id'] if isinstance(row, dict) else row[0])

    if not student_ids:
        # also check by roll as fallback (when student user doesn't exist yet)
        c.execute(_sql("SELECT id FROM students WHERE roll=?"), (user['username'],))
        by_roll = c.fetchone()
        if by_roll:
            student_ids.append(by_roll['id'] if isinstance(by_roll, dict) else by_roll[0])

    if not student_ids:
        conn.close()
        st.warning("No student record found; contact admin to link your user.")
        return

    id_list_placeholder = ','.join(['?'] * len(student_ids)) if not USE_POSTGRES else ','.join(['%s'] * len(student_ids))
    q = _sql("SELECT a.date,sub.name as subject,a.status,s.class_level as class "
             "FROM attendance a "
             "JOIN subjects sub ON a.subject_id=sub.id "
             "JOIN students s ON s.id=a.student_id "
             "WHERE a.student_id IN (" + id_list_placeholder + ") "
             "AND a.status IN ('present','absent') "
             "AND a.date NOT IN ('date','subject') "
             "AND sub.name NOT IN ('subject')")
    df = pd.read_sql_query(q, conn, params=tuple(student_ids))
    # drop any garbage header rows still lurking
    if not df.empty:
        df = df[~df['date'].astype(str).str.lower().isin(['date', 'subject'])]
        df = df[~df['subject'].astype(str).str.lower().isin(['subject'])]
        df = df[~df['status'].astype(str).str.lower().isin(['status'])]
        df = df[~df['class'].astype(str).str.lower().isin(['class'])]

    # compute percentages
    pct = pd.read_sql_query(
        _sql("SELECT sub.name as subject, s.class_level as class, SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END)*100.0/COUNT(*) as pct "
             "FROM attendance a JOIN subjects sub ON a.subject_id=sub.id "
             "JOIN students s ON s.id=a.student_id "
             "JOIN users u ON (u.id=s.id OR u.username=s.roll) "
             "WHERE u.username=? AND a.status IN ('present','absent') AND a.date NOT IN ('date','subject') AND s.class_level NOT IN ('class','CLASS') AND sub.name NOT IN ('subject') GROUP BY sub.name,s.class_level"),
        conn, params=(user['username'],))

    # convert pct to numeric and drop invalid values
    if not pct.empty:
        pct['pct'] = pd.to_numeric(pct['pct'], errors='coerce')
        pct = pct.dropna(subset=['pct'])

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


def show_resources(user):
    """Show notes and assignments relevant to the student's class."""
    conn = get_connection()
    c = conn.cursor()
    # Determine the student's class level
    c.execute(_sql("SELECT s.class_level FROM students s JOIN users u ON u.id=s.id WHERE u.username=?"), (user['username'],))
    row = c.fetchone()
    if not row:
        conn.close()
        st.info("No student record found. Contact admin.")
        return
    class_level = row['class_level'] if isinstance(row, dict) else row[0]

    # Fetch notes and assignments for this class
    c.execute(_sql("SELECT n.id,n.title,n.filename,n.created_at,s.name AS subject FROM notes n JOIN subjects s ON n.subject_id=s.id WHERE s.class_level=? ORDER BY n.created_at DESC"), (class_level,))
    notes = c.fetchall()

    c.execute(_sql("SELECT a.id,a.title,a.filename,a.due_date,a.created_at,s.name AS subject FROM assignments a JOIN subjects s ON a.subject_id=s.id WHERE s.class_level=? ORDER BY a.created_at DESC"), (class_level,))
    assignments = c.fetchall()

    conn.close()

    st.subheader(f"Resources for {class_level}")

    if not notes and not assignments:
        st.info("No resources found for your class.")
        return

    if notes:
        st.write("### Notes")
        for n in notes:
            n = n if isinstance(n, dict) else {
                'id': n[0],
                'title': n[1],
                'filename': n[2],
                'created_at': n[3],
                'subject': n[4]
            }
            label = f"{n['title']} ({n['subject']})"
            if st.button(f"Download: {label}", key=f"note_{n['id']}"):
                try:
                    with open(f"uploads/{n['filename']}", 'rb') as f:
                        st.download_button(f"Download {label}", data=f.read(), file_name=n['filename'])
                except FileNotFoundError:
                    st.error("File not found on server. Contact faculty to re-upload.")

    if assignments:
        st.markdown("---")
        st.write("### Assignments")
        for a in assignments:
            a = a if isinstance(a, dict) else {
                'id': a[0],
                'title': a[1],
                'filename': a[2],
                'due_date': a[3],
                'created_at': a[4],
                'subject': a[5]
            }
            due = a.get('due_date') or 'No due date'
            label = f"{a['title']} ({a['subject']} - due {due})"
            if st.button(f"Download: {label}", key=f"assn_{a['id']}"):
                try:
                    with open(f"uploads/{a['filename']}", 'rb') as f:
                        st.download_button(f"Download {label}", data=f.read(), file_name=a['filename'])
                except FileNotFoundError:
                    st.error("File not found on server. Contact faculty to re-upload.")
