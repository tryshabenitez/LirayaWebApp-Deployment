import random
import string

import numpy as np
from io import BytesIO
import re
import base64
import cv2
import os
import easyocr
import pandas as pd
from PIL import Image 
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from spellchecker import SpellChecker
import spacy

nlp = spacy.load("en_core_web_sm")

import tempfile
from google.cloud import vision

# Check if running on Railway with JSON in env
if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    # Write credentials to a temporary file (lives only while the app runs)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
        temp_file.write(credentials_json.encode())
        temp_file.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name


def predict_title_with_google_vision(image_content):
    try:
        # Initialize and use Google Vision API
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_content)
        response = client.text_detection(image=image)

        # Get and clean the text
        if not response.text_annotations:
            return ""
        
        text = response.text_annotations[0].description
        # Clean up: normalize spaces and handle line breaks
        text = ' '.join(text.replace('\n', ' ').split())
        
        return text.strip()
    except Exception as e:
        print(f"Error in text detection: {str(e)}")
        return ""
  
#------------------------------------- INDEX/TOC/ABSTRACT -------------------------------------#



#------------------ Pre-Processing Image ------------------#



#------------------ OCR Processing ------------------#


#------------------ Post-Processing Image ------------------#




#------------------ Cleaning (Very Minimal) ------------------#
def _collapse_spaces_keep_newlines(s: str) -> str:
    """
    Collapse spaces but preserve paragraph breaks.
    """
    # Collapse multiple spaces inside a line
    lines = [re.sub(r'\s+', ' ', line).strip() for line in s.splitlines()]
    # Rejoin with newlines (paragraphs intact)
    return "\n".join([line for line in lines if line])

