import os
import streamlit as st
from db import get_connection, _sql, USE_POSTGRES
import pandas as pd
from attendance import mark_attendance

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _ensure_faculty_record(user, conn):
    """Ensure a faculty row exists tied to this user and return its id."""
    uid = None
    try:
        uid = int(user.get('id'))
    except Exception:
        uid = None

    cur = conn.cursor()

    if uid is not None:
        # Ensure row exists for this faculty user
        cur.execute(_sql("SELECT id FROM faculty WHERE id=?"), (uid,))
        if not cur.fetchone():
            name = user.get('username', '').strip()
            if USE_POSTGRES:
                cur.execute(_sql("INSERT INTO faculty (id,name) SELECT ?,? WHERE NOT EXISTS (SELECT 1 FROM faculty WHERE id=?)"),
                            (uid, name, uid))
            else:
                # SQLite supports INSERT OR IGNORE
                cur.execute(_sql("INSERT OR IGNORE INTO faculty (id,name) VALUES (?,?)"), (uid, name))
            conn.commit()
        return uid

    # fallback: match by username
    uname = user.get('username', '').strip().lower()
    cur.execute(_sql("SELECT id FROM faculty WHERE LOWER(name)=?"), (uname,))
    row = cur.fetchone()
    if row:
        return row['id'] if isinstance(row, dict) else row[0]
    return None


