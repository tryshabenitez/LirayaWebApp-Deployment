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

#------------------ TOC FUNCTIONS ------------------#

def _group_vision_words_into_lines(entities) -> list[list[dict]]:
    """
    Group Vision word-level annotations into horizontal lines using y-centers.
    entities: response.text_annotations[1:], items with bounding_poly and description
    Returns list of lines, each a list of word dicts with text and geometry, ordered by x.
    """
    words = []
    for ent in entities or []:
        try:
            txt = (ent.description or '').strip()
            if not txt:
                continue
            verts = getattr(ent, 'bounding_poly', None).vertices if getattr(ent, 'bounding_poly', None) else []
            xs = [v.x for v in verts if v is not None and hasattr(v, 'x')]
            ys = [v.y for v in verts if v is not None and hasattr(v, 'y')]
            if not xs or not ys:
                continue
            x_min, x_max = float(min(xs)), float(max(xs))
            y_min, y_max = float(min(ys)), float(max(ys))
            words.append({
                'text': txt,
                'x_center': 0.5 * (x_min + x_max),
                'y_center': 0.5 * (y_min + y_max),
                'y_top': y_min,
                'y_bottom': y_max,
                'height': max(4.0, (y_max - y_min)),
                'x_left': x_min,
                'x_right': x_max,
            })
        except Exception:
            continue

    if not words:
        return []

    # Determine a reasonable vertical tolerance for grouping
    heights = [w['height'] for w in words]
    med_h = float(np.median(heights)) if heights else 14.0
    y_tol = 0.6 * med_h

    # Sort by y, then group into lines
    words.sort(key=lambda w: (w['y_center'], w['x_center']))
    lines: list[list[dict]] = []
    cur_line: list[dict] = []
    cur_y = None
    for w in words:
        y = w['y_center']
        if cur_y is None or abs(y - cur_y) <= y_tol:
            cur_line.append(w)
            cur_y = y if cur_y is None else 0.5 * (cur_y + y)
        else:
            if cur_line:
                cur_line.sort(key=lambda t: t['x_left'])
                lines.append(cur_line)
            cur_line = [w]
            cur_y = y
    if cur_line:
        cur_line.sort(key=lambda t: t['x_left'])
        lines.append(cur_line)

    # Stitch lines that are likely the same physical line but got split
    if len(lines) > 1:
        # global median height for thresholds
        all_heights = [w['height'] for line in lines for w in line]
        g_med_h = float(np.median(all_heights)) if all_heights else 14.0
        y_merge_tol = 0.4 * g_med_h
        x_gap_tol = max(12.0, 0.8 * g_med_h)  # tolerate small horizontal gaps

        def line_metrics(line):
            x_l = min(w['x_left'] for w in line)
            x_r = max(w['x_right'] for w in line)
            y_m = float(np.median([w['y_center'] for w in line]))
            return x_l, x_r, y_m

        stitched: list[list[dict]] = []
        for ln in lines:
            if not stitched:
                stitched.append(ln)
                continue
            px_l, px_r, py = line_metrics(stitched[-1])
            cx_l, cx_r, cy = line_metrics(ln)
            # merge if y very close and horizontal gap is small
            if abs(cy - py) <= y_merge_tol and (0 <= (cx_l - px_r) <= x_gap_tol):
                merged = stitched.pop()
                merged.extend(ln)
                merged.sort(key=lambda t: t['x_left'])
                stitched.append(merged)
            else:
                stitched.append(ln)
        lines = stitched

    return lines

def _format_toc_line(title_raw: str) -> str:
    """
    Given a raw line string, extract a TOC entry in the form 'Title ... Page'.
    Handles dot leaders (......) or none, page numbers or roman numerals, and ranges.
    If no trailing page token is found, returns the cleaned line.
    """
    line = re.sub(r"\s+", " ", title_raw or '').strip()
    if not line:
        return ''

    # Match a trailing page token: digits or roman numerals, with optional range
    page_pat = re.compile(r"(?i)(\b(?:\d{1,4}|[ivxlcdm]{1,7})(?:\s*[-–]\s*(?:\d{1,4}|[ivxlcdm]{1,7}))?)\s*$")
    m = page_pat.search(line)
    if not m:
        # No explicit page at end; collapse dot leaders to a single ellipsis
        return re.sub(r"\.{2,}", " ... ", line).strip()

    page = m.group(1).strip()
    title = line[:m.start()].rstrip()
    # Remove trailing dot leaders or stray dots
    title = re.sub(r"\s*\.{2,}\s*$", " ", title)
    # Collapse multiple dots inside title
    title = re.sub(r"\.{2,}", " ... ", title)
    title = re.sub(r"\s+", " ", title).strip(" .\t")
    if not title:
        return page
    return f"{title} ... {page}"

