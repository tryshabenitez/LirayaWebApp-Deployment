from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import logout 
from .models import AccountInformation, UserAccounts, ResetPassword, Books, KeywordLog, BookViewLog, name_validator, middle_name_validator
from django.urls import reverse
from django.core.mail import send_mail
import random
from django.core.exceptions import FieldError
import calendar
import string
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import login_required
from social_django.models import UserSocialAuth
from django.utils.dateformat import DateFormat
from django.core.files.storage import FileSystemStorage
import base64
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
import os
from django.conf import settings
import re
from django.contrib.auth.hashers import check_password, make_password  
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from datetime import datetime, date, timedelta
import re
import logging 
import traceback
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F,  Max, Value, CharField, Case, When, Sum, Min, DateTimeField
from django.db.models.functions import Concat, TruncMonth, Coalesce
from datetime import timedelta
from django.utils import timezone
import re as _re
from .utils import generate_otp, send_otp_email, predict_title_with_google_vision, ocr_extract_text 
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO
import base64
import json
import spacy
import cv2
import difflib
import numpy as np
import easyocr 
import torch
from django.db import IntegrityError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.db.models import Q, Count
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.contrib.auth import update_session_auth_hash
from spellchecker import SpellChecker
from django.views.decorators.csrf import csrf_exempt
import requests
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from difflib import get_close_matches
from collections import Counter
from django.db import transaction
from django.utils.timezone import localdate
import time
from .pdf_generator import (
    generate_account_information,
    generate_account_bookrecords,
    generate_book_details,  
    generate_keyword_search_history,
)
import matplotlib.pyplot as plt
from collections import defaultdict
import pandas as pd
from django.db import models
from cloudinary import uploader
from cloudinary.uploader import upload, destroy
import pytz
import matplotlib
matplotlib.use('Agg') 
from dateutil.relativedelta import relativedelta

nlp = spacy.load('en_core_web_sm')

##### ENSURE THAT ROLES CANNOT ACCESS OTHER HTML #########
def login_checker(view_func):
    def _wrapped_view(request, *args, **kwargs):
        # Reload the page first
        # Check if the user is logged in by checking if 'account_id' exists in the session
        account_id = request.session.get('account_id')

        # If 'account_id' doesn't exist in the session, the user is logged out
        if not account_id:
            messages.error(request, "You must log in first.")
            return redirect('login')  # Redirect to the login page if the user is not logged in
        
        try:
            # Get the user account status
            user_account = UserAccounts.objects.get(account_id=account_id)
            account_status = user_account.account_status

            # If the account is deactivated, log the user out
            if account_status == 'DEACTIVATED':
                request.session.flush()  # Flush the session to log the user out
                messages.error(request, "Your account has been deactivated.")
                return redirect('login')  # Redirect to the login page

        except UserAccounts.DoesNotExist:
            messages.error(request, "Account not found.")
            return redirect('login')

        # If the user is logged in and the account is active, proceed to the view
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
# Decorator to check user login and role
def role_required(required_role):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            account_id = request.session.get('account_id')
            if not account_id:
                return redirect('login')  # Redirect to login if not logged in

            try:
                account = AccountInformation.objects.get(account_id=account_id)
                user_account = UserAccounts.objects.get(account=account)

                # Allow DEPARTMENT to be treated the same as LIBRARIAN
                if not (
                    user_account.role.upper() == required_role.upper()
                    or (
                        required_role.upper() == "LIBRARIAN"
                        and user_account.role.upper() == "DEPARTMENT"
                    )
                ):
                    error_message = "access_restricted"
                    
                    # Add the error message to the Django messages framework
                    messages.error(request, "Access restricted. You do not have permission to access this page.")
                    
                    # Role-specific redirection
                    if user_account.role.upper() == "ADMIN":
                        return redirect(reverse('admin_homepage') + f"?error_message={error_message}")
                    elif user_account.role.upper() in ["LIBRARIAN", "DEPARTMENT"]:
                        return redirect(reverse('librarian_homepage') + f"?error_message={error_message}")
                    else:
                        return redirect(reverse('error_page') + f"?error_message={error_message}")  # Redirect to error page

                # If the role matches, proceed with the view
                return view_func(request, *args, **kwargs)
            except AccountInformation.DoesNotExist:
                return redirect('login')  # Redirect to login if account not found
            except UserAccounts.DoesNotExist:
                return redirect('login')  # Redirect to login if user account not found

        return _wrapped_view
    return decorator

################## USER DASHBOARD ###########################
def _normalize_terms_for_logging(raw, stopwords):
    if not raw:
        return []

    s = (raw or '').replace(',', ' ')
    parts = []
    for t in s.split():  # splits on any whitespace
        tt = t.strip()
        if not tt:
            continue
        low = tt.lower()
        if low in stopwords:
            continue
        parts.append(low)

    # de-dup preserving order
    seen, out = set(), []
    for w in parts:
        if w not in seen:
            out.append(w)
            seen.add(w)
    return out


def user_homepage(request):
    return render(request, 'user_homepage.html')


def user_aboutus(request):
    return render(request, 'user_aboutus.html')