#------------------ Image Transfer to Views ------------------#
def ocr_extract_text(image_data_uri: str, scanned_type: str = "TOC") -> str:
    """
    OCR pipeline using Google Cloud Vision API for document text detection.
    """
    print("=================")
    print(scanned_type)
    print("=================")
    try:
        # Get binary data from URI
        try:
            b64 = image_data_uri.split(',', 1)[1]
        except Exception:
            b64 = image_data_uri

        # Decode image data
        img_bytes = base64.b64decode(b64)
        
        # Initialize Vision API client
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=img_bytes)
        
        # Use document text detection (optimized for dense text)
        # Use different detection methods based on scan type
        if scanned_type.upper() == "TOC":
            # For TOC, text_detection gives better layout spacing
            response = client.text_detection(image=image)
            print("========USING=========")
            print(scanned_type)
            print("=================")

            if not response.text_annotations:
                return "No text detected"

            # Each text_annotation[1:] is an individual word or symbol with coordinates
            words = response.text_annotations[1:]

            # Collect words with their positions
            word_entries = []
            max_x = max(w.bounding_poly.vertices[1].x for w in words)  # Get rightmost x coordinate
            min_x = min(w.bounding_poly.vertices[0].x for w in words)  # Get leftmost x coordinate
            x_range = max_x - min_x
            
            for w in words:
                vertices = w.bounding_poly.vertices
                # Calculate dimensions
                height = abs(vertices[2].y - vertices[0].y)
                width = abs(vertices[1].x - vertices[0].x)
                y_mid = (vertices[0].y + vertices[2].y) / 2
                x_start = vertices[0].x
                
                # More permissive height filter and consider width relative to page width
                if 3 < height < 150 and width < x_range * 0.8:  # Allow larger height range and limit max width
                    word_entries.append((y_mid, x_start, w.description.strip(), height))

            # Sort top to bottom, then left to right
            word_entries.sort(key=lambda v: (v[0], v[1]))

            # Calculate adaptive y_threshold based on median word height
            heights = [h for _, _, _, h in word_entries]
            median_height = sorted(heights)[len(heights)//2] if heights else 20
            y_threshold = median_height * 0.7  # Adaptive threshold based on text size
            
            # Initialize line processing
            lines = []
            current_line = []
            last_y = None

            for y, x, text_word, _ in word_entries:
                if last_y is None or abs(y - last_y) <= y_threshold:
                    current_line.append((x, text_word))
                else:
                    # Process the current line
                    if current_line:
                        current_line.sort(key=lambda t: t[0])
                        line_text = " ".join(t[1] for t in current_line)
                        
                        # Clean up common OCR issues
                        line_text = re.sub(r'\s+', ' ', line_text)  # normalize spaces
                        line_text = re.sub(r'\.{2,}', '', line_text)  # remove excessive dots entirely
                        line_text = re.sub(r'[^\w\s.,-]', '', line_text)  # remove unwanted symbols
                        line_text = line_text.strip()
                        
                        if line_text:  # Only add non-empty lines
                            lines.append(line_text)
                    current_line = [(x, text_word)]
                last_y = y

            # Process the final line
            if current_line:
                current_line.sort(key=lambda t: t[0])
                line_text = " ".join(t[1] for t in current_line)
                line_text = re.sub(r'\s+', ' ', line_text)
                line_text = re.sub(r'\.{2,}', '...', line_text)
                line_text = re.sub(r'[^\w\s.,-]', '', line_text)
                line_text = line_text.strip()
                if line_text:
                    lines.append(line_text)

            # Filter out any remaining noise lines (e.g., single characters, page numbers alone)
            lines = [line for line in lines if len(line.strip()) > 1]
            
            # Combine lines into one string with preserved newlines
            cleaned = "\n".join(lines)
            return cleaned
        else:
            # For other types (INDEX, ABSTRACT), use document_text_detection
            response = client.document_text_detection(image=image)
            print("========USING=========")
            print(scanned_type)
            print("=================")
        
        if not response.text_annotations:
            return "No text detected"
            
        # Get the full text from the response
        text = response.text_annotations[0].description
        
        # Basic cleanup while preserving paragraph structure
        cleaned = _collapse_spaces_keep_newlines(text)
        return cleaned
        
    except Exception as e:
        return "Error processing document"


#------------------------------------- INDEX/TOC/ABSTRACT -------------------------------------#
    

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(to_email, otp_code):
    subject = 'LIRAYA New Verification Code for Password Reset'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [to_email]
    
    text_content = (
        f"A new OTP has been generated for your LIRAYA password reset.\n"
        f"Your new code is: {otp_code}\n\n"
        f"The previous OTP you received is no longer valid.\n"
        f"This new code will expire in 5 minutes."
    )

    html_content = f"""
    <html>
      <body style="background-color:#f4f4f4; padding:30px; font-family:Arial, sans-serif;">
        <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1); text-align:center;">
          
          <div style="margin-bottom: 3px;">
            <img src="https://cdn-icons-png.flaticon.com/128/18363/18363064.png" alt="Security Icon" width="45" style="margin-bottom: -3px;" />
          </div>
          <h1 style="color:#561c24; font-size: 42px; font-weight:900; margin: 0px;">LIRAYA</h1>
          
          <h3 style="color:#333; margin-top: 10px;">New Verification Code Issued</h3>

          <p style="color:#555;">
            A new verification code has been generated for your <strong>LIRAYA</strong> password reset.
            <br />
            <strong style="color:#c0392b;">The previous code you received is no longer valid.</strong>
            <br />
            Please use the updated OTP below. This code will expire in <strong>5 minutes</strong>.
          </p>

          <div style="margin:20px 0; padding:15px; background-color:#f9f9f9; border:1px dashed #ccc; border-radius:5px;">
            <p style="font-size:14px; margin: 0;">
              <strong>VERIFICATION CODE:</strong>
              <strong style="color:#561c24; font-size:24px; letter-spacing: 3px;">{otp_code}</strong>
            </p>
          </div>

          <hr style="margin:30px 0;">
          <p style="font-size:12px; color:#777;">
            If you did not request a password reset, you may ignore this email.
          </p>
          <p style="font-size:12px; color:#777;">
            For assistance, please contact our support team.
          </p>
        </div>
      </body>
    </html>
    """

    # Construct the email and send
    msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")
    msg.send()




