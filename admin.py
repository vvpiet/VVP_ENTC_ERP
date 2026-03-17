import streamlit as st
from db import get_connection, _sql, get_db_info
from auth import hash_password
import pandas as pd


def rerun():
    # Streamlit removed or renamed experimental_rerun in some versions
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        # fallback via runtime exception
        try:
            from streamlit.runtime.scriptrunner import RerunException
            from streamlit.runtime.scriptrunner_utils.script_requests import RerunData
            raise RerunException(RerunData())
        except ImportError:
            # last resort: refresh by writing a small script tag
            st.write("<meta http-equiv=\"refresh\" content=\"0\">", unsafe_allow_html=True)


def admin_dashboard():
    st.title("Admin Dashboard")
    db_info = get_db_info()
    st.sidebar.markdown("### Connection")
    if db_info.get("backend") == "postgres":
        st.sidebar.success(f"Postgres / Neon")
        st.sidebar.write(f"URL: `{db_info.get('url')}`")
    else:
        st.sidebar.success("SQLite")
        st.sidebar.write(f"File: `{db_info.get('path')}`")

    menu = ["Users","Students","Subjects","Timetable","Attendance Reports"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Users":
        manage_users()
    elif choice == "Students":
        manage_students()
    elif choice == "Subjects":
        manage_subjects()
    elif choice == "Timetable":
        manage_timetable()
    elif choice == "Attendance Reports":
        view_reports()


def manage_users():
    st.subheader("Manage Users")
    with st.form("create_user"):
        uname = st.text_input("Username")
        pwd = st.text_input("Password", type='password')
        role = st.selectbox("Role", ["admin","faculty","student"])
        submitted = st.form_submit_button("Create")
        if submitted:
            from auth import create_user
            uname = uname.strip()
            conn = get_connection()
            try:
                uid = create_user(uname, pwd, role)
                # add corresponding student/faculty entry if needed
                cur = conn.cursor()
                if role == 'student':
                    # NOTE: psycopg2 requires a cursor for execute (sqlite allows conn.execute)
                    cur.execute(
                        _sql("INSERT INTO students (id,name,roll) VALUES (?,?,?) ON CONFLICT(roll) DO NOTHING"),
                        (uid, uname, uname)
                    )
                    st.write(f"Inserted student row for user id {uid}")
                elif role == 'faculty':
                    # ensure faculty table uses the same id and name as user
                    try:
                        cur.execute(
                            _sql("INSERT INTO faculty (id,name) VALUES (?,?)"),
                            (uid, uname)
                        )
                        st.write(f"Inserted faculty row for user id {uid}")
                    except Exception as e:
                        st.error(f"Faculty insert failed: {e}")
                        raise
                conn.commit()
                st.success("User created")
                rerun()
            except Exception as e:
                st.error(str(e))
            finally:
                conn.close()
    # list users (avoid pandas quirks by using cursor directly)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(_sql("SELECT u.id, COALESCE(s.name, f.name, u.username) as display_name, u.username, u.role FROM users u LEFT JOIN students s ON u.id = s.id LEFT JOIN faculty f ON u.id = f.id"))
    rows = cur.fetchall()
    users = []
    for r in rows:
        users.append({
            'id': r['id'],
            'Name': r['display_name'],
            'username': r['username'],
            'role': r['role']
        })
    conn.close()

    if users:
        st.table(users)
    else:
        st.info("No users found")

    st.markdown("---")
    st.subheader("Delete user")
    if users:
        display_map = {u['Name']: u for u in users}
        to_delete_display = st.selectbox("Select user", list(display_map.keys()))
        if st.button("Delete user"):
            u = display_map[to_delete_display]
            conn = get_connection()
            cur = conn.cursor()
            try:
                cur.execute(_sql("DELETE FROM attendance WHERE student_id=?"), (u['id'],))
                cur.execute(_sql("DELETE FROM students WHERE id=?"), (u['id'],))
                cur.execute(_sql("DELETE FROM faculty WHERE id=?"), (u['id'],))
                cur.execute(_sql("DELETE FROM users WHERE id=?"), (u['id'],))
                conn.commit()
                st.success(f"Deleted user {to_delete_display}")
                rerun()
            except Exception as e:
                st.error(f"Delete failed: {str(e)}")
            finally:
                conn.close()


def manage_students():
    st.subheader("Students")
    st.write("Upload a CSV/XLS file with columns roll,name,class")
    file = st.file_uploader("Student list", type=["csv","xls","xlsx"])
    if file is not None:
        try:
            if file.name.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            return
        df.columns = [c.strip().lower() for c in df.columns]
        if not {'roll','name','class'}.issubset(set(df.columns)):
            st.error("File must contain roll, name, class columns")
        else:
            # normalize class values
            df['class'] = df['class'].astype(str).str.strip().str.upper()
            order = {'SY':0,'TY':1,'BTECH':2}
            df['class_order'] = df['class'].map(lambda x: order.get(x,99))
            df.sort_values(['class_order','roll'], inplace=True)
            conn = get_connection()
            c = conn.cursor()
            c.execute(_sql("DELETE FROM students"))
            for _, row in df.iterrows():
                cls = str(row['class']).upper()
                try:
                    c.execute(_sql("INSERT INTO students (name,roll,class_level) VALUES (?,?,?)"), (row['name'], row['roll'], cls))
                except Exception as e:
                    # skip duplicates or report
                    print(f"skipping roll {row['roll']}: {e}")
            conn.commit()
            conn.close()
            st.success("Students uploaded and sorted")

    st.markdown("---")
    st.subheader("Delete student")
    conn = get_connection()
    df_students = pd.read_sql_query(_sql("SELECT id,name,roll,class_level FROM students"), conn)
    conn.close()
    if not df_students.empty:
        to_delete = st.selectbox("Select student (roll)", df_students['roll'].tolist())
        if st.button("Delete student"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(_sql("DELETE FROM attendance WHERE student_id IN (SELECT id FROM students WHERE roll=?)"), (to_delete,))
            cur.execute(_sql("DELETE FROM students WHERE roll=?"), (to_delete,))
            conn.commit()
            conn.close()
            st.success(f"Deleted student {to_delete}")


def manage_subjects():
    st.subheader("Subjects")
    conn = get_connection()
    c = conn.cursor()
    # form for adding new subject
    with st.form("add_subject"):
        name = st.text_input("Name")
        code = st.text_input("Code")
        class_level = st.selectbox("Class Level", ["SY","TY","BTech"], index=0)
        # choose faculty
        cur_fac = conn.cursor()
        cur_fac.execute(_sql("SELECT id,name FROM faculty"))
        fac_rows = cur_fac.fetchall()
        fac_options = [""] + [r['name'] for r in fac_rows]
        fac = st.selectbox("Faculty", fac_options)
        submitted = st.form_submit_button("Add")
        if submitted:
            # validate fields
            if not name or not code:
                st.error("Name and Code are required")
            else:
                fid = None
                if fac:
                    # find faculty id by name
                    fid = next((r['id'] for r in fac_rows if r['name'] == fac), None)
                # check uniqueness
                c.execute(_sql("SELECT 1 FROM subjects WHERE code=?"), (code,))
                exists = c.fetchone()
                if exists:
                    st.error("Subject code already exists")
                else:
                    try:
                        c.execute(_sql("INSERT INTO subjects (name,code,faculty_id,class_level) VALUES (?,?,?,?)"), (name, code, fid, class_level))
                        conn.commit()
                        st.success("Subject added")
                        rerun()
                    except Exception as e:
                        st.error(str(e))
    # Close and reopen connection to get fresh data
    conn.close()
    conn = get_connection()
    
    # show subjects with fresh data
    df = pd.read_sql_query(_sql("SELECT s.id,s.name,s.code,s.class_level,f.name as faculty FROM subjects s LEFT JOIN faculty f ON s.faculty_id=f.id"), conn)
    
    if not df.empty:
        st.write("### Subject Assignments:")
        # Create display dataframe with proper column names
        display_data = []
        for idx, row in df.iterrows():
            # Skip if this is a header row
            if str(row['id']).lower() == 'id':
                continue
            display_data.append({
                'ID': row['id'],
                'Name': str(row['name']),
                'Code': str(row['code']),
                'Class': str(row['class_level']),
                'Faculty': str(row['faculty']) if pd.notna(row['faculty']) else 'Unassigned'
            })
        if display_data:
            display_df = pd.DataFrame(display_data)
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No subjects found")
    else:
        st.info("No subjects found")

    st.markdown("---")
    st.subheader("Update subject faculty")
    if not df.empty:
        to_update = st.selectbox("Select subject to update", df['code'].tolist())
        # get faculty options
        cur_fac = conn.cursor()
        cur_fac.execute(_sql("SELECT id,name FROM faculty"))
        fac_rows = cur_fac.fetchall()
        fac_options = [""] + [r['name'] for r in fac_rows]
        new_fac = st.selectbox("Assign to faculty", fac_options, key="update_faculty")
        if st.button("Update subject"):
            fid = None
            if new_fac:
                fid = next((r['id'] for r in fac_rows if r['name'] == new_fac), None)
            cur = conn.cursor()
            cur.execute(_sql("UPDATE subjects SET faculty_id=? WHERE code=?"), (fid, to_update))
            conn.commit()
            st.success(f"Updated subject {to_update} assigned to {new_fac if new_fac else 'unassigned'}")
            rerun()

    st.markdown("---")
    st.subheader("Delete subject")
    if not df.empty:
        to_delete = st.selectbox("Select subject code", df['code'].tolist())
        if st.button("Delete subject"):
            try:
                cur = conn.cursor()
                cur.execute(_sql("DELETE FROM attendance WHERE subject_id IN (SELECT id FROM subjects WHERE code=?)"), (to_delete,))
                cur.execute(_sql("DELETE FROM timetable WHERE subject_id IN (SELECT id FROM subjects WHERE code=?)"), (to_delete,))
                cur.execute(_sql("DELETE FROM subjects WHERE code=?"), (to_delete,))
                conn.commit()
                st.success(f"Deleted subject {to_delete}")
                rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")
    conn.close()


def manage_timetable():
    from timetable import edit_timetable
    st.subheader("Timetable")
    edit = st.checkbox("Edit mode")
    if edit:
        edit_timetable()
    conn = get_connection()
    df = pd.read_sql_query(_sql("SELECT t.day,t.hour,s.name AS subject FROM timetable t LEFT JOIN subjects s ON t.subject_id=s.id"), conn)
    st.dataframe(df)
    conn.close()


def view_reports():
    st.subheader("Attendance Reports")
    period = st.selectbox("Period", ["Daily","Weekly","Monthly","Custom"])
    today = pd.to_datetime("today").normalize()
    if period == "Daily":
        start = st.date_input("Date", today.date())
        end = start
    elif period == "Weekly":
        start = st.date_input("Week start", today.date())
        end = start + pd.Timedelta(days=6)
    elif period == "Monthly":
        month = st.date_input("Month start", today.replace(day=1).date())
        start = month
        end = (pd.to_datetime(month) + pd.offsets.MonthEnd(0)).date()
    else:
        start = st.date_input("Start date", today.date())
        end = st.date_input("End date", today.date())

    if st.button("Generate report"):
        conn = get_connection()
        df = pd.read_sql_query(
            _sql("SELECT a.date, s.name as subject, st.roll, st.name as student, a.status "
                 "FROM attendance a "
                 "JOIN students st ON a.student_id=st.id "
                 "JOIN subjects s ON a.subject_id=s.id "
                 "WHERE date BETWEEN ? AND ?"),
            conn, params=(str(start), str(end)))
        conn.close()
        if df.empty:
            st.warning("No attendance records found for the selected period.")
            return
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name=f"attendance_{start}_{end}.csv")
        st.dataframe(df)
