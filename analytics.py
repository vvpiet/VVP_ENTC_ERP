import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_connection, _sql


def show_analytics():
    st.subheader("Analytics Dashboard")
    conn = get_connection()
    df = pd.read_sql_query(
        _sql("SELECT sub.name as subject, sub.class_level as class, a.status, COUNT(*) as count FROM attendance a "
             "JOIN subjects sub ON a.subject_id=sub.id GROUP BY sub.name,sub.class_level,a.status"), conn)
    conn.close()
    if not df.empty:
        fig = px.bar(df, x='subject', y='count', color='status', barmode='group', title='Attendance by Subject')
        st.plotly_chart(fig)
    else:
        st.write("No data")
