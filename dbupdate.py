import sqlite3

def update_schema():
    conn = sqlite3.connect('cardsnap.db')
    c = conn.cursor()
    try:
        # Add requester column to requests table if it doesn't exist
        c.execute("ALTER TABLE requests ADD COLUMN timestamp TEXT")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    conn.commit()
    conn.close()

update_schema()
