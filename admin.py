import streamlit as st
from db import get_connection, _sql
from auth import hash_password
import pandas as pd


def admin_dashboard():
    st.title("Admin Dashboard")
    menu = ["Users","Students","Subjects","Timetable","View Reports"]
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Users":
        manage_users()
    elif choice == "Students":
        manage_students()
    elif choice == "Subjects":
        manage_subjects()
    elif choice == "Timetable":
        manage_timetable()
    elif choice == "View Reports":
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
            conn = get_connection()
            try:
                create_user(uname, pwd, role)
                # add corresponding student/faculty entry if needed
                if role == 'student':
                    conn.execute(
                        _sql("INSERT INTO students (id,name,roll) VALUES ((SELECT id FROM users WHERE username=?),?,?) ON CONFLICT(roll) DO NOTHING"),
                        (uname, uname, uname)
                    )
                elif role == 'faculty':
                    # ensure faculty table uses the same id and name as user
                    # note: username already normalized in create_user
                    cur = conn.cursor()
                    cur.execute(_sql("SELECT id FROM users WHERE username=?"), (uname,))
                    urow = cur.fetchone()
                    if urow:
                        uid = urow[0]
                        conn.execute(
                            _sql("INSERT INTO faculty (id,name) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name"),
                            (uid, uname)
                        )
                conn.commit()
                st.success("User created")
            except Exception as e:
                st.error(str(e))
            finally:
                conn.close()
    # list users
    conn = get_connection()
    df = pd.read_sql_query(_sql("SELECT id,username,role FROM users"), conn)
    conn.close()
    st.dataframe(df)


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
        fac_df = pd.read_sql_query(_sql("SELECT id,name FROM faculty"), conn)
        fac = st.selectbox("Faculty", [''] + fac_df['name'].tolist())
        submitted = st.form_submit_button("Add")
        if submitted:
            # validate fields
            if not name or not code:
                st.error("Name and Code are required")
            else:
                fid = None
                if fac:
                    fid = fac_df[fac_df['name']==fac]['id'].values[0]
                    try:
                        fid = int(fid)
                    except Exception:
                        fid = None
                # check uniqueness
                exists = c.execute(_sql("SELECT 1 FROM subjects WHERE code=?"), (code,)).fetchone()
                if exists:
                    st.error("Subject code already exists")
                else:
                    try:
                        c.execute(_sql("INSERT INTO subjects (name,code,faculty_id,class_level) VALUES (?,?,?,?)"), (name, code, fid, class_level))
                        conn.commit()
                        st.success("Subject added")
                    except Exception as e:
                        st.error(str(e))
    # show subjects
    df = pd.read_sql_query(_sql("SELECT s.id,s.name,s.code,s.class_level,f.name as faculty FROM subjects s LEFT JOIN faculty f ON s.faculty_id=f.id"), conn)
    st.dataframe(df)
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
    st.subheader("PDF Reports")
    st.write("Use the reports module to generate PDFs.")