def user_search(request):
    # ------- Base queryset -------
    books = Books.objects.filter(is_archived=False)

    # ------- Read query params -------
    q = (request.GET.get('q') or "").strip()
    field = (request.GET.get('field') or "allFields").strip()
    sort_option = request.GET.get('sort', 'Relevance')

    # Multiple-select facets: strip out empty values coming from hidden inputs
    cats   = [c.strip() for c in request.GET.getlist('active_categories') if c.strip()]
    rtypes = [t.strip() for t in request.GET.getlist('active_resource_types') if t.strip()]
    subs   = [s.strip() for s in request.GET.getlist('active_subjects') if s.strip()]


    # cast years defensively
    def _to_int_or_none(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    min_year = _to_int_or_none(request.GET.get('min_year'))
    max_year = _to_int_or_none(request.GET.get('max_year'))

    # ------- Stopwords (connecting words) -------
    STOPWORDS = {
        'the','or','at','and','of','to','a','an','in','on','by','for','with','from',
        'is','are','as','that','this','these','those','be','was','were','been','it',
        'its','into','than','then','over','under','between','among','via','per','vs'
    }

    # ===============================
    #        FUZZY (difflib)
    # ===============================
    # --- Token helpers: logging vs. search ---

    def split_words_logging(s):
        """
        Original behavior for KeywordLog:
        - strip punctuation (incl. '-', '–', ',')
        - log only clean alphanumeric tokens
        """
        raw = (s or '').replace(',', ' ').split()
        out = []
        for w in raw:
            w = _re.sub(r'[^A-Za-z0-9]', '', w).strip()
            if not w or w in {'-', '–', '_', '—'}:
                continue
            wl = w.lower()
            if wl not in STOPWORDS:
                out.append(wl)
        return out

    def split_words_search(s):
        """
        Search-focused tokenizer:
        - keeps '-', en/em dash, and comma *inside* tokens
        - trims leading/trailing commas
        - avoids splitting 'pre-test' into 'pre' + 'test'
        """
        raw = (s or '').split()
        out = []
        for w in raw:
            # keep -, en dash, em dash, comma
            w = _re.sub(r'[^A-Za-z0-9,\-\u2013\u2014]', '', w)
            # drop stray leading/trailing commas (e.g., 'color,' -> 'color')
            w = w.strip(',').strip()
            if not w or w in {'-', '–', '_', '—'}:
                continue
            wl = w.lower()
            if wl not in STOPWORDS:
                out.append(w)
        return out

    def split_keywords(s):
        """
        Split comma-separated keywords into tokens for facets/search,
        preserving '-', en dash, and em dash inside tokens.
        """
        out = []
        for chunk in (s or '').split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            for w in chunk.split():
                w = _re.sub(r'[^A-Za-z0-9\-\u2013\u2014]', '', w).strip().strip(',')
                if not w or w in {'-', '–', '_', '—'}:
                    continue
                wl = w.lower()
                if wl not in STOPWORDS:
                    out.append(w)
        return out


    def build_reference_vocab(row_limit=20000):
        """
        Build a small in-memory vocabulary from titles and primary_keyword.
        Capped by row_limit to keep it fast and deterministic.
        """
        vocab = set()
        for title, keywords in Books.objects.only('title', 'primary_keyword') \
                                           .values_list('title', 'primary_keyword')[:row_limit]:
            if title:
                for w in title.replace(',', ' ').split():
                    wl = w.strip().lower()
                    if len(wl) >= 3 and wl not in STOPWORDS:
                        vocab.add(wl)
            if keywords:
                for w in keywords.replace(',', ' ').split():
                    wl = w.strip().lower()
                    if len(wl) >= 3 and wl not in STOPWORDS:
                        vocab.add(wl)
        return list(vocab)

    # Build per-request (kept as in your original)
    REFERENCE_VOCAB = build_reference_vocab()

    def fuzzy_variants(token, n=5, cutoff=None):
        """
        Safer fuzzy variants to reduce false positives:
        - No fuzz for very short tokens (<=3 chars).
        - Dynamic cutoff: stricter for short/medium tokens.
        - Limit length drift (±2 chars).
        Always returns a list with the original token first.
        """
        base = (token or "").strip().lower()
        if not base:
            return [base]

        if len(base) <= 3:
            return [base]

        if cutoff is None:
            cutoff = 0.82 if len(base) <= 6 else 0.78

        matches = difflib.get_close_matches(base, REFERENCE_VOCAB, n=n, cutoff=cutoff)
        matches = [m for m in matches if abs(len(m) - len(base)) <= 2]

        if base not in matches:
            matches.insert(0, base)
        else:
            matches.remove(base)
            matches.insert(0, base)

        return matches

    # ===============================
    #           LOGGING (kept)
    # ===============================
    SEP = "\n"
    def _append_time(pk):
        now = timezone.now()
        ts_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")
        KeywordLog.objects.filter(pk=pk).update(
            search_times=Case(
                When(search_times__isnull=True, then=Value(ts_str)),
                When(search_times__exact='', then=Value(ts_str)),
                default=Concat('search_times', Value(SEP), Value(ts_str)),
                output_field=CharField(),
            ),
            updated_at=now,
        )

    if q and q.strip():
        try:
            corrected_terms = []
            for token in split_words_logging(q):
                variants = fuzzy_variants(token, n=1, cutoff=0.85)  # a bit stricter for logging
                if variants:
                    corrected = variants[0].lower()
                    term = corrected
                    if corrected != token.lower():
                        corrected_terms.append(f"{token}→{corrected}")

                    obj, _ = KeywordLog.objects.get_or_create(user_keyword_search=term)
                    KeywordLog.objects.filter(pk=obj.pk).update(
                        user_search_count=F('user_search_count') + 1,
                        updated_at=timezone.now(),
                    )
                    _append_time(obj.pk)

            if corrected_terms:
                KeywordLog.objects.create(
                    user_keyword_search="; ".join(corrected_terms),
                    user_search_count=1,
                    updated_at=timezone.now()
                )

        except Exception:
            # Never block search if logging fails
            pass

    # ===============================
    #           SEARCH
    # ===============================
    also_terms = []  # collect fuzzy extras to show in the UI
    highlight_tokens = []

        # Fallback highlighter so blank/ignored queries don't break the view
    def build_highlight_fn(style, tokens):
        def _no_highlight(text):
            return text or ""
        return _no_highlight


    if q:
        tokens = split_words_search(q)
        kw_tokens = split_keywords(q)

        # Normalize/dedupe tokens for highlighting (but keep original case for later use)
        seen = set()
        norm_tokens = []
        for raw in tokens:
            base = (raw or '').strip().strip(',').lower()
            if not base or base in STOPWORDS or len(base) < 2:
                continue
            if base not in seen:
                seen.add(base)
                norm_tokens.append(raw)
        highlight_tokens = norm_tokens

        def build_token_q(field_name, term):
            """
            Build a Q() that enforces the following rules:
        
            - KEYWORDS:
                * if len(term) < 7: require 1:1 whole-word match (iregex)
                * else:             allow icontains
        
            - TITLE / AUTHOR:
                * if len(term) <= 3: whole-word iregex
                * else:              icontains
        
            - ALL FIELDS:
                * Apply keyword rules to keywords:
                    - <7 letters = 1:1 whole-word match
                    - >=7 letters = icontains
                * Apply normal title/author rules based on length
            """
        
            term = (term or "").strip()
            if not term:
                return Q()
        
            # ================================
            #      KEYWORDS (direct search)
            # ================================
            if field_name == 'keywords':
                if len(term) < 7:
                    # strict whole-word
                    pattern = r'\b' + _re.escape(term) + r'\b'
                    return Q(primary_keyword__iregex=pattern)
                else:
                    return Q(primary_keyword__icontains=term)
        
            # ================================
            #       TITLE / AUTHOR ONLY
            # ================================
            if field_name == 'title':
                if len(term) <= 3:
                    pattern = r'\b' + _re.escape(term) + r'\b'
                    return Q(title__iregex=pattern)
                else:
                    return Q(title__icontains=term)
        
            if field_name == 'author':
                if len(term) <= 3:
                    pattern = r'\b' + _re.escape(term) + r'\b'
                    return Q(author__iregex=pattern)
                else:
                    return Q(author__icontains=term)
        
            # ================================
            #       ALL FIELDS (title, author, keywords)
            # ================================
            # --- KEYWORDS part: apply SAME RULES as field="keywords" ---
            if len(term) < 7:
                kw_pattern = r'\b' + _re.escape(term) + r'\b'
                keyword_q = Q(primary_keyword__iregex=kw_pattern)
            else:
                keyword_q = Q(primary_keyword__icontains=term)
        
            # --- TITLE / AUTHOR part ---
            if len(term) <= 3:
                # whole-word for short tokens
                short_pattern = r'\b' + _re.escape(term) + r'\b'
                return (
                    Q(title__iregex=short_pattern) |
                    Q(author__iregex=short_pattern) |
                    keyword_q
                )
        
            # longer terms: substring allowed
            return (
                Q(title__icontains=term) |
                Q(author__icontains=term) |
                keyword_q
            )


    
        def is_reasonable_alt(base, alt):
            """
            Decide if 'alt' is worth showing in 'Also searching for'.
            - Skip empty, identical, very short, or digit-containing variants.
            - If base is purely alphabetic, alt must be purely alphabetic too.
            """
            base = (base or "").strip().lower()
            alt  = (alt or "").strip().lower()
    
            if not base or not alt:
                return False
            if alt == base:
                return False
            if len(alt) <= 3:
                return False
    
            # Drop anything with digits, e.g. 'computer13'
            if any(ch.isdigit() for ch in alt):
                return False
    
            # If the original term is alphabetic, ignore non-alphabetic variants
            if base.isalpha() and not alt.isalpha():
                return False
    
            return True

        # ===============================
        #        HIGHLIGHTING
        # ===============================
        def build_highlight_fn(style, tokens):
            """
            style:
              - 'keywords' => BOLD + ALL CAPS for matched tokens
              - 'title'    => italic for matched tokens
              - 'author'   => bold for matched tokens
            We:
            - match case-insensitively
            - treat an optional trailing 's' as part of the match (color/colors)
            - escape non-matched text before injecting HTML
            """
            # Build regex for the query tokens
            patterns = []
            for raw in tokens or []:
                base = (raw or '').strip().strip(',').lower()
                if not base or base in STOPWORDS or len(base) < 2:
                    continue
                # simple plural support: color -> color / colors
                if base.endswith('s'):
                    patterns.append(_re.escape(base))
                else:
                    patterns.append(_re.escape(base) + 's?')
    
            if not patterns:
                return lambda text: text or ''
    
            pattern = _re.compile(r'\b(' + '|'.join(patterns) + r')\b', _re.IGNORECASE)
    
            def apply(text):
                if not text:
                    return ''
                result = []
                last = 0
                s = text
    
                for m in pattern.finditer(s):
                    start, end = m.span()
                    # non-matched segment
                    if start > last:
                        result.append(escape(s[last:start]))
    
                    token = m.group(0)
                    esc_token = escape(token)
    
                    if style == 'keywords':
                        # BOLD + ALL CAPS
                        repl = f"<strong>{esc_token.upper()}</strong>"
                    elif style == 'title':
                        # italic, keep original case
                        repl = f"<em>{esc_token}</em>"
                    elif style == 'author':
                        # bold, keep original case
                        repl = f"<strong>{esc_token}</strong>"
                    else:
                        repl = esc_token
    
                    result.append(repl)
                    last = end
    
                # tail segment
                if last < len(s):
                    result.append(escape(s[last:]))
    
                return mark_safe(''.join(result))
    
            return apply



        def apply_field_filters(qs, field_name, toks):
            """Apply fuzzy variants per token + build clean 'Also searching for' list."""
            for t in toks:
                t_norm = (t or "").strip().lower()
                if not t_norm:
                    continue

                # For very short tokens, skip fuzzy; use the raw token only
                if len(t_norm) <= 3:
                    variants = [t_norm]
                else:
                    variants = fuzzy_variants(t_norm, n=5)  # original first

                # Build 'Also searching for' only from *reasonable* longer variants
                if len(t_norm) > 3:
                    for v in variants[1:]:  # skip original at index 0
                        if is_reasonable_alt(t_norm, v) and v not in also_terms:
                            also_terms.append(v)

                # Build the OR Q for all variants (search behaviour can stay generous)
                q_or = Q()
                for v in variants:
                    q_or |= build_token_q(field_name, v)

                qs = qs.filter(q_or)
            return qs



        if field == 'author':
            books = apply_field_filters(books, 'author', tokens or kw_tokens)
        elif field == 'title':
            books = apply_field_filters(books, 'title', tokens or kw_tokens)
        elif field == 'keywords':
            books = apply_field_filters(books, 'keywords', kw_tokens or tokens)
        else:
            # allFields: merge unique tokens
            token_set, seen = [], set()
            for t in tokens + kw_tokens:
                tl = t.lower()
                if tl not in seen:
                    token_set.append(t)
                    seen.add(tl)
            books = apply_field_filters(books, 'all', token_set)

    # ===============================
    #         YEAR FILTERS
    # ===============================
    if min_year is not None:
        books = books.filter(year_of_publication__gte=min_year)
    if max_year is not None:
        books = books.filter(year_of_publication__lte=max_year)

    # ===============================
    #    CATEGORY / RESOURCE TYPE
    # ===============================
    # (IMPORTANT) Use the repeated params lists directly; DO NOT split on commas.
    if cats:
        books = books.filter(shelf_category__in=cats)

    if rtypes:
        books = books.filter(book_type__in=rtypes)

    # ===============================
    #   SUBJECTS FACET FILTER (still fuzzy, but safer variants)
    # ===============================
    if subs:
        q_or = Q()
        for s_term in subs:
            # no fuzzy for very short subjects
            if len(s_term) <= 3:
                variants = [s_term.lower()]
            else:
                variants = fuzzy_variants(s_term, n=5)

            for v in variants:
                q_or |= build_token_q('keywords', v)

        if q_or:
            books = books.filter(q_or)


    # ===============================
    #           SORT
    # ===============================
    if sort_option == 'Relevance':
        books = books.order_by('-pk')  # ensures stable pagination
    elif sort_option == 'Newest to Oldest':
        books = books.order_by('-year_of_publication')
    elif sort_option == 'Oldest to Newest':
        books = books.order_by('year_of_publication')
    elif sort_option == 'Author':
        books = books.order_by('author')
    elif sort_option == 'Title':
        books = books.order_by('title')
    # 'Relevance' -> keep current order

    # ===============================
    #           FACETS
    # ===============================
    shelf_categories = (
        books.values('shelf_category')
             .annotate(count=Count('shelf_category'))
             .order_by('-count', 'shelf_category')
    )

    resource_types = (
        books.values('book_type')
             .annotate(count=Count('book_type'))
             .order_by('-count', 'book_type')
    )

    # Subjects / Keywords facet (simple count)
    subj_counter = {}
    for s in books.values_list('primary_keyword', flat=True):
        for token in split_keywords(s or ''):
            key = token.lower()
            subj_counter[key] = subj_counter.get(key, 0) + 1

    subjects_facet = [
        {'term': k, 'display': k.title(), 'count': v}
        for k, v in subj_counter.items()
    ]
    subjects_facet.sort(key=lambda x: (-x['count'], x['display']))

    # ===============================
    #         PAGINATION
    # ===============================
    paginator = Paginator(books, 10)  # 10 per page
    page = request.GET.get('page')
    books_page = paginator.get_page(page)

    current_page = books_page.number
    total_pages = paginator.num_pages

    # ===============================
    #     APPLY HIGHLIGHTING
    # ===============================
    kw_highlighter     = build_highlight_fn('keywords', highlight_tokens)
    title_highlighter  = build_highlight_fn('title',    highlight_tokens)
    author_highlighter = build_highlight_fn('author',   highlight_tokens)

    for b in books_page:
        # Keywords: BOLD + ALL CAPS for matched tokens
        b.highlighted_keywords = kw_highlighter(getattr(b, 'primary_keyword', '') or '')

        # Title: already styled as a title; just italicize matched parts
        b.highlighted_title = title_highlighter(getattr(b, 'title', '') or '')

        # Author: bold matched parts in the author string
        b.highlighted_author = author_highlighter(getattr(b, 'author', '') or '')


    # ===============================
    #           CONTEXT
    # ===============================
    qs_no_book = request.GET.copy()
    qs_no_book.pop('book_id', None)
    qs_no_book = qs_no_book.urlencode()
    current_year = timezone.now().year

    context = {
        'books': books_page,
        'current_page': current_page,
        'total_pages': total_pages,
        'page_range': paginator.page_range,
        'sort_option': sort_option,
        'shelf_categories': shelf_categories,
        'resource_types': resource_types,
        'subjects': subjects_facet,
        'active_categories': cats,            # lists preserved
        'active_resource_types': rtypes,      # lists preserved
        'active_subjects': subs,              # lists preserved
        'qs_no_book': qs_no_book,             # ViewInfo
        'current_year': current_year,
        'also_searching': also_terms,         # "Also searching for"
    }

    return render(request, 'user_search.html', context)






# views.py
def view_info(request):
    book_id = request.GET.get('book_id')
    if not book_id:
        return redirect('user_search')

    book = get_object_or_404(Books, book_id=book_id)

    # view counter (unchanged)
    try:
        with transaction.atomic():
            rec, _ = BookViewLog.objects.select_for_update().get_or_create(
                book_id=book.book_id,
                defaults={'book_count': 0},
            )
            rec.book_count = (rec.book_count or 0) + 1
            rec.save()
    except Exception:
        pass

    # NEW: build a qs for "Return" WITHOUT book_id
    qs = request.GET.copy()
    qs.pop('book_id', None)
    return render(request, 'user_viewinfo.html', {
        'book': book,
        'return_qs': qs.urlencode(),
    })



def user_suggestions(request):
    q = (request.GET.get('q') or '').strip()
    field = (request.GET.get('field') or 'allFields').strip()

    if not q:
        return JsonResponse({'results': []})

    # Tokenize by comma/space, drop small common connectors
    raw_tokens = re.split(r'[,\s]+', q)
    stopwords = {'the', 'or', 'at', 'a', 'an', 'and', 'of', 'to', 'for', 'in', 'on'}
    tokens = [t for t in raw_tokens if t and t.lower() not in stopwords]

    if not tokens:
        return JsonResponse({'results': []})

    base_qs = Books.objects.filter(is_archived=False)
    results = []

    # Helper to AND-filter tokens on one field
    def and_filter(qs, field_name):
      for tok in tokens:
          qs = qs.filter(**{f"{field_name}__icontains": tok})
      return qs

    # Titles
    if field in ('allFields', 'title'):
        tqs = and_filter(base_qs, 'title')
        titles = list(tqs.values_list('title', flat=True).distinct()[:8])
        results.extend({'type': 'title', 'text': t} for t in titles)

    # Authors
    if field in ('allFields', 'author'):
        aqs = and_filter(base_qs, 'author')
        authors = list(aqs.values_list('author', flat=True).distinct()[:8])
        results.extend({'type': 'author', 'text': a} for a in authors)

    # Keywords (split the stored comma list into individual keywords)
    if field in ('allFields', 'keywords'):
        kqs = and_filter(base_qs, 'primary_keyword')
        seen = set()
        keywords = []
        # Scan a limited number of rows for performance
        for kw_str in kqs.values_list('primary_keyword', flat=True)[:200]:
            if not kw_str:
                continue
            for kw in (x.strip() for x in kw_str.split(',')):
                if not kw:
                    continue
                low = kw.lower()
                if all(tok.lower() in low for tok in tokens) and kw not in seen:
                    seen.add(kw)
                    keywords.append(kw)
                    if len(keywords) >= 8:
                        break
            if len(keywords) >= 8:
                break
        results.extend({'type': 'keywords', 'text': k} for k in keywords)

    # Mix for allFields
    if field == 'allFields':
        titles   = [r for r in results if r['type'] == 'title'][:3]
        authors  = [r for r in results if r['type'] == 'author'][:3]
        keywords = [r for r in results if r['type'] == 'keywords'][:2]
        results = titles + authors + keywords
    else:
        results = results[:8]

    return JsonResponse({'results': results})




    #### USER FUNCTIONS END ######

def user_viewinfo(request):
    return render(request, 'user_viewinfo.html')



########### ADMIN DASHBOARD ############
########### ADMIN DASHBOARD ############
logger = logging.getLogger(__name__)


def get_user_info(account_id):
    # Retrieve the account information based on account_id
    account = get_object_or_404(AccountInformation, account_id=account_id)
    
    # Retrieve the user account information to get the role
    user_account = UserAccounts.objects.get(account=account)

    # Handle middle name (None if N/A, na, or blank)
    if account.middle_name and account.middle_name.lower() in ['n/a', 'na']:
        account.middle_name = None
    
    # Format the full name (First, Middle, and Last Name)
    full_name = f"{account.first_name} {account.middle_name or ''} {account.last_name}".strip()

    # Return the user information as a dictionary, including the role
    return {
        'account_id': account.account_id,
        'profile_picture': account.profile_picture,
        'full_name': full_name,
        'role': user_account.role  # Include the role from UserAccounts
    }


@login_checker
@role_required('ADMIN')
def admin_homepage(request):
    account_id = request.session.get('account_id')
    user_info = get_user_info(account_id)
    if not account_id:
        return redirect('login')

    try:
        account = AccountInformation.objects.get(account_id=account_id)
    except AccountInformation.DoesNotExist:
        return redirect('login')

    # Base queryset for books
    books = Books.objects.filter(is_archived=False)  # Exclude archived books for admin

    # ---------- Query params ----------
    query = request.GET.get('q', '').strip()  # Get the search query
    field = request.GET.get('field', 'allFields').strip()  # Field to search in (title, author, etc.)
    sort_by = request.GET.get('sort', 'all')  # Sorting option

    # Apply search filters based on the selected field
    if query:
        print(f"Applying search with query: {query} in field: {field}")

        if field == 'title':
            books = books.filter(title__icontains=query)
        elif field == 'author':
            books = books.filter(author__icontains=query)
        elif field == 'keywords':
            books = books.filter(primary_keyword__icontains=query)
        else:  # allFields
            books = books.filter(
                Q(title__icontains=query) | Q(author__icontains=query) | Q(primary_keyword__icontains=query)
            )



    # ---------- Sorting ----------
    if sort_by == 'all':
        books = books.order_by('book_id')
    elif sort_by == 'oldest_to_newest':
        books = books.order_by('date_uploaded')
    elif sort_by == 'newest_to_oldest':
        books = books.order_by('-date_uploaded')
    elif sort_by == 'author':
        books = books.order_by('author')
    elif sort_by == 'keyword':
        books = books.order_by('primary_keyword')
    elif sort_by == 'subject':
        books = books.order_by('book_type')
    elif sort_by == 'title':
        books = books.order_by('title')

    # ---------- Total book count (should remain unchanged) ----------
    total_books = books.count() 

    # ---------- Pagination ----------
    paginator = Paginator(books, 10)  # Show 10 books per page
    page_number = request.GET.get('page')  # Get the current page number from query params
    page_obj = paginator.get_page(page_number)  # Get the page object

    context = {
        'user_info': user_info,
        'page_obj': page_obj,  # Only the books for the current page (pagination)
        'book_count': total_books,
        'sort_by': sort_by,
        'query': query,
        'field': field,
    }
    return render(request, 'admin_homepage.html', context)




@login_checker
@role_required('ADMIN')
def admin_suggestions(request):
    query = request.GET.get('q', '').strip()
    field = request.GET.get('field', 'allFields').strip()

    # Allow search even for short queries (1 character)
    if not query:
        return JsonResponse({'results': []})

    # Tokenize by comma/space, drop small common connectors
    raw_tokens = re.split(r'[,\s]+', query)
    stopwords = {'the', 'or', 'at', 'a', 'an', 'and', 'of', 'to', 'for', 'in', 'on'}
    tokens = [t for t in raw_tokens if t and t.lower() not in stopwords]

    if not tokens:
        return JsonResponse({'results': []})

    base_qs = Books.objects.filter(is_archived=False)
    results = []

    # Helper to AND-filter tokens on one field
    def and_filter(qs, field_name):
        for tok in tokens:
            qs = qs.filter(**{f"{field_name}__icontains": tok})
        return qs

    # Titles
    if field in ('allFields', 'title'):
        tqs = and_filter(base_qs, 'title')
        titles = list(tqs.values_list('title', flat=True).distinct()[:200])
        results.extend({'type': 'title', 'text': t} for t in titles)

    # Authors - ensure partial matches for multi-word names
    if field in ('allFields', 'author'):
        aqs = and_filter(base_qs, 'author')
        authors = list(aqs.values_list('author', flat=True).distinct()[:200])
        
        if not authors:  # If no matches found with tokenized query
            authors = list(base_qs.values_list('author', flat=True).distinct()[:200])
        
        results.extend({'type': 'author', 'text': a} for a in authors)

    # Keywords (split the stored comma list into individual keywords)
    if field in ('allFields', 'keywords'):
        kqs = and_filter(base_qs, 'primary_keyword')
        seen = set()
        keywords = []
        # Scan a limited number of rows for performance
        for kw_str in kqs.values_list('primary_keyword', flat=True)[:200]:
            if not kw_str:
                continue
            for kw in (x.strip() for x in kw_str.split(',')):
                if not kw:
                    continue
                low = kw.lower()
                if all(tok.lower() in low for tok in tokens) and kw not in seen:
                    seen.add(kw)
                    keywords.append(kw)
                    if len(keywords) >= 8:
                        break
            if len(keywords) >= 8:
                break
        results.extend({'type': 'keywords', 'text': k} for k in keywords)

    # Prioritize results by matching query
    results = sorted(results, key=lambda x: x['text'].lower().startswith(query.lower()), reverse=True)

    # Mix for allFields
    if field == 'allFields':
        titles   = [r for r in results if r['type'] == 'title']
        authors  = [r for r in results if r['type'] == 'author']
        keywords = [r for r in results if r['type'] == 'keywords']
        results = titles + authors + keywords

    # Limit to 10 results
    results = results[:10]

    return JsonResponse({'results': results})
       

@login_checker
@role_required('ADMIN')
def admin_bookdetails(request):
    book_id = request.GET.get('book_id')  # Get the book_id from URL
    account_id = request.session.get('account_id') 
    user_info = get_user_info(account_id)
    try:
        # Fetch the specific book details from the database
        book = Books.objects.get(book_id=book_id, is_archived=False)
        
        
        context = {
            'book': book,  # Pass the book details to the template
            'user_info': user_info,
        }
        return render(request, 'admin_bookdetails.html', context)

    except Books.DoesNotExist:
        messages.error(request, "Book not found.")
        return redirect('admin_homepage')  # Redirect to admin homepage if the book does not exist


@login_checker
@role_required('ADMIN')
def admin_manageaccount(request):
    # Fetch all accounts with their associated user roles
    accounts = UserAccounts.objects.select_related('account').all().order_by('account__account_id')
    account_id = request.session.get('account_id') 
    user_info = get_user_info(account_id)
    
    search_query = request.GET.get('search', '')
    if search_query:
        accounts = accounts.filter(
            Q(account__first_name__icontains=search_query) | 
            Q(account__middle_name__icontains=search_query) |
            Q(account__last_name__icontains=search_query)
        )
    
    # Handle the role filter (if provided)
    role_filter = request.GET.get('role', 'all')
    if role_filter != 'all':
        accounts = accounts.filter(role=role_filter)

    # Handle the status filter (if provided)
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        accounts = accounts.filter(account_status=status_filter)

    # Handle sorting
    sort_option = request.GET.get('sort', 'all')
    if sort_option == 'az':
        accounts = accounts.order_by('account__first_name')  # Sort A-Z
    elif sort_option == 'za':
        accounts = accounts.order_by('-account__first_name')  # Sort Z-A
    elif sort_option == 'all':
        # No sorting applied, just show the accounts as they are
        accounts = accounts.all()  # You can omit this line since it's the default state, but it's good practice
    
    # Handling account activation and deactivation based on the action
    account_id = request.GET.get('account_id')
    action = request.GET.get('action')
    
    if account_id and action:
        user_account = get_object_or_404(UserAccounts, account_id=account_id)

        if action == 'activate':
            user_account.account_status = 'ACTIVE'
            user_account.save()
            messages.success(request, "Successfully REACTIVATED this account.")

        elif action == 'deactivate':
            user_account.account_status = 'DEACTIVATED'
            user_account.save()
            messages.success(request, "Successfully DEACTIVATED this account.")

        elif action == 'new':
            user_account.account_status = 'NEW'
            user_account.save()
            messages.success(request, "Successfully REACTIVATED this account.")

        # Preserve all query parameters after action
        params = request.GET.copy()
        # Remove action and account_id so they don't persist in the URL
        params.pop('action', None)
        params.pop('account_id', None)
        query_string = params.urlencode()
        redirect_url = reverse('admin_manageaccount')
        if query_string:
            redirect_url += f'?{query_string}'
        return redirect(redirect_url)
    
    # Pagination: Show 10 accounts per page
    paginator = Paginator(accounts, 10)
    page = request.GET.get('page')

    try:
        accounts_paginated = paginator.get_page(page)
    except PageNotAnInteger:
        accounts_paginated = paginator.get_page(1)  # If the page is not an integer, show the first page
    except EmptyPage:
        accounts_paginated = paginator.get_page(paginator.num_pages)  # If the page is out of range, show the last page

    total_accounts = accounts.count()
    
    first_user = UserAccounts.objects.order_by("created_when").first()
    earliest_date = first_user.created_when.date() if first_user else localdate()

    
    
    return render(request, 'admin_manageaccount.html', {
        'accounts': accounts_paginated,
        'user_info': user_info,
        'total_accounts': total_accounts,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'page': page,
        'row_number': accounts_paginated.start_index,
        'earliest_date': earliest_date,
        'earliest_year': earliest_date.year,
        'earliest_month': earliest_date.month,
})






@login_checker
@role_required('ADMIN')
def admin_manageaccount_viewprofile(request, account_id):
    # Fetch the account and associated user account details
    account = get_object_or_404(AccountInformation, account_id=account_id)
    user_account = get_object_or_404(UserAccounts, account=account)
    
    # Get the logged-in user's account_id from the session
    logged_in_account_id = request.session.get('account_id')

    # Fetch logged-in user's info using the logged-in account_id
    user_info = get_user_info(logged_in_account_id)
    
    # Format the birthdate to display in the desired format
    formatted_birthdate = DateFormat(account.birth_date).format('Y-m-d')

    return render(request, 'admin_manageaccount_viewprofile.html', {
    'account': account,  # Pass account object to template
    'user_info': user_info,
    'role': user_account.role,  # Pass the role to the template
    'formatted_birthdate': formatted_birthdate,  # Pass formatted birthdate
    'account_status': user_account.account_status  # Pass account status to the template
})
    
   
@login_checker
@role_required('ADMIN')
def admin_createaccount(request):
    # Fetch the account and associated user account details
    account_id = request.session.get('account_id') 
    user_info = get_user_info(account_id)
    if request.method == 'POST':
        # Safely get form values
        role = request.POST.get('role')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '').strip().capitalize()
        middle_name = request.POST.get('middle_name', '').strip().capitalize()
        last_name = request.POST.get('last_name', '').strip().capitalize()
        
        errors = {}

        # Validate middle name
        if not middle_name:
            errors['middle_name'] = "Middle name is required. Use 'N/A' if not applicable."
        elif middle_name.strip().lower() == 'n/a':
            middle_name = 'N/A'  # Normalize to uppercase for consistency


        # Inline validator checks
        try:
            name_validator(first_name)
        except ValidationError as e:
            errors['first_name'] = e.message

        try:
            name_validator(last_name)
        except ValidationError as e:
            errors['last_name'] = e.message

        try:
            middle_name_validator(middle_name)
        except ValidationError as e:
            errors['middle_name'] = e.message

        # Email validation
        if not email:
            errors['email'] = "Please enter email."
        else:
            try:
                validate_email(email)
                if AccountInformation.objects.filter(email=email).exists():
                    errors['email'] = "This email is already used."
            except ValidationError:
                errors['email'] = "Please enter a valid email address."

        # Role validation
        if not role or role == "":
            errors['role'] = "Please choose a role."

        # Preserve form values
        input_values = {
            'role': role,
            'email': email,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
        }

        # If errors, return page with inline messages
        if errors:
            return render(request, 'admin_createaccount.html', {
                'errors': errors,
                'input_values': input_values,
                'user_info': user_info
            })


        # Format role
        if role.upper() == "LIBRARY ASSISTANT":
            role = "LIBRARIAN"
        elif role.upper() == "DEPARTMENT":
            role = "DEPARTMENT"   
        else:
            role = role.upper()

        # Generate username: liraya_0000, liraya_0001, etc.
        latest_account = AccountInformation.objects.filter(username__startswith='liraya_').order_by('-account_id').first()
        if latest_account:
            try:
                last_number = int(latest_account.username.split('_')[1])
            except (IndexError, ValueError):
                last_number = -1
        else:
            last_number = -1

        username = f'liraya_{last_number + 1:04d}'
        raw_password = last_name.lower() 
        hashed_password = make_password(raw_password)
        

        try:
            # Create AccountInformation record
            new_account = AccountInformation.objects.create(
                email=email,
                username=username,
                password=hashed_password,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                birth_date='2000-01-01',
                gender='',
                contact_num='0000000000',
                house_no='',
                street_village='',
                barangay='',
                city_municipality='',
                province='',
                zipcode='0000',
                state='',
            )

            # Create UserAccounts record
            UserAccounts.objects.create(
                account=new_account,
                role=role,
                account_status='NEW',
                previous_status='NEW',
                created_by_id=account_id,
            )

            # Compose HTML email
            html_content = f"""
            <html>
              <body style="background-color:#f4f4f4; padding:30px; font-family:Arial, sans-serif;">
                <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1); text-align:center;">
                  <div style="margin-bottom: 3px;">
                    <img src="https://cdn-icons-png.flaticon.com/128/9428/9428893.png" alt="Confetti Icon" width="45" style="margin-bottom: -3px;" />
                  </div>
                  <h1 style="color:#561c24; font-size: 42px; font-weight:900; margin: 0px;">LIRAYA</h1>
                  <h3 style="color:#333; margin-top: 10px;">Your account has been successfully registered!</h3>
                  <p style="color:#555;">
                    You can now log in and access your <strong style="color:#555;">LIRAYA</strong> dashboard.<br>
                    <span style="color:#555;">You are required to change your password and update your profile information upon first login.</span>
                  </p>
                  
                  <div style="margin:20px 0; padding:15px; background-color:#f9f9f9; border:1px dashed #ccc; border-radius:5px;">
                    <p style="font-size:13px;">
                        <strong>USERNAME:</strong>
                        <strong style="color:#561c24; font-size:18px;">{username}</strong>
                    </p>
                    <p style="font-size:13px;">
                        <strong>PASSWORD:</strong>
                        <strong style="color:#561c24; font-size:18px;">{raw_password}</strong>
                    </p>
                  </div>

                  <a href="https://www.tupcliraya.site/login/" style="display:inline-block; margin-top:10px; padding:10px 20px; background-color:#561c24; color:white; text-decoration:none; border-radius:5px;">Log in Now</a>

                  <hr style="margin:30px 0;">
                  <p style="font-size:12px; color:#777;">
                    <strong style="color:#561c24;">LIRAYA's</strong> Terms and Conditions are aligned with the principles of the 
                    <a href="https://privacy.gov.ph/data-privacy-act/" target="_blank" style="color:#561c24; text-decoration: none;">
                        <strong>Data Privacy Act of 2012 (RA 10173)</strong>
                    </a>. By using LIRAYA, you agree to the collection, use, and protection of your personal information in accordance with Philippine data privacy laws.
                  </p>
                </div>
              </body>
            </html>
            """

            # Send email
            email_message = EmailMultiAlternatives(
                subject='Your LIRAYA Account Has Been Registered',
                body='This is an HTML email. Please view this in an HTML-compatible email viewer.',
                from_email='lirayaautomated@gmail.com',
                to=[email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()

            messages.success(request, f"Account for {email} was successfully created!")
            return redirect('admin_createaccount')


        except IntegrityError:
            errors['email'] = "This email is already used."
            return render(request, 'admin_createaccount.html', {
                'errors': errors,
                'input_values': input_values,
                'user_info': user_info  
            })

    # For GET request
    return render(request, 'admin_createaccount.html', {'user_info': user_info}) 


def admin_templateinheritance(request):
    return render (request, 'admin_inheritance.html')

@login_checker
@role_required('ADMIN')
def redirect_to_profile(request):
    # You can add any additional logic here if needed
    return redirect('admin_profile')  # This will redirect to the 'admin_profile' view


@login_checker
@role_required('ADMIN')
def admin_profile(request):
    account_id = request.session.get('account_id')  # Try getting account_id from session
    

    if account_id:
        try:
            # Get the account information based on account_id
            account = AccountInformation.objects.get(account_id=account_id)

            # Get the corresponding user account information (role)
            user_account = UserAccounts.objects.get(account=account)  # This gets the role of the user
            
            if request.method == "POST":
                form_type = request.POST.get('form_type')
                
                if form_type == 'profile_update':
                    try:
                        # Handle Profile Update Form Submission

                        # 1. Handle First Name, Middle Name, and Last Name
                        first_name = request.POST.get('first_name')
                        middle_name = request.POST.get('middle_name')
                        last_name = request.POST.get('last_name')
                    

                        # Ensure that none of these fields are blank
                        if not first_name or not first_name.strip():
                            raise ValidationError("First name cannot be blank.")
                        if not last_name or not last_name.strip():
                            raise ValidationError("Last name cannot be blank.")
                            
                        # For middle_name, if it's empty or contains only invalid values, it will be set to None
                        if middle_name:
                            middle_name = middle_name.strip()
                            if middle_name.lower() in ['n/a', 'na', 'na', 'n/a']:
                                middle_name = None
                            else:
                                middle_name = middle_name.title()  # Capitalize first letter of each word
                        else:
                            middle_name = None

                        # Capitalize the first letter of each word for first and last names
                        first_name = first_name.strip().title()
                        last_name = last_name.strip().title()

                        # Update Account Information
                        account.first_name = first_name
                        account.middle_name = middle_name
                        account.last_name = last_name

                        # 2. Handle Address Fields
                        house_no = request.POST.get('house_no')
                        street_village = request.POST.get('street_village')
                        barangay = request.POST.get('barangay')
                        city = request.POST.get('city')
                        province = request.POST.get('province')
                        state = request.POST.get('state')

                        # Ensure that none of the address fields are blank
                        if not house_no or not house_no.strip():
                            raise ValidationError("House number cannot be blank.")
                        if not street_village or not street_village.strip():
                            raise ValidationError("Street or village cannot be blank.")
                        if not city or not city.strip():
                            raise ValidationError("City cannot be blank.")
                        if not barangay or not barangay.strip():
                            raise ValidationError("Barangay cannot be blank.")
                        if not province or not province.strip():
                            raise ValidationError("Province cannot be blank.")
                        if not state or not state.strip():
                            raise ValidationError("State cannot be blank.")
                        if any(char.isdigit() for char in state):
                            raise ValidationError("State must be a valid string and cannot contain numbers.")

                        # Ensure all are strings and trimmed, with proper length
                        account.house_no = str(house_no).strip()[:20]  # Truncate to max length 20
                        account.street_village = str(street_village).strip()[:100]  # Max length 100
                        account.city_municipality = str(city).strip()[:100]
                        account.barangay = str(barangay).strip()[:100]
                        account.province = str(province).strip()[:100]
                        account.state = str(state).strip()[:100]

                        # 3. Handle Zipcode (Only integers, between 0100 and 9811)
                        zipcode = request.POST.get('zipcode')
                        
                        if zipcode and re.match(r'^\d{4}$', zipcode) and 100 <= int(zipcode) <= 9811:
                            account.zipcode = zipcode
                        else:
                            raise ValidationError("Invalid Zipcode. It should be a 4-digit number between 0100 and 9811.")
                        
                        # Handle Birthdate (18+ age validation)
                        birthdate = request.POST.get('birthdate')

                        # Check if birthdate is provided
                        if not birthdate:  
                            raise ValidationError("Birthdate is required.")

                        # Proceed with parsing the date
                        try:
                            birth_date = datetime.strptime(birthdate, '%Y-%m-%d').date()  # Parse the birthdate
                        except ValueError:
                            raise ValidationError("Invalid birthdate format. Please use YYYY-MM-DD.")

                        # Calculate the age based on the birthdate
                        today = date.today()
                        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                        
                        
                        # Validate age (18+ and 80-)
                        if age < 18:
                            raise ValidationError("You must be at least 18 years old to register.")
                        elif age > 80:
                            raise ValidationError("You must be 80 years old or younger to register.")
                        
                        # If the age is valid, save the birthdate
                        account.birth_date = birth_date

                        # 5. Handle Gender (Valid options: Male, Female, Other)
                        gender = request.POST.get('gender')
                        # Ensure gender is selected (not empty)
                        if not gender:
                            raise ValidationError("Please select a valid gender.")
                        elif gender not in ['Male', 'Female', 'Other']:
                            raise ValidationError("Please select a valid gender.")
                        # Save the gender to the account
                        account.gender = gender


                        # 6. Handle Email (Must be a valid email address)
                        email = request.POST.get('email')
                        
                        try:
                            EmailValidator()(email)  # Use Django's email validator
                            account.email = email
                        except ValidationError:
                            raise ValidationError("Invalid email address.")

                        # 7. Handle Contact Number (Must be 11 digits, starting with 09)
                        # Retrieve the contact number from the form submission
                        contact_num = request.POST.get('contact_num')

                        # Check if contact_num is not None or empty before applying regex
                        if contact_num:
                            # Regex check: Validate the format of the contact number
                            if re.match(r'^09\d{9}$', contact_num):      
                                # If valid, save it to the account
                                account.contact_num = contact_num
                            else:
                                raise ValidationError("Invalid contact number. It must be 11 digits and start with '09'.")
                        else:
                            # Debugging: If no contact number is received
                            raise ValidationError("Contact number is required.")

                        # 8. Handle Username (Check if it exists already)
                        username = request.POST.get('username')
                        
                        
                        # Check if the username contains spaces
                        if ' ' in username:
                            raise ValidationError("Username should not contain spaces. Please choose another.")

                        min_length = 4
                        if len(username) < min_length:
                            raise ValidationError(f"Username must be at least {min_length} characters long. Please choose another.")
                        

                        if username != account.username:
                            # If the username has changed, check if it already exists in the database
                            if AccountInformation.objects.filter(username=username).exists():
                                raise ValidationError("This username is already taken. Please choose another.")
                            
                            # If the username is unique, update the account's username
                            account.username = username
                        

                        # Save the updated account information to the database
                        account.save()
                        messages.success(request, "Profile updated successfully.")

                    except ValidationError as ve:
                        logger.error(f"ValidationError occurred: {ve}")
                        # Log the full traceback
                        logger.error(traceback.format_exc())
                        messages.error(request, f"Error: {ve}")
                    
                    except Exception as e:
                        logger.error(f"An unexpected error occurred: {e}")
                        # Log the full traceback
                        logger.error(traceback.format_exc())
                        messages.error(request, "An unexpected error occurred. Please try again later.")
            
                elif form_type == 'image_upload':
                    cropped_image_data = request.POST.get('cropped_image')
                
                    if cropped_image_data:
                        try:
                            # Extract the base64 image data
                            format, imgstr = cropped_image_data.split(';base64,')  # Split the header and the data part
                            ext = format.split('/')[-1]  # Get the file extension (e.g., jpeg, png)
                
                            # Decode the base64 image
                            img_data = base64.b64decode(imgstr)
                            img_file = ContentFile(img_data, name=f"{account.account_id}-{account.first_name}-{account.last_name}.{ext}")
                
                            # Check and remove the old image from Cloudinary if exists
                            if account.profile_picture:
                                public_id = account.profile_picture.name.split('/')[-1].split('.')[0]
                                uploader.destroy(public_id)
                
                            # Upload the new image to Cloudinary
                            cloudinary_response = uploader.upload(img_file)
                
                            # Save the Cloudinary URL (secure_url) to the model and save the account
                            account.profile_picture = cloudinary_response['secure_url']  # Save the full URL
                            account.save()
                
                            messages.success(request, "Profile picture updated successfully.")
                
                        except Exception as e:
                            logger.error(f"Error uploading image to Cloudinary: {e}")
                            messages.error(request, "Error uploading profile picture. Please try again.")
                            return redirect('admin_profile')
                    else:
                        messages.error(request, "No image data provided.")
                        return redirect('admin_profile')
                        
                        
                elif form_type == 'password_change':
                    try:
                        # Handle password change form submission
                        current_password = request.POST.get('current_password')
                        new_password = request.POST.get('new_password')
                        confirm_password = request.POST.get('confirm_password')

                        # 1st Check: verify current password against stored hash
                        if not check_password(current_password, account.password):
                            messages.error(request, "Incorrect current password.")
                        else:
                            # 2nd Check: New password not same as current
                            if check_password(new_password, account.password):
                                messages.error(request, "New password cannot be the same as the current password.")
                            # 3rd Check: New password meets the requirements
                            elif len(new_password) < 6:
                                messages.error(request, "Password must be at least 6 characters long.")
                            # 4th Check: New password == confirm password
                            elif new_password != confirm_password:
                                messages.error(request, "New password and confirm password do not match.")
                            else:
                                # Hash and save the new password
                                account.password = make_password(new_password)
                                account.save()
                                # Keep session valid after password change (optional)
                                try:
                                    update_session_auth_hash(request, account)
                                except Exception:
                                    pass
                                messages.success(request, "Password updated successfully.")
                                
                    except Exception as e:
                        # Log any exception that occurs
                        logger.error(f"Error during password change: {str(e)}", exc_info=True)
                        messages.error(request, "An error occurred while changing the password.")
                        
                return redirect('admin_profile')  # Redirect after processing the form

            # Format birth_date as YYYY-MM-DD
            formatted_birthdate = DateFormat(account.birth_date).format('Y-m-d')

            context = {
                'account': account,  # Pass the account data to the template
                'role': user_account.role,  # Pass the role data to the template
                'formatted_birthdate': formatted_birthdate  # Pass the formatted birthdate
            }
            return render(request, 'admin_profile.html', context)
        except AccountInformation.DoesNotExist:
            return redirect('login')  # Redirect to login page if account doesn't exist
        except UserAccounts.DoesNotExist:
            return redirect('login')  # Redirect to login page if the user account does not exist
    else:
        return redirect('login')  # Redirect to login page if account_id is not found

@login_checker
@role_required('ADMIN')
def admin_records(request):
    account_id = request.session.get('account_id') 
    user_info = get_user_info(account_id)
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'all')  # Default sorting set to 'all'
    page_number = request.GET.get('page', 1)  # Current page

    # Get role filter parameter, default to 'all'
    role_filter = request.GET.get('role', 'all')

    # Initialize queryset with librarian and department accounts
    librarian_accounts = UserAccounts.objects.filter(
        role__in=['LIBRARIAN', 'DEPARTMENT']
    ).order_by('account__account_id')

    # Get separate counts for librarians and departments
    total_librarian = UserAccounts.objects.filter(role='LIBRARIAN').count()
    total_department = UserAccounts.objects.filter(role='DEPARTMENT').count()

    # Apply role filter if specified
    if role_filter != 'all':
        librarian_accounts = librarian_accounts.filter(role=role_filter)

    # Apply search query filter
    if search_query:
        librarian_accounts = librarian_accounts.filter(
            Q(account__first_name__icontains=search_query) |
            Q(account__middle_name__icontains=search_query) |
            Q(account__last_name__icontains=search_query)
        )
    
    # Count of currently filtered accounts
    total_accounts = librarian_accounts.count()
    
    # Sorting logic
    if sort_by == 'name_asc':
        librarian_accounts = librarian_accounts.order_by('account__first_name', 'account__middle_name', 'account__last_name')
    elif sort_by == 'name_desc':
        librarian_accounts = librarian_accounts.order_by('-account__first_name', '-account__middle_name', '-account__last_name')
    elif sort_by == 'books_asc':
        librarian_accounts = librarian_accounts.annotate(book_count=Count('account__books')).order_by('book_count')
    elif sort_by == 'books_desc':
        librarian_accounts = librarian_accounts.annotate(book_count=Count('account__books')).order_by('-book_count')
    elif sort_by == 'all':  # Default sorting (no sorting applied)
        librarian_accounts = librarian_accounts  # No order_by() applied)
  
    # Paginate the results: 10 accounts per page
    paginator = Paginator(librarian_accounts, 10)
    page_obj = paginator.get_page(page_number)

    # Prepare the data for display
    records = []
    for index, user_account in enumerate(page_obj.object_list, start=page_obj.start_index()):
        librarian = user_account.account
        full_name = f"{librarian.first_name} {librarian.middle_name[0] if librarian.middle_name else ''} {librarian.last_name}".strip()
        books_uploaded = Books.objects.filter(account=librarian, is_archived=False).count()
        records.append({
            'index': index,
            'full_name': full_name,
            'books_uploaded': books_uploaded,
            'account': librarian,  # Ensure account is included in the context
        })

    return render(request, 'admin_records.html', {
        'records': records,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'role_filter': role_filter,     # Add role_filter to the template context
        'total_librarian': total_librarian,    # Total librarian accounts
        'total_department': total_department,   # Total department accounts
        'total_accounts': total_accounts,       # Combined total of both roles
        'user_info': user_info,
    })

@login_checker
@role_required('ADMIN')
def admin_records_view(request, account_id):
    # Get the logged-in user's account_id from the session
    logged_in_account_id = request.session.get('account_id')

    # Fetch logged-in user's info using the logged-in account_id
    user_info = get_user_info(logged_in_account_id)
    # Retrieve the librarian's account using the account_id from the URL
    librarian_account = get_object_or_404(UserAccounts, account_id=account_id)

    # Get the full name (First Name, Middle Initial, Last Name)
    full_name = f"{librarian_account.account.first_name} {librarian_account.account.middle_name[0] if librarian_account.account.middle_name else ''} {librarian_account.account.last_name}"

    # Get the librarian's role
    role = librarian_account.role

    # Get all books uploaded by the librarian
    books = Books.objects.filter(account=librarian_account.account, is_archived=False)

    # Handle search query
    search_query = request.GET.get('search', '')
    if search_query:
        books = books.filter(title__icontains=search_query)

    # Handle sort query
    sort_by = request.GET.get('sort', 'all')
    if sort_by == 'all':
        books = books.order_by('book_id')
    elif sort_by == 'oldest_to_newest':
        books = books.order_by('year_of_publication')
    elif sort_by == 'newest_to_oldest':
        books = books.order_by('-year_of_publication')
    elif sort_by == 'az':
        books = books.order_by('title')
    elif sort_by == 'za':
        books = books.order_by('-title')

    # Pagination setup
    paginator = Paginator(books, 10)  # Show 10 books per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Prepare the data for display
    books_data = []
    for book in page_obj.object_list:
        books_data.append({
            'title': book.title,
            'author': book.author,
            'year_of_publication': book.year_of_publication,
            'primary_keyword': book.primary_keyword,
            'book_cover': book.book_cover if book.book_cover else None,
            'book_id': book.book_id,  # Correctly accessing the primary key
        })

    # Render the template with the librarian's info and books data
    return render(request, 'admin_records_view.html', {
        'librarian_account': librarian_account,
        'full_name': full_name,
        'role': role,
        'total_books_uploaded': books.count(),
        'books': books_data,
        'search_query': search_query,
        'sort_by': sort_by,
        'page_obj': page_obj,
        'user_info': user_info,
    })



def admin_logout(request):
    # Clear session data to log out the user
    request.session.flush()  # This ensures all session data is cleared

    # Add cache control headers to prevent the browser from caching the page
    response = redirect('login')  # Redirect to the login page
    
    # Prevent browser from caching the page
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Prevent caching
    response['Pragma'] = 'no-cache'  # Older HTTP/1.0 cache control
    response['Expires'] = '0'  # Set expiry date to a past time to prevent caching

    # Make sure the session is properly cleared (for good measure)
    logout(request)  # This will log out the user by clearing the session and user data

    # Redirect to the login page
    return response


def check_username(request):
    username = request.GET.get('username')
    exists = AccountInformation.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})
    
