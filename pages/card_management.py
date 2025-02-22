import streamlit as st
from database.db import db
from database.models import BusinessCard, Company, AuditLog
from utils.scanner import Scanner
from utils.auth import login_required, role_required
from datetime import datetime
import io
from PIL import Image
from sqlalchemy import or_
import pytesseract

# Configure pytesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

@login_required
def render_card_management():
    """Render the card management page."""
    st.title("Card Management")
    
    tab1, tab2 = st.tabs(["Add Card", "View Cards"])
    
    with tab1:
        st.header("Add New Business Card")
        
        # File upload
        uploaded_file = st.file_uploader("Upload Business Card Image", type=['png', 'jpg', 'jpeg'])
        
        # Initialize form fields
        company_name = None
        contact_name = None
        position = None
        email = None
        phone = None
        website = None
        event_name = None
        
        if uploaded_file is not None:
            # Display the uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption='Uploaded Business Card', use_container_width=True)
            
            # Process button
            if st.button("Process Card"):
                with st.spinner("Processing..."):
                    try:
                        # Get image bytes
                        img_byte_arr = uploaded_file.getvalue()
                        
                        # Extract text and parse information
                        raw_text, parsed_info = Scanner.extract_text_from_image(img_byte_arr)
                        
                        # Display results in columns
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Extracted Information")
                            company_name = st.text_input("Company Name (Optional)", value=parsed_info.get('company', ''))
                            contact_name = st.text_input("Contact Name (Optional)", value=parsed_info.get('name', ''))
                            position = st.text_input("Position", value=parsed_info.get('position', ''))
                            email = st.text_input("Email", value=parsed_info.get('email', ''))
                            phone = st.text_input("Phone", value=parsed_info.get('phone', ''))
                            website = st.text_input("Website", value=parsed_info.get('website', ''))
                            event_name = st.text_input("Event Name (Optional)")
                        
                        with col2:
                            st.subheader("Raw Text")
                            st.text_area("Detected Text", value=raw_text, height=300)
                            
                    except Exception as e:
                        st.error(f"Error processing card: {str(e)}")
        
        # Save button
        if st.button("Save Card"):
            try:
                with db.get_session() as session:
                    # Create or get company if company name is provided
                    company_id = None
                    if company_name:
                        company = session.query(Company).filter(Company.name == company_name).first()
                        if not company:
                            company = Company(
                                name=company_name,
                                website=website,
                                created_by_id=st.session_state.user_id
                            )
                            session.add(company)
                            session.flush()  # Get company ID
                        company_id = company.id
                    
                    # Create new business card
                    card = BusinessCard(
                        company_id=company_id,
                        contact_name=contact_name if contact_name else None,
                        position=position if position else None,
                        email=email if email else None,
                        phone=phone if phone else None,
                        website=website if website else None,
                        event_name=event_name if event_name else None,
                        created_by_id=st.session_state.user_id,
                        created_at=datetime.utcnow(),
                        detected_text=raw_text if 'raw_text' in locals() else None,
                        parsed_data=parsed_info if 'parsed_info' in locals() else None,
                        qr_code_data=None  # Will be set below if QR code is detected
                    )
                    
                    # Extract additional information from parsed_info if available
                    if 'parsed_info' in locals():
                        card.mobile = parsed_info.get('mobile')
                        card.fax = parsed_info.get('fax')
                        card.street_address = parsed_info.get('address')
                        card.city = parsed_info.get('city')
                        card.state = parsed_info.get('state')
                        card.postal_code = parsed_info.get('postal_code')
                        card.country = parsed_info.get('country')
                        card.department = parsed_info.get('department')
                        card.social_linkedin = parsed_info.get('linkedin')
                        card.social_twitter = parsed_info.get('twitter')
                        card.social_facebook = parsed_info.get('facebook')
                        card.notes = parsed_info.get('notes')

                    if uploaded_file:
                        # Save image
                        img_byte_arr = uploaded_file.getvalue()
                        
                        # Try to detect QR code
                        try:
                            qr_data = Scanner.scan_qr_code(img_byte_arr)
                            if qr_data:
                                card.qr_code_data = qr_data
                        except Exception as e:
                            st.warning(f"Could not scan QR code: {str(e)}")
                        
                        # Save image file
                        image_path = Scanner.save_image(img_byte_arr)
                        card.image_path = image_path
                    
                    session.add(card)
                    
                    # Create audit log
                    log = AuditLog(
                        user_id=st.session_state.user_id,
                        action="create_card",
                        details={
                            "company": company_name if company_name else "Unknown",
                            "contact": contact_name if contact_name else "Unknown",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    session.add(log)
                    session.commit()
                    
                st.success("Business card saved successfully!")
                st.rerun()  # Refresh the page to show updated data
                
            except Exception as e:
                st.error(f"Error saving business card: {str(e)}")
    
    with tab2:
        st.header("View Business Cards")
        
        # Search filters
        search_col1, search_col2 = st.columns(2)
        with search_col1:
            search_query = st.text_input("Search by company or contact name")
        with search_col2:
            with db.get_session() as session:
                companies = session.query(Company).all()
                company_filter = st.selectbox(
                    "Filter by Company",
                    ["All Companies"] + [company.name for company in companies]
                )
        
        # Get cards with filters
        with db.get_session() as session:
            # Use joinedload to eagerly load the company relationship
            from sqlalchemy.orm import joinedload
            query = session.query(BusinessCard).options(joinedload(BusinessCard.company))
            
            if company_filter != "All Companies":
                query = query.join(Company).filter(Company.name == company_filter)
            
            if search_query:
                query = query.outerjoin(Company).filter(
                    or_(
                        Company.name.ilike(f"%{search_query}%"),
                        BusinessCard.contact_name.ilike(f"%{search_query}%")
                    )
                )
            
            # Execute query and get all results within the session
            cards = query.order_by(BusinessCard.created_at.desc()).all()
            
            # Display cards
            for card in cards:
                company_name = card.company.name if card.company else "Unknown Company"
                contact_name = card.contact_name if card.contact_name else "Unknown Contact"
                
                st.markdown("---")  # Add a separator between cards
                st.subheader(f"{company_name} - {contact_name}")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if card.image_path:
                        try:
                            image = Image.open(card.image_path)
                            st.image(image, caption="Business Card Image", use_container_width=True)
                        except Exception:
                            st.warning("Image file not found")
                
                with col2:
                    st.subheader("Contact Information")
                    if card.contact_name:
                        st.write(f"**Contact:** {card.contact_name}")
                    if card.position:
                        st.write(f"**Position:** {card.position}")
                    if card.email:
                        st.write(f"**Email:** {card.email}")
                    if card.phone:
                        st.write(f"**Phone:** {card.phone}")
                    if card.company:
                        st.write(f"**Company:** {company_name}")
                        if card.company.website:
                            st.write(f"**Website:** {card.company.website}")
                    
                    # Add View More Info button
                    if st.button("View More Info", key=f"more_info_{card.id}"):
                        st.markdown("##### Additional Contact Details")
                        if card.mobile:
                            st.write(f"**Mobile:** {card.mobile}")
                        if card.fax:
                            st.write(f"**Fax:** {card.fax}")
                        if card.department:
                            st.write(f"**Department:** {card.department}")
                        
                        st.markdown("##### Address Information")
                        if any([card.street_address, card.city, card.state, card.postal_code, card.country]):
                            if card.street_address:
                                st.write(f"**Street:** {card.street_address}")
                            if card.city:
                                st.write(f"**City:** {card.city}")
                            if card.state:
                                st.write(f"**State:** {card.state}")
                            if card.postal_code:
                                st.write(f"**Postal Code:** {card.postal_code}")
                            if card.country:
                                st.write(f"**Country:** {card.country}")
                        
                        st.markdown("##### Social Media")
                        if card.social_linkedin:
                            st.write(f"**LinkedIn:** {card.social_linkedin}")
                        if card.social_twitter:
                            st.write(f"**Twitter:** {card.social_twitter}")
                        if card.social_facebook:
                            st.write(f"**Facebook:** {card.social_facebook}")
                        
                        if card.notes:
                            st.markdown("##### Notes")
                            st.write(card.notes)
                        
                        if card.parsed_data:
                            st.markdown("##### All Parsed Data")
                            st.json(card.parsed_data)
                    
                    if card.event_name:
                        st.write(f"**Event:** {card.event_name}")
                    st.write(f"**Created:** {card.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if st.session_state.user_role == "Admin":
                        if st.button("Delete", key=f"delete_{card.id}"):
                            try:
                                with db.get_session() as session:
                                    card_to_delete = session.query(BusinessCard).get(card.id)
                                    session.delete(card_to_delete)
                                    
                                    # Create audit log
                                    log = AuditLog(
                                        user_id=st.session_state.user_id,
                                        action="delete_card",
                                        details={
                                            "company": company_name,
                                            "contact": contact_name,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    )
                                    session.add(log)
                                    session.commit()
                                
                                st.success("Card deleted successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting card: {str(e)}")
                
                with col3:
                    st.subheader("OCR Results")
                    if card.detected_text:
                        st.markdown("##### Raw Detected Text")
                        st.code(card.detected_text)
                    
                    if card.qr_code_data:
                        st.markdown("##### QR Code Data")
                        st.code(card.qr_code_data) 