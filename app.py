from PIL import Image
import streamlit as st
import requests
import io
import base64
import re

API_KEY = st.secrets["key"]

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


# Set the app name and favicon
app_name = "Cardsnap"
favicon_emoji = "📇"
st.set_page_config(page_title=app_name, page_icon=favicon_emoji)
# Title
st.title("Business Card Digitizer")

# Instructions
st.write("Upload an image of a business card to detect text.")

# Capture or upload an image
uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])

# Display the uploaded image and trigger text detection
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption='Uploaded Business Card', use_column_width=True)

    image_bytes = uploaded_file.getvalue()

    if st.button("Detect Text"):
        result = detect_text(image_bytes)
        full_text = result['responses'][0]['fullTextAnnotation']['text']
        st.write("Detected Text:")
        st.markdown(f"```\n{full_text}\n```")
