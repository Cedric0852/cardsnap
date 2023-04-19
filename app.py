from PIL import Image
import streamlit as st
import requests
import io
import base64
import re
from sqlalchemy_utils import escape_like
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import or_
import streamlit_ace as st_ace
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

def detect_text(image):
    url = "https://vision.googleapis.com/v1/images:annotate?key=" + API_KEY
    headers = {'Content-Type': 'application/json'}
    image_content = base64.b64encode(image).decode('UTF-8')
    data = {
      "requests": [
        {
          "image": {
            "content": image_content
          },
          "features": [
            {
              "type": "DOCUMENT_TEXT_DETECTION"
            }
          ]
        }
      ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()
# Add a function to save detected text to the database
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


# Set the app name and favicon
app_name = "Cardsnap"
favicon_emoji = "📇"
st.set_page_config(page_title=app_name, page_icon=favicon_emoji)
# Add a navigation bar to switch between pages
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Card Snap History"])
#Home page
if page == "Home":
  # Title
  st.title("Business Card Digitizer ,  CARDSNAP")

  # Instructions
  st.write("Upload or take a picture  of a business card.")

  # Capture or upload an image
  uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])

  # Display the uploaded image and trigger text detection
  if uploaded_file:
      image = Image.open(uploaded_file)
      st.image(image, caption='Uploaded Business Card', use_column_width=True)

      image_bytes = uploaded_file.getvalue()
      event_name = st.text_input("Event Name (optional)")

      if st.button("Detect Text"):
        result = detect_text(image_bytes)
        full_text = result['responses'][0]['fullTextAnnotation']['text']
        st.write("Detected Text:")
        st.markdown(f"```\n{full_text}\n```")
        timestamp = datetime.utcnow()
        save_to_db(event_name, full_text, timestamp)
        st.success("Text saved successfully!")
elif page == "Card Snap History":
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
        if st.button(f"Delete Entry {i}"):
            delete_card_snap(card_snap.id)
            st.success(f"Deleted entry: {card_snap.event_name if card_snap.event_name else 'No Event Name'} - {card_snap.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            st.write("---")
        
    if st.button("Export to Excel"):
      card_snaps = get_card_snaps()
      df = card_snaps_to_dataframe(card_snaps)
      excel_file = to_excel(df)

      b64 = base64.b64encode(excel_file).decode()
      href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="card_snap_history.xlsx">Download Card Snap History as Excel</a>'
      st.markdown(href, unsafe_allow_html=True)
