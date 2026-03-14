import streamlit as st
from db import initialize_db
from auth import validate_login, hash_password, create_user
from admin import admin_dashboard
from faculty import faculty_portal
from student import student_portal
from analytics import show_analytics
from utils import check_alerts_threshold


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


def main():
    st.set_page_config(page_title="College ERP", layout="wide")
    initialize_db()
    st.sidebar.title("College ERP")
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
    if not st.session_state.logged_in:
        login()
    else:
        user = st.session_state.user
        if user['role'] == 'admin':
            # run analytics and alerts periodically
            check_alerts_threshold()
            admin_dashboard()
            show_analytics()
        elif user['role'] == 'faculty':
            faculty_portal(user)
        elif user['role'] == 'student':
            student_portal(user)
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            rerun()


def login():
    st.subheader("Login")
    uname = st.text_input("Username")
    pwd = st.text_input("Password", type='password')
    if st.button("Login"):
        user = validate_login(uname, pwd)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            rerun()
        else:
            st.error("Invalid credentials")
    with st.expander("Create admin account"):
        au = st.text_input("Admin username", key='au')
        ap = st.text_input("Admin password", type='password', key='ap')
        if st.button("Create", key='create_admin'):
            try:
                create_user(au, ap, 'admin')
                # automatically log in the new admin
                user = validate_login(au, ap)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    rerun()
                else:
                    st.success("Admin created, please login")
            except Exception as e:
                st.error(str(e))

if __name__ == "__main__":
    main()