def _vision_toc_text(response) -> str:
    """Build TOC-friendly text from Vision response using horizontal line grouping."""
    try:
        entities = response.text_annotations[1:] if response and getattr(response, 'text_annotations', None) else []
        lines = _group_vision_words_into_lines(entities)

        # Helper to join tokens conservatively and compute indentation
        def join_line(line_words):
            parts = []
            for w in line_words:
                t = w['text']
                if not t:
                    continue
                if parts and re.fullmatch(r"[.,:;!?)]", t):
                    parts[-1] = parts[-1] + t
                elif t in ["(", "[", "{"]:
                    parts.append(t)
                else:
                    if parts and parts[-1] in ["(", "[", "{"]:
                        parts[-1] = parts[-1] + t
                    else:
                        parts.append(t)
            raw = " ".join(parts)
            indent = min((w['x_left'] for w in line_words), default=0.0)
            return raw, indent

        page_pat = re.compile(r"(?i)(\b(?:\d{1,4}|[ivxlcdm]{1,7})(?:\s*[-–]\s*(?:\d{1,4}|[ivxlcdm]{1,7}))?)\s*$")
        heading_drop = {"table of contents", "contents", "page"}

        # Build raw lines with geometry
        items = []
        for lw in lines:
            raw, indent = join_line(lw)
            if not raw:
                continue
            if raw.strip().lower() in heading_drop:
                continue
            items.append({
                'raw': raw,
                'indent': indent,
                'has_page': bool(page_pat.search(raw)),
            })

        # Merge wrapped lines: accumulate until we encounter a line with a page at end
        formatted_lines = []
        buffer_text = None
        buffer_indent = None
        indent_tol = 24.0  # pixels; conservative default

        for it in items:
            raw = it['raw']
            indent = it['indent']
            has_page = it['has_page']

            if buffer_text is None:
                if has_page:
                    formatted = _format_toc_line(raw)
                    if formatted:
                        formatted_lines.append(formatted)
                else:
                    buffer_text = raw
                    buffer_indent = indent
                continue

            # buffer exists
            if abs(indent - buffer_indent) <= indent_tol:
                # same block
                buffer_text = f"{buffer_text} {raw}".strip()
                if has_page:
                    formatted = _format_toc_line(buffer_text)
                    if formatted:
                        formatted_lines.append(formatted)
                    buffer_text = None
                    buffer_indent = None
            else:
                # indentation changed: flush buffer cautiously
                # If buffer had no page, just append as-is
                if buffer_text:
                    formatted_lines.append(_format_toc_line(buffer_text))
                buffer_text = None
                buffer_indent = None
                # handle current
                if has_page:
                    formatted = _format_toc_line(raw)
                    if formatted:
                        formatted_lines.append(formatted)
                else:
                    buffer_text = raw
                    buffer_indent = indent

        # Flush any remaining buffer
        if buffer_text:
            formatted_lines.append(_format_toc_line(buffer_text))

        # Remove empties and collapse multiple blanks
        formatted_lines = [ln for ln in (formatted_lines or []) if (ln and ln.strip())]
        return "\n".join(formatted_lines)
    except Exception:
        return ""

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
            # For TOC, use text_detection and then build line-wise 'title ... page'
            response = client.text_detection(image=image)
            print("========USING=========")
            print(scanned_type)
            print("=================")
        else:
            # For other types (INDEX, ABSTRACT), use document_text_detection
            response = client.document_text_detection(image=image)
            print("========USING=========")
            print(scanned_type)
            print("=================")
        
        if not response.text_annotations:
            return "No text detected"
            
        if scanned_type.upper() == "TOC":
            # Prefer structured TOC formatting from word boxes
            toc_text = _vision_toc_text(response)
            if toc_text.strip():
                return toc_text
            # Fallback to cleaned full text if grouping fails
            text = response.text_annotations[0].description
            return _collapse_spaces_keep_newlines(text)
        else:
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




