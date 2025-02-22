import pytesseract
from PIL import Image
import qrcode
from pyzbar.pyzbar import decode
import io
import os
import uuid
from datetime import datetime
import re

# Configure pytesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

class Scanner:
    @staticmethod
    def detect_text(image_bytes: bytes) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang='eng')
            return text
        except Exception as e:
            raise Exception(f"Error detecting text: {str(e)}")

    @staticmethod
    def extract_text_from_image(image_bytes: bytes) -> tuple[str, dict]:
        """
        Extract text from image using OCR and parse business card information.
        Returns (raw_text, parsed_info)
        """
        try:
            raw_text = Scanner.detect_text(image_bytes)
            
            # Parse the extracted text
            parsed_info = Scanner._parse_business_card_text(raw_text)
            
            return raw_text, parsed_info
            
        except Exception as e:
            raise Exception(f"Error processing image: {str(e)}")
    
    @staticmethod
    def _parse_business_card_text(text: str) -> dict:
        """Parse business card text to extract structured information."""
        info = {
            'name': None,
            'position': None,
            'email': None,
            'phone': None,
            'mobile': None,
            'fax': None,
            'company': None,
            'website': None,
            'address': None,
            'city': None,
            'state': None,
            'postal_code': None,
            'country': None,
            'department': None,
            'linkedin': None,
            'twitter': None,
            'facebook': None,
            'notes': None
        }
        
        # Split text into lines and remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            info['email'] = emails[0]
        
        # Extract phone numbers
        phone_pattern = r'(?:\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            # Assume first number is primary phone
            info['phone'] = phones[0]
            # If there are multiple numbers, assume second is mobile
            if len(phones) > 1:
                info['mobile'] = phones[1]
            # If there are three numbers, assume third is fax
            if len(phones) > 2:
                info['fax'] = phones[2]
        
        # Extract website
        website_pattern = r'(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})+)'
        websites = re.findall(website_pattern, text)
        if websites:
            info['website'] = websites[0]
        
        # Extract social media handles
        social_patterns = {
            'linkedin': r'(?:linkedin\.com/in/|linkedin:?)([a-zA-Z0-9_-]+)',
            'twitter': r'(?:twitter\.com/|twitter:?)([a-zA-Z0-9_]+)',
            'facebook': r'(?:facebook\.com/|facebook:?)([a-zA-Z0-9_.]+)'
        }
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, text.lower())
            if matches:
                info[platform] = matches[0]
        
        # Extract address components
        address_pattern = r'\b\d+\s+[A-Za-z0-9\s,.-]+\b'
        addresses = re.findall(address_pattern, text)
        if addresses:
            info['address'] = addresses[0]
        
        # Try to identify postal code
        postal_pattern = r'\b\d{5}(?:-\d{4})?\b'
        postal_codes = re.findall(postal_pattern, text)
        if postal_codes:
            info['postal_code'] = postal_codes[0]
        
        # Try to identify name and position
        # Usually, name is in larger font and appears first
        if lines:
            info['name'] = lines[0]
            if len(lines) > 1:
                info['position'] = lines[1]
        
        # Try to identify company name
        # Often appears after position or in larger font
        company_indicators = ['inc', 'corp', 'ltd', 'llc', 'company', 'co.']
        for line in lines:
            lower_line = line.lower()
            if any(indicator in lower_line for indicator in company_indicators):
                info['company'] = line
                break
        
        # Try to identify department
        department_indicators = ['department', 'dept', 'division', 'team']
        for line in lines:
            lower_line = line.lower()
            if any(indicator in lower_line for indicator in department_indicators):
                info['department'] = line
                break
        
        return info
    
    @staticmethod
    def scan_qr_code(image_bytes: bytes) -> str:
        """Scan QR code from image and return decoded data."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            decoded_objects = decode(image)
            
            if decoded_objects:
                return decoded_objects[0].data.decode('utf-8')
            return None
            
        except Exception as e:
            raise Exception(f"Error scanning QR code: {str(e)}")
    
    @staticmethod
    def generate_qr_code(data: dict) -> tuple[bytes, str]:
        """
        Generate QR code from business card or company data.
        Returns (qr_code_image_bytes, qr_code_data)
        """
        try:
            if data.get('type') == 'business_card' and 'raw_text' in data:
                # For business cards with raw text, use the raw text directly
                qr_data = data['raw_text']
            elif data.get('type') == 'company':
                # For company data, create a formatted string
                company_info = []
                for key, value in data.items():
                    if key != 'type' and value:  # Skip 'type' field and None values
                        # Convert key from snake_case to Title Case
                        formatted_key = ' '.join(word.capitalize() for word in key.split('_'))
                        company_info.append(f"{formatted_key}: {value}")
                qr_data = '\n'.join(company_info)
            else:
                # For other cases, create vCard format
                vcard_data = f"""BEGIN:VCARD
VERSION:3.0
FN:{data.get('name', '')}
ORG:{data.get('company', '')}
TITLE:{data.get('position', '')}
TEL:{data.get('phone', '')}
EMAIL:{data.get('email', '')}
URL:{data.get('website', '')}
END:VCARD"""
                qr_data = vcard_data
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            qr_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            return img_byte_arr, qr_data
            
        except Exception as e:
            raise Exception(f"Error generating QR code: {str(e)}")
    
    @staticmethod
    def save_image(image_bytes: bytes, directory: str = "uploads") -> str:
        """Save image to disk and return the file path."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Generate unique filename
            filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(directory, filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            return filepath
            
        except Exception as e:
            raise Exception(f"Error saving image: {str(e)}") 