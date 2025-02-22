import pandas as pd
import json
import vobject
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
from typing import List, Dict, Any
from database.models import BusinessCard, Company

class Exporter:
    @staticmethod
    def to_excel(data: List[Dict[str, Any]], filename: str) -> bytes:
        """Export data to Excel format."""
        try:
            df = pd.DataFrame(data)
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            return excel_buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Error exporting to Excel: {str(e)}")
    
    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> bytes:
        """Export data to CSV format."""
        try:
            df = pd.DataFrame(data)
            return df.to_csv(index=False).encode('utf-8')
            
        except Exception as e:
            raise Exception(f"Error exporting to CSV: {str(e)}")
    
    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> bytes:
        """Export data to JSON format."""
        try:
            return json.dumps(data, indent=2).encode('utf-8')
            
        except Exception as e:
            raise Exception(f"Error exporting to JSON: {str(e)}")
    
    @staticmethod
    def to_pdf(data: List[Dict[str, Any]], title: str = "Business Cards") -> bytes:
        """Export data to PDF format."""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            elements.append(Paragraph(title, styles['Title']))
            
            # Convert data to table format
            if data:
                headers = list(data[0].keys())
                table_data = [headers]
                for item in data:
                    table_data.append([str(item.get(h, '')) for h in headers])
                
                # Create table
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)
            
            # Build PDF
            doc.build(elements)
            return buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Error exporting to PDF: {str(e)}")
    
    @staticmethod
    def to_vcard(card: BusinessCard, company: Company = None) -> bytes:
        """Export business card to vCard format."""
        try:
            # Create vCard
            vcard = vobject.vCard()
            
            # Add name
            vcard.add('fn').value = card.contact_name
            
            # Add organization
            if company:
                vcard.add('org').value = [company.name]
            
            # Add title
            if card.position:
                vcard.add('title').value = card.position
            
            # Add email
            if card.email:
                vcard.add('email').value = card.email
            
            # Add phone
            if card.phone:
                tel = vcard.add('tel')
                tel.value = card.phone
                tel.type_param = 'WORK'
            
            # Add company details if available
            if company:
                # Add address
                if any([company.street_address, company.city, company.state, company.postal_code, company.country]):
                    adr = vcard.add('adr')
                    adr.value = vobject.vcard.Address(
                        street=company.street_address or '',
                        city=company.city or '',
                        region=company.state or '',
                        code=company.postal_code or '',
                        country=company.country or ''
                    )
                    adr.type_param = 'WORK'
                
                # Add website
                if company.website:
                    vcard.add('url').value = company.website
            
            return vcard.serialize().encode('utf-8')
            
        except Exception as e:
            raise Exception(f"Error exporting to vCard: {str(e)}")
    
    @staticmethod
    def business_card_to_dict(card: BusinessCard, company: Company = None) -> Dict[str, Any]:
        """Convert business card to dictionary format for export."""
        data = {
            'Contact Name': card.contact_name,
            'Position': card.position,
            'Email': card.email,
            'Phone': card.phone,
            'Event': card.event_name,
            'Created At': card.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if company:
            data.update({
                'Company': company.name,
                'Company Email': company.email,
                'Company Phone': company.contact_primary,
                'Website': company.website,
                'Address': f"{company.street_address}, {company.city}, {company.state} {company.postal_code}, {company.country}".strip(", "),
                'Industry': company.industry
            })
        
        return data 