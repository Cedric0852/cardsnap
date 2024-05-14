import streamlit as st
import bcrypt
import sqlite3
from PIL import Image
import io
import base64
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pytesseract

# Database connection
engine = create_engine("sqlite:///cardsnap.db")
Base = declarative_base()

class CardSnap(Base):
    __tablename__ = "cardsnap"
    id = Column(Integer, primary_key=True)
    event_name = Column(String, nullable=True)
    detected_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Configure pytesseract path if needed
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# Set the app name and favicon
app_name = "Cardsnap"
favicon_emoji = "📇"
st.set_page_config(page_title=app_name, page_icon=favicon_emoji)

# Functions to handle user authentication
def create_user(username, password, role):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed_password, role))
        conn.commit()
        return "User created successfully."
    except sqlite3.IntegrityError:
        return "User already exists."
    finally:
        conn.close()

def authenticate_user_role(username, password, role):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('SELECT password FROM users WHERE username=? AND role=?', (username, role))
        result = c.fetchone()
        if result:
            stored_hash = result[0]
            if bcrypt.checkpw(password.encode(), stored_hash):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        print(f"Error during authentication: {e}")
        return False
    finally:
        conn.close()

def authenticate_admin(username, password):
    return authenticate_user_role(username, password, "Admin")

def authenticate_user(username, password):
    return authenticate_user_role(username, password, "User")

# Functions for business card digitization
def detect_text(image):
    image = Image.open(io.BytesIO(image))
    text = pytesseract.image_to_string(image, lang='eng')
    return text

def save_to_db(event_name, detected_text, timestamp):
    card_snap = CardSnap(event_name=event_name, detected_text=detected_text, timestamp=timestamp)
    session.add(card_snap)
    session.commit()

def get_card_snaps():
    return session.query(CardSnap).order_by(CardSnap.timestamp.desc()).all()

def delete_card_snap(card_snap_id):
    card_snap = session.query(CardSnap).filter(CardSnap.id == card_snap_id).first()
    if card_snap:
        session.delete(card_snap)
        session.commit()

def search_card_snaps(search_keywords):
    keywords = f"%{search_keywords}%"
    search_condition = or_(
        CardSnap.detected_text.like(keywords),
        CardSnap.event_name.like(keywords)
    )
    return session.query(CardSnap).filter(search_condition).all()

def card_snaps_to_dataframe(card_snaps):
    data = {
        "Event Name": [card_snap.event_name for card_snap in card_snaps],
        "Business Card Info": [card_snap.detected_text for card_snap in card_snaps],
        "Timestamp": [card_snap.timestamp for card_snap in card_snaps],
    }
    return pd.DataFrame(data)

def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Card Snap History')
    writer.save()
    excel_data = output.getvalue()
    return excel_data

# User authentication state
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

# Login route
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["User", "Admin"])

    if st.button("Login"):
        if role == "Admin":
            auth_status = authenticate_admin(username, password)
        else:
            auth_status = authenticate_user(username, password)

        if auth_status:
            st.session_state.authentication_status = True
            st.session_state.username = username
            st.session_state.role = role
            st.success("Login successful")
            st.experimental_rerun()
        else:
            st.error("Username or password is incorrect")

# Logout route
def logout():
    st.session_state.authentication_status = None
    st.session_state.username = None
    st.session_state.role = None
    st.experimental_rerun()

# Home page
def home_page():
    st.title("Business Card Digitizer - CARDSNAP")
    st.write("Upload or take a picture of a business card.")
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption='Uploaded Business Card', use_column_width=True)
        image_bytes = uploaded_file.getvalue()
        event_name = st.text_input("Event Name (optional)")
        if st.button("Detect Text"):
            detected_text = detect_text(image_bytes)
            st.write("Detected Text:")
            st.markdown(f"```\n{detected_text}\n```")
            timestamp = datetime.utcnow()
            save_to_db(event_name, detected_text, timestamp)
            st.success("Text saved successfully!")

# Card Snap History page
def card_snap_history_page():
    st.title("Card Snap History")
    search_keywords = st.text_input("Search", "")
    if search_keywords:
        card_snaps = search_card_snaps(search_keywords)
    else:
        card_snaps = get_card_snaps()

    for i, card_snap in enumerate(card_snaps):
        st.subheader(f"{card_snap.event_name if card_snap.event_name else 'No Event Name'} - {card_snap.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        unique_key = f"card_snap_text_area_{i}"
        st.text_area("Detected Text", value=card_snap.detected_text, height=150, max_chars=None, key=unique_key)
        if st.button("Delete", key=f"delete_button_{i}"):
            delete_card_snap(card_snap.id)
            st.success(f"Deleted entry: {card_snap.event_name if card_snap.event_name else 'No Event Name'} - {card_snap.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            st.experimental_rerun()

    if st.button("Export to Excel"):
        card_snaps = get_card_snaps()
        df = card_snaps_to_dataframe(card_snaps)
        excel_file = to_excel(df)
        b64 = base64.b64encode(excel_file).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="card_snap_history.xlsx">Download Card Snap History as Excel</a>'
        st.markdown(href, unsafe_allow_html=True)

# User Management page (Admin only)
def user_management_page():
    st.header("User Management")
    st.write("Manage user accounts here.")

    # Create user form
    st.subheader("Create User")
    create_username = st.text_input("Username (create)")
    create_password = st.text_input("Password (create)", type="password")
    create_role = st.selectbox("Role (create)", ["User", "Admin"])
    if st.button("Create User"):
        if create_username and create_password:
            result = create_user(create_username, create_password, create_role)
            st.success(result)
        else:
            st.error("Please provide both username and password.")

    # Read users
    st.subheader("User List")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username, role FROM users")
    users = c.fetchall()
    conn.close()
    for user in users:
        st.write(f"Username: {user[0]}, Role: {user[1]}")

    # Update user role form
    st.subheader("Update User Role")
    update_username = st.text_input("Username (update)")
    new_role = st.selectbox("New Role", ["User", "Admin"], key="update_role")
    if st.button("Update Role"):
        if update_username:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET role=? WHERE username=?", (new_role, update_username))
            conn.commit()
            conn.close()
            st.success(f"Updated role for {update_username} to {new_role}")
        else:
            st.error("Please provide the username.")

    # Delete user form
    st.subheader("Delete User")
    delete_username = st.text_input("Username (delete)")
    if st.button("Delete User"):
        if delete_username:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username=?", (delete_username,))
            conn.commit()
            conn.close()
            st.success(f"Deleted user {delete_username}")
        else:
            st.error("Please provide the username.")

# Main application logic
if st.session_state.authentication_status:
    st.sidebar.title("Navigation")
    if st.sidebar.button("Logout"):
        logout()

    if st.session_state.role == "Admin":
        page = st.sidebar.radio("Go to", ["Home", "Card Snap History", "Manage Users"])
        if page == "Home":
            home_page()
        elif page == "Card Snap History":
            card_snap_history_page()
        elif page == "Manage Users":
            user_management_page()
    else:
        page = st.sidebar.radio("Go to", ["Home", "Card Snap History"])
        if page == "Home":
            home_page()
        elif page == "Card Snap History":
            card_snap_history_page()
else:
    login()
