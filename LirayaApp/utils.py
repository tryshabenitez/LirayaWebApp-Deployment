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

# EasyOCR function for text extraction
def predict_title_with_easyocr(image):

    # Initialize EasyOCR reader for English
    reader = easyocr.Reader(['en'])
    # Perform OCR on the image
    result = reader.readtext(image)
    # Combine the OCR result to extract title
    extracted_text = ' '.join([res[1] for res in result])
    return extracted_text
  
#------------------------------------- INDEX/TOC/ABSTRACT -------------------------------------#

_EASYOCR_READER = easyocr.Reader(['en', 'tl'], gpu=False)

#------------------ Pre-Processing Image ------------------#
def _preprocess_image_for_ocr(img_pil: Image.Image) -> Image.Image:
    """
    Gentle pre-processing:
    - Convert to grayscale
    - Light histogram equalization (optional, boosts contrast without losing details)
    """
    img_cv = np.array(img_pil)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)  # keep text strokes clear
    return Image.fromarray(gray)


#------------------ OCR Processing ------------------#

def _easyocr_text_from_array(img_array: np.ndarray, scanned_type: str = "TOC") -> str:
    """
    EasyOCR with column-aware ordering.
    Non-Index: unchanged.
    Index: cluster OCR word boxes into 2 or 3 vertical columns, then read L->R and top->bottom.
    """

    scanned_type = (scanned_type or "").strip().lower()
    if scanned_type == "index":
        # ---------------- helpers ----------------
        def _ocr_words(arr: np.ndarray):
            """Return list of (x_center, y_top, y_bottom, text, conf, box_width)."""
            out = []
            res = _EASYOCR_READER.readtext(arr, detail=1, paragraph=False)
            for item in (res or []):
                try:
                    box, txt, conf = item
                except Exception:
                    # some easyocr versions return (box, txt)
                    box, txt = item[:2]
                    conf = 1.0
                if not txt or conf is None:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                x_c = float(np.mean(xs))
                y_t = float(min(ys))
                y_b = float(max(ys))
                w   = float(max(xs) - min(xs))
                txt = re.sub(r"\s+", " ", str(txt)).strip()
                if not txt:
                    continue
                out.append((x_c, y_t, y_b, txt, float(conf), w))
            return out

        def _kmeans_1d(xs: np.ndarray, k: int, iters: int = 25):
            """Tiny 1-D kmeans; returns centers (sorted) and labels aligned to xs."""
            # init centers using quantiles for stability
            qs = np.linspace(0, 1, k + 2)[1:-1]
            centers = np.quantile(xs, qs)
            labels = np.zeros(len(xs), dtype=int)
            for _ in range(iters):
                # assign
                dists = np.abs(xs[:, None] - centers[None, :])
                new_labels = np.argmin(dists, axis=1)
                if np.array_equal(new_labels, labels):
                    break
                labels = new_labels
                # update
                for j in range(k):
                    m = xs[labels == j]
                    if len(m):
                        centers[j] = float(np.mean(m))
            order = np.argsort(centers)
            remap = {old: i for i, old in enumerate(order)}
            centers_sorted = centers[order]
            labels_sorted = np.array([remap[l] for l in labels], dtype=int)
            return centers_sorted, labels_sorted

        def _group_lines(words):
            """
            words: list of tuples for one column, sorted by y_top.
            Build text lines by grouping close y's and concatenate tokens.
            """
            if not words:
                return []
            # median height for adaptive line gap
            heights = [max(4.0, (y_b - y_t)) for _, y_t, y_b, *_ in words]
            med_h = float(np.median(heights)) if heights else 14.0
            y_tol = 0.65 * med_h

            lines = []
            cur_y = None
            cur = []
            for item in words:
                _, y_t, y_b, txt, *_ = item
                y_mid = 0.5 * (y_t + y_b)
                if cur_y is None or abs(y_mid - cur_y) <= y_tol:
                    cur.append(txt)
                    cur_y = y_mid if cur_y is None else 0.5 * (cur_y + y_mid)
                else:
                    lines.append(" ".join(cur).strip())
                    cur = [txt]
                    cur_y = y_mid
            if cur:
                lines.append(" ".join(cur).strip())

            # tidy dot leaders but keep them
            lines = [re.sub(r'\s*\.{2,}\s*', '...', ln) for ln in lines if ln]
            return lines

        def _score_bleed(lines: list[str]) -> int:
            """Your bleed score; unchanged."""
            score = 0
            for i in range(len(lines) - 1):
                prev = lines[i]
                curr = lines[i + 1]
                if re.search(r',\s*$', prev):
                    if re.match(
                        r"^[A-Za-z][A-Za-z0-9\s'’\-/()]*\s+\d+(?:\s*[-–]\s*\d+)?"
                        r"(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*", curr
                    ):
                        score += 1
            return score

        def _build_by_k(words_all, k):
            """Cluster words into k columns and return ordered lines."""
            if len(words_all) < max(20, 6 * k):
                return []  # too few words for reliable clustering
            xs = np.array([w[0] for w in words_all], dtype=float)
            centers, labels = _kmeans_1d(xs, k=k)

            # order clusters left->right
            order = np.argsort(centers)
            cols = []
            for cidx in order:
                col_words = [w for w, lab in zip(words_all, labels) if lab == cidx]
                # sort by y_top
                col_words.sort(key=lambda t: (t[1], t[0]))
                cols.append(_group_lines(col_words))

            # flatten: L->R columns
            lines = []
            for col in cols:
                lines.extend(col)
            return lines

        # ---------------- OCR and candidates ----------------
        words = _ocr_words(img_array)

        candidates = []

        # Candidate 1: k=3 columns
        k3_lines = _build_by_k(words, 3)
        if k3_lines:
            candidates.append(("kmeans_3col", k3_lines))

        # Candidate 2: k=2 columns
        k2_lines = _build_by_k(words, 2)
        if k2_lines:
            candidates.append(("kmeans_2col", k2_lines))

        # Fallback A: previous single paragraph (detail=0, paragraph=True)
        single = _EASYOCR_READER.readtext(img_array, detail=0, paragraph=True)
        single_lines = []
        if single:
            tmp = []
            for para in single:
                tmp.extend([re.sub(r'\s+', ' ', ln).strip()
                            for ln in str(para).splitlines() if ln.strip()])
            single_lines = [re.sub(r'\.{2,}', '...', ln) for ln in tmp if ln]
            candidates.append(("single", single_lines))

        # If all else fails: plain detail=0, paragraph=False
        if not candidates:
            res = _EASYOCR_READER.readtext(img_array, detail=0)
            if res:
                candidates.append(("raw", [re.sub(r'\s+', ' ', r).strip() for r in res if r.strip()]))

        # ---------------- choose best ----------------
        best_name, best_lines, best_score = None, None, None
        for name, lines in candidates:
            score = _score_bleed(lines)
            # prefer lower bleed; then prefer *more* lines (more granular)
            if (best_score is None or
                score < best_score or
                (score == best_score and len(lines) > len(best_lines or []))):
                best_name, best_lines, best_score = name, lines, score

        return "\n".join(best_lines or [])
    else: 
        result = _EASYOCR_READER.readtext(img_array, detail=0)
        return "" if not result else "\n".join(result)


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
    Raw OCR pipeline with conditional paragraph handling.
    """
    try:
        b64 = image_data_uri.split(',', 1)[1]
    except Exception:
        b64 = image_data_uri  

    img_bytes = base64.b64decode(b64)
    img = Image.open(BytesIO(img_bytes)).convert("RGB")

    pre = _preprocess_image_for_ocr(img)
    arr = np.array(pre)

    raw = _easyocr_text_from_array(arr, scanned_type)   # <-- pass scanned_type
    if not raw:
        return "No text detected"

    cleaned = _collapse_spaces_keep_newlines(raw)
    return cleaned


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