def faculty_portal(user):
    st.title(f"Faculty Portal - {user['username']}")
    menu = ["Take Attendance","LER","Notes & Assignments","View Attendance","Timetable"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Take Attendance":
        take_attendance(user)
    elif choice == "LER":
        lecture_engagement_register(user)
    elif choice == "Notes & Assignments":
        faculty_materials(user)
    elif choice == "View Attendance":
        view_attendance(user)
    elif choice == "Timetable":
        show_timetable()


def take_attendance(user):
    st.subheader("Take Attendance")
    conn = get_connection()
    cur = conn.cursor()

    # Ensure there is a faculty record for this user and obtain its id.
    fid = _ensure_faculty_record(user, conn)

    # retrieve subjects for this faculty
    subjects_data = []
    if fid is not None:
        cur.execute(_sql("SELECT s.id,s.name,s.class_level FROM subjects s WHERE s.faculty_id=?"), (fid,))
        subject_rows = cur.fetchall()
        # Convert rows to list of dicts
        for row in subject_rows:
            row_dict = row if isinstance(row, dict) else {
                'id': row[0],
                'name': row[1],
                'class_level': row[2]
            }
            subjects_data.append(row_dict)
    conn.close()

    if not subjects_data:
        st.info("You have no subjects assigned. Ask admin to add some.")
        return

    # build dropdown labels including class
    subject_id = None
    if subjects_data:
        labels = [f"{s['name']} ({s.get('class_level', '')})" for s in subjects_data]
        sel = st.selectbox("Subject", labels)
        # map back to id
        idx = labels.index(sel)
        subject_id = int(subjects_data[idx]['id'])

    if 'selected_subject' not in st.session_state:
        st.session_state.selected_subject = None

    if st.button("Load students") and subject_id is not None:
        st.session_state.selected_subject = subject_id

    # if a subject has been loaded, display attendance form
    if st.session_state.selected_subject is not None:
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

    # Ensure there is a faculty record for this user and get its id
    fid = _ensure_faculty_record(user, conn)

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
        try:
            cur = conn.cursor()
            cur.execute(_sql("INSERT INTO ler (faculty_id,subject_id,date,lecture_number,syllabus_covered_pct,present_count,absent_rolls) VALUES (?,?,?,?,?,?,?)"),
                        (fid, subject_id, str(lecture_date), lecture_num, syllabus_pct, len(present_rolls), ",".join(absent_rolls)))
            
            # Commit the transaction
            conn.commit()
            
            # Verify insertion by querying back immediately
            cur_verify = conn.cursor()
            cur_verify.execute(_sql("SELECT COUNT(*) as cnt FROM ler WHERE faculty_id=? AND date=?"), 
                              (fid, str(lecture_date)))
            verify_row = cur_verify.fetchone()
            verify_count = verify_row['cnt'] if isinstance(verify_row, dict) else verify_row[0]
            
            st.success(f"✅ LER saved successfully (verified: {verify_count} LER entries for this date)")
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            st.error(f"❌ Failed to save LER: {str(e)}")
            import traceback
            st.error(f"Details: {traceback.format_exc()}")

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


def faculty_materials(user):
    """Allow faculty to upload notes and assignments for their subjects."""
    st.subheader("Notes & Assignments")

    # resolve faculty id and ensure a faculty record exists for this user
    conn = get_connection()
    cur = conn.cursor()
    fid = _ensure_faculty_record(user, conn)

    if fid is None:
        st.error("Faculty record not found. Ask admin to create your faculty entry.")
        conn.close()
        return

    # fetch subjects for this faculty
    cur.execute(_sql("SELECT id,name,code,class_level FROM subjects WHERE faculty_id=?"), (fid,))
    subj_rows = cur.fetchall()
    subjects = []
    for row in subj_rows:
        subj = row if isinstance(row, dict) else {'id': row[0], 'name': row[1], 'code': row[2], 'class_level': row[3]}
        subjects.append(subj)

    if not subjects:
        st.info("No subjects assigned. Ask admin to assign subjects.")
        conn.close()
        return

    # Keep the selected subject stable across reruns (to avoid losing selection)
    labels = [f"{s['name']} ({s.get('class_level','')})" for s in subjects]
    default_index = 0
    if 'faculty_material_subject_id' in st.session_state:
        prev_id = st.session_state['faculty_material_subject_id']
        for i, s in enumerate(subjects):
            if s['id'] == prev_id:
                default_index = i
                break

    sel = st.selectbox("Subject", labels, index=default_index)
    selected_index = labels.index(sel)
    subject = subjects[selected_index]
    st.session_state['faculty_material_subject_id'] = subject['id']

    # upload section
    st.markdown("---")
    st.write("### Upload Notes")
    note_title = st.text_input("Title")
    note_file = st.file_uploader("Select file", type=['pdf','docx','txt','pptx'], key='note_upload')
    if st.button("Upload Note"):
        if not note_title or not note_file:
            st.error("Title and file are required")
        else:

            os.makedirs('uploads', exist_ok=True)
            filename = f"{subject['code']}_note_{int(pd.Timestamp('now').timestamp())}_{note_file.name}"
            path = os.path.join(UPLOAD_DIR, filename)
            with open(path, 'wb') as f:
                f.write(note_file.getbuffer())
            cur.execute(_sql("INSERT INTO notes (subject_id,title,filename) VALUES (?,?,?)"),
                        (subject['id'], note_title, filename))
            conn.commit()
            st.success("Note uploaded")

    st.markdown("---")
    st.write("### Upload Assignment")
    assn_title = st.text_input("Assignment title", key='assn_title')
    due_date = st.date_input("Due date")
    assn_file = st.file_uploader("Select assignment file", type=['pdf','docx','txt','pptx'], key='assn_upload')
    if st.button("Upload Assignment"):
        if not assn_title or not assn_file:
            st.error("Title and file are required")
        else:
            os.makedirs('uploads', exist_ok=True)
            filename = f"{subject['code']}_assn_{int(pd.Timestamp('now').timestamp())}_{assn_file.name}"
            path = os.path.join(UPLOAD_DIR, filename)
            with open(path, 'wb') as f:
                f.write(assn_file.getbuffer())
            cur.execute(_sql("INSERT INTO assignments (subject_id,title,filename,due_date) VALUES (?,?,?,?)"),
                        (subject['id'], assn_title, filename, str(due_date)))
            conn.commit()
            st.success("Assignment uploaded")

    # show existing materials for this subject
    st.markdown("---")
    st.write("### Existing Notes")
    try:
        cur.execute(_sql("SELECT id,title,filename,created_at FROM notes WHERE subject_id=? ORDER BY created_at DESC"), (subject['id'],))
        notes = cur.fetchall()
        if notes:
            for idx, note_row in enumerate(notes):
                note = note_row if isinstance(note_row, dict) else {
                    'id': note_row[0],
                    'title': note_row[1],
                    'filename': note_row[2],
                    'created_at': note_row[3]
                }
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 {note['title']}")
                with col2:
                    try:
                        note_path = os.path.join(UPLOAD_DIR, note['filename'])
                        if os.path.exists(note_path):
                            with open(note_path, 'rb') as f:
                                st.download_button("📥", data=f.read(), file_name=note['filename'], key=f"note_dl_{note['id']}")
                        else:
                            st.error("File missing: {}".format(note['filename']))
                    except FileNotFoundError:
                        st.error("File missing")
        else:
            st.info("No notes uploaded yet")
    except Exception as e:
        st.error(f"Error loading notes: {e}")

    st.markdown("---")
    st.write("### Existing Assignments")
    try:
        cur.execute(_sql("SELECT id,title,filename,due_date,created_at FROM assignments WHERE subject_id=? ORDER BY created_at DESC"), (subject['id'],))
        assignments = cur.fetchall()
        if assignments:
            for idx, assn_row in enumerate(assignments):
                assn = assn_row if isinstance(assn_row, dict) else {
                    'id': assn_row[0],
                    'title': assn_row[1],
                    'filename': assn_row[2],
                    'due_date': assn_row[3],
                    'created_at': assn_row[4]
                }
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📋 {assn['title']} (Due: {assn.get('due_date')})")
                with col2:
                    try:
                        assn_path = os.path.join(UPLOAD_DIR, assn['filename'])
                        if os.path.exists(assn_path):
                            with open(assn_path, 'rb') as f:
                                st.download_button("📥", data=f.read(), file_name=assn['filename'], key=f"assn_dl_{assn['id']}")
                        else:
                            st.error("File missing: {}".format(assn['filename']))
                    except FileNotFoundError:
                        st.error("File missing")
        else:
            st.info("No assignments posted yet")
    except Exception as e:
        st.error(f"Error loading assignments: {e}")

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
