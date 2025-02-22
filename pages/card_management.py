import streamlit as st
from database.db import db
from database.models import BusinessCard, Company
from utils.scanner import Scanner
from utils.auth import login_required, role_required
from datetime import datetime
import io
from PIL import Image

@login_required
def render_card_management():
    """Render the card management page."""
    st.title("Card Management")
    
    # Create tabs for different functions
    tab1, tab2, tab3 = st.tabs(["Scan Card", "View Cards", "Search"])
    
    with tab1:
        render_scan_tab()
    
    with tab2:
        render_view_tab()
    
    with tab3:
        render_search_tab()

def render_scan_tab():
    """Render the card scanning tab."""
    st.header("Scan Business Card")
    
    # File upload
    uploaded_file = st.file_uploader("Upload business card image", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        # Display uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Business Card", use_column_width=True)
        
        # Process button
        if st.button("Process Card"):
            with st.spinner("Processing..."):
                try:
                    # Get image bytes
                    image_bytes = uploaded_file.getvalue()
                    
                    # Save image
                    image_path = Scanner.save_image(image_bytes)
                    
                    # Extract text and parse information
                    raw_text, parsed_info = Scanner.extract_text_from_image(image_bytes)
                    
                    # Try to scan QR code
                    qr_data = Scanner.scan_qr_code(image_bytes)
                    
                    # Show results
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Extracted Information")
                        st.write("Name:", parsed_info.get('name'))
                        st.write("Position:", parsed_info.get('position'))
                        st.write("Email:", parsed_info.get('email'))
                        st.write("Phone:", parsed_info.get('phone'))
                        st.write("Company:", parsed_info.get('company'))
                        st.write("Website:", parsed_info.get('website'))
                        
                        # Allow editing
                        st.subheader("Edit Information")
                        edited_info = {
                            'name': st.text_input("Name", value=parsed_info.get('name', '')),
                            'position': st.text_input("Position", value=parsed_info.get('position', '')),
                            'email': st.text_input("Email", value=parsed_info.get('email', '')),
                            'phone': st.text_input("Phone", value=parsed_info.get('phone', '')),
                            'company': st.text_input("Company", value=parsed_info.get('company', '')),
                            'website': st.text_input("Website", value=parsed_info.get('website', ''))
                        }
                    
                    with col2:
                        st.subheader("Raw Text")
                        st.text_area("Extracted Text", value=raw_text, height=200)
                        
                        if qr_data:
                            st.subheader("QR Code Data")
                            st.text_area("Decoded QR Code", value=qr_data, height=100)
                    
                    # Save button
                    if st.button("Save Card"):
                        # Check if company exists
                        company = None
                        with db.get_session() as session:
                            if edited_info['company']:
                                company = session.query(Company).filter(
                                    Company.name == edited_info['company']
                                ).first()
                                
                                # Create new company if it doesn't exist
                                if not company and st.session_state.user_role == "Admin":
                                    company = Company(
                                        name=edited_info['company'],
                                        email=edited_info['email'],
                                        website=edited_info['website'],
                                        contact_primary=edited_info['phone'],
                                        created_by_id=st.session_state.user_id
                                    )
                                    session.add(company)
                                    session.flush()
                            
                            # Create business card
                            card = BusinessCard(
                                contact_name=edited_info['name'],
                                position=edited_info['position'],
                                email=edited_info['email'],
                                phone=edited_info['phone'],
                                company_id=company.id if company else None,
                                detected_text=raw_text,
                                qr_code_data=qr_data,
                                image_path=image_path,
                                created_by_id=st.session_state.user_id
                            )
                            session.add(card)
                            session.commit()
                            
                            st.success("Business card saved successfully!")
                            
                            # Generate QR code for the card
                            qr_image_bytes, vcard_data = Scanner.generate_qr_code(edited_info)
                            st.download_button(
                                label="Download Contact QR Code",
                                data=qr_image_bytes,
                                file_name=f"contact_qr_{edited_info['name'].lower().replace(' ', '_')}.png",
                                mime="image/png"
                            )
                    
                except Exception as e:
                    st.error(f"Error processing card: {str(e)}")

def render_view_tab():
    """Render the card viewing tab."""
    st.header("View Business Cards")
    
    # Get all cards
    with db.get_session() as session:
        if st.session_state.user_role == "Admin":
            cards = session.query(BusinessCard).all()
        else:
            cards = session.query(BusinessCard).filter(
                BusinessCard.created_by_id == st.session_state.user_id
            ).all()
    
    # Display cards
    for card in cards:
        with st.expander(f"{card.contact_name} - {card.position or 'No Position'}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("Contact Information:")
                st.write(f"Name: {card.contact_name}")
                st.write(f"Position: {card.position}")
                st.write(f"Email: {card.email}")
                st.write(f"Phone: {card.phone}")
                
                if card.company_id:
                    company = session.query(Company).get(card.company_id)
                    if company:
                        st.write("\nCompany Information:")
                        st.write(f"Company: {company.name}")
                        st.write(f"Website: {company.website}")
            
            with col2:
                if card.image_path:
                    try:
                        image = Image.open(card.image_path)
                        st.image(image, caption="Business Card Image", use_column_width=True)
                    except Exception:
                        st.warning("Image file not found")
            
            # Admin controls
            if st.session_state.user_role == "Admin":
                if st.button("Delete Card", key=f"delete_{card.id}"):
                    session.delete(card)
                    session.commit()
                    st.success("Card deleted successfully!")
                    st.experimental_rerun()

def render_search_tab():
    """Render the card search tab."""
    st.header("Search Business Cards")
    
    # Search inputs
    search_query = st.text_input("Search by name, company, or content")
    
    if search_query:
        with db.get_session() as session:
            # Build search query
            search_term = f"%{search_query}%"
            if st.session_state.user_role == "Admin":
                cards = session.query(BusinessCard).filter(
                    (BusinessCard.contact_name.like(search_term)) |
                    (BusinessCard.detected_text.like(search_term)) |
                    (BusinessCard.email.like(search_term)) |
                    (BusinessCard.phone.like(search_term))
                ).all()
            else:
                cards = session.query(BusinessCard).filter(
                    BusinessCard.created_by_id == st.session_state.user_id,
                    (BusinessCard.contact_name.like(search_term)) |
                    (BusinessCard.detected_text.like(search_term)) |
                    (BusinessCard.email.like(search_term)) |
                    (BusinessCard.phone.like(search_term))
                ).all()
            
            if cards:
                st.write(f"Found {len(cards)} results:")
                for card in cards:
                    with st.expander(f"{card.contact_name} - {card.position or 'No Position'}"):
                        st.write(f"Email: {card.email}")
                        st.write(f"Phone: {card.phone}")
                        st.write(f"Created: {card.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        if card.company_id:
                            company = session.query(Company).get(card.company_id)
                            if company:
                                st.write(f"Company: {company.name}")
            else:
                st.info("No results found") 