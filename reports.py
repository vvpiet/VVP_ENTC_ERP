from fpdf import FPDF
from db import get_connection, _sql
import pandas as pd
import streamlit as st


def generate_student_report(user):
    conn = get_connection()
    # find student id from user
    cur = conn.cursor()
    cur.execute(_sql("SELECT s.id FROM students s JOIN users u ON u.id=s.id WHERE u.username=?"), (user['username'],))
    res = cur.fetchone()
    if not res:
        st.error("Student record not found")
        conn.close()
        return
    student_id = res['id'] if isinstance(res, dict) else res[0]
    # fetch attendance
    df = pd.read_sql_query(
        _sql("SELECT a.date,sub.name,a.status FROM attendance a JOIN subjects sub ON a.subject_id=sub.id WHERE a.student_id=?"),
        conn, params=(student_id,))
    conn.close()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"Attendance Report for {user['username']}", ln=1)
    pdf.ln(5)
    for idx, row in df.iterrows():
        pdf.cell(0, 8, txt=f"{row['date']} - {row['name']} - {row['status']}", ln=1)
    pdf_path = f"report_{user['username']}.pdf"
    pdf.output(pdf_path)
    st.success(f"Report generated: {pdf_path}")
    st.download_button("Download report", data=open(pdf_path, "rb"), file_name=pdf_path)
