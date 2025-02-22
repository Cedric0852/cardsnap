import streamlit as st
from database.db import db
from database.models import Company, BusinessCard
from utils.scanner import Scanner
from utils.auth import login_required, role_required
from datetime import datetime
import io
from PIL import Image

@login_required
@role_required(["Admin"])
def render_company_management():
    """Render the company management page."""
    st.title("Company Management")
    
    # Create tabs for different functions
    tab1, tab2, tab3 = st.tabs(["Add Company", "View Companies", "Search"])
    
    with tab1:
        render_add_company_tab()
    
    with tab2:
        render_view_companies_tab()
    
    with tab3:
        render_search_companies_tab()

def render_add_company_tab():
    """Render the add company tab."""
    st.header("Add New Company")
    
    # Company form
    with st.form("add_company_form"):
        name = st.text_input("Company Name*")
        col1, col2 = st.columns(2)
        
        with col1:
            email = st.text_input("Email*")
            contact_primary = st.text_input("Primary Contact")
            contact_secondary = st.text_input("Secondary Contact")
            website = st.text_input("Website")
            industry = st.text_input("Industry")
        
        with col2:
            street_address = st.text_input("Street Address")
            city = st.text_input("City")
            state = st.text_input("State/Province")
            postal_code = st.text_input("Postal Code")
            country = st.text_input("Country")
        
        col3, col4 = st.columns(2)
        with col3:
            social_linkedin = st.text_input("LinkedIn URL")
            registration_number = st.text_input("Registration Number")
        
        with col4:
            social_twitter = st.text_input("Twitter URL")
            social_facebook = st.text_input("Facebook URL")
        
        logo = st.file_uploader("Company Logo", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("Add Company")
        
        if submitted:
            if not name or not email:
                st.error("Company name and email are required.")
                return
            
            try:
                # Save logo if uploaded
                logo_path = None
                if logo:
                    logo_bytes = logo.getvalue()
                    logo_path = Scanner.save_image(logo_bytes, directory="company_logos")
                
                # Create company
                company = Company(
                    name=name,
                    email=email,
                    contact_primary=contact_primary,
                    contact_secondary=contact_secondary,
                    website=website,
                    street_address=street_address,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    country=country,
                    social_linkedin=social_linkedin,
                    social_twitter=social_twitter,
                    social_facebook=social_facebook,
                    logo_path=logo_path,
                    industry=industry,
                    registration_number=registration_number,
                    created_by_id=st.session_state.user_id
                )
                
                # Generate QR code with company info
                company_info = {
                    'name': name,
                    'email': email,
                    'phone': contact_primary,
                    'website': website,
                    'address': f"{street_address}, {city}, {state} {postal_code}, {country}".strip(", ")
                }
                qr_image_bytes, qr_data = Scanner.generate_qr_code(company_info)
                company.qr_code_data = qr_data
                
                # Save to database
                db.add_item(company)
                
                st.success("Company added successfully!")
                
                # Display QR code
                st.image(qr_image_bytes, caption="Company QR Code", use_container_width=True)
                
            except Exception as e:
                st.error(f"Error adding company: {str(e)}")

def render_view_companies_tab():
    """Render the view companies tab."""
    st.header("View Companies")
    
    # Get all companies
    with db.get_session() as session:
        companies = session.query(Company).all()
        
        for company in companies:
            with st.expander(f"{company.name} - {company.industry or 'No Industry'}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("Basic Information:")
                    st.write(f"Email: {company.email}")
                    st.write(f"Primary Contact: {company.contact_primary}")
                    st.write(f"Secondary Contact: {company.contact_secondary}")
                    st.write(f"Website: {company.website}")
                    st.write(f"Industry: {company.industry}")
                    
                    st.write("\nAddress:")
                    address = f"{company.street_address}, {company.city}, {company.state} {company.postal_code}, {company.country}"
                    st.write(address.strip(", "))
                    
                    st.write("\nSocial Media:")
                    if company.social_linkedin:
                        st.write(f"LinkedIn: {company.social_linkedin}")
                    if company.social_twitter:
                        st.write(f"Twitter: {company.social_twitter}")
                    if company.social_facebook:
                        st.write(f"Facebook: {company.social_facebook}")
                
                with col2:
                    if company.logo_path:
                        try:
                            logo = Image.open(company.logo_path)
                            st.image(logo, caption="Company Logo", use_container_width=True)
                        except Exception:
                            st.warning("Logo file not found")
                    
                    # Show associated business cards
                    cards = session.query(BusinessCard).filter(
                        BusinessCard.company_id == company.id
                    ).all()
                    if cards:
                        st.write(f"\nAssociated Business Cards ({len(cards)}):")
                        for card in cards:
                            st.write(f"- {card.contact_name} ({card.position})")
                
                # Edit and Delete buttons
                col3, col4 = st.columns(2)
                with col3:
                    if st.button("Edit Company", key=f"edit_{company.id}"):
                        st.session_state.editing_company = company
                        st.experimental_rerun()
                
                with col4:
                    if st.button("Delete Company", key=f"delete_{company.id}"):
                        # Check for associated cards
                        if cards:
                            st.error("Cannot delete company with associated business cards.")
                        else:
                            session.delete(company)
                            session.commit()
                            st.success("Company deleted successfully!")
                            st.experimental_rerun()

                st.markdown("##### Company QR Code")
                # Prepare a company data dictionary for QR code generation
                address = f"{company.street_address}, {company.city}, {company.state} {company.postal_code}, {company.country}"
                company_data = {
                    'name': company.name,
                    'email': company.email,
                    'phone': company.contact_primary,
                    'website': company.website,
                    'address': address.strip(", ")
                }
                try:
                    qr_image_bytes, _ = Scanner.generate_qr_code(company_data)
                    st.image(qr_image_bytes, caption="Company QR Code", use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not generate company QR code: {str(e)}")

def render_search_companies_tab():
    """Render the company search tab."""
    st.header("Search Companies")
    
    # Search inputs
    search_query = st.text_input("Search by name, industry, or location")
    
    if search_query:
        with db.get_session() as session:
            # Build search query
            search_term = f"%{search_query}%"
            companies = session.query(Company).filter(
                (Company.name.like(search_term)) |
                (Company.industry.like(search_term)) |
                (Company.city.like(search_term)) |
                (Company.state.like(search_term)) |
                (Company.country.like(search_term))
            ).all()
            
            if companies:
                st.write(f"Found {len(companies)} results:")
                for company in companies:
                    with st.expander(f"{company.name} - {company.industry or 'No Industry'}"):
                        st.write(f"Email: {company.email}")
                        st.write(f"Contact: {company.contact_primary}")
                        st.write(f"Website: {company.website}")
                        st.write(f"Location: {company.city}, {company.state}, {company.country}")
                        
                        # Count associated cards
                        card_count = session.query(BusinessCard).filter(
                            BusinessCard.company_id == company.id
                        ).count()
                        st.write(f"Associated Business Cards: {card_count}")
            else:
                st.info("No results found") 