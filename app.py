from PIL import Image
import streamlit as st
import requests
import io
import base64
import re
from sqlalchemy_utils import escape_like
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import or_
import streamlit_ace as st_ace
from PIL import Image
import pytesseract
from database.db import db
from database.models import User, BusinessCard, Company, AuditLog
from utils.auth import AuthManager, login_required, role_required
from utils.scanner import Scanner
from utils.export import Exporter
from pages.card_management import render_card_management
from pages.company_management import render_company_management
from pages.export_management import render_export_management
from pages.user_management import render_user_management

API_KEY = st.secrets["key"]
#database connection 
# Set up the SQLite database
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
#TExt detection function

# def detect_text(image):
#     url = "https://vision.googleapis.com/v1/images:annotate?key=" + API_KEY
#     headers = {'Content-Type': 'application/json'}
#     image_content = base64.b64encode(image).decode('UTF-8')
#     data = {
#       "requests": [
#         {
#           "image": {
#             "content": image_content
#           },
#           "features": [
#             {
#               "type": "DOCUMENT_TEXT_DETECTION"
#             }
#           ]
#         }
#       ]
#     }
#     response = requests.post(url, headers=headers, json=data)
#     return response.json()
# Add a function to save detected text to the database


# Configure pytesseract path if needed (especially on Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def detect_text(image):
    # Convert image bytes to an image object
    image = Image.open(io.BytesIO(image))
    # Use Tesseract to do OCR on the image
    text = pytesseract.image_to_string(image, lang='eng')
    return text
def save_to_db(event_name, detected_text, timestamp):
    card_snap = CardSnap(event_name=event_name, detected_text=detected_text, timestamp=timestamp)
    session.add(card_snap)
    session.commit()

# Add a function to retrieve records from the database
def get_card_snaps():
    return session.query(CardSnap).order_by(CardSnap.timestamp.desc()).all()
# Add this function to delete a card_snap entry by ID
def delete_card_snap(card_snap_id):
    card_snap = session.query(CardSnap).filter(CardSnap.id == card_snap_id).first()
    if card_snap:
        session.delete(card_snap)
        session.commit()
# Add a function to filter records based on search keywords
def search_card_snaps(search_keywords):
    keywords = f"%{search_keywords}%"
    
    if search_keywords.isdigit():
        search_value = int(search_keywords)
        search_keywords_no_zero = f"%{search_value}%"
        search_condition = or_(
            CardSnap.detected_text.like(keywords),
            CardSnap.detected_text.like(search_keywords_no_zero),
            CardSnap.event_name.like(keywords)
        )
    else:
        search_condition = or_(
            CardSnap.detected_text.like(keywords),
            CardSnap.event_name.like(keywords)
        )

    return session.query(CardSnap).filter(search_condition).all()
# export function 
# Add a function to convert the database records to a DataFrame
def card_snaps_to_dataframe(card_snaps):
    data = {
        "Event Name": [card_snap.event_name for card_snap in card_snaps],
        "Business Card Info": [card_snap.detected_text for card_snap in card_snaps],
        "Timestamp": [card_snap.timestamp for card_snap in card_snaps],
    }
    return pd.DataFrame(data)

# Add the export to Excel button
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Card Snap History')
    writer.save()
    excel_data = output.getvalue()
    return excel_data

# Initialize database
db.init_db()

