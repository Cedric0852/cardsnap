import streamlit as st
from database.db import db
from database.models import BusinessCard, Company, ExportLog, User
from utils.export import Exporter
from utils.auth import login_required
from datetime import datetime, date
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
    st.header("Export Data")
    
    # Add data type selection
    data_type = st.radio(
        "Select Data Type to Export",
        ["Business Cards", "Companies"],
        horizontal=True
    )
    
    # Get data for filtering
    with db.get_session() as session:
        # Get companies for filter
        companies = session.query(Company).all()
        company_names = ["All"] + [company.name for company in companies]
        
        if data_type == "Business Cards":
            # Get date range from business cards
            first_card = session.query(BusinessCard).order_by(BusinessCard.created_at.asc()).first()
            last_card = session.query(BusinessCard).order_by(BusinessCard.created_at.desc()).first()
            min_date = first_card.created_at.date() if first_card else date(2000, 1, 1)
            max_date = last_card.created_at.date() if last_card else datetime.now().date()
        else:
            # Get date range from companies
            first_company = session.query(Company).order_by(Company.created_at.asc()).first()
            last_company = session.query(Company).order_by(Company.created_at.desc()).first()
            min_date = first_company.created_at.date() if first_company else date(2000, 1, 1)
            max_date = last_company.created_at.date() if last_company else datetime.now().date()
    
    # Filters
    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if data_type == "Business Cards":
            selected_company = st.selectbox("Company", company_names)
    
    with col2:
        start_date = st.date_input("Start Date", min_date)
    
    with col3:
        end_date = st.date_input("End Date", max_date)
    
    # Export format selection
    export_format = st.selectbox(
        "Export Format",
        ["Excel", "CSV", "PDF", "JSON"] + (["vCard"] if data_type == "Business Cards" else [])
    )
    
    # Get filtered data
    with db.get_session() as session:
        if data_type == "Business Cards":
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
            
            items = query.all()
        else:
            query = session.query(Company)
            
            # Apply date filters
            query = query.filter(
                Company.created_at >= datetime.combine(start_date, datetime.min.time()),
                Company.created_at <= datetime.combine(end_date, datetime.max.time())
            )
            
            # Apply user role filter
            if st.session_state.user_role != "Admin":
                query = query.filter(Company.created_by_id == st.session_state.user_id)
            
            items = query.all()
    
    if not items:
        st.warning("No data found with the selected filters.")
        return
    
    # Export button
    if st.button("Export Data"):
        try:
            # Convert data to dictionary format
            export_data = []
            with db.get_session() as session:
                if data_type == "Business Cards":
                    for card in items:
                        company = session.query(Company).get(card.company_id) if card.company_id else None
                        card_dict = Exporter.business_card_to_dict(card, company)
                        export_data.append(card_dict)
                else:
                    for company in items:
                        company_dict = Exporter.company_to_dict(company)
                        export_data.append(company_dict)
            
                # Export based on selected format
                if export_format == "Excel":
                    output = Exporter.to_excel(export_data, f"{data_type.lower().replace(' ', '_')}.xlsx")
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    filename = f"{data_type.lower().replace(' ', '_')}.xlsx"
                elif export_format == "CSV":
                    output = Exporter.to_csv(export_data)
                    mime = "text/csv"
                    filename = f"{data_type.lower().replace(' ', '_')}.csv"
                elif export_format == "PDF":
                    if data_type == "Business Cards":
                        simplified_data = [{k: v for k, v in d.items() if k != 'Parsed Data'} for d in export_data]
                        output = Exporter.to_pdf(simplified_data, f"{data_type} Export")
                    else:
                        output = Exporter.to_pdf(export_data, f"{data_type} Export")
                    mime = "application/pdf"
                    filename = f"{data_type.lower().replace(' ', '_')}.pdf"
                elif export_format == "JSON":
                    output = Exporter.to_json(export_data)
                    mime = "application/json"
                    filename = f"{data_type.lower().replace(' ', '_')}.json"
                elif export_format == "vCard" and data_type == "Business Cards":
                    import zipfile
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for card in items:
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
                items_exported=len(items),
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
            
            st.success(f"Successfully exported {len(items)} records to {export_format}")
            
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

    # Add this temporarily for debugging
    with db.get_session() as session:
        card = session.query(BusinessCard).first()
        st.write("Debug - First card in database:", {
            'id': card.id,
            'contact_name': card.contact_name,
            'parsed_data': card.parsed_data,
            # Add other fields you want to check
        })

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
                    
                    # Get user info for admin view
                    if st.session_state.user_role == "Admin":
                        try:
                            user = session.query(User).get(export.user_id)
                            if user:
                                st.write(f"Exported by: {user.username}")
                            else:
                                st.write("Exported by: Unknown User")
                        except Exception:
                            st.write("Exported by: Unknown User")
        else:
            st.info("No export history found.") 