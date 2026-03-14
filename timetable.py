import streamlit as st
from db import get_connection, _sql
import pandas as pd


def edit_timetable():
    st.subheader("Edit Timetable")
    conn = get_connection()
    c = conn.cursor()
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday']
    hours = [1,2,3,4,5,6]
    subjects = pd.read_sql_query(_sql("SELECT id,name FROM subjects"), conn)
    table = {}
    for d in days:
        for h in hours:
            sel = st.selectbox(f"{d} - Hour {h}", [''] + subjects['name'].tolist(), key=f"{d}{h}")
            if sel:
                sid = subjects[subjects['name']==sel]['id'].values[0]
                table[(d,h)] = sid
    if st.button("Save Timetable"):
        c.execute(_sql("DELETE FROM timetable"))
        for (d,h), sid in table.items():
            c.execute(_sql("INSERT INTO timetable (day,hour,subject_id) VALUES (?,?,?)"), (d,h,sid))
        conn.commit()
        st.success("Saved")
    conn.close()


def view_timetable():
    conn = get_connection()
    df = pd.read_sql_query(_sql("SELECT day,hour,s.name AS subject FROM timetable t LEFT JOIN subjects s ON t.subject_id=s.id"), conn)
    conn.close()
    return df