# Page config
st.set_page_config(
    page_title="CardSnap",
    page_icon="📇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'username' not in st.session_state:
    st.session_state.username = None

def login_user(username: str, password: str) -> bool:
    """Authenticate user and set session state."""
    user = AuthManager.authenticate_user(username, password)
    if user:
        st.session_state.user_id = user.id
        st.session_state.user_role = user.role
        st.session_state.username = user.username
        
        # Log login
        log = AuditLog(
            user_id=user.id,
            action="login",
            details={"timestamp": datetime.utcnow().isoformat()}
        )
        db.add_item(log)
        return True
    return False

def logout_user():
    """Clear session state and log out user."""
    if st.session_state.user_id:
        # Log logout
        log = AuditLog(
            user_id=st.session_state.user_id,
            action="logout",
            details={"timestamp": datetime.utcnow().isoformat()}
        )
        db.add_item(log)
    
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.username = None
    st.experimental_rerun()

def login_page():
    """Render login page."""
    st.title("Welcome to CardSnap 📇")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        ### Login
        Please enter your credentials to continue.
        """)
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if login_user(username, password):
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
    
    with col2:
        st.markdown("""
        ### About CardSnap
        
        CardSnap is a modern business card management system that helps you:
        
        - 📸 Scan and digitize business cards
        - 🔍 Extract information using OCR
        - 📱 Generate and scan QR codes
        - 🏢 Manage company information
        - 📊 Export data in multiple formats
        
        Get started by logging in with your credentials.
        """)

def main_navigation():
    """Render main navigation sidebar."""
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    
    # Role-specific navigation
    if st.session_state.user_role == "Admin":
        page = st.sidebar.radio(
            "Navigation",
            ["Home", "Card Management", "Company Management", "User Management", "Export", "Audit Logs"]
        )
    elif st.session_state.user_role == "Sales":
        page = st.sidebar.radio(
            "Navigation",
            ["Home", "Card Management", "Company View", "Export"]
        )
    else:  # User role
        page = st.sidebar.radio(
            "Navigation",
            ["Home", "Card Management", "Company View", "Export"]
        )
    
    if st.sidebar.button("Logout"):
        logout_user()
    
    return page

def render_dashboard():
    """Render the dashboard page."""
    st.title("Dashboard")
    
    # Get statistics
    with db.get_session() as session:
        # Card statistics
        if st.session_state.user_role == "Admin":
            total_cards = session.query(BusinessCard).count()
            total_companies = session.query(Company).count()
            total_users = session.query(User).count()
        else:
            total_cards = session.query(BusinessCard).filter(
                BusinessCard.created_by_id == st.session_state.user_id
            ).count()
            total_companies = session.query(Company).filter(
                Company.created_by_id == st.session_state.user_id
            ).count()
            total_users = 1
        
        # Recent activity
        recent_cards = session.query(BusinessCard).order_by(
            BusinessCard.created_at.desc()
        ).limit(5).all()
    
    # Display statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Cards", total_cards)
    with col2:
        st.metric("Total Companies", total_companies)
    if st.session_state.user_role == "Admin":
        with col3:
            st.metric("Total Users", total_users)
    
    # Display recent activity
    st.subheader("Recent Activity")
    for card in recent_cards:
        with st.expander(f"{card.contact_name} - {card.created_at.strftime('%Y-%m-%d %H:%M:%S')}"):
            st.write(f"Position: {card.position}")
            st.write(f"Email: {card.email}")
            st.write(f"Phone: {card.phone}")
            if card.company_id:
                company = session.query(Company).get(card.company_id)
                if company:
                    st.write(f"Company: {company.name}")

def render_company_view():
    """Render the company view page for non-admin users."""
    st.title("Company Information")
    
    with db.get_session() as session:
        companies = session.query(Company).all()
        
        for company in companies:
            with st.expander(f"{company.name} - {company.industry or 'No Industry'}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("Basic Information:")
                    st.write(f"Email: {company.email}")
                    st.write(f"Primary Contact: {company.contact_primary}")
                    st.write(f"Website: {company.website}")
                    st.write(f"Industry: {company.industry}")
                    
                    st.write("\nAddress:")
                    address = f"{company.street_address}, {company.city}, {company.state} {company.postal_code}, {company.country}"
                    st.write(address.strip(", "))
                
                with col2:
                    if company.logo_path:
                        try:
                            logo = Image.open(company.logo_path)
                            st.image(logo, caption="Company Logo", use_column_width=True)
                        except Exception:
                            st.warning("Logo file not found")
                    
                    # Show QR code if available
                    if company.qr_code_data:
                        qr_image_bytes, _ = Scanner.generate_qr_code({
                            'name': company.name,
                            'email': company.email,
                            'phone': company.contact_primary,
                            'website': company.website,
                            'address': address.strip(", ")
                        })
                        st.image(qr_image_bytes, caption="Company QR Code", width=200)

def main():
    """Main application logic."""
    # Check if user is logged in
    if not st.session_state.user_id:
        login_page()
        return
    
    # Get current page from navigation
    current_page = main_navigation()
    
    # Render selected page
    if current_page == "Home":
        render_dashboard()
    
    elif current_page == "Card Management":
        render_card_management()
    
    elif current_page == "Company Management" and st.session_state.user_role == "Admin":
        render_company_management()
    
    elif current_page == "Company View":
        render_company_view()
    
    elif current_page == "User Management" and st.session_state.user_role == "Admin":
        render_user_management()
    
    elif current_page == "Export":
        render_export_management()
    
    elif current_page == "Audit Logs" and st.session_state.user_role == "Admin":
        st.title("Audit Logs")
        # Audit logs content will be implemented in Phase 3
        st.info("Audit logs will be implemented in the next phase.")

if __name__ == "__main__":
    main()
