import streamlit as st
from db import get_connection, _sql
import pandas as pd
from attendance import mark_attendance


def faculty_portal(user):
    st.title(f"Faculty Portal - {user['username']}")
    menu = ["Take Attendance","LER","View Attendance","Timetable"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Take Attendance":
        take_attendance(user)
    elif choice == "LER":
        lecture_engagement_register(user)
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
    cur = conn.cursor()
    if uid is not None:
        # try matching by user id first
        cur.execute(_sql("SELECT id FROM faculty WHERE id=?"), (uid,))
        row = cur.fetchone()
        if row:
            fid = row['id'] if isinstance(row, dict) else row[0]
    if fid is None:
        # fallback: match by username (case-insensitive)
        uname = user.get('username', '').strip().lower()
        cur.execute(_sql("SELECT id FROM faculty WHERE LOWER(name)=?"), (uname,))
        row = cur.fetchone()
        if row:
            fid = row['id'] if isinstance(row, dict) else row[0]
    # retrieve subjects for this faculty
    if fid is not None:
        cur.execute(_sql("SELECT s.id,s.name,s.class_level FROM subjects s WHERE s.faculty_id=?"), (fid,))
        subject_rows = cur.fetchall()
        # Convert rows to list of dicts
        subjects_data = []
        for row in subject_rows:
            row_dict = row if isinstance(row, dict) else {
                'id': row[0],
                'name': row[1],
                'class_level': row[2]
            }
            subjects_data.append(row_dict)
    else:
        subjects_data = []
    conn.close()

    if not subjects_data:
        st.info("You have no subjects assigned. Ask admin to add some.")
        return

    # build dropdown labels including class
    if subjects_data:
        labels = [f"{s['name']} ({s.get('class_level', '')})" for s in subjects_data]
        sel = st.selectbox("Subject", labels)
        # map back to id
        idx = labels.index(sel)
        subject_id = int(subjects_data[idx]['id'])

    if st.button("Load students") and subject is not None:
        st.session_state.selected_subject = subject

    # if a subject has been loaded, display attendance form
    if st.session_state.selected_subject:
        mark_attendance(st.session_state.selected_subject)


def view_attendance(user):
    st.subheader("Attendance Records")
    conn = get_connection()
    c = conn.cursor()
    c.execute(_sql("SELECT a.date,s.name as student,s.class_level as class,sub.name as subject,a.status FROM attendance a "
             "JOIN students s ON a.student_id=s.id "
             "JOIN subjects sub ON a.subject_id=sub.id"))
    rows = c.fetchall()
    conn.close()
    
    # Convert to dataframe for display
    if rows:
        data = []
        for row in rows:
            row_dict = row if isinstance(row, dict) else {
                'date': row[0],
                'student': row[1],
                'class': row[2],
                'subject': row[3],
                'status': row[4]
            }
            data.append(row_dict)
        df = pd.DataFrame(data)
        st.dataframe(df)
    else:
        st.info("No attendance records found")


def lecture_engagement_register(user):
    st.subheader("Lecture Engagement Register (LER)")
    conn = get_connection()
    cur = conn.cursor()
    # resolve faculty id same as attendance logic
    fid = None
    try:
        uid = int(user.get('id'))
    except Exception:
        uid = None
    if uid is not None:
        cur.execute(_sql("SELECT id FROM faculty WHERE id=?"), (uid,))
        row = cur.fetchone()
        if row:
            fid = row['id'] if isinstance(row, dict) else row[0]
    if fid is None:
        uname = user.get('username', '').strip().lower()
        cur.execute(_sql("SELECT id FROM faculty WHERE LOWER(name)=?"), (uname,))
        row = cur.fetchone()
        if row:
            fid = row['id'] if isinstance(row, dict) else row[0]

    if fid is None:
        st.info("Faculty record not found. Ask admin to create your faculty entry.")
        conn.close()
        return

    # Use cursor instead of pandas
    cur = conn.cursor()
    cur.execute(_sql("SELECT id,name,class_level FROM subjects WHERE faculty_id=?"), (fid,))
    subject_rows = cur.fetchall()
    
    # Convert rows to list of dicts
    subjects_data = []
    for row in subject_rows:
        row_dict = row if isinstance(row, dict) else {
            'id': row[0],
            'name': row[1],
            'class_level': row[2]
        }
        subjects_data.append(row_dict)
    
    if not subjects_data:
        st.info("No subjects assigned. Ask admin to assign subjects.")
        conn.close()
        return

    subj_labels = [f"{s['name']} ({s.get('class_level', '')})" for s in subjects_data]
    sel = st.selectbox("Subject", subj_labels)
    idx = subj_labels.index(sel)
    subject_id = int(subjects_data[idx]['id'])

    lecture_date = st.date_input("Lecture date")
    lecture_num = st.number_input("Lecture number", min_value=1, value=1)
    syllabus_pct = st.slider("Syllabus covered (%)", 0, 100, 0)

    # pull attendance records for this subject/date using cursor
    cur.execute(_sql("SELECT st.roll,st.name,a.status FROM attendance a JOIN students st ON a.student_id=st.id WHERE a.subject_id=? AND a.date=?"), (subject_id, str(lecture_date)))
    attend_rows = cur.fetchall()
    
    # Convert to dicts for easier handling
    attend_data = []
    for row in attend_rows:
        row_dict = row if isinstance(row, dict) else {
            'roll': row[0],
            'name': row[1],
            'status': row[2]
        }
        attend_data.append(row_dict)
    
    present_rolls = [r['roll'] for r in attend_data if r['status'] == 'present']
    absent_rolls = [r['roll'] for r in attend_data if r['status'] == 'absent']

    st.write(f"**Present ({len(present_rolls)})**: {', '.join(present_rolls) if present_rolls else 'None'}")
    st.write(f"**Absent ({len(absent_rolls)})**: {', '.join(absent_rolls) if absent_rolls else 'None'}")

    if st.button("Save LER"):
        cur = conn.cursor()
        cur.execute(_sql("INSERT INTO ler (faculty_id,subject_id,date,lecture_number,syllabus_covered_pct,present_count,absent_rolls) VALUES (?,?,?,?,?,?,?)"),
                    (fid, subject_id, str(lecture_date), lecture_num, syllabus_pct, len(present_rolls), ",".join(absent_rolls)))
        conn.commit()
        st.success("LER saved")

    # show previous records for this faculty using cursor
    st.markdown("---")
    st.write("### Previous LER entries")
    cur.execute(_sql("SELECT l.id,l.date,l.lecture_number,l.syllabus_covered_pct,l.present_count,l.absent_rolls,s.name as subject FROM ler l JOIN subjects s ON l.subject_id=s.id WHERE l.faculty_id=? ORDER BY l.date DESC"), (fid,))
    ler_rows = cur.fetchall()
    
    if ler_rows:
        ler_data = []
        for row in ler_rows:
            row_dict = row if isinstance(row, dict) else {
                'id': row[0],
                'date': row[1],
                'lecture_number': row[2],
                'syllabus_covered_pct': row[3],
                'present_count': row[4],
                'absent_rolls': row[5],
                'subject': row[6]
            }
            ler_data.append(row_dict)
        ler_df = pd.DataFrame(ler_data)
        st.dataframe(ler_df)
    else:
        st.info("No previous LER entries")
    
    conn.close()


def show_timetable():
    st.subheader("Timetable")
    conn = get_connection()
    c = conn.cursor()
    c.execute(_sql("SELECT day,hour,s.name AS subject FROM timetable t LEFT JOIN subjects s ON t.subject_id=s.id"))
    rows = c.fetchall()
    conn.close()
    
    if rows:
        data = []
        for row in rows:
            row_dict = row if isinstance(row, dict) else {
                'day': row[0],
                'hour': row[1],
                'subject': row[2]
            }
            data.append(row_dict)
        df = pd.DataFrame(data)
        st.dataframe(df)
    else:
        st.info("No timetable entries found")
