# College ERP System

A simple College ERP built with Python, Streamlit, SQLite, Pandas, Plotly, and FPDF. Features:

- Admin dashboard for user/subject/timetable management
- Upload student lists (CSV/XLS) with roll, name and class; records auto-sorted by class
- Faculty portal for attendance and timetable
- Student portal for viewing attendance, timetable, alerts, and downloading PDF reports
- Subject-wise attendance tracking (subjects include class level; students filtered accordingly)
- Timetable editing
- Automatic attendance percentage alerts
- PDF report generation using FPDF
- Analytics dashboard with Plotly charts
- Modern UI layout using Streamlit
- Ready for deployment (e.g., Streamlit Cloud, Heroku)

## Setup

1. Clone the repo or download.
2. Navigate to the project folder.
3. Create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

4. Run the app:

```bash
streamlit run app.py
```

5. Open the URL shown by Streamlit in your browser.

6. Create an admin account using the form on login page, then login to start managing.

## Deployment

### Local (SQLite)

- Use `streamlit run app.py`.
- The database is stored in `college.db` in the project root.

### Streamlit Cloud + Neon (Postgres)

1. Push the repo to GitHub.
2. On Streamlit Cloud, create a new app and point it to the repo.
3. In App Settings → Secrets, set a secret named `DATABASE_URL` (or `NEON_DATABASE_URL`) to your Neon/Postgres connection string.

The app detects `DATABASE_URL` and will automatically use the remote Postgres database instead of SQLite.

## Notes

- Database file `college.db` will be created in root on first run.
- Use the admin dashboard to add users, students, faculty, subjects, and manage timetable.