def deactivate_account(request):
    account_id = request.session.get('account_id')

    if account_id:
        try:
            account = AccountInformation.objects.get(account_id=account_id)
            user_account = UserAccounts.objects.get(account=account)
            
            # Update the account status to DEACTIVATED
            user_account.account_status = 'DEACTIVATED'
            user_account.previous_status = user_account.account_status  # Store the previous status
            user_account.save()

            # Log out the user and flush session data
            logout(request)

            # Redirect to login page with success message
            messages.success(request, "Your account has been deactivated successfully.")
            return redirect('login')  # Redirect to the login page

        except AccountInformation.DoesNotExist:
            messages.error(request, "Account not found.")
            return redirect('login')  # Redirect to login page
        except UserAccounts.DoesNotExist:
            messages.error(request, "User account details not found.")
            return redirect('login')  # Redirect to login page
    else:
        messages.error(request, "No session found. Please log in first.")
        return redirect('login')  # Redirect to login page





#----------------------------- GENERATE PDF FUNCTIONS -----------------------------#

DATA_FLOOR = date(2025, 9, 1)

def _clamp_date(d: date) -> date:
    today = date.today()
    if d < DATA_FLOOR: return DATA_FLOOR
    if d > today:      return today
    return d

def _resolve_date_window(request):
    """
    Returns (start_date, end_date, range_label)
    Respects: date_mode = week|month|year|all, week_ref, month, year.
    """
    today = date.today()
    mode = request.GET.get('date_mode', 'all')

    def label(d1, d2):
        if d1.year == d2.year and d1.month == d2.month:
            return f"{d1.strftime('%b')} {d1.day}–{d2.day}, {d2.year}"
        return f"{d1.strftime('%b %d, %Y')} – {d2.strftime('%b %d, %Y')}"

    if mode == 'week':
        ref_str = request.GET.get('week_ref')  # YYYY-MM-DD
        ref = datetime.strptime(ref_str, "%Y-%m-%d").date() if ref_str else today
        end_d = _clamp_date(ref)
        start_d = _clamp_date(end_d - timedelta(days=6))
        return start_d, end_d, label(start_d, end_d)

    elif mode == 'month':
        m = request.GET.get('month')
        y = request.GET.get('year')
        year = int(y) if y else today.year
        month = int(m) if m else today.month
        start_d = _clamp_date(date(year, month, 1))
        last = date(year, 12, 31) if month == 12 else (date(year, month + 1, 1) - timedelta(days=1))
        end_d = _clamp_date(last)
        return start_d, end_d, f"{start_d.strftime('%b %Y')}"

    elif mode == 'year':
        y = request.GET.get('year')
        year = int(y) if y else today.year
        start_d = _clamp_date(date(year, 1, 1))
        end_d   = _clamp_date(date(year, 12, 31))
        if year == today.year:
            end_d = _clamp_date(today)
        return start_d, end_d, f"{year}"

    else:  # all time
        start_d = DATA_FLOOR
        end_d   = _clamp_date(today)
        return start_d, end_d, "All time"

def _apply_account_filters(qs, request):
    """Mirror your page filters only if 'use_filters' is truthy."""
    use_filters = request.GET.get('use_filters') in ('1', 'true', 'True', 'on')
    if not use_filters:
        return qs

    search = request.GET.get('search', '').strip()
    role   = request.GET.get('role', 'all')
    status = request.GET.get('status', 'all')
    sort   = request.GET.get('sort', 'all')

    if search:
        qs = qs.filter(
            Q(account__first_name__icontains=search) |
            Q(account__middle_name__icontains=search) |
            Q(account__last_name__icontains=search)
        )

    if role and role != 'all':
        qs = qs.filter(role=role.upper())

    if status and status != 'all':
        qs = qs.filter(account_status=status.upper())

    if sort == 'az':
        qs = qs.order_by('account__first_name')
    elif sort == 'za':
        qs = qs.order_by('-account__first_name')

    return qs

def _get_requester_identity(request):
    acct_id = request.session.get('account_id')
    if not acct_id:
        return {"full_name": "Unknown", "role": "Unknown"}
    try:
        acct = AccountInformation.objects.get(pk=acct_id)
        ua   = UserAccounts.objects.filter(account=acct).first()
        full_name = f"{acct.first_name} {acct.middle_name + ' ' if acct.middle_name else ''}{acct.last_name}"
        role = ua.role if ua else "Unknown"
        return {"full_name": full_name, "role": role}
    except AccountInformation.DoesNotExist:
        return {"full_name": "Unknown", "role": "Unknown"}


