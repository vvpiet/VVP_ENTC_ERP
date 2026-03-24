#!/usr/bin/env python3
"""
Migration script to add missing columns to attendance table.
Run this on the server where the app is deployed.
"""

from db import get_connection, USE_POSTGRES

def migrate_attendance_columns():
    if not USE_POSTGRES:
        print("Migration only needed for PostgreSQL. Skipping.")
        return

    conn = get_connection()
    c = conn.cursor()

    print("Adding 'time' column to attendance table if missing...")
    c.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='attendance' AND column_name='time') THEN
            ALTER TABLE attendance ADD COLUMN time TEXT;
            RAISE NOTICE 'Added time column';
        ELSE
            RAISE NOTICE 'time column already exists';
        END IF;
    END $$;
    """)

    print("Adding 'lecture_number' column to attendance table if missing...")
    c.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='attendance' AND column_name='lecture_number') THEN
            ALTER TABLE attendance ADD COLUMN lecture_number INTEGER;
            RAISE NOTICE 'Added lecture_number column';
        ELSE
            RAISE NOTICE 'lecture_number column already exists';
        END IF;
    END $$;
    """)

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate_attendance_columns()