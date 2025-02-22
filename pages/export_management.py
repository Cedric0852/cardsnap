import streamlit as st
from database.db import db
from database.models import BusinessCard, Company, ExportLog
from utils.export import Exporter
from utils.auth import login_required
from datetime import datetime
import io

@login_required
def render_export_management():
    """Render the export management page."""
    st.title("Export Data")
    
    # Create tabs for different export functions
    tab1, tab2 = st.tabs(["Export Business Cards", "Export History"])
    
    with tab1:
        render_export_tab()
    
    with tab2:
        render_history_tab()

def render_export_tab():
    """Render the main export tab."""
    st.header("Export Business Cards")
    
    # Get data for filtering
    with db.get_session() as session:
        # Get companies for filter
        companies = session.query(Company).all()
        company_names = ["All"] + [company.name for company in companies]
        
        # Get date range from data
        first_card = session.query(BusinessCard).order_by(BusinessCard.created_at.asc()).first()
        last_card = session.query(BusinessCard).order_by(BusinessCard.created_at.desc()).first()
        
        min_date = first_card.created_at if first_card else datetime.now()
        max_date = last_card.created_at if last_card else datetime.now()
    
    # Filters
    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_company = st.selectbox("Company", company_names)
    
    with col2:
        start_date = st.date_input("Start Date", min_date)
    
    with col3:
        end_date = st.date_input("End Date", max_date)
    
    # Export format selection
    export_format = st.selectbox(
        "Export Format",
        ["Excel", "CSV", "PDF", "vCard", "JSON"]
    )
    
    # Get filtered data
    with db.get_session() as session:
        query = session.query(BusinessCard)
        
        # Apply company filter
        if selected_company != "All":
            company = session.query(Company).filter(Company.name == selected_company).first()
            if company:
                query = query.filter(BusinessCard.company_id == company.id)
        
        # Apply date filters
        query = query.filter(
            BusinessCard.created_at >= datetime.combine(start_date, datetime.min.time()),
            BusinessCard.created_at <= datetime.combine(end_date, datetime.max.time())
        )
        
        # Apply user role filter
        if st.session_state.user_role != "Admin":
            query = query.filter(BusinessCard.created_by_id == st.session_state.user_id)
        
        cards = query.all()
    
    if not cards:
        st.warning("No data found with the selected filters.")
        return
    
    # Export button
    if st.button("Export Data"):
        try:
            # Convert cards to dictionary format
            card_data = []
            for card in cards:
                company = session.query(Company).get(card.company_id) if card.company_id else None
                card_dict = Exporter.business_card_to_dict(card, company)
                card_data.append(card_dict)
            
            # Export based on selected format
            if export_format == "Excel":
                output = Exporter.to_excel(card_data, "business_cards.xlsx")
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                filename = "business_cards.xlsx"
            elif export_format == "CSV":
                output = Exporter.to_csv(card_data)
                mime = "text/csv"
                filename = "business_cards.csv"
            elif export_format == "PDF":
                output = Exporter.to_pdf(card_data, "Business Cards Export")
                mime = "application/pdf"
                filename = "business_cards.pdf"
            elif export_format == "JSON":
                output = Exporter.to_json(card_data)
                mime = "application/json"
                filename = "business_cards.json"
            elif export_format == "vCard":
                # For vCard, we'll create a zip of individual vCards
                import zipfile
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for card in cards:
                        company = session.query(Company).get(card.company_id) if card.company_id else None
                        vcard_data = Exporter.to_vcard(card, company)
                        filename = f"{card.contact_name.lower().replace(' ', '_')}.vcf"
                        zf.writestr(filename, vcard_data)
                output = zip_buffer.getvalue()
                mime = "application/zip"
                filename = "business_cards.zip"
            
            # Log export
            export_log = ExportLog(
                user_id=st.session_state.user_id,
                export_type=export_format,
                items_exported=len(cards),
                status="Success"
            )
            session.add(export_log)
            session.commit()
            
            # Offer download
            st.download_button(
                label=f"Download {export_format}",
                data=output,
                file_name=filename,
                mime=mime
            )
            
            st.success(f"Successfully exported {len(cards)} records to {export_format}")
            
        except Exception as e:
            st.error(f"Error during export: {str(e)}")
            # Log failed export
            export_log = ExportLog(
                user_id=st.session_state.user_id,
                export_type=export_format,
                items_exported=0,
                status="Failed"
            )
            session.add(export_log)
            session.commit()

def render_history_tab():
    """Render the export history tab."""
    st.header("Export History")
    
    with db.get_session() as session:
        # Get export history
        if st.session_state.user_role == "Admin":
            exports = session.query(ExportLog).order_by(ExportLog.export_date.desc()).all()
        else:
            exports = session.query(ExportLog).filter(
                ExportLog.user_id == st.session_state.user_id
            ).order_by(ExportLog.export_date.desc()).all()
        
        if exports:
            for export in exports:
                with st.expander(f"Export on {export.export_date.strftime('%Y-%m-%d %H:%M:%S')}"):
                    st.write(f"Format: {export.export_type}")
                    st.write(f"Records: {export.items_exported}")
                    st.write(f"Status: {export.status}")
                    
                    # Get user info
                    if st.session_state.user_role == "Admin":
                        user = session.query(User).get(export.user_id)
                        if user:
                            st.write(f"Exported by: {user.username}")
        else:
            st.info("No export history found.") 