# Thresholds you can tune
ONBOARDING_GRACE_DAYS = 7
LIBRARIAN_INACTIVE_DAYS = 14
GOOD_UPLOADS_7D = 3
LOW_UPLOADS_7D = 1

def generate_pdf(request, report_type):
    
    account_details, error = get_account_details(request)
    if error:
        return error
    
    first_name, middle_name, last_name, role = account_details
    date_range = request.GET.get('date_range', 'all_time')

    # Define user info here - using Philippines timezone (Asia/Manila)
    philippines_timezone = pytz.timezone('Asia/Manila')
    philippines_now = timezone.now().astimezone(philippines_timezone)

    user_info = {
        'full_name': f"{first_name} {middle_name} {last_name}".strip(),
        'role': role,
        'time_generated': philippines_now.strftime("%I:%M:%S %p"),  # 12-hour format with AM/PM
        'date_generated': philippines_now.strftime("%B %d, %Y"),
    }
    
    pdf_buffer = BytesIO()

    tz_now = timezone.localtime(timezone.now())
    today  = tz_now.date()

    if report_type == 'account_information':
        # --- Inputs ---
        start_d, end_d, range_label = _resolve_date_window(request)
        mode_with_biodata = request.GET.get('include_biodata') in ('1', 'true', 'True', 'on')

        requester = _get_requester_identity(request)

        # --- Account set (optionally filtered like the table) ---
        qs_accounts = UserAccounts.objects.select_related('account')
        qs_accounts = _apply_account_filters(qs_accounts, request)

        # 🔥 THIS is where you should insert filtering
        qs_accounts = qs_accounts.filter(created_when__date__lte=end_d)

        # --- Window-wide aggregation (used for summary and some per-user KPIs) ---
        uploads_window = Books.objects.filter(
            date_uploaded__gte=start_d,
            date_uploaded__lte=end_d
        )
        uploads_in_window = uploads_window.count()
        active_uploaders_in_window = uploads_window.values('account').distinct().count()

        total_accounts = qs_accounts.count()

        # ✅ Correct aggregation: roles and status
        by_role = dict(
            qs_accounts.values('role')
            .annotate(n=Count('role'))
            .values_list('role', 'n')
        )
        by_status = dict(
            qs_accounts.values('account_status')
            .annotate(n=Count('account_status'))
            .values_list('account_status', 'n')
        )

        created_in_window = qs_accounts.filter(
            created_when__date__gte=start_d,
            created_when__date__lte=end_d
        ).count()

        # --- Per-account KPIs + remarks
        # IMPORTANT: always build this payload so summary tables have data,
        # even when we are NOT rendering biodata cards.
        accounts_payload = []
        for ua in qs_accounts:
            ai = ua.account

            # profile picture absolute path (if any) — harmless if unused
            pp_url = ai.profile_picture if ai.profile_picture else None

            created_dt = ua.created_when
            created_on = created_dt.date() if created_dt else None
            days_old   = (min(end_d, today) - created_on).days if created_on else None

            # uploads lifetime + in windows
            lifetime_uploads = Books.objects.filter(account=ai).count()

            uploads_7d  = Books.objects.filter(
                account=ai,
                date_uploaded__gt=end_d - timedelta(days=7),
                date_uploaded__lte=end_d
            ).count()

            uploads_14d = Books.objects.filter(
                account=ai,
                date_uploaded__gt=end_d - timedelta(days=14),
                date_uploaded__lte=end_d
            ).count()

            uploads_user_window = uploads_window.filter(account=ai).count()
            user_uploads_q = uploads_window.filter(account=ai)

            THESIS_RE = r'(thesis|dissertation|capstone)'
            thesis_q = Q(book_type__iregex=THESIS_RE) | Q(scanned_type__iregex=THESIS_RE)

            thesis_in_window = user_uploads_q.filter(thesis_q).count()
            books_in_window  = user_uploads_q.exclude(thesis_q).count()

            active_days_in_window = Books.objects.filter(
                account=ai,
                date_uploaded__gte=start_d,
                date_uploaded__lte=end_d
            ).values('date_uploaded').distinct().count()

            last_upload = Books.objects.filter(account=ai).aggregate(m=Max('date_uploaded'))['m']
            days_since_last_upload = (end_d - last_upload).days if last_upload else None

            # basic address (used in biodata card only)
            addr = ", ".join(filter(None, [
                ai.house_no,
                ai.street_village,
                ai.barangay,
            ]))

            # age (used in biodata card only)
            age_years = None
            if ai.birth_date:
                age_years = today.year - ai.birth_date.year - (
                    (today.month, today.day) < (ai.birth_date.month, ai.birth_date.day)
                )

            # created by (admin who created this)
            created_by_name = "—"
            if ua.created_by:
                cb = ua.created_by
                created_by_name = f"{cb.first_name} {cb.middle_name + ' ' if cb.middle_name else ''}{cb.last_name}"

            # --- Role-specific rule-based remark ---
            remark = ""
            role_upper = (ua.role or "").upper()
            status_upper = (ua.account_status or "").upper()

            # initialize admin-specific counters
            created_count = 0
            created_fullnames = []
            still_new_over7 = 0

            if role_upper == "LIBRARIAN":
                if status_upper == "NEW" and (days_old or 0) >= ONBOARDING_GRACE_DAYS and uploads_7d == 0:
                    remark = ("NEW for ≥7 days with 0 uploads in last 7 days → "
                              "consider deactivation or follow-up / training.")
                elif status_upper == "ACTIVE" and uploads_14d == 0:
                    remark = (f"ACTIVE but 0 uploads in last {LIBRARIAN_INACTIVE_DAYS} days → "
                              "check in with the librarian.")
                elif uploads_7d >= GOOD_UPLOADS_7D:
                    remark = (f"Good momentum: {uploads_7d} upload(s) in last 7 days. "
                              "Consider recognizing performance.")
                elif uploads_7d <= LOW_UPLOADS_7D:
                    remark = (f"Low activity: {uploads_7d} upload(s) in last 7 days. "
                              "Offer support or clarify targets.")
                else:
                    remark = "Steady activity."
            else:  # ADMIN (or other roles)
                created_qs = UserAccounts.objects.filter(
                    created_by=ai,
                    created_when__date__gte=start_d,
                    created_when__date__lte=end_d
                ).select_related('account')

                created_count = created_qs.count()
                created_fullnames = []
                for ua_new in created_qs:
                    acc = ua_new.account
                    mi  = (acc.middle_name + ' ') if acc.middle_name else ''
                    created_fullnames.append(f"{acc.first_name} {mi}{acc.last_name}")

                still_new_over7 = created_qs.filter(
                    role__iexact='LIBRARIAN',
                    account_status__iexact='NEW',
                    created_when__lte=end_d - timedelta(days=ONBOARDING_GRACE_DAYS)
                ).count()

                if still_new_over7:
                    remark = (f"{created_count} account(s) created this period; "
                              f"{still_new_over7} librarian(s) still NEW ≥7 days → "
                              "follow up on onboarding.")
                elif created_count:
                    remark = f"{created_count} account(s) created this period."
                elif uploads_user_window:
                    remark = f"No new accounts; {uploads_user_window} upload(s) this period."
                else:
                    remark = "No administrative actions or uploads recorded this period."

            # --- Build payload ---
            bio_payload = {
                "full_name": f"{ai.first_name} {ai.middle_name + ' ' if ai.middle_name else ''}{ai.last_name}",
                "role": ua.role,
                "status": ua.account_status,
                "username": ai.username,
                "email": ai.email,
                "profile_picture_url": pp_url,
                "birth_date": ai.birth_date.isoformat() if ai.birth_date else "—",
                "age_years": age_years,
                "contact": ai.contact_num,
                "address": addr,
                "zipcode": ai.zipcode,
                "gender": getattr(ai, "gender", "—"),
                "city": ai.city_municipality,
                "province": ai.province,
                "state": ai.state,
                "created_on": created_on.isoformat() if created_on else "—",
                "created_at": created_on.isoformat() if created_on else "—",  # for _deactivation_recommendations()
                "days_old": days_old,
                "created_by": created_by_name,
                "last_upload": last_upload.isoformat() if last_upload else "—",
            }

            perf_payload = {
                "uploads_7d": uploads_7d,
                "uploads_14d": uploads_14d,
                "active_days_in_window": active_days_in_window,
                "days_since_last_upload": days_since_last_upload,
                "uploads_in_window": uploads_user_window,
                "lifetime_uploads": lifetime_uploads,
                "thesis_in_window": thesis_in_window,
                "books_in_window":  books_in_window,
                "days_since_created": (end_d - created_on).days if created_on else None,
                # Admin fields:
                "created_in_window": created_count if role_upper == "ADMIN" else 0,
                "created_accounts_fullnames": created_fullnames if role_upper == "ADMIN" else [],
                "created_accounts_list": list(
                    UserAccounts.objects.filter(
                        created_by=ai,
                        created_when__date__gte=start_d,
                        created_when__date__lte=end_d
                    ).values_list("account__last_name", flat=True)
                ) if role_upper == "ADMIN" else [],
                "remark": remark,
            }

            # If you want to slim payload when summary_only, you could drop
            # heavy fields here, but it's optional/safe to keep them.
            accounts_payload.append({"bio": bio_payload, "performance": perf_payload})

        # --- Assemble context for the PDF ---
        context = {
            "meta": {
                "title": "Account Information Report",
                "about": "Detailed account information and performance within the selected range.",
                "generated_by": requester["full_name"],
                "generated_by_role": requester["role"],
                "generated_at": tz_now.strftime("%I:%M %p"),
                "range_label": range_label,
                "start_date": start_d.isoformat(),
                "end_date": end_d.isoformat(),
                "mode": "with_biodata" if mode_with_biodata else "summary_only",
                "filters_used": request.GET.get('use_filters') in ('1','true','True','on'),
            },
            "summary": {
                "totals": {
                    "accounts": total_accounts,
                    "roles": by_role,
                    "status": by_status,
                    "accounts_created_in_window": created_in_window,
                    "uploads_in_window": uploads_in_window,
                    "active_uploaders_in_window": active_uploaders_in_window,
                },
            },
            "accounts": accounts_payload,  # <-- ALWAYS populated now
        }

        # Render
        generate_account_information(pdf_buffer, context)
        file_name = 'Liraya_AccountInformation_Report.pdf'
        
    elif report_type == 'book_details':
        admin_generatebookdetails_pdf(pdf_buffer, request.GET.get('book_id'), user_info)  # Pass user info to report generation
        file_name = 'Liraya_BookDetails_Report.pdf'

    elif report_type == 'account_bookrecords':
        # Build params from the modal form in admin_records.html
        period_type = (request.GET.get('period_type') or 'today').strip()
        date_range_params = {
            'period_type': period_type,
            'days': request.GET.get('days'),
            'weeks': request.GET.get('weeks'),
            'months': request.GET.get('months'),
            'years': request.GET.get('years'),
            'start_date': request.GET.get('start_date'),
            'end_date': request.GET.get('end_date'),
        }

        admin_generate_accountbookrecords(pdf_buffer, date_range_params, user_info)
        file_name = 'Liraya_AccountBookRecords_Report.pdf'
    
    elif report_type == 'keyword_search_history':
        # Uses only KeywordLog fields
        # Normalize filter
        tf_raw = request.GET.get('timeFilter', 'all')
        tf_key = tf_raw.strip().lower().replace(' ', '').replace('_', '').replace('-', '')
        tf = (
            'last24hours' if tf_key in ('last24hours', 'last24h', '24h') else
            'last7days' if tf_key in ('last7days', '7d') else
            'last30days' if tf_key in ('last30days', '30d') else
            # REMOVED: last12months
            'lastmonth' if tf_key in ('lastmonth',) else
            'lastyear' if tf_key in ('lastyear',) else
            'all'
        )
    
        end_dt = timezone.localtime(timezone.now())    # window end (local)
        tz_now = end_dt                                # for "generated_at"
    
        logs_qs = KeywordLog.objects.all()
    
        # ---------- helpers ----------
        def _to_aware(dt):
            """Return an aware datetime in current TZ, or None."""
            if dt is None:
                return None
            if isinstance(dt, str):
                # parse "YYYY-MM-DD HH:MM:SS[.ffffff]" safely
                try:
                    dt = datetime.fromisoformat(dt.strip())
                except Exception:
                    return None
            if not isinstance(dt, datetime):
                return None
            if timezone.is_naive(dt):
                try:
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                except Exception:
                    dt = timezone.make_aware(dt)  # default
            return dt
    
        def _lt(dt):
            """localtime wrapper that tolerates strings/naive values."""
            adt = _to_aware(dt)
            return timezone.localtime(adt) if adt else None
    
        # Choose the ACTIVITY timestamp field (for Figure 1 totals).
        # Only pick fields that are actually DateTimeField.
        field_map = {f.name: f for f in KeywordLog._meta.get_fields() if hasattr(f, 'get_internal_type')}
        def _is_dt(name): 
            f = field_map.get(name)
            return isinstance(f, DateTimeField) or (getattr(f, 'get_internal_type', lambda: '')() == 'DateTimeField')
    
        for_name_order = ('search_times', 'updated_at', 'created_at')
        activity_field = next((n for n in for_name_order if _is_dt(n)), 'created_at')
    
        # ---- Build X-axis buckets and counts (Figure 1 + Figure 2) ----
        def _bucket_data(qs, tf, end_dt):
            """
            Returns:
            labels: list[str]
            counts_total: list[int]       (Figure 1: sum of user_search_count by ACTIVITY time)
            counts_new: list[int]         (Figure 2: NEW keywords by created_at; distinct keyword_id)
            start_dt: datetime
            end_used: datetime
            """
            labels, counts_total, counts_new = [], [], []
            start_dt = None
            end_used = end_dt
    
            # ---------- All Time (quartiles) ----------
            if tf == 'all':
                # Use created_at for start, ACTIVITY field for end
                agg = qs.aggregate(first=Min('created_at'), last=Max(activity_field))
                first_dt = _lt(agg['first'])
                last_dt  = _lt(agg['last'])
                labels = ['Earliest', '2nd Quarter', '3rd Quarter', 'Latest']
    
                if not first_dt or not last_dt:
                    return labels, [0, 0, 0, 0], [0, 0, 0, 0], end_dt, end_dt
    
                start_dt = first_dt
                end_used = last_dt
                span = end_used - start_dt
                if span.total_seconds() <= 0:
                    total_searches = int(qs.aggregate(total=Sum('user_search_count'))['total'] or 0)
                    new_ids = set(qs.values_list('keyword_id', flat=True))
                    return labels, [total_searches, 0, 0, 0], [len(new_ids), 0, 0, 0], start_dt, end_used
    
                q1_end = start_dt + span / 4
                q2_end = start_dt + span / 2
                q3_end = start_dt + (span * 3) / 4
    
                counts_total = [0, 0, 0, 0]
                new_sets = [set(), set(), set(), set()]
    
                for log in qs:
                    ts = _lt(getattr(log, activity_field, None)) or end_used
                    v = int(getattr(log, 'user_search_count', 0) or 0)
                    if ts <= q1_end:
                        counts_total[0] += v
                    elif ts <= q2_end:
                        counts_total[1] += v
                    elif ts <= q3_end:
                        counts_total[2] += v
                    else:
                        counts_total[3] += v
    
                    crt = _lt(getattr(log, 'created_at', None)) or start_dt
                    if crt <= q1_end:
                        new_sets[0].add(log.keyword_id)
                    elif crt <= q2_end:
                        new_sets[1].add(log.keyword_id)
                    elif crt <= q3_end:
                        new_sets[2].add(log.keyword_id)
                    else:
                        new_sets[3].add(log.keyword_id)
    
                counts_new = [len(s) for s in new_sets]
                return labels, counts_total, counts_new, start_dt, end_used
    
            # ---------- Last 24 Hours (4 bands) ----------
            if tf == 'last24hours':
                start_dt = end_dt - timedelta(hours=24)
                labels = ['00:00 - 06:00', '06:00 - 12:00', '12:00 - 18:00', '18:00 - 23:59']
                counts_total = [0, 0, 0, 0]
                new_sets = [set(), set(), set(), set()]
    
                for log in qs.filter(**{f"{activity_field}__gte": start_dt, f"{activity_field}__lte": end_dt}):
                    dt = _lt(getattr(log, activity_field))
                    hr = dt.hour if dt else 0
                    idx = 0 if hr < 6 else 1 if hr < 12 else 2 if hr < 18 else 3
                    counts_total[idx] += int(getattr(log, 'user_search_count', 0) or 0)
    
                for log in qs.filter(created_at__gte=start_dt, created_at__lte=end_dt):
                    dt = _lt(log.created_at)
                    hr = dt.hour if dt else 0
                    idx = 0 if hr < 6 else 1 if hr < 12 else 2 if hr < 18 else 3
                    new_sets[idx].add(log.keyword_id)
    
                return labels, counts_total, [len(s) for s in new_sets], start_dt, end_dt
    
            # ---------- Last 7 Days (Day 1 ... Day 7) ----------
            if tf == 'last7days':
                start_dt = (end_dt - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
                labels = [f'Day {i}' for i in range(1, 8)]
                counts_total = [0] * 7
                new_sets = [set() for _ in range(7)]
    
                for log in qs.filter(**{f"{activity_field}__gte": start_dt, f"{activity_field}__lte": end_dt}):
                    d = (_lt(getattr(log, activity_field)) or end_dt).date()
                    idx = (d - start_dt.date()).days
                    if 0 <= idx <= 6:
                        counts_total[idx] += int(getattr(log, 'user_search_count', 0) or 0)
    
                for log in qs.filter(created_at__gte=start_dt, created_at__lte=end_dt):
                    d = (_lt(log.created_at) or start_dt).date()
                    idx = (d - start_dt.date()).days
                    if 0 <= idx <= 6:
                        new_sets[idx].add(log.keyword_id)
    
                return labels, counts_total, [len(s) for s in new_sets], start_dt, end_dt
    
            # ---------- Last 30 Days (Week 1-4) ----------
            if tf == 'last30days':
                start_dt = end_dt - timedelta(days=30)
                labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
                counts_total = [0, 0, 0, 0]
                new_sets = [set(), set(), set(), set()]
    
                for log in qs.filter(**{f"{activity_field}__gte": start_dt, f"{activity_field}__lte": end_dt}):
                    days_since = ((_lt(getattr(log, activity_field)) or end_dt).date() - start_dt.date()).days
                    idx = 0 if days_since <= 6 else 1 if days_since <= 13 else 2 if days_since <= 21 else 3
                    counts_total[idx] += int(getattr(log, 'user_search_count', 0) or 0)
    
                for log in qs.filter(created_at__gte=start_dt, created_at__lte=end_dt):
                    days_since = ((_lt(log.created_at) or start_dt).date() - start_dt.date()).days
                    idx = 0 if days_since <= 6 else 1 if days_since <= 13 else 2 if days_since <= 21 else 3
                    new_sets[idx].add(log.keyword_id)
    
                return labels, counts_total, [len(s) for s in new_sets], start_dt, end_dt
    
            # ---------- Last Month (previous full month; single bucket) ----------
            if tf == 'lastmonth':
                first_this_month = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                last_month_end = first_this_month - timedelta(seconds=1)
                start_dt = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_used = last_month_end
                labels = [last_month_end.strftime('%B %Y')]
    
                total = int(qs.filter(**{f"{activity_field}__gte": start_dt, f"{activity_field}__lte": end_used})
                            .aggregate(total=Sum('user_search_count'))['total'] or 0)
                new_ids = set(qs.filter(created_at__gte=start_dt, created_at__lte=end_used)
                                .values_list('keyword_id', flat=True))
                return labels, [total], [len(new_ids)], start_dt, end_used
    
            # ---------- Last Year (previous calendar year, Jan-Dec) ----------
            if tf == 'lastyear':
                year = end_dt.year - 1
                start_dt = end_dt.replace(year=year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_used = end_dt.replace(year=year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
                labels = ['January','February','March','April','May','June','July','August','September','October','November','December']
                counts_total = [0] * 12
                new_sets = [set() for _ in range(12)]
    
                for log in qs.filter(**{f"{activity_field}__year": year}):
                    dt = _lt(getattr(log, activity_field))
                    if not dt: 
                        continue
                    counts_total[dt.month - 1] += int(getattr(log, 'user_search_count', 0) or 0)
    
                for log in qs.filter(created_at__year=year):
                    dt = _lt(log.created_at)
                    if not dt:
                        continue
                    new_sets[dt.month - 1].add(log.keyword_id)
    
                return labels, counts_total, [len(s) for s in new_sets], start_dt, end_used
    
            # ---------- Fallback: All Time (single bucket) ----------
            labels = ['All Time']
            total = int(qs.aggregate(total=Sum('user_search_count'))['total'] or 0)
            first_created = _lt(qs.aggregate(first=Min('created_at'))['first']) or end_dt
            last_activity = _lt(qs.aggregate(last=Max(activity_field))['last']) or end_dt
            start_dt = first_created
            end_used = last_activity
            new_ids = set(qs.values_list('keyword_id', flat=True))
            return labels, [total], [len(new_ids)], start_dt, end_used
    
        labels, counts, new_counts, start_dt, end_used = _bucket_data(logs_qs, tf, end_dt)
    
        total = sum(counts) if counts else 0
        total_new = sum(new_counts) if new_counts else 0
    
        start_d = start_dt.date() if isinstance(start_dt, datetime) else end_dt.date()
        end_d = end_used.date() if isinstance(end_used, datetime) else end_dt.date()
        days = max(1, (end_d - start_d).days + 1)
    
        avg = round(total / days, 2) if days else 0.0
        avg_new = round(total_new / days, 2) if days else 0.0
    
        # Build the time-filtered logs for Page 3 using the same window
        if tf == 'all':
            logs_for_page3 = logs_qs.order_by('-updated_at')
        else:
            logs_for_page3 = logs_qs.filter(**{
                f"{activity_field}__gte": start_dt,
                f"{activity_field}__lte": end_used
            }).order_by('-updated_at')
    
        context = {
            "meta": {
                "title": "Keyword Search History Report",
                "about": "Figure 1 shows total keyword searches; Figure 2 shows new keywords.",
                "generated_by": user_info.get("full_name"),
                "generated_by_role": user_info.get("role"),
                "generated_at": tz_now.strftime("%I:%M %p"),
                "range_label": tf,
            },
            "stats": {
                "total_searches": total,
                "start_date": start_d.strftime("%B %d, %Y"),
                "end_date": end_d.strftime("%B %d, %Y"),
                "days": days,
                "average_per_day": avg,
            },
            "chart": {
                "labels": labels,
                "counts": counts,          # Figure 1 buckets
            },
            # --- Figure 2 payload (NEW keywords by created_at) ---
            "stats_new": {
                "total_new_keywords": total_new,
                "start_date": start_d.strftime("%B %d, %Y"),
                "end_date": end_d.strftime("%B %d, %Y"),
                "days": days,
                "average_new_per_day": avg_new,
            },
            "chart_new": {
                "labels": labels,
                "counts": new_counts,      # Figure 2 buckets
            },
    
            # IMPORTANT: pass logs so the PDF generator can build Page 3 aligned with the same window
            "logs": logs_for_page3,
        }
    
        # Build PDF (first page: Figure 1; second page: Figure 2; third page: No-results table)
        generate_keyword_search_history(pdf_buffer, context, user_info)
        file_name = 'Liraya_KeywordSearchHistory_Report.pdf'

        
    else:
        return HttpResponse("Invalid report type.", status=400)

    pdf_buffer.seek(0)
    resp = HttpResponse(pdf_buffer, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return resp


#-------------------------- GET USER DETAILS AT THE TOP --------------------------#
# Function to fetch account details
def get_account_details(request):
    # Get account ID from the session
    account_id = request.session.get('account_id')
    if not account_id:
        return None, HttpResponse("Account not found in session", status=404)
    
    try:
        # Get the specific AccountInformation and UserAccounts
        account = AccountInformation.objects.get(account_id=account_id)
        user_account = UserAccounts.objects.get(account=account)
    except AccountInformation.DoesNotExist:
        return None, HttpResponse("Account not found", status=404)
    except UserAccounts.DoesNotExist:
        return None, HttpResponse("User account not found", status=404)
    
    # Get the user information (first name, middle name, last name, role)
    first_name = user_account.account.first_name.capitalize()
    middle_name = user_account.account.middle_name.capitalize() if user_account.account.middle_name else ''
    last_name = user_account.account.last_name.capitalize()
    role = user_account.role.capitalize()
    
    return (first_name, middle_name, last_name, role), None


#-------------------------- BOOK DETAILS --------------------------#
# New function to generate book details PDF using book_id
def admin_generatebookdetails_pdf(pdf_buffer, book_id, user_info):
    try:
        # Fetch the book details based on the book_id
        book = Books.objects.get(book_id=book_id)
        
        uploaded_account = book.account
        uploaded_full_name = f"{uploaded_account.first_name} {uploaded_account.middle_name or ''} {uploaded_account.last_name}".strip()
        
        # Prepare the dynamic data for the book
        dynamic_data = [
            {
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'co_author': book.co_author or 'N/A',
                'year_of_publication': book.year_of_publication,
                'publisher': book.publisher or 'N/A',
                'primary_keyword': book.primary_keyword,
                'book_cover': book.book_cover.url if book.book_cover else None,
                'book_type': book.book_type,
                'scanned_type': book.scanned_type,
                'scanned_content': book.scanned_content,
                'shelf_category': book.shelf_category,
                'date_uploaded': book.date_uploaded.strftime("%B %d, %Y"),
                'uploaded_account_full_name': uploaded_full_name,
            }
        ]
        
        # Generate the book details 
        file_name = "Liraya_BookDetails_Report.pdf"
        generate_book_details(pdf_buffer, dynamic_data, file_name, user_info)  # Pass user_info as a dictionary
    except Books.DoesNotExist:
        raise HttpResponse("Book not found.", status=404)



#------------------------------ BOOK RECORDS ------------------------------#
def admin_generate_accountbookrecords(pdf_buffer, date_range, user_info):
    try:
        # Apply Philippines timezone for date computations (consistent with other reports)
        philippines_timezone = pytz.timezone('Asia/Manila')
        philippines_now = timezone.now().astimezone(philippines_timezone)
        # Pass the localized 'today' into range resolver so window aligns with PH time
        filter_date, display_range, window_start, window_end = _resolve_bookrecords_range(date_range, today=philippines_now.date())
    
        # Step 2: Fetch uploaders (include LIBRARIAN and DEPARTMENT roles)
        librarian_accounts = UserAccounts.objects.filter(role__in=["LIBRARIAN", "DEPARTMENT"]) 
        
        account_info_data = []
        
        
        # Step 4.1: Get the librarian who uploaded the most and fewest books
        
        
        # Step 3: Iterate over each librarian and gather their data
        for librarian in librarian_accounts:
            account_obj = librarian.account  # Get the associated AccountInformation for each librarian
            
            # Step 3.1: Filter books by the librarian and resolved date window
            # Only count non-archived books to align with UI counts
            base_qs = Books.objects.filter(account=account_obj, is_archived=False)
            # Always prefer the resolved concrete window (window_start/window_end) for consistency with the chart
            if window_start and window_end:
                books_uploaded = base_qs.filter(date_uploaded__gte=window_start, date_uploaded__lte=window_end)
            elif window_start:
                books_uploaded = base_qs.filter(date_uploaded__gte=window_start)
            elif window_end:
                books_uploaded = base_qs.filter(date_uploaded__lte=window_end)
            else:
                books_uploaded = base_qs  # No date filter (all time)

            # Step 3.2: Get the count of books uploaded
            total_books_uploaded = books_uploaded.count()

            # Step 3.3: Get the latest book uploaded date
            latest_book_date = books_uploaded.aggregate(latest_date=Max('date_uploaded'))['latest_date']
            
            # Step 3.4: Add the librarian's data to the list
            account_info_data.append({
                'account_name': f"{account_obj.first_name} {' ' + account_obj.middle_name if account_obj.middle_name else ''} {account_obj.last_name}",
                'role': (librarian.role.title() if getattr(librarian, 'role', None) else 'N/A'),
                'total_books_uploaded': total_books_uploaded,
                'latest_book_date': latest_book_date or 'Not uploaded today',
                'data_range': display_range,
            })


        # Step 4.1: Build librarian-level summary safely (handle empty dataset)
        if account_info_data:
            highest_uploaded_librarians = [l for l in account_info_data if l['total_books_uploaded'] == max(account_info_data, key=lambda x: x['total_books_uploaded'])['total_books_uploaded']]
            lowest_uploaded_librarians = [l for l in account_info_data if l['total_books_uploaded'] == min(account_info_data, key=lambda x: x['total_books_uploaded'])['total_books_uploaded']]

            librarians_with_no_uploads = len([l for l in account_info_data if l['total_books_uploaded'] == 0])
            total_librarians = len(account_info_data)
            top_librarians = sorted(account_info_data, key=lambda x: x['total_books_uploaded'], reverse=True)[:10]

            # Prepare labels; list up to 3 names, collapse to 'Multiple accounts' for 4 or more
            high_names = [l['account_name'] for l in highest_uploaded_librarians]
            low_names  = [l['account_name'] for l in lowest_uploaded_librarians]

            def _join_names(names):
                n = len(names)
                if n == 0:
                    return 'N/A'
                if n == 1:
                    return names[0]
                if n == 2:
                    return f"{names[0]} and {names[1]}"
                if n == 3:
                    return f"{names[0]}, {names[1]}, and {names[2]}"
                return 'Multiple accounts'

            def _subject_label(names):
                return _join_names(names)

            def _verb(n, singular='has', plural='have'):
                return singular if n == 1 else plural

            highest_subject = _subject_label(high_names)
            highest_verb    = _verb(len(high_names))
            lowest_subject  = _subject_label(low_names)
            lowest_verb     = _verb(len(low_names))

            # Most recent upload among the highs (guard None dates by sorting key that handles None)
            def _safe_date(v):
                d = v.get('latest_book_date')
                return d or date.min

            most_recent_highest_upload_date = max(highest_uploaded_librarians, key=_safe_date).get('latest_book_date')
            recent_names = [l['account_name'] for l in highest_uploaded_librarians if l.get('latest_book_date') == most_recent_highest_upload_date]
            recent_subject = _subject_label(recent_names)

            # Total uploads across all librarians/departments in the selected window
            total_books_all = sum(l['total_books_uploaded'] for l in account_info_data)

            if total_books_all == 0:
                table_description_account_info = f"""
                    <b>Librarian/Department Upload Data for {display_range}</b><br/><br/>
                    No uploads were recorded from librarians or departments during this period.<br/>
                    Total accounts considered: <b>{total_librarians}</b>.
                """
            else:
                table_description_account_info = f"""
                    <b>Librarian/Department Upload Data for {display_range}</b><br/><br/>
                    Table 1 shows that <b>{highest_subject}</b> {highest_verb} uploaded the highest number of books during the {display_range}, 
                    with a total of <b>{(highest_uploaded_librarians[0]['total_books_uploaded'] if highest_uploaded_librarians else 0)}</b> books. In contrast, <b>{lowest_subject}</b> 
                    {lowest_verb} uploaded the fewest books during this period, with a total of <b>{(lowest_uploaded_librarians[0]['total_books_uploaded'] if lowest_uploaded_librarians else 0)}</b> books.<br/><br/>
                    
                    Overall, a total of <b>{total_books_all}</b> books were uploaded across all librarians/departments during this period.<br/><br/>

                    The most recent book upload was made by <b>{recent_subject}</b> on <b>{most_recent_highest_upload_date or 'N/A'}</b>. 
                    There are <b>{librarians_with_no_uploads}</b> librarians/departments who have not uploaded any books within the specified range. The total number of accounts is <b>{total_librarians}</b>.<br/><br/>
                    
                    The most active librarians/departments are the following (highest to lowest books uploaded):<br/>
                    <ol>
                        {"".join([f"<li>{i+1}. {l['account_name']}</li>" for i, l in enumerate(top_librarians)])}
                    </ol>

                """
        else:
            table_description_account_info = f"""
                <b>Librarian/Department Upload Data for {display_range}</b><br/><br/>
                No librarian or department data available for the selected range. Overall, <b>no uploads</b> were recorded during this period.
            """
        
        # Step 4: Prepare the second data - Categorize books by type (Thesis, Academic)
        # Apply the same resolved window
        # Only include non-archived books in categorized summaries
        cb_qs = Books.objects.filter(is_archived=False)
        # Use the same resolved window here too to ensure descriptions/tables match counts
        if window_start and window_end:
            categorized_books = cb_qs.filter(date_uploaded__gte=window_start, date_uploaded__lte=window_end)
        elif window_start:
            categorized_books = cb_qs.filter(date_uploaded__gte=window_start)
        elif window_end:
            categorized_books = cb_qs.filter(date_uploaded__lte=window_end)
        else:
            categorized_books = cb_qs

        # Separate the books into Thesis and Academic categories
        thesis_books = categorized_books.filter(book_type='Thesis').order_by('title')  # Alphabetical order by title
        academic_books = categorized_books.filter(book_type='Academic').order_by('title')  # Alphabetical order by title

            # Prepare data for categorized books with details
        categorized_books_data = []
        
        # Annotate thesis books with book_count from BookViewLog (safe when empty)
        annotated_thesis = thesis_books.annotate(
            book_count=models.Subquery(
                BookViewLog.objects.filter(book_id=models.OuterRef('book_id')).values('book_count')[:1]
            )
        )

        if thesis_books.exists():
            # Materialize minimal fields for tie handling
            thesis_rows = list(
                annotated_thesis.values('title', 'date_uploaded', 'book_id', 'book_count')
            )

            # Helper to join up to 3 titles; 4+ => "Multiple books"
            def _join_titles(names):
                names = [n for n in names if n]
                if not names:
                    return 'N/A'
                if len(names) >= 4:
                    return 'Multiple books'
                if len(names) == 1:
                    return names[0]
                if len(names) == 2:
                    return f"{names[0]} and {names[1]}"
                return f"{names[0]}, {names[1]}, and {names[2]}"

            # Views-based ties (treat None as 0)
            view_counts = [(row['title'], int(row['book_count'] or 0)) for row in thesis_rows]
            if view_counts:
                mv_max = max(vc for _, vc in view_counts)
                lv_min = min(vc for _, vc in view_counts)
                mv_titles = [t for t, vc in view_counts if vc == mv_max]
                lv_titles = [t for t, vc in view_counts if vc == lv_min]
            else:
                mv_max = lv_min = 0
                mv_titles = lv_titles = []

            # Date-based ties
            dates = [row['date_uploaded'] for row in thesis_rows if row.get('date_uploaded') is not None]
            if dates:
                latest_dt = max(dates)
                oldest_dt = min(dates)
                latest_titles = [row['title'] for row in thesis_rows if row.get('date_uploaded') == latest_dt]
                oldest_titles = [row['title'] for row in thesis_rows if row.get('date_uploaded') == oldest_dt]
            else:
                latest_titles = []
                oldest_titles = []

            mv_label = _join_titles(mv_titles)
            lv_label = _join_titles(lv_titles)
            latest_label = _join_titles(latest_titles)
            oldest_label = _join_titles(oldest_titles)

            table_description_thesis_books = f"""
                <b>Thesis Books for {display_range}</b><br/><br/>
                Table 2 displays the list of all thesis books uploaded within the {display_range}. A total of <b>{thesis_books.count()}</b> thesis books were uploaded during this period. 
                The table shows that the most viewed book(s) is/are <b>{mv_label}</b>, with <b>{mv_max}</b> views, 
                while the least viewed book(s) is/are <b>{lv_label}</b>, with <b>{lv_min}</b> views. 
                The most recently uploaded book(s) is/are <b>{latest_label}</b>, while the oldest uploaded book(s) is/are <b>{oldest_label}</b>.
            """
        else:
            table_description_thesis_books = f"""
                <b>Thesis Books for {display_range}</b><br/><br/>
                No thesis books were uploaded in this period.
            """
        
        # Add Thesis books
        if thesis_books.exists():
            for book in thesis_books:
                # Fetch book views from BookViewLog
                book_views = BookViewLog.objects.filter(book_id=book.book_id).first()
                book_count = book_views.book_count if book_views else 0

                categorized_books_data.append({
                    'book_id': book.book_id,
                    'title': book.title,
                    'author': f"{book.author}, {book.co_author}" if book.co_author else book.author,
                    'date_uploaded': book.date_uploaded,
                    'book_count': book_count,
                    'book_type': 'Thesis',
                })
        else:
            # If no Thesis books, append "NO DATA"
            categorized_books_data.append({
                'book_id': 'N/A',
                'title': 'NO DATA',
                'author': 'NO DATA',
                'date_uploaded': 'N/A',
                'book_count': 0,
                'book_type': 'Thesis',
            })

        # Annotate academic books with book_count from BookViewLog (safe when empty)
        annotated_academic = academic_books.annotate(
            book_count=models.Subquery(
                BookViewLog.objects.filter(book_id=models.OuterRef('book_id')).values('book_count')[:1]
            )
        )

        # Add the table description for academic books (safe when empty)
        if academic_books.exists():
            acad_rows = list(
                annotated_academic.values('title', 'date_uploaded', 'book_id', 'book_count')
            )

            def _join_titles_ac(names):
                names = [n for n in names if n]
                if not names:
                    return 'N/A'
                if len(names) >= 4:
                    return 'Multiple books'
                if len(names) == 1:
                    return names[0]
                if len(names) == 2:
                    return f"{names[0]} and {names[1]}"
                return f"{names[0]}, {names[1]}, and {names[2]}"

            view_counts_ac = [(row['title'], int(row['book_count'] or 0)) for row in acad_rows]
            if view_counts_ac:
                mv_max_ac = max(vc for _, vc in view_counts_ac)
                lv_min_ac = min(vc for _, vc in view_counts_ac)
                mv_titles_ac = [t for t, vc in view_counts_ac if vc == mv_max_ac]
                lv_titles_ac = [t for t, vc in view_counts_ac if vc == lv_min_ac]
            else:
                mv_max_ac = lv_min_ac = 0
                mv_titles_ac = lv_titles_ac = []

            dates_ac = [row['date_uploaded'] for row in acad_rows if row.get('date_uploaded') is not None]
            if dates_ac:
                latest_dt_ac = max(dates_ac)
                oldest_dt_ac = min(dates_ac)
                latest_titles_ac = [row['title'] for row in acad_rows if row.get('date_uploaded') == latest_dt_ac]
                oldest_titles_ac = [row['title'] for row in acad_rows if row.get('date_uploaded') == oldest_dt_ac]
            else:
                latest_titles_ac = []
                oldest_titles_ac = []

            mv_label_ac = _join_titles_ac(mv_titles_ac)
            lv_label_ac = _join_titles_ac(lv_titles_ac)
            latest_label_ac = _join_titles_ac(latest_titles_ac)
            oldest_label_ac = _join_titles_ac(oldest_titles_ac)

            table_description_academic_books = f"""
                <b>Academic Books for {display_range}</b><br/><br/>
                Table 3 displays the list of all academic books uploaded within the {display_range}. A total of <b>{academic_books.count()}</b> academic books were uploaded during this period. 
                The table shows that the most viewed book(s) is/are <b>{mv_label_ac}</b>, with <b>{mv_max_ac}</b> views, 
                while the least viewed book(s) is/are <b>{lv_label_ac}</b>, with <b>{lv_min_ac}</b> views. 
                The most recently uploaded book(s) is/are <b>{latest_label_ac}</b>, while the oldest uploaded book(s) is/are <b>{oldest_label_ac}</b>.
            """
        else:
            table_description_academic_books = f"""
                <b>Academic Books for {display_range}</b><br/><br/>
                No academic books were uploaded in this period.
            """
        # Add Academic books
        if academic_books.exists():
            for book in academic_books:
                # Fetch book views from BookViewLog
                book_views = BookViewLog.objects.filter(book_id=book.book_id).first()
                book_count = book_views.book_count if book_views else 0

                categorized_books_data.append({
                    'book_id': book.book_id,
                    'title': book.title,
                    'author': f"{book.author}, {book.co_author}" if book.co_author else book.author,
                    'date_uploaded': book.date_uploaded,
                    'book_count': book_count,
                    'book_type': 'Academic',
                })
        else:
            # If no Academic books, append "NO DATA"
            categorized_books_data.append({
                'book_id': 'N/A',
                'title': 'NO DATA',
                'author': 'NO DATA',
                'date_uploaded': 'N/A',
                'book_count': 0,
                'book_type': 'Academic',
            })
            
        # ---------------- Shelf Category Counts (Table 4) ---------------- #
        # Compute counts per shelf category in the same resolved window (non-archived only)
        shelf_counts_qs = categorized_books.values('shelf_category').annotate(n=Count('shelf_category'))
        # Build data rows (then sort alphabetically by category, case-insensitive)
        shelf_counts_data = []
        for row in shelf_counts_qs:
            shelf_counts_data.append({
                'shelf_category': row.get('shelf_category') or 'Uncategorized',
                'count': int(row.get('n') or 0),
            })
        shelf_counts_data.sort(key=lambda r: (r['shelf_category'] or '').lower())

        # Description with tie handling (list up to 3 categories, else 'Multiple categories')
        if shelf_counts_data:
            counts = [r['count'] for r in shelf_counts_data]
            max_c = max(counts)
            min_c = min(counts)
            high_names = [r['shelf_category'] for r in shelf_counts_data if r['count'] == max_c]
            low_names  = [r['shelf_category'] for r in shelf_counts_data if r['count'] == min_c]

            def _join_labels(names):
                names = [n for n in names if n]
                if len(names) >= 4:
                    return 'Multiple categories'
                if len(names) == 0:
                    return 'N/A'
                if len(names) == 1:
                    return names[0]
                if len(names) == 2:
                    return f"{names[0]} and {names[1]}"
                return f"{names[0]}, {names[1]}, and {names[2]}"

            high_label = _join_labels(high_names)
            low_label  = _join_labels(low_names)

            table_description_shelf = f"""
                <b>Shelf Category Counts for {display_range}</b><br/><br/>
                Table 4 summarizes the number of books per shelf category within the selected range. The category/categories with the highest count is/are <b>{high_label}</b> with <b>{max_c}</b> book(s),
                while the lowest is/are <b>{low_label}</b> with <b>{min_c}</b> book(s).
            """
        else:
            table_description_shelf = f"""
                <b>Shelf Category Counts for {display_range}</b><br/><br/>
                No books were uploaded in this period, so no shelf category counts are available.
            """

        all_description_of_tables_data = []
        all_description_of_tables_data.extend([
            {"account_info_desc": table_description_account_info},
            {"thesis_books_desc": table_description_thesis_books},
            {"academic_books_desc": table_description_academic_books},
            {"shelf_counts_desc": table_description_shelf},
        ])
        
        # Step 5: Generate the report using ReportLab (passing account_info_data, categorized_books_data, and user_info)
        file_name = "Liraya_AccountBookRecords_Report.pdf"
        
        graph_path, graph_description = generate_librarian_upload_chart(window=(window_start, window_end), label=display_range)

        # Header start/end dates for Book Range line: only use the resolved window
        if window_start and window_end:
            start_date_str = window_start.strftime('%B %d, %Y')
            end_date_str = window_end.strftime('%B %d, %Y')
        else:
            start_date_str = None
            end_date_str = None

        generate_account_bookrecords(
            pdf_buffer,
            account_info_data,
            categorized_books_data,
            user_info,
            file_name,
            graph_path,
            graph_description,
            all_description_of_tables_data,
            shelf_counts_data,
            start_date_str,
            end_date_str
        )

    except Exception as e:
        logger.error(f"Error generating account book records report: {str(e)}")
        return HttpResponse(f"Error generating account book records report: {str(e)}", status=500)

def _data_floor() -> date:
    """
    Dynamic lower bound for any report/chart range.
    Falls back to the previous constant if DB has no rows or on error.
    """
    try:
        earliest = Books.objects.aggregate(m=Min('date_uploaded'))['m']
        if earliest is None:
            return DATA_FLOOR
        return earliest if isinstance(earliest, date) else earliest.date()
    except Exception:
        return DATA_FLOOR

def _resolve_bookrecords_range(date_range, today=None):
    """
    Compute (filter_date, display_range, window_start, window_end) from the admin modal params or legacy string.
    - date_range: dict like {period_type, days|weeks|months|years|start_date|end_date} OR legacy string key
    - filter_date: either a single date (lower bound), a (start,end) tuple, or None for 'all'
    - display_range: human-readable label used in descriptions
    - window_start/window_end: concrete inclusive window bounds for charting (or None/None for 'all')
    """
    current_date = today or datetime.now().date()
    filter_date = None
    display_range = 'All Time'

    if isinstance(date_range, dict):
        params = date_range
        period_type = (params.get('period_type') or 'today').strip()

        if period_type == 'today':
            filter_date = current_date
            display_range = 'Today'
        elif period_type == 'days':
            days = int(params.get('days') or 1)
            filter_date = current_date - timedelta(days=days)
            display_range = f"Last {days} Days"
        elif period_type == 'weeks':
            weeks = int(params.get('weeks') or 1)
            filter_date = current_date - timedelta(weeks=weeks)
            display_range = f"Last {weeks} Weeks"
        elif period_type == 'months':
            months = int(params.get('months') or 1)
            filter_date = (current_date - relativedelta(months=months))
            display_range = f"Last {months} Months"
        elif period_type == 'years':
            years = int(params.get('years') or 1)
            filter_date = (current_date - relativedelta(years=years))
            display_range = f"Last {years} Years"
        elif period_type == 'custom':
            sd_raw = params.get('start_date')
            ed_raw = params.get('end_date')
            start_date = datetime.strptime(sd_raw, '%Y-%m-%d').date() if sd_raw else None
            end_date = datetime.strptime(ed_raw, '%Y-%m-%d').date() if ed_raw else current_date
            if start_date and end_date and start_date > end_date:
                start_date, end_date = end_date, start_date
            filter_date = (start_date, end_date)
            if start_date and end_date:
                display_range = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
            else:
                display_range = 'Custom Range'
        elif period_type == 'all':
            filter_date = None
            display_range = 'All Time'
        else:
            raise ValueError("Invalid period type provided.")
    else:
        key = (date_range or '').strip()
        if key == 'today':
            filter_date = current_date
            display_range = 'Today'
        elif key == 'last_1_week':
            filter_date = current_date - timedelta(weeks=1)
            display_range = 'Last 1 Week'
        elif key == 'last_2_weeks':
            filter_date = current_date - timedelta(weeks=2)
            display_range = 'Last 2 Weeks'
        elif key == 'last_1_month':
            filter_date = current_date - timedelta(days=30)
            display_range = 'Last 1 Month'
        elif key == 'last_6_months':
            filter_date = current_date - timedelta(days=180)
            display_range = 'Last 6 Months'
        elif key == 'last_1_year':
            filter_date = current_date - timedelta(days=365)
            display_range = 'Last 1 Year'
        elif key in ('all_time', 'all'):
            filter_date = None
            display_range = 'All Time'
        else:
            raise ValueError("Invalid date range provided.")

    # Concrete chart window
    if isinstance(filter_date, tuple):
        sd, ed = filter_date
        window_start = sd or _data_floor()
        window_end = ed or current_date
    elif filter_date:
        window_start = filter_date
        window_end = current_date
    else:
        window_start, window_end = None, None

    return filter_date, display_range, window_start, window_end

def generate_librarian_upload_chart(window=None, label=None, date_range=None):
    """
    Generate a line chart of librarian uploads over a given window with adaptive x-axis granularity.

    Inputs:
    - window: (start_date, end_date) tuple of date or datetime (inclusive). When None/None, uses all-time.
    - label: display label for description (e.g., "Last 6 Months", "Today"). Optional.
    - date_range: legacy string (e.g., 'today', 'last_1_week') for backward-compat; used only if window is None.

    Outputs:
    - (graph_path, graph_description)
    """
    try:
        # 1) Resolve concrete window [ws, we] using Philippines timezone
        philippines_timezone = pytz.timezone('Asia/Manila')
        philippines_now = timezone.now().astimezone(philippines_timezone)
        today = philippines_now.date()
        ws, we = None, None

        if window and isinstance(window, (tuple, list)) and len(window) == 2:
            ws, we = window
        else:
            # Backward compatibility with legacy string date_range
            key = (date_range or '').strip() if date_range else None
            if key in (None, '', 'all_time', 'all'):
                ws, we = None, None
            elif key == 'today':
                ws = today
                we = today
            elif key == 'last_1_week':
                ws = today - timedelta(weeks=1)
                we = today
            elif key == 'last_2_weeks':
                ws = today - timedelta(weeks=2)
                we = today
            elif key == 'last_1_month':
                ws = today - timedelta(days=30)
                we = today
            elif key == 'last_6_months':
                ws = today - timedelta(days=180)
                we = today
            elif key == 'last_1_year':
                ws = today - timedelta(days=365)
                we = today
            else:
                raise ValueError("Invalid date range provided.")

        # If all-time requested, infer from data (use non-archived to match UI/report semantics)
        if ws is None or we is None:
            agg = Books.objects.filter(is_archived=False).aggregate(mn=Min('date_uploaded'), mx=Max('date_uploaded'))
            mn, mx = agg.get('mn'), agg.get('mx')
            if not mn or not mx:
                # no data at all
                mn = today
                mx = today
            # Convert to date if needed
            ws = mn.date() if hasattr(mn, 'date') else mn
            we = mx.date() if hasattr(mx, 'date') else mx

        if ws > we:
            ws, we = we, ws

        # 2) Determine granularity and step
        # Compute span in days
        span_days = max(1, (we - ws).days + 1)

        # granularity: use 'day' even for single-day windows (Books.date_uploaded is a DateField)
        if span_days <= 1:
            gran = 'day'
        elif span_days <= 45:
            gran = 'day'
        elif span_days <= 365:
            gran = 'week'
        elif span_days <= 3 * 365:
            gran = 'month'
        else:
            gran = 'year'

        # Max number of bins for readability
        MAX_BINS = 60

        def months_between(d1, d2):
            return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1

        def years_between(d1, d2):
            return (d2.year - d1.year) + 1

        # number of base units
        if gran == 'hour':
            units = 24
        elif gran == 'day':
            units = span_days
        elif gran == 'week':
            units = max(1, (span_days + 6) // 7)
        elif gran == 'month':
            units = months_between(ws, we)
        else:
            units = years_between(ws, we)

        # choose a nice step (1,2,5,10,20,50...)
        def nice_step(n_units, max_bins=MAX_BINS):
            candidates = [1, 2, 3, 5, 7, 10, 14, 15, 20, 30, 60, 90, 120]
            for c in candidates:
                if (n_units + c - 1) // c <= max_bins:
                    return c
            # fallback
            return max(1, (n_units + max_bins - 1) // max_bins)

        step = nice_step(units)

        # 3) Build bins and labels
        bins = []
        labels = []

        if gran == 'hour':
            # Use the single day (ws) as reference
            ref_dt = datetime(ws.year, ws.month, ws.day)
            h = 0
            while h < 24:
                bins.append(('hour', h))
                labels.append(f"{h:02d}:00")
                h += step
        elif gran == 'day':
            cur = ws
            while cur <= we:
                bins.append(('day', cur))
                labels.append(cur.strftime('%Y-%m-%d'))
                cur = cur + timedelta(days=step)
        elif gran == 'week':
            cur = ws
            while cur <= we:
                bins.append(('week', cur))
                labels.append(f"Week of {cur.strftime('%Y-%m-%d')}")
                cur = cur + timedelta(weeks=step)
        elif gran == 'month':
            cur = date(ws.year, ws.month, 1)
            end_m = date(we.year, we.month, 1)
            while cur <= end_m:
                bins.append(('month', cur.year, cur.month))
                labels.append(f"{cur.year}-{cur.month:02d}")
                cur = (cur + relativedelta(months=step))
        else:  # year
            cur_y = ws.year
            while cur_y <= we.year:
                bins.append(('year', cur_y))
                labels.append(str(cur_y))
                cur_y += step

        # 4) Chart - Collect data per librarian (LIBRARIAN + DEPARTMENT)
        librarian_accounts = UserAccounts.objects.filter(role__in=["LIBRARIAN", "DEPARTMENT"])  
        uploads_by_lib = {}          # key: account_id, value: list[int] counts per bin
        id_to_label = {}             # account_id -> display label (Full Name + ID)

        # Precompute date bounds (inclusive on both ends)
        start_d = ws
        end_d = we

        for ua in librarian_accounts.select_related('account'):
            account_id = ua.account.account_id
            # Use a more detailed full name (include middle name if present) to reduce ambiguity
            middle = f" {ua.account.middle_name}" if getattr(ua.account, 'middle_name', None) else ''
            full_name = f"{ua.account.first_name}{middle} {ua.account.last_name}".strip()
            # Display label includes unique account ID to avoid merging same-named librarians
            display_label = f"{full_name} (ID:{account_id})"
            id_to_label[account_id] = display_label

            # Match counts with UI by excluding archived books
            qs = Books.objects.filter(
                account=ua.account,
                is_archived=False,
                date_uploaded__gte=start_d,
                date_uploaded__lte=end_d
            )

            # Map each upload to a bin
            counts = [0] * len(bins)
            for book in qs.only('date_uploaded'):
                dt = book.date_uploaded
                # If it's date-only, coerce to datetime for consistency
                if isinstance(dt, date) and not isinstance(dt, datetime):
                    dt = datetime(dt.year, dt.month, dt.day)

                if gran == 'day':
                    # distance in days from ws
                    d = (dt.date() - ws).days
                    if d >= 0:
                        idx = d // step
                        if 0 <= idx < len(counts):
                            counts[idx] += 1
                elif gran == 'week':
                    d = (dt.date() - ws).days
                    if d >= 0:
                        w = d // 7
                        idx = w // step
                        if 0 <= idx < len(counts):
                            counts[idx] += 1
                elif gran == 'month':
                    ddt = dt.date()
                    months = (ddt.year - ws.year) * 12 + (ddt.month - ws.month)
                    if months >= 0:
                        idx = months // step
                        if 0 <= idx < len(counts):
                            counts[idx] += 1
                else:  # year
                    years = dt.year - ws.year
                    if years >= 0:
                        idx = years // step
                        if 0 <= idx < len(counts):
                            counts[idx] += 1

            uploads_by_lib[account_id] = counts

        # 5) Keep top 10 librarians by total
        totals = {acct_id: sum(vals) for acct_id, vals in uploads_by_lib.items()}
        top10 = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
        top_ids = [acct_id for (acct_id, _) in top10] if top10 else []
        top_labels = [id_to_label[acct_id] for acct_id in top_ids]

        # 6) Build DataFrame for plotting
        if top_ids:
            data = {id_to_label[acct_id]: uploads_by_lib.get(acct_id, [0] * len(bins)) for acct_id in top_ids}
            df = pd.DataFrame(data, index=labels)

            # Plot
            plt.figure(figsize=(10, 6))
            colors = plt.cm.get_cmap('tab20', len(df.columns))
            for idx, name in enumerate(df.columns):
                plt.plot(df.index, df[name], label=name, color=colors(idx))

            title = "Librarian Book Uploads Over Time"
            plt.title(title)
            # X-axis label based on granularity
            xlabel = {
                'hour': 'Hour of Day',
                'day': 'Date',
                'week': 'Week Start',
                'month': 'Month',
                'year': 'Year',
            }[gran]
            plt.xlabel(xlabel)
            plt.ylabel('Number of Book Uploads')
            plt.xticks(rotation=45)

            max_y = int(df.max().max()) if not df.empty else 0
            plt.yticks(range(0, max(1, max_y) + 2))
            plt.legend(loc='upper left')
            plt.grid(True)

            ax = plt.gca()
            for side in ['top', 'right', 'bottom', 'left']:
                ax.spines[side].set_color('#3e151a')
                ax.spines[side].set_linewidth(2)

            media_dir = os.path.join(os.getcwd(), 'LirayaApp', 'media', 'graphs')
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
            graph_filename = 'librarian_uploads_over_time.png'
            graph_path = os.path.join(media_dir, graph_filename)

            plt.tight_layout()
            plt.savefig(graph_path)
            plt.close()
        else:
            # Create a placeholder chart that clearly says "No Data"
            plt.figure(figsize=(10, 6))
            plt.title('Librarian Book Uploads Over Time')
            plt.text(0.5, 0.5, 'No Data Available for Selected Range', ha='center', va='center', fontsize=14)
            plt.axis('off')
            media_dir = os.path.join(os.getcwd(), 'LirayaApp', 'media', 'graphs')
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
            graph_filename = 'librarian_uploads_over_time.png'
            graph_path = os.path.join(media_dir, graph_filename)
            plt.savefig(graph_path)
            plt.close()

        # 7) Build description
        # Determine date range string
        if ws == we:
            date_range_str = ws.strftime('%B %d, %Y')
        else:
            date_range_str = f"{ws.strftime('%B %d, %Y')} to {we.strftime('%B %d, %Y')}"

        used_label = label or date_range or 'Selected Range'

        if not top_ids:
            graph_description = (
                f"""
                Figure 1 shows librarian upload activity for <b>{used_label}</b> (<i>{date_range_str}</i>).<br/>
                No data is available for this range. The placeholder chart is shown for completeness.
                """
            )
        else:
            unit_text = {
                'hour': 'hour',
                'day': 'day',
                'week': 'week',
                'month': 'month',
                'year': 'year',
            }[gran]
            step_text = f"every {step} {unit_text}{'' if step == 1 else 's'}"
            graph_description = (
                f"""
                Figure 1 shows librarian upload activity for <b>{used_label}</b> (<i>{date_range_str}</i>),
                grouped {step_text}. Each line represents a librarian (LIBRARIAN/DEPARTMENT roles).
                """
            )

            # Append top librarians summary
            number_librarians = 0
            # Compute real elapsed time between ws and we (inclusive days)
            total_days_span = max(1, (we - ws).days + 1)
            # Convert span to the same unit as chart granularity
            if gran == 'day':
                denom_units = float(total_days_span)
            elif gran == 'week':
                denom_units = total_days_span / 7.0
            elif gran == 'month':
                # Average days per month to account for varying month lengths
                denom_units = total_days_span / 30.4375
            else:  # 'year'
                # Average days per year (including leap years)
                denom_units = total_days_span / 365.25

            denom_units = max(1e-9, denom_units)  # safety against division by zero

            for acct_id in top_ids:
                name = id_to_label[acct_id]
                total_books = float(totals.get(acct_id, 0))
                number_librarians += 1
                if int(total_books) == 0:
                    graph_description += (
                        f"<br/>{number_librarians}. <b>{name}</b> recorded <b>no uploads</b> for this range."
                    )
                else:
                    # Average per real elapsed time unit matching the chart granularity
                    avg_per_unit = total_books / denom_units
                    graph_description += (
                        f"<br/>{number_librarians}. <b>{name}</b> uploaded a total of <b>{int(total_books)}</b> books "
                        f"(avg {avg_per_unit:.2f} per {unit_text})."
                    )

        return graph_path, graph_description

    except Exception as e:
        print(f"Error generating librarian upload chart: {e}")
        return None, None



########### LIBRARIAN DASHBOARD ############
@login_checker
@role_required('LIBRARIAN')
def librarian_homepage(request):
    # Get the logged-in user's account_id from the session
    account_id = request.session.get('account_id')
    user_info = get_user_info(account_id)

    if account_id:
        # Retrieve the librarian account object
        account = AccountInformation.objects.get(account_id=account_id)

        # Fetch only the books uploaded by this librarian that are not archived
        books = Books.objects.filter(account=account, is_archived=False)  # Filter by librarian's account and only non-archived books
        total_book_count = books.count()  # Total books uploaded by librarian

        # ---------- Search Functionality ----------
        query = request.GET.get('q', '').strip()  # Get the search query
        field = request.GET.get('field', 'allFields').strip()  # Field to search in (title, author, etc.)

        # Apply search filters based on the selected field
        if query:
            if field == 'title':
                books = books.filter(title__icontains=query)
            elif field == 'author':
                books = books.filter(author__icontains=query)
            elif field == 'keywords':
                books = books.filter(primary_keyword__icontains=query)
            else:  # allFields
                books = books.filter(
                    Q(title__icontains=query) | Q(author__icontains=query) | Q(primary_keyword__icontains=query)
                )

        # ---------- Sorting ----------
        sort_by = request.GET.get('sort', 'all')  # Sorting option (e.g., recently uploaded)
        if sort_by == 'all':
            books = books.order_by('book_id')
        elif sort_by == 'oldest_to_newest':
            books = books.order_by('date_uploaded')
        elif sort_by == 'newest_to_oldest':
            books = books.order_by('-date_uploaded')
        elif sort_by == 'author':
            books = books.order_by('author')
        elif sort_by == 'keyword':
            books = books.order_by('primary_keyword')
        elif sort_by == 'subject':
            books = books.order_by('book_type')
        elif sort_by == 'title':
            books = books.order_by('title')
        
        # ---------- Pagination: Show 10 books per page ----------
        paginator = Paginator(books, 10)  # Show 10 books per page
        page_number = request.GET.get('page')  # Get current page number from query params
        page_obj = paginator.get_page(page_number)  # Get the page object

        # Handle archiving action
        if request.method == 'POST' and 'archive' in request.POST:
            book = Books.objects.get(book_id=request.POST.get('archive'))
            book.is_archived = not book.is_archived  # Toggle the archived status
            book.save()

            # Redirect after archiving to refresh the book list without the archived book
            return redirect('librarian_homepage')

        # Pass the books, book_count, page_obj, and sort_by to the template
        return render(request, 'librarian_homepage.html', {
            'page_obj': page_obj,  # Use page_obj for paginated books
            'user_info': user_info,
            'book_count': total_book_count,
            'sort_by': sort_by,
            'query': query,
            'field': field,
        })

    return redirect('login')  # If not logged in, redirect to login page



@login_checker
@role_required('LIBRARIAN')
def librarian_suggestions(request):
    query = request.GET.get('q', '').strip()
    field = request.GET.get('field', 'allFields').strip()

    if not query:
        return JsonResponse({'results': []})

    # Tokenize by comma/space, drop small common connectors
    raw_tokens = re.split(r'[,\s]+', query)
    stopwords = {'the', 'or', 'at', 'a', 'an', 'and', 'of', 'to', 'for', 'in', 'on'}
    tokens = [t for t in raw_tokens if t and t.lower() not in stopwords]

    if not tokens:
        return JsonResponse({'results': []})

    base_qs = Books.objects.filter(is_archived=False)
    results = []

    # Helper to AND-filter tokens on one field
    def and_filter(qs, field_name):
        for tok in tokens:
            qs = qs.filter(**{f"{field_name}__icontains": tok})
        return qs

    # Titles
    if field in ('allFields', 'title'):
        tqs = and_filter(base_qs, 'title')
        titles = list(tqs.values_list('title', flat=True).distinct()[:200])
        results.extend({'type': 'title', 'text': t} for t in titles)

    # Authors - ensure partial matches for multi-word names
    if field in ('allFields', 'author'):
        aqs = and_filter(base_qs, 'author')
        authors = list(aqs.values_list('author', flat=True).distinct()[:200])
        
        if not authors:  # If no matches found with tokenized query
            authors = list(base_qs.values_list('author', flat=True).distinct()[:200])
        
        results.extend({'type': 'author', 'text': a} for a in authors)

    # Keywords (split the stored comma list into individual keywords)
    if field in ('allFields', 'keywords'):
        kqs = and_filter(base_qs, 'primary_keyword')
        seen = set()
        keywords = []
        # Scan a limited number of rows for performance
        for kw_str in kqs.values_list('primary_keyword', flat=True)[:200]:
            if not kw_str:
                continue
            for kw in (x.strip() for x in kw_str.split(',')):
                if not kw:
                    continue
                low = kw.lower()
                if all(tok.lower() in low for tok in tokens) and kw not in seen:
                    seen.add(kw)
                    keywords.append(kw)
                    if len(keywords) >= 8:
                        break
            if len(keywords) >= 8:
                break
        results.extend({'type': 'keywords', 'text': k} for k in keywords)

    # Prioritize results by matching query
    results = sorted(results, key=lambda x: x['text'].lower().startswith(query.lower()), reverse=True)
    
    # Mix for allFields
    if field == 'allFields':
        titles   = [r for r in results if r['type'] == 'title']
        authors  = [r for r in results if r['type'] == 'author']
        keywords = [r for r in results if r['type'] == 'keywords']
        results = titles + authors + keywords

    # Limit to 10 results
    results = results[:10]

    return JsonResponse({'results': results})

@login_checker
@role_required('LIBRARIAN')
def librarian_view_details(request, book_id):
    # Get the logged-in user's account_id from the session
    account_id = request.session.get('account_id')
    user_info = get_user_info(account_id)

    # If account_id doesn't exist, redirect to the login page
    if not account_id:
        return redirect('login')

    try:
        # Retrieve the librarian's account object
        account = AccountInformation.objects.get(account_id=account_id)
    except AccountInformation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Account not found.'}, status=404)

    try:
        # Fetch the book that belongs to this librarian using both account_id and book_id
        book = get_object_or_404(Books, book_id=book_id, account=account)
    except Books.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Book not found.'}, status=404)

    # Define fixed categories for 'DEPARTMENT' role
    department_categories = [
        'DEPARTMENT OF ENGINEERING (DOE)',
        'DEPARTMENT OF INDUSTRIAL EDUCATION (DED)',
        'DEPARTMENT OF INDUSTRIAL TECHNOLOGY (DIT)',
        'OFFICE OF STUDENT AFFAIRS (OSA)'
    ]

    # Fetch categories for the librarian (excluding department categories)
    if user_info['role'] == 'DEPARTMENT':
        categories = department_categories  # Use predefined categories for DEPARTMENT users
    else:
        categories = Books.objects.exclude(shelf_category__in=department_categories).values('shelf_category').distinct()  # Get dynamic categories for LIBRARIAN


    # Handle archiving action (toggle the book's archived status)
    if 'archive' in request.GET:  
        book.is_archived = not book.is_archived  # Toggle the archived status
        book.save()

         # Use Django's messages framework to add a success message
        messages.success(request, 'Book successfully deleted!')

        # Return a JSON response indicating success
        return JsonResponse({'success': True})

    # --- Update book details ---
    if request.method == 'POST':
        try:
            ctype = (request.headers.get('Content-Type') or '').lower()

            # Allowed text fields for update
            allowed_fields = [
                'title',
                'author',
                'co_author',
                'year_of_publication',
                'publisher',
                'shelf_category',
            ]

            # Update book details based on the request body
            if ctype.startswith('application/json'):
                # If it's JSON data
                data = json.loads(request.body.decode('utf-8'))
                for field in allowed_fields:
                    if field in data:
                        setattr(book, field, data[field])

            else:
                # If it's form data
                for field in allowed_fields:
                    if field in request.POST:
                        setattr(book, field, request.POST.get(field))

                # Handle book cover upload to Cloudinary
                if 'book_cover' in request.FILES:
                    book_cover = request.FILES['book_cover']
                    try:
                        # Delete old cover from Cloudinary if exists
                        if book.book_cover:
                            public_id = book.book_cover.name.split('/')[-1].split('.')[0]
                            destroy(public_id)
                
                        # Upload new cover to Cloudinary
                        cloudinary_response = upload(book_cover)
                        book.book_cover = cloudinary_response['secure_url']  # Save secure URL
                
                    except Exception as e:
                        messages.error(request, f"Error uploading book cover: {e}")
                        return JsonResponse({'success': False, 'message': f"Error uploading book cover: {str(e)}"}, status=500)
                        
            book.save()
            return JsonResponse({'success': True, 'message': 'Book details updated successfully!'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)

    # Render the view details page with the book and categories data
    context = {
        'book': book,
        'user_info': user_info,
        'categories': categories,
        'department_categories': department_categories, 
    }
    return render(request, 'librarian_ViewDetails.html', context)


@csrf_exempt
def check_spelling(request):
    print("DEBUG:", request.method, request.body)

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        text = data.get('text', '').strip()
        print("DEBUG: Text length =", len(text))

        if not text:
            return JsonResponse({'errors': {}}, status=200)

        # --- Step 1: Light cleaning to reduce OCR noise ---
        import re
        clean_text = re.sub(r'[^A-Za-z0-9\s.,;:!?\'"-]', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        # --- Step 2: Language detection (prefer English) ---
        if any(ch in clean_text for ch in 'ñáéíóú'):
            language = 'tl'
        else:
            language = 'en-US'

        print("DEBUG: Language selected =", language)

        # --- Step 3: Try spell-check with LanguageTool ---
        try:
            response = requests.post(
                settings.LANGUAGETOOL_URL,
                data={'text': clean_text, 'language': language},
                timeout=10
            )

        except requests.RequestException as req_err:
            print("DEBUG: RequestException ->", req_err)
            return JsonResponse({'error': 'LanguageTool server unreachable'}, status=502)

        if response.status_code != 200:
            # --- Step 4: Handle known LanguageTool errors gracefully ---
            if "too many errors" in response.text.lower():
                print("DEBUG: Too many errors detected, skipping check.")
                return JsonResponse({
                    'error': 'Spell-check skipped: text contains too many OCR errors. Please re-scan or clean the text.'
                }, status=200)
            print("DEBUG: LanguageTool API error", response.status_code, response.text)
            return JsonResponse({'error': 'LanguageTool API error'}, status=500)

        lt_result = response.json()
        print("DEBUG: Matches found =", len(lt_result.get('matches', [])))

        # --- Step 5: Extract suggestions ---
        errors = {}
        for match in lt_result.get('matches', []):
            offset = match.get('offset', 0)
            length = match.get('length', 0)
            word = clean_text[offset: offset + length]
            suggestions = [s['value'] for s in match.get('replacements', [])]
            if suggestions:
                errors[word] = suggestions[:8]  # limit to 8

        return JsonResponse({'errors': errors}, status=200)

    except Exception as e:
        print("DEBUG ERROR:", e)
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=400)

@login_checker
@role_required('LIBRARIAN')
def librarian_addbook(request):
    account_id = request.session.get('account_id')
    user_info = get_user_info(account_id)

    # Define fixed categories for 'DEPARTMENT' role
    department_categories = [
        'DEPARTMENT OF ENGINEERING (DOE)',
        'DEPARTMENT OF INDUSTRIAL EDUCATION (DED)',
        'DEPARTMENT OF INDUSTRIAL TECHNOLOGY (DIT)',
        'OFFICE OF STUDENT AFFAIRS (OSA)'
    ]

    # Fetch all categories for LIBRARIAN or restrict for DEPARTMENT
    if user_info['role'] == 'DEPARTMENT':
        categories = department_categories  # Use predefined categories for DEPARTMENT users
    else:
        categories = Books.objects.exclude(shelf_category__in=department_categories).values('shelf_category').distinct()
        categories = sorted([category['shelf_category'] for category in categories])  # Sort categories alphabetically (A-Z)

    
    publishers = Books.objects.values('publisher').distinct()
    publishers = sorted([publisher['publisher'] for publisher in publishers])  # Sorting publishers

    # Handle AJAX request for title check / OCR
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body.decode('utf-8'))

        # Category Deletion Request
        if 'deleteCategory' in data:
            category_name = data.get('categoryName', '').strip()
            if category_name:
                # Find books with this category and update the shelf category to None
                books_with_category = Books.objects.filter(shelf_category=category_name)

                if books_with_category.exists():
                    # Remove the category from the books (set shelf_category to None)
                    books_with_category.update(shelf_category="Uncategorized")

                    # Optionally, you can remove the category from the dropdown list as well
                    # If you want to delete the category from the system entirely, you could do that here too

                    return JsonResponse({'success': True, 'message': 'Category removed from books successfully!'})

                return JsonResponse({'success': False, 'message': 'No books found with the specified category.'})


    # Handle AJAX request for title check / OCR
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body.decode('utf-8'))

        # --- 1) Duplicate title check (case-insensitive) ---
        if 'checkTitle' in data:
            title = (data.get('bookTitle') or '').strip()
            if not title:
                return JsonResponse({'exists': False})
            return JsonResponse({'exists': Books.objects.filter(title__iexact=title).exists()})
        
        # --- 2) Category name check ---
        if 'checkCategory' in data:
            category_name = (data.get('categoryName') or '').strip()
            if not category_name:
                return JsonResponse({'exists': False})
            return JsonResponse({'exists': Books.objects.filter(shelf_category__iexact=category_name).exists()})

        # --- 3) Publisher name check ---
        if 'checkPublisher' in data:
            publisher_name = (data.get('publisherName') or '').strip()
            if not publisher_name:
                return JsonResponse({'exists': False})
            return JsonResponse({'exists': Books.objects.filter(publisher__iexact=publisher_name).exists()})


        # --- 2) Title extraction from cropped cover ---
        if 'title_image_data' in data:
            try:
                img_data = data.get('title_image_data')
                img_data = img_data.split(',')[1]              # strip data URI prefix
                img_data = base64.b64decode(img_data)         # convert to binary
                
                # Process the image data directly
                predicted_title = predict_title_with_google_vision(img_data)
                
                return JsonResponse({'book_title': predicted_title})
            except Exception as e:
                print(f"Error processing title: {str(e)}")
                return JsonResponse({'error': f'Error: {str(e)}'}, status=500)

        # --- 3) Document text extraction using Google Cloud Vision ---
        if 'image_data' in data:
            try:
                data_uri = data.get('image_data')
                scanned_type = data.get('scanned_type', "TOC")
                if not data_uri:
                    return JsonResponse({'error': 'No image data received'}, status=400)

                # Process with Google Cloud Vision OCR
                extracted_text = ocr_extract_text(data_uri, scanned_type)

                return JsonResponse({
                    'extracted_text': extracted_text,
                })
            except Exception as e:
                print(f"Error during document text detection: {str(e)}")
                return JsonResponse({'error': f'Error: {str(e)}'}, status=500)

    # --- Regular POST (saving book) — UNCHANGED ---
    if request.method == 'POST':
        title = (request.POST.get('bookTitle') or '').strip()

        if not title:
            messages.error(request, "The book title cannot be empty.")
            return redirect('librarian_addbook')

        if Books.objects.filter(title__iexact=title).exists():
            messages.error(request, "A book with this title already exists.")
            return redirect('librarian_addbook')

        # Authors → "Last, First"
        authors = request.POST.getlist('author[]')
        author_list = []
        for author in authors:
            author_parts = author.split(",", 1)
            if len(author_parts) == 2:
                author_last_name = author_parts[0].strip()
                author_first_name = author_parts[1].strip()
            else:
                author_last_name = author.strip()
                author_first_name = ''
            author_list.append(f"{author_last_name}, {author_first_name}")
        author = ", ".join(author_list)

        # Ensure the author string does not exceed 500 characters
        if len(author) > 500:
            author = author[:500]  # Trim to 500 characters

    

        # Co-Authors
        co_authors = request.POST.getlist('coAuthor[]')
        co_author_list = []
        for co_author in co_authors:
            co_author_parts = co_author.split(",", 1)
            if len(co_author_parts) == 2:
                co_author_last_name = co_author_parts[0].strip()
                co_author_first_name = co_author_parts[1].strip()
            else:
                co_author_last_name = co_author.strip()
                co_author_first_name = ''
            co_author_list.append(f"{co_author_last_name}, {co_author_first_name}")
        co_author = ", ".join(co_author_list) if co_authors else None

        # Ensure the co-author string does not exceed 500 characters
        if co_author and len(co_author) > 500:
            co_author = co_author[:500]  # Trim to 500 characters

        year_of_publication = request.POST.get('YearofPublication')
        if year_of_publication == "N/A":
            year_of_publication = None


       
        category_name = request.POST.get('bookShelfCategory')
        if category_name:
            if not Books.objects.filter(shelf_category=category_name).exists():
                pass
        
        # If the user is a DEPARTMENT, ensure they select from the predefined categories
        if user_info['role'] == 'DEPARTMENT' and category_name not in department_categories:
            messages.error(request, "You can only choose from the predefined categories.")
            return redirect('librarian_addbook')


        publisher_name = request.POST.get('publisher')
        if publisher_name:
            if not Books.objects.filter(publisher=publisher_name).exists():
                pass

        book_keyword = request.POST.get('bookKeyword')
        date_uploaded = request.POST.get('dateUploaded')
        book_cover = request.FILES.get('bookCover')
        
        account = AccountInformation.objects.get(account_id=account_id)

        scanned_content = request.POST.get('scannedContent') or "No content extracted"

        new_book = Books(
            account=account,
            title=title,
            author=author,
            co_author=co_author,
            year_of_publication=year_of_publication,
            publisher=publisher_name,
            shelf_category=category_name, 
            primary_keyword=book_keyword,
            date_uploaded=date_uploaded,
            book_type=request.POST.get('bookType'),
            scanned_content=scanned_content,
            scanned_type=request.POST.get('scanned_type')
        )

        if book_cover:
            try:
                # If book cover exists, delete old one from Cloudinary
                if new_book.book_cover:
                    public_id = new_book.book_cover.name.split('/')[-1].split('.')[0]
                    destroy(public_id)  # Remove old image from Cloudinary

                # Upload new image to Cloudinary
                cloudinary_response = upload(book_cover)
                new_book.book_cover = cloudinary_response['secure_url']  # Save the URL to the model

            except Exception as e:
                messages.error(request, f"Error uploading book cover: {e}")
                return redirect('librarian_addbook')

        new_book.save()
        messages.success(request, 'Book successfully added!')
        return redirect('librarian_homepage')

    return render(request, 'librarian_AddBook.html', {
        'categories': categories,
        'publishers': publishers, 
        'user_info': user_info,
        'department_categories': department_categories, 
    })
    
@login_checker
@role_required('LIBRARIAN')
def librarian_profile(request):
    account_id = request.session.get('account_id')  # Try getting account_id from session

    if account_id:
        try:
            # Get the account information based on account_id
            account = AccountInformation.objects.get(account_id=account_id)
            user_info = get_user_info(account_id)
            # Get the corresponding user account information (role)
            user_account = UserAccounts.objects.get(account=account)  # This gets the role of the user
            
            if request.method == "POST":
                form_type = request.POST.get('form_type')
                
                if form_type == 'profile_update':
                    try:
                        # Handle Profile Update Form Submission

                        # 1. Handle First Name, Middle Name, and Last Name
                        first_name = request.POST.get('first_name')
                        middle_name = request.POST.get('middle_name')
                        last_name = request.POST.get('last_name')
                    

                        # Ensure that none of these fields are blank
                        if not first_name or not first_name.strip():
                            raise ValidationError("First name cannot be blank.")
                        if not last_name or not last_name.strip():
                            raise ValidationError("Last name cannot be blank.")
                            
                        # For middle_name, if it's empty or contains only invalid values, it will be set to None
                        if middle_name:
                            middle_name = middle_name.strip()
                            if middle_name.lower() in ['n/a', 'na', 'na', 'n/a']:
                                middle_name = None
                            else:
                                middle_name = middle_name.title()  # Capitalize first letter of each word
                        else:
                            middle_name = None

                        # Capitalize the first letter of each word for first and last names
                        first_name = first_name.strip().title()
                        last_name = last_name.strip().title()

                        # Update Account Information
                        account.first_name = first_name
                        account.middle_name = middle_name
                        account.last_name = last_name

                        # 2. Handle Address Fields
                        house_no = request.POST.get('house_no')
                        street_village = request.POST.get('street_village')
                        city = request.POST.get('city')
                        barangay = request.POST.get('barangay')
                        province = request.POST.get('province')
                        state = request.POST.get('state')

                        # Ensure that none of the address fields are blank
                        if not house_no or not house_no.strip():
                            raise ValidationError("House number cannot be blank.")
                        if not street_village or not street_village.strip():
                            raise ValidationError("Street or village cannot be blank.")
                        if not city or not city.strip():
                            raise ValidationError("City cannot be blank.")
                        if not barangay or not barangay.strip():
                            raise ValidationError("Barangay cannot be blank.")
                        if not province or not province.strip():
                            raise ValidationError("Province cannot be blank.")
                        if not state or not state.strip():
                            raise ValidationError("State cannot be blank.")
                        if any(char.isdigit() for char in state):
                            raise ValidationError("State must be a valid string and cannot contain numbers.")

                        # Ensure all are strings and trimmed, with proper length
                        account.house_no = str(house_no).strip()[:20]  # Truncate to max length 20
                        account.street_village = str(street_village).strip()[:100]  # Max length 100
                        account.city_municipality = str(city).strip()[:100]
                        account.barangay = str(barangay).strip()[:100]
                        account.province = str(province).strip()[:100]
                        account.state = str(state).strip()[:100]

                        # 3. Handle Zipcode (Only integers, between 0100 and 9811)
                        zipcode = request.POST.get('zipcode')
                        
                        if zipcode and re.match(r'^\d{4}$', zipcode) and 100 <= int(zipcode) <= 9811:
                            account.zipcode = zipcode
                        else:
                            raise ValidationError("Invalid Zipcode. It should be a 4-digit number between 0100 and 9811.")
                        
                        # Handle Birthdate (18+ age validation)
                        birthdate = request.POST.get('birthdate')

                        # Check if birthdate is provided
                        if not birthdate:  
                            raise ValidationError("Birthdate is required.")

                        # Proceed with parsing the date
                        try:
                            birth_date = datetime.strptime(birthdate, '%Y-%m-%d').date()  # Parse the birthdate
                        except ValueError:
                            raise ValidationError("Invalid birthdate format. Please use YYYY-MM-DD.")

                        # Calculate the age based on the birthdate
                        today = date.today()
                        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                        
                        
                        # Validate age (18+ and 80-)
                        if age < 18:
                            raise ValidationError("You must be at least 18 years old to register.")
                        elif age > 80:
                            raise ValidationError("You must be 80 years old or younger to register.")
                        
                        # If the age is valid, save the birthdate
                        account.birth_date = birth_date

                        # 5. Handle Gender (Valid options: Male, Female, Other)
                        gender = request.POST.get('gender')
                        # Ensure gender is selected (not empty)
                        if not gender:
                            raise ValidationError("Please select a valid gender.")
                        elif gender not in ['Male', 'Female', 'Other']:
                            raise ValidationError("Please select a valid gender.")
                        # Save the gender to the account
                        account.gender = gender


                        # 6. Handle Email (Must be a valid email address)
                        email = request.POST.get('email')
                        
                        try:
                            EmailValidator()(email)  # Use Django's email validator
                            account.email = email
                        except ValidationError:
                            raise ValidationError("Invalid email address.")

                        # 7. Handle Contact Number (Must be 11 digits, starting with 09)
                        # Retrieve the contact number from the form submission
                        contact_num = request.POST.get('contact_num')

                        # Check if contact_num is not None or empty before applying regex
                        if contact_num:
                            # Regex check: Validate the format of the contact number
                            if re.match(r'^09\d{9}$', contact_num):      
                                # If valid, save it to the account
                                account.contact_num = contact_num
                            else:
                                raise ValidationError("Invalid contact number. It must be 11 digits and start with '09'.")
                        else:
                            # Debugging: If no contact number is received
                            raise ValidationError("Contact number is required.")

                        # 8. Handle Username (Check if it exists already)
                        username = request.POST.get('username')
                        
                        
                        # Check if the username contains spaces
                        if ' ' in username:
                            raise ValidationError("Username should not contain spaces. Please choose another.")

                        min_length = 4
                        if len(username) < min_length:
                            raise ValidationError(f"Username must be at least {min_length} characters long. Please choose another.")
                        

                        if username != account.username:
                            # If the username has changed, check if it already exists in the database
                            if AccountInformation.objects.filter(username=username).exists():
                                raise ValidationError("This username is already taken. Please choose another.")
                            
                            # If the username is unique, update the account's username
                            account.username = username
                        

                        # Save the updated account information to the database
                        account.save()
                        messages.success(request, "Profile updated successfully.")

                    except ValidationError as ve:
                        logger.error(f"ValidationError occurred: {ve}")
                        # Log the full traceback
                        logger.error(traceback.format_exc())
                        messages.error(request, f"Error: {ve}")
                    
                    except Exception as e:
                        logger.error(f"An unexpected error occurred: {e}")
                        # Log the full traceback
                        logger.error(traceback.format_exc())
                        messages.error(request, "An unexpected error occurred. Please try again later.")

                elif form_type == 'image_upload':
                    cropped_image_data = request.POST.get('cropped_image')
                
                    if cropped_image_data:
                        try:
                            # Extract the base64 image data
                            format, imgstr = cropped_image_data.split(';base64,')  # Split the header and the data part
                            ext = format.split('/')[-1]  # Get the file extension (e.g., jpeg, png)
                
                            # Decode the base64 image
                            img_data = base64.b64decode(imgstr)
                            img_file = ContentFile(img_data, name=f"{account.account_id}-{account.first_name}-{account.last_name}.{ext}")
                
                            # Check and remove the old image from Cloudinary if exists
                            if account.profile_picture:
                                public_id = account.profile_picture.name.split('/')[-1].split('.')[0]
                                uploader.destroy(public_id)
                
                            # Upload the new image to Cloudinary
                            cloudinary_response = uploader.upload(img_file)
                
                            # Save the Cloudinary URL (secure_url) to the model and save the account
                            account.profile_picture = cloudinary_response['secure_url']  # Save the full URL
                            account.save()
                
                            messages.success(request, "Profile picture updated successfully.")
                
                        except Exception as e:
                            logger.error(f"Error uploading image to Cloudinary: {e}")
                            messages.error(request, "Error uploading profile picture. Please try again.")
                            return redirect('librarian_profile')
                    else:
                        messages.error(request, "No image data provided.")
                        return redirect('librarian_profile')            
                                    
                elif form_type == 'password_change':
                    try:
                        # Handle password change form submission
                        current_password = request.POST.get('current_password')
                        new_password = request.POST.get('new_password')
                        confirm_password = request.POST.get('confirm_password')

                        # 1st Check: verify current password against stored hash
                        if not check_password(current_password, account.password):
                            messages.error(request, "Incorrect current password.")
                        else:
                            # 2nd Check: New password not same as current
                            if check_password(new_password, account.password):
                                messages.error(request, "New password cannot be the same as the current password.")
                            # 3rd Check: New password meets the requirements
                            elif len(new_password) < 6:
                                messages.error(request, "Password must be at least 6 characters long.")
                            # 4th Check: New password == confirm password
                            elif new_password != confirm_password:
                                messages.error(request, "New password and confirm password do not match.")
                            else:
                                # Hash and save the new password
                                account.password = make_password(new_password)
                                account.save()
                                # Keep session valid after password change (optional)
                                try:
                                    update_session_auth_hash(request, account)
                                except Exception:
                                    pass
                                messages.success(request, "Password updated successfully.")
                                
                    except Exception as e:
                        # Log any exception that occurs
                        logger.error(f"Error during password change: {str(e)}", exc_info=True)
                        messages.error(request, "An error occurred while changing the password.")
                        
                return redirect('librarian_profile')  # Redirect after processing the form

            # Format birth_date as YYYY-MM-DD
            formatted_birthdate = DateFormat(account.birth_date).format('Y-m-d')

            context = {
                'account': account,  # Pass the account data to the template
                'role': user_account.role,  # Pass the role data to the template
                'formatted_birthdate': formatted_birthdate,  # Pass the formatted birthdate
                'user_info': user_info,
            }
            return render(request, 'librarian_profile.html', context)
        except AccountInformation.DoesNotExist:
            return redirect('login')  # Redirect to login page if account doesn't exist
        except UserAccounts.DoesNotExist:
            return redirect('login')  # Redirect to login page if the user account does not exist
    else:
        return redirect('login')  # Redirect to login page if account_id is not found

    # You can add logic to fetch and display librarian data if needed



@login_checker
@role_required('LIBRARIAN')
def librarian_search_history(request):
    from functools import lru_cache

    STOPWORDS = {
        'the','or','at','and','of','to','a','an','in','on','by','for','with','from',
        'is','are','as','that','this','these','those','be','was','were','been','it',
        'its','into','than','then','over','under','between','among','via','per','vs'
    }

    def _split_words_same_as_user(s: str):
        raw = (s or '').replace(',', ' ').split()
        out = []
        for w in raw:
            w = _re.sub(r'[^A-Za-z0-9]', '', w).strip()
            if not w or w in {'-', '–', '_'}:
                continue
            wl = w.lower()
            if wl not in STOPWORDS:
                out.append(wl)
        return out

    def _build_reference_vocab(row_limit=20000):
        vocab = set()
        for title, keywords in Books.objects.only('title', 'primary_keyword') \
                                           .values_list('title', 'primary_keyword')[:row_limit]:
            if title:
                for w in title.replace(',', ' ').split():
                    wl = w.strip().lower()
                    if len(wl) >= 3 and wl not in STOPWORDS:
                        vocab.add(wl)
            if keywords:
                for w in keywords.replace(',', ' ').split():
                    wl = w.strip().lower()
                    if len(wl) >= 3 and wl not in STOPWORDS:
                        vocab.add(wl)
        return list(vocab)

    @lru_cache(maxsize=1)
    def _get_vocab():
        return _build_reference_vocab()

    def _fuzzy_variants_same_as_user(token, n=7, cutoff=0.68):
        base = (token or "").lower()
        if not base:
            return []
        vocab = _get_vocab()
        matches = difflib.get_close_matches(base, vocab, n=n, cutoff=cutoff)
        if base not in matches:
            matches.insert(0, base)
        return matches

    def compute_book_results_count_same_as_user(query_str: str) -> int:
        """
        Mirror user_search for q=<string>:
        - split to tokens (stopwords removed)
        - for each token, OR fuzzy variants across (title|author|primary_keyword)
        - AND tokens together
        """
        tokens = _split_words_same_as_user(query_str)
        if not tokens:
            return 0

        qs = Books.objects.filter(is_archived=False)
        for t in tokens:
            variants = _fuzzy_variants_same_as_user(t, n=7, cutoff=0.68) or [t]
            q_or = Q()
            for v in variants:
                q_or |= (Q(title__icontains=v) |
                         Q(author__icontains=v) |
                         Q(primary_keyword__icontains=v))
            qs = qs.filter(q_or)
        return qs.count()

    # --- original logic (unchanged) ---
    account_id = request.session.get('account_id')
    user_info = get_user_info(account_id)

    # Normalize filter key
    tf_raw = request.GET.get('timeFilter', 'all')
    tf_key = (tf_raw or 'all').strip().lower().replace(' ', '').replace('_', '')
    if tf_key in ('24h', 'last24h'):
        time_filter = 'last24hours'
    elif tf_key in ('7d',):
        time_filter = 'last7days'
    elif tf_key in ('30d',):
        time_filter = 'last30days'
    else:
        time_filter = tf_key if tf_key in ('all', 'last24hours', 'last7days', 'last30days') else 'all'

    # Clock "now" and latest Last-Searched anchor from data
    now = timezone.now()
    latest_ts = KeywordLog.objects.aggregate(m=Max('updated_at'))['m'] or now

    # Pick Δ (period)
    if time_filter == 'last24hours':
        delta = timedelta(hours=24)
    elif time_filter == 'last7days':
        delta = timedelta(days=7)
    elif time_filter == 'last30days':
        delta = timedelta(days=30)
    else:
        delta = None  # all time

    # Effective window = intersection: [ max(now-Δ, latest-Δ) , latest ]
    if delta is None:
        keyword_logs_qs = KeywordLog.objects.all()
    else:
        start_a = now - delta
        start_b = latest_ts - delta
        start_date = start_a if start_a >= start_b else start_b
        keyword_logs_qs = KeywordLog.objects.filter(updated_at__gte=start_date, updated_at__lte=latest_ts)

    # Get search query
    query = request.GET.get('q', '').strip()
    
    # Apply search filter if query exists
    if query:
        keyword_logs_qs = keyword_logs_qs.filter(user_keyword_search__icontains=query)

    # Sort by search count after applying the time filter
    keyword_logs_qs = keyword_logs_qs.order_by('-user_search_count')

    # Paginate
    paginator = Paginator(keyword_logs_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Build payload
    logs_data = []
    for log in page_obj:
        kw = (getattr(log, 'user_keyword_search', '') or '').strip()
        book_results_count = compute_book_results_count_same_as_user(kw)

        logs_data.append({
            'user_keyword_search': kw,
            'user_search_count': log.user_search_count,
            'updated_at': log.updated_at.strftime('%Y-%m-%d %H:%M:%S') if log.updated_at else '',
            'book_results_count': book_results_count,  # used by template
            'user_info': user_info,
        })

    # AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'keyword_logs': logs_data,
            'currentPage': page_obj.number,
            'totalPages': paginator.num_pages,
            'timeFilter': time_filter,
            'anchor': latest_ts.strftime('%Y-%m-%d %H:%M:%S'),
        })

    # Render
    return render(
        request,
        'librarian_SearchHistory.html',
        {
            'keyword_logs': logs_data,
            'user_info': user_info,
            'page_obj': page_obj,
            'timeFilter': time_filter,
            'query': query,  
        }
    )
 
def logout_view(request):
    # Log the user out
    logout(request)

    # Redirect to login page
    return redirect('login')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Look for account with matching username and password
        account = AccountInformation.objects.filter(username=username).first()
        if not account:
            messages.error(request, "Invalid username or password.")
            return redirect('login')
        
        # Verify hashed password
        if not check_password(password, account.password):
            messages.error(request, "Invalid username or password.")
            return redirect('login')

        # Look for related user account info
        user_account = UserAccounts.objects.filter(account=account).first()
        if not user_account:
            messages.error(request, "No user role information found.")
            return redirect('login')

        # Reject deactivated accounts
        if user_account.account_status.upper() == 'DEACTIVATED':
            messages.error(request, "This account has been deactivated. Please contact admin.")
            return redirect('login')
            
            

        # ✅ Store account_id in session
        request.session['account_id'] = account.account_id
        request.session['username'] = account.username
        request.session['role'] = user_account.role.upper()

        if user_account.account_status.upper() == 'NEW':
            return redirect(f"/login/first_login/?account_id={account.account_id}")  # Goes to force_change_password.html

        role = user_account.role.upper()
        if role == 'ADMIN':
            return redirect('admin_homepage')
        elif role in ['LIBRARIAN', 'DEPARTMENT']: 
            return redirect('librarian_homepage')
        else:
            messages.error(request, "Unknown role type.")
            return redirect('login')  

    return render(request, 'login.html')

@login_required
def google_login_redirect(request):
    user = request.user

    try:
        # Get the social auth data for Google
        social_user = user.social_auth.get(provider='google-oauth2')
        print("✅ Extra Data from Google:", social_user.extra_data)
        gmail = social_user.extra_data['email']
        
        # ✅ Debug print — check what Gmail was returned
        print("✅ Gmail from Google:", gmail)

        # ✅ Match Gmail with your database
        account = AccountInformation.objects.get(email=gmail)
        user_account = UserAccounts.objects.get(account=account)

        # ❗️Check if account is deactivated
        if user_account.account_status.upper() == 'DEACTIVATED':
            messages.error(request, "This account has been deactivated. Please contact admin.")
            return redirect('login')

        # ✅ Store in session
        request.session['account_id'] = account.account_id
        request.session['username'] = account.username
        request.session['role'] = user_account.role.upper()

        # ✅ Redirect based on role and status
        if user_account.account_status.upper() == 'NEW':
            return redirect(f"/login/first_login/?account_id={account.account_id}")

        role = user_account.role.upper()
        if role == 'ADMIN':
            return redirect('admin_homepage')
        elif role in ['LIBRARIAN', 'DEPARTMENT']: 
            return redirect('librarian_homepage')
        else:
            messages.error(request, "Unknown role type.")
            return redirect('login')

    except AccountInformation.DoesNotExist:
        messages.error(request, "No account found for this Gmail.")
        return redirect('login')
    except Exception as e:
        messages.error(request, f"Login failed: {str(e)}")
        return redirect('login')


def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            account = AccountInformation.objects.get(email=email)
        except AccountInformation.DoesNotExist:
            messages.error(request, "Email not found. Please check and try again.")
            return render(request, 'forgotpass.html')

        # Generate OTP
        otp = generate_otp()
        expiration_time = timezone.now() + timedelta(minutes=5)

        # Save to ResetPassword table
        ResetPassword.objects.create(
            account=account,
            otp_code=otp,
            expires_at=expiration_time
        )
        
        # HTML Email Content
        html_content = f"""
        <html>
          <body style="background-color:#f4f4f4; padding:30px; font-family:Arial, sans-serif;">
            <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1); text-align:center;">
              
              <div style="margin-bottom: 3px;">
                <img src="https://cdn-icons-png.flaticon.com/128/18363/18363064.png" alt="Security Icon" width="45" style="margin-bottom: -3px;" />
              </div>
              <h1 style="color:#561c24; font-size: 42px; font-weight:900; margin: 0px;">LIRAYA</h1>
              
              <h3 style="color:#333; margin-top: 10px;">Email Verification Code</h3>

              <p style="color:#555;">
                Use the code below to verify your identity and securely reset your password for your <strong style="color:#561c24;">LIRAYA</strong> account.
                <br>
                This code will expire in <strong>5 minutes</strong>.
              </p>

              <div style="margin:20px 0; padding:15px; background-color:#f9f9f9; border:1px dashed #ccc; border-radius:5px;">
                <p style="font-size:14px; margin: 0;">
                  <strong>VERIFICATION CODE:</strong>
                  <strong style="color:#561c24; font-size:24px; letter-spacing: 3px;">{otp}</strong>
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

        # Send Email
        subject = "LIRAYA Password Reset Code"
        from_email = "lirayaautomated@gmail.com"
        to = [email]
        text_content = f"Your OTP code to reset your LIRAYA password is: {otp}. It will expire in 5 minutes."

        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()


        # Store the account_id temporarily in session for next step
        request.session['reset_account_id'] = account.account_id
        messages.success(request, "An OTP has been sent to your email.")

        return redirect('email_verification')

    return render(request, 'forgotpass.html')

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def resend_otp_view(request):
    email = request.GET.get('email')

    try:
        account = AccountInformation.objects.get(email=email)
    except AccountInformation.DoesNotExist:
        messages.error(request, "Account with this email does not exist.")
        return redirect('forgot_password')

    # Mark previous OTPs as used
    ResetPassword.objects.filter(account=account, is_used=False).update(is_used=True)

    # Create a new OTP
    new_otp = generate_otp()
    expires_at = timezone.now() + timezone.timedelta(minutes=5)

    ResetPassword.objects.create(
        account=account,
        otp_code=new_otp,
        is_used=False,
        expires_at=expires_at
    )

    # Send new OTP
    send_otp_email(email, new_otp)
    messages.success(request, "A new verification code has been sent to your email.")
    
    return redirect(f"{reverse('email_verification')}?email={email}")

def verification_view(request):
    account_id = request.session.get('reset_account_id')

    if not account_id:
        messages.error(request, "Session expired. Please restart the password reset process.")
        return redirect('forgot_password')

    try:
        account = AccountInformation.objects.get(account_id=account_id)
    except AccountInformation.DoesNotExist:
        messages.error(request, "Account not found.")
        return redirect('forgot_password')

    email = account.email  # For template

    if request.method == 'POST':
        # Combine 6 OTP inputs into one string
        otp_input = ''.join([request.POST.get(f'otp{i}', '') for i in range(1, 7)])

        try:
            reset = ResetPassword.objects.get(
                account_id=account_id,
                otp_code=otp_input,
                is_used=False,
                is_cancelled=False 
            )
        except ResetPassword.DoesNotExist:
            messages.error(request, "Invalid OTP code. Please try again.")
            return render(request, 'otp_verification.html', {'email': email})

        if reset.expires_at < timezone.now():
            messages.error(request, "OTP has expired. Please request a new one.")
            return render(request, 'otp_verification.html', {'email': email})

        # OTP is valid
        reset.is_used = True
        reset.save()

        # Pass verified ID to session
        request.session['reset_verified_account_id'] = account_id
        return redirect('change_password')

    # For GET requests, render with email in context
    return render(request, 'otp_verification.html', {'email': email})

def change_password_view(request):
    account_id = request.session.get('reset_verified_account_id')
    if not account_id:
        messages.error(request, "Session expired. Please start again.")
        return redirect('forgot_password')

    errors = {}

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if len(new_password) < 6:
            errors['new_password'] = "Password must be at least 6 characters."

        if errors:
            return render(request, 'change_password.html', {'errors': errors})

        account = get_object_or_404(AccountInformation, account_id=account_id)
        account.password = make_password(new_password)
        account.save()

        request.session.flush()
        messages.success(request, "Your password has been updated! Please log in.")
        return redirect('login')

    return render(request, 'change_password.html')



def cancel_otp_view(request):
    account_id = request.session.get('reset_account_id')
    
    if account_id:
        # Cancel any active OTPs
        ResetPassword.objects.filter(
            account_id=account_id,
            is_used=False,
            is_cancelled=False
        ).update(is_cancelled=True)

        # Clean up session
        request.session.pop('reset_account_id', None)

    return redirect('login')


def first_login_view(request):
    account_id = request.GET.get('account_id')  # Ensure account_id is passed

    if not account_id:
        messages.error(request, "Account ID is missing.")
        return redirect('login')

    account = get_object_or_404(AccountInformation, account_id=account_id)
    user_account = get_object_or_404(UserAccounts, account=account)
    
    errors = {} 

    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(old_password, account.password):
            errors['old_password'] = "Password is incorrect."

        if new_password != confirm_password:
             errors['confirm_password'] = "Passwords do not match."

        if check_password(new_password, account.password):
            errors['new_password'] = "New password must be different from the old password."
            
        if len(new_password) < 6:
            errors['new_password'] = "Password must be at least 6 characters long."

        if errors:
            return render(request, 'force_change_password.html', {
                'account_id': account_id,
                'errors': errors,
            })


        # Update the password and activate the account
        account.password = make_password(new_password)
        account.save()

        user_account.account_status = 'ACTIVE'
        user_account.previous_status= 'ACTIVE'
        user_account.save()
        
        messages.success(
            request,
            f"Password successfully updated! Please proceed to update your profile, {account.first_name}."
        )

        # Redirect based on role
        role = user_account.role.upper()
        if role == 'ADMIN':
            return redirect('admin_profile')
        elif role in ['LIBRARIAN', 'DEPARTMENT']:
            return redirect('librarian_profile')
        else:
            messages.error(request, "Unknown role. Please contact system administrator.")
            return redirect('login')

    return render(request, 'force_change_password.html', {'account_id': account_id})
