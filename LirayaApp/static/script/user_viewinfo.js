// ------------------------------
// user_viewinfo.js
// - Auto-open sidebar
// - Pages "Show Pages" modal (moved from inline)
// - Citation modal (APA/Chicago/MLA)
// ------------------------------

// ---------- Utilities ----------
function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function joinAuthors(author, coauthor) {
  const parts = [];
  if (author) parts.push(author);
  if (coauthor) parts.push(coauthor);
  return parts.join('; ');
}

// ---------- Auto-open sidebar on load ----------
document.addEventListener('DOMContentLoaded', function () {
  const sidebar = document.querySelector('.sidebar');
  if (sidebar && !sidebar.classList.contains('open')) {
    if (typeof toggleSidebar === 'function') toggleSidebar();
  }
});

// ---------- Citations Modal ----------
(function () {
  const citeBtn   = document.getElementById('cite-btn');
  const citeModal = document.getElementById('cite-modal');
  const closeBtn  = document.getElementById('close-cite-modal');
  const bodyEl    = document.getElementById('cite-modal-body');
  const metaEl    = document.getElementById('book-meta');

  if (!metaEl || !bodyEl || !citeBtn || !citeModal) return;

  function sentenceCase(str) {
    const s = String(str || '').trim();
    if (!s) return s;
    return s[0].toUpperCase() + s.slice(1).toLowerCase();
  }
  function headlineCase(str) {
    return String(str || '').replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1));
  }

  function buildCitations() {
    // Pull metadata
    const title     = metaEl?.dataset.title || '';
    const author    = metaEl?.dataset.author || '';
    const theCoauthors = metaEl?.dataset.coauthor || '';
    const year      = metaEl?.dataset.year || '';
    const publisher = metaEl?.dataset.publisher || '';

    // Authors
    const authorList = parseAuthors(author, theCoauthors);
    const apaAuthors = formatApaAuthorList(authorList); // "Last, F. M., & Last, F. M."
    const chicagoMlaAuthors = [author, theCoauthors].filter(Boolean).join('; ').trim();

    // Escapes
    const eApaAuthors = escapeHtml(apaAuthors);
    const eAuthorsCM  = escapeHtml(chicagoMlaAuthors);
    const eYear       = escapeHtml(year);
    const ePublisher  = escapeHtml(publisher);

    const titleAPA = escapeHtml(sentenceCase(title));
    const titleHL  = escapeHtml(headlineCase(title));

    // APA 7: Author(s). (Year). *Title in sentence case*. Publisher.
    const apa = `
      <div style="margin-bottom:10px;">
        <strong>APA (7th ed.) Citation</strong><br>
        ${eApaAuthors ? eApaAuthors + '. ' : ''}
        ${eYear ? '(' + eYear + '). ' : ''}
        ${titleAPA ? '<em>' + titleAPA + '</em>. ' : ''}
        ${ePublisher ? ePublisher + '.' : ''}
      </div>
    `;

    // Chicago 17 (Notes & Bibliography): Author(s). *Title in Headline Case*. Publisher, Year.
    const chicago = `
      <div style="margin-bottom:10px;">
        <strong>Chicago Style (17th ed., Notes & Bibliography)</strong><br>
        ${eAuthorsCM ? eAuthorsCM + '. ' : ''}
        ${titleHL ? '<em>' + titleHL + '</em>. ' : ''}
        ${ePublisher ? ePublisher + ', ' : ''}${eYear ? eYear + '.' : ''}
      </div>
    `;

    // MLA 9: Author(s). *Title in Title Case*. Publisher, Year.
    const mla = `
      <div style="margin-bottom:10px;">
        <strong>MLA (9th ed.) Citation</strong><br>
        ${eAuthorsCM ? eAuthorsCM + '. ' : ''}
        ${titleHL ? '<em>' + titleHL + '</em>. ' : ''}
        ${ePublisher ? ePublisher + ', ' : ''}${eYear ? eYear + '.' : ''}
      </div>
    `;

    const warn = `
      <div style="margin-top:6px; font-size:12px; color:#555;">
        <em></em>
      </div>
    `;

    return apa + chicago + mla + warn;
  }

  function openCiteModal() {
    bodyEl.innerHTML = buildCitations();
    citeModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeCiteModal() {
    citeModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  citeBtn.addEventListener('click', openCiteModal);
  closeBtn && closeBtn.addEventListener('click', closeCiteModal);
  citeModal.addEventListener('click', function (e) {
    if (e.target === citeModal) closeCiteModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && citeModal.style.display === 'flex') closeCiteModal();
  });
})();

// ---------- Pages Modal (moved from inline script) ----------
(function () {
  const btn     = document.getElementById('show-pages-btn');
  const wrap    = document.getElementById('pages-table-wrapper');
  const anchor  = document.getElementById('pages-anchor');
  const holder  = document.getElementById('scanned-content-holder');
  const rawAttr = holder ? holder.dataset.content || '' : '';

  // Decode \uXXXX sequences that come from Django's escapejs
  function decodeJsUnicodeEscapes(s) {
    if (!s) return '';
    return s
      .replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) =>
        String.fromCharCode(parseInt(hex, 16))
      )
      .replace(/\\u/g, ' '); // any stray "\u" without 4 hex digits -> space
  }

  const raw = decodeJsUnicodeEscapes(rawAttr);
  // If this looks like a thesis ABSTRACT, hide the button and bail out early
  if (/\babstract\b/i.test(raw)) {
    if (btn) btn.style.display = 'none';
    return; // do not wire up modal at all
  }


  const modal      = document.getElementById('pages-modal');
  const modalBody  = document.getElementById('pages-modal-body');
  const modalClose = document.getElementById('close-pages-modal');

  if (!modal || !modalBody || !wrap || !btn) return;

  let built = false;

  function normalizeText(text) {
    if (!text) return '';
    let s = text;
  
    // Remove zero-width and joiners entirely (do NOT turn into spaces)
    s = s.replace(/[\u200B\u200C\u200D\u2060\uFEFF]/g, '');
  
    // Remove micro/uncommon spaces ONLY when they appear between letters
    // (prevents A C K … artifacts from OCR)
    s = s.replace(/([A-Za-z])[\u2000-\u200A\u202F\u205F]+(?=[A-Za-z])/g, '$1');
  
    // Convert remaining exotic spaces to regular spaces (word separators)
    s = s.replace(/[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]/g, ' ');
  
    // Normalize dash/minus/hyphen variants to a simple hyphen
    s = s.replace(/[\u2010-\u2015\u2212\uFE63\uFF0D]/g, '-');
  
    // Collapse extra spaces
    s = s.replace(/\s{2,}/g, ' ');
  
    // "Electron, 57-58" -> "Electron 57-58"
    s = s.replace(/,\s*(?=\d)/g, ' ');
  
    // Ensure digits and letters are separated BOTH ways (safe)
    s = s.replace(/([A-Za-z\)\]\.])(\d)/g, '$1 $2');   // letter before digit
    s = s.replace(/(\d)(?=[A-Za-z(])/g, '$1 ');        // digit before letter
    s = s.replace(/(\d)(?=[A-Z])/g, '$1 ');            // digit before capital
  
    return s.trim();
  }

  function parsePairs(text) {
    const cleaned = normalizeText(text);
    if (!cleaned) return [];
  
    // We will split more precisely INSIDE the loop when we detect glued tokens
    const tokens = cleaned.split(/\s+/);
    const pairs = [];
    let words = [];
    let i = 0;
  
    // Accept clean page tokens: "12", "12,13,15", "12-14", "12–14", "12—14"
    // Tolerate trailing ";" or "," on each token.
    const isPageChunk = (rawTok) => {
      const t = String(rawTok).replace(/[;,]$/, ''); // drop trailing semicolon/comma
      return /^\d+(?:(?:[,\-–—]\d+)+)?$/.test(t);
    };
  
    // Break up glued tokens like:
    //   "Chapter12" -> ["Chapter","12"]
    //   "FOREWORDvii" -> ["FOREWORD","vii"]  (roman part handled as text, not page)
    //   "ixChapter" -> ["ix","Chapter"]
    //   "Figure3" -> ["Figure","3"]
    function splitTokenIfGlued(tok) {
      let m;
  
      // Chapter/Figure (with common OCR typos) glued to digits
      m = tok.match(/^(chapter|chaptr|chaptre|ciapter|figure|figuer|figre)(\d+)$/i);
      if (m) return [m[1], m[2]];
  
      // Letters glued to digits at the end: "Keyword31"
      m = tok.match(/^([A-Za-z]+)(\d+)$/);
      if (m) return [m[1], m[2]];
  
      // Letters glued to roman numerals at the end (≥2)
      m = tok.match(/^([A-Za-z]{3,})([ivxlcdm]{2,})$/i);
      if (m) return [m[1], m[2]];
  
      // Roman numerals glued before Chapter/Figure
      m = tok.match(/^([ivxlcdm]{2,})(chapter|chaptr|chaptre|ciapter|figure|figuer|figre)$/i);
      if (m) return [m[1], m[2]];
  
      return null;
    }
  
    // Ignore headings and titles that shouldn't become keywords
    function isIgnorableKeyword(str) {
      const s = str.trim();
  
      // Chapter/Figure headings (with typos)
      if (/^(chapter|chaptr|chaptre|ciapter)\s*\d+$/i.test(s)) return true;
      if (/^(figure|figuer|figre)\s*\d+$/i.test(s)) return true;
  
      // Front matter with Roman numerals
      if (/^(foreword|acknowledgments?|introduction)\s+[ivxlcdm]+$/i.test(s)) return true;
      if (/^[A-Za-z]{3,}\s+[ivxlcdm]{2,}$/i.test(s)) return true;
  
      // Standalone year (any 4 digits)
      if (/^\d{4}$/.test(s)) return true;
  
      // 1D/2D/3D (allow "3 D")
      if (/^[123]\s*D$/i.test(s)) return true;
  
      // MODULE n
      if (/^module\s+\d+$/i.test(s)) return true;
  
      return false;
    }
  
    while (i < tokens.length) {
      let tok = tokens[i];
  
      // If token is glued, split it in-place so subsequent logic sees parts separately
      const split = splitTokenIfGlued(tok);
      if (split) {
        tokens.splice(i, 1, split[0], split[1]);
        tok = tokens[i];
      }
  
      if (!isPageChunk(tok)) {
        // strip trailing separators from keyword tokens too
        words.push(tok.replace(/[;,]$/, ''));
        i++;
        continue;
      }
      if (words.length === 0) { i++; continue; }
  
      // Collect contiguous page-like chunks ("12", "12-14", "12,13", incl. en/em dashes)
      const pageParts = [];
      while (i < tokens.length) {
        const nextTok = tokens[i];
        const s2 = splitTokenIfGlued(nextTok);
        if (s2) tokens.splice(i, 1, s2[0], s2[1]);
  
        if (!isPageChunk(tokens[i])) break;
  
        // Normalize any dash variant to a simple hyphen; strip trailing semicolons/commas
        const normalized = String(tokens[i]).replace(/[;,]$/, '').replace(/[–—]/g, '-');
        pageParts.push(normalized);
        i++;
      }
  
      // Preserve ranges & comma lists
      const pages = pageParts.length ? pageParts.join(', ') : '—';
  
      const keyword = words.join(' ').replace(/\s+/g, ' ').trim();
  
      if (isIgnorableKeyword(keyword)) {
        words = [];
        continue;
      }
  
      if (keyword) pairs.push({ keyword, pages });
      words = [];
    }
  
    if (words.length) {
      const keyword = words.join(' ').trim();
      if (!isIgnorableKeyword(keyword)) {
        pairs.push({ keyword, pages: '—' });
      }
    }
  
    return pairs;
  }


  function buildTable() {
    const tbody = document.querySelector('#pages-table tbody');
    if (!tbody) return;
  
    const pairs = parsePairs(raw);
  
    // ---- 1) Group by keyword (case-insensitive) and merge pages ----
    const groups = new Map();
    const splitPages = (pagesStr) =>
      String(pagesStr)
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);
  
    for (const p of pairs) {
      const key = String(p.keyword).trim().toLowerCase();
      if (!key) continue;
  
      if (!groups.has(key)) {
        groups.set(key, {
          keyword: p.keyword,          // keep original casing from first appearance
          pageSet: new Set(),          // to dedupe page tokens
          pageList: [],                // to preserve first-seen order
          hasNumeric: false,           // to help with the "hide button" logic
        });
      }
  
      const g = groups.get(key);
  
      // Merge pages: ignore '—' if we already have numeric pages
      if (p.pages && p.pages !== '—') {
        const tokens = splitPages(p.pages);
        for (const tok of tokens) {
          if (!g.pageSet.has(tok)) {
            g.pageSet.add(tok);
            g.pageList.push(tok);
          }
          if (/\d/.test(tok)) g.hasNumeric = true;
        }
      } else {
        // If no pages yet, allow '—' as placeholder
        if (g.pageList.length === 0) {
          g.pageSet.add('—');
          g.pageList.push('—');
        }
      }
    }
  
    // Convert groups back to array of { keyword, pages }
    const merged = [];
    for (const g of groups.values()) {
      // If we ended up with tokens and also had an initial '—', drop the '—'
      let list = g.pageList;
      if (list.length > 1 && list.includes('—')) {
        list = list.filter(t => t !== '—');
      }
      const pages = list.length ? list.join(', ') : '—';
      merged.push({ keyword: g.keyword, pages, _hasNumeric: g.hasNumeric });
    }
  
    // ---- 2) Sort: special-characters first, then A→Z (case-insensitive) ----
    const collator = new Intl.Collator('en', { sensitivity: 'base' });
    const startsWithLetter = s => /^[A-Za-z]/.test(String(s).trim());
  
    merged.sort((a, b) => {
      const aIsLetter = startsWithLetter(a.keyword) ? 1 : 0; // 0 = special, 1 = letters
      const bIsLetter = startsWithLetter(b.keyword) ? 1 : 0;
      if (aIsLetter !== bIsLetter) return aIsLetter - bIsLetter; // specials first
      return collator.compare(a.keyword, b.keyword);
    });
  
    // ---- 3) Hide button if nothing numeric remains ----
    const hasPages = merged.some(p => /\d/.test(p.pages));
    if (!hasPages) {
      const btn = document.getElementById('show-pages-btn');
      if (btn) btn.style.display = 'none';
      built = true;
      return;
    }
  
    if (!merged.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="2">No page index available.</td>';
      tbody.appendChild(tr);
      built = true;
      return;
    }
  
    // ---- 4) Render (BOLD + UPPERCASE titles) ----
    merged.forEach((p, idx) => {
      const tr = document.createElement('tr');
      tr.className = idx % 2 === 0 ? 'row-odd' : 'row-even';
      const esc = (v) =>
        String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
      tr.innerHTML = `<td><strong>${esc(p.keyword).toUpperCase()}</strong></td><td>${esc(p.pages)}</td>`;
      tbody.appendChild(tr);
    });
  
    built = true;
  }



  function openModal() {
    if (!built) buildTable();
    if (modalBody && wrap) {
      wrap.style.display = 'block';
      modalBody.appendChild(wrap);
    }
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (btn) btn.textContent = 'Hide Pages';
  }

  function closeModal() {
    if (anchor && wrap && anchor.parentNode) {
      anchor.insertAdjacentElement('afterend', wrap);
      wrap.style.display = 'none';
    }
    modal.style.display = 'none';
    document.body.style.overflow = '';
    if (btn) btn.textContent = 'Show Pages';
  }

  btn.addEventListener('click', function () {
    const isOpen = modal.style.display !== 'none' && modal.style.display !== '';
    if (isOpen) closeModal();
    else openModal();
  });

  modalClose && modalClose.addEventListener('click', closeModal);
  modal.addEventListener('click', function (e) {
    if (e.target === modal) closeModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      const isOpen = modal.style.display !== 'none' && modal.style.display !== '';
      if (isOpen) closeModal();
    }
  });
})();

function parseAuthors(primaryAuthor, coAuthors) {
  // Combine primary + co-authors into a single array of raw strings
  const raw = []
  if (primaryAuthor) raw.push(String(primaryAuthor))
  if (coAuthors) raw.push(String(coAuthors))

  // Join using a sentinel, then split ONLY on strong delimiters that aren't commas-in-names.
  const joined = raw.join(' ; ')

  // Allowed separators: semicolon ;  pipe |  slash /  " and "  " & "  newline
  const parts = joined
    .split(/\s*(?:;|\||\/|\band\b|&|\r?\n)\s*/i)
    .map(s => s.trim())
    .filter(Boolean)

  return parts
}

function toApaInitials(givenAndMiddle) {
  if (!givenAndMiddle) return ''
  // remove honorifics accidentally typed into given names
  const cleaned = givenAndMiddle
    .replace(/\b(Mr|Mrs|Ms|Miss|Dr|Prof)\.?\b/gi, '')
    .trim()

  if (!cleaned) return ''

  return cleaned
    .split(/\s+/)
    .filter(Boolean)
    .map(tok => {
      // Hyphenated given names → J.-L. pattern
      if (tok.includes('-')) {
        return tok
          .split('-')
          .filter(Boolean)
          .map(seg => (seg[0] || '').toUpperCase() + '.')
          .join('-')
      }
      return (tok[0] || '').toUpperCase() + '.'
    })
    .join(' ')
}

function nameToApa(rawName) {
  if (!rawName) return ''

  // Trim weird spaces and remove common suffixes from the *end*
  let name = String(rawName)
    .replace(/[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000]/g, ' ')
    .replace(/\s+(Jr\.?|Sr\.?|III|II|IV)\s*$/i, '')
    .trim()

  // Case 1: "Last, First Middle"
  if (name.includes(',')) {
    const [last, rest] = name.split(',', 2).map(s => s.trim()).filter(Boolean)
    const initials = toApaInitials(rest || '')
    return last ? (initials ? `${last}, ${initials}` : last) : initials
  }

  // Case 2: "First Middle Last"
  const tokens = name.split(/\s+/).filter(Boolean)
  if (tokens.length === 1) return tokens[0]

  const last = tokens[tokens.length - 1]
  const given = tokens.slice(0, -1).join(' ')
  const initials = toApaInitials(given)
  return `${last}, ${initials}`
}

function formatApaAuthorList(authorArray) {
  const formatted = authorArray.map(nameToApa).filter(Boolean)

  // APA 7: use comma between authors, and an ampersand before the final author.
  if (formatted.length <= 1) return formatted.join('')
  if (formatted.length === 2) return `${formatted[0]} & ${formatted[1]}`
  return `${formatted.slice(0, -1).join(', ')}, & ${formatted[formatted.length - 1]}`
}

function copyPageLink() {
  const url = window.location.href;

  // Modern API first
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(url)
      .then(() => showToast('Link copied to clipboard'))
      .catch(() => legacyCopy(url));
  } else {
    legacyCopy(url);
  }

  function legacyCopy(text) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showToast('Link copied to clipboard');
    } catch (e) {
      // Absolute fallback
      window.prompt('Copy this link:', text);
    }
  }
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.position = 'fixed';
  toast.style.left = '50%';
  toast.style.bottom = '24px';
  toast.style.transform = 'translateX(-50%)';
  toast.style.padding = '10px 14px';
  toast.style.background = '#3e151a';
  toast.style.color = '#fff7f7';
  toast.style.borderRadius = '8px';
  toast.style.fontSize = '14px';
  toast.style.boxShadow = '0 6px 18px rgba(0,0,0,0.25)';
  toast.style.zIndex = '99999';
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity 220ms ease';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 240);
  }, 1200);
}
function bindCopyLinkButton() {
  const btn = Array.from(document.querySelectorAll('.action-btn'))
    .find(el => el.textContent.trim().toLowerCase() === 'copy page link');
  if (!btn) return;
  btn.addEventListener('click', function(e) {
    e.preventDefault();
    copyPageLink();
  });
}
document.addEventListener('DOMContentLoaded', bindCopyLinkButton);



function initQrCode() {
  const openBtn    = document.getElementById('btn-qr');
  const modal      = document.getElementById('qr-modal');
  const closeBtn   = document.getElementById('close-qr-modal');
  const imgEl      = document.getElementById('qr-image');
  const dlBtn      = document.getElementById('qr-download');
  const openImgBtn = document.getElementById('qr-open-new');

  if (!openBtn || !modal || !imgEl) return;

  function buildQrSrc(urlString) {
    const data = encodeURIComponent(urlString);
    return `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${data}`;
  }

  function openModal() {
    const url = window.location.href;          // current page link
    imgEl.src = buildQrSrc(url);
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  openBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  modal.addEventListener('click', function (e) {
    if (e.target === modal) closeModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal.style.display === 'flex') closeModal();
  });

  if (dlBtn) {
    dlBtn.addEventListener('click', async function (e) {
      e.preventDefault();
      const src = imgEl && imgEl.src;
      if (!src) return;

      try {
        const res = await fetch(src, {
          mode: 'cors',
          cache: 'no-cache',
          referrerPolicy: 'no-referrer',
        });
        if (!res.ok) throw new Error('Failed to fetch QR image');
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = 'liraya-qr.png';
        document.body.appendChild(a);
        a.click();
        a.remove();

        setTimeout(() => URL.revokeObjectURL(blobUrl), 1500);
      } catch (err) {
        console.warn('QR direct download failed; opening in new tab instead.', err);
        window.open(src, '_blank', 'noopener');
      }
    });
  }

  if (openImgBtn) {
    openImgBtn.addEventListener('click', function () {
      if (imgEl && imgEl.src) window.open(imgEl.src, '_blank', 'noopener');
    });
  }
}

// Ensure it runs
document.addEventListener('DOMContentLoaded', initQrCode);

(function () {
  // Hide "Show Pages" if scanned content contains the word "Abstract" (case-insensitive)
  function decodeJsUnicodeEscapes(s) {
    if (!s) return '';
    return s
      .replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
      .replace(/\\u/g, ' ');
  }

  document.addEventListener('DOMContentLoaded', function () {
    const holder = document.getElementById('scanned-content-holder');
    const btn    = document.getElementById('show-pages-btn');
    if (!holder || !btn) return;

    const rawAttr  = holder.dataset.content || '';
    const decoded  = decodeJsUnicodeEscapes(rawAttr);

    // Case-insensitive whole-word match for "abstract"
    if (/\babstract\b/i.test(decoded)) {
      btn.style.display = 'none';
    }
  });
})();


// === Add-only: strip numbered prefixes like "1.", "1.1", "1.1.2", "3.1,3" ===
(function () {
  // Remove leading outline numbers (handles dots OR commas between levels, and trailing "." or ")" or whitespace)
  function stripHeadingNumber(s) {
    return String(s || '')
      .replace(/^\s*\d+(?:[.,]\d+)*(?:[.)]|\s+)\s*/ , '')  // e.g., "1. ", "1.1 ", "1.1.2 ", "3.1,3 "
      .trim();
  }

  // Preserve original, then wrap
  const _origParsePairs = window.parsePairs || parsePairs;
  window.parsePairs = function (text) {
    const pairs = _origParsePairs(text) || [];
    return pairs
      .map(p => ({
        keyword: stripHeadingNumber(p.keyword),
        pages: p.pages
      }))
      .filter(p => p.keyword); // drop rows that became empty after stripping
  };
})();

// === ADD-ONLY WRAP: protect "3D/2D/1D", strip outline numbers like "1.", "1.1", etc. ===
(function () {
  // Use a harmless sentinel character for D so digit-letter split won't trigger on it.
  // Here we use Latin capital D with dot below: U+1E0E (looks like 'Ḏ').
  const SENTINEL_D = '\u1E0E';

  // Protect occurrences like "3D", "3-D", "3 D" (and 1/2 as well) so normalizeText won't split "3D".
  function protectDimensionalTokens(s) {
    return String(s || '')
      // normalize "3 - D" → "3D" first
      .replace(/\b([123])\s*-\s*D\b/gi, '$1D')
      .replace(/\b([123])\s*D\b/gi, (_, d) => `${d}${SENTINEL_D}`);
  }

  // Restore sentinel back to normal "D"
  function unprotectDimensionalTokens(s) {
    return String(s || '').replace(new RegExp(SENTINEL_D, 'g'), 'D');
  }

  // Remove leading numbering like "1.", "1.1", "1.1.2", "3.1,3", optionally followed by "." or ")" and space
  function stripHeadingNumber(s) {
    return String(s || '')
      .replace(/^\s*\d+(?:[.,]\s*\d+)*(?:[.)]|\s+)?\s*/ , '')
      .trim();
  }

  // Detect keywords that are ONLY numbering (so we drop them entirely)
  function isPureHeadingNumber(s) {
    return /^\s*\d+(?:[.,]\s*\d+)*\.?\s*$/.test(String(s || ''));
  }

  // Keep original, then wrap
  const _origParsePairs = (typeof window !== 'undefined' && window.parsePairs) ? window.parsePairs : parsePairs;

  // Override global parsePairs by wrapping (no edits to original)
  function wrappedParsePairs(text) {
    // 1) Protect 1D/2D/3D before parsing to avoid "3" being counted as a page
    const protectedText = protectDimensionalTokens(text);

    // 2) Run original parser
    const pairs = _origParsePairs(protectedText) || [];

    // 3) Post-process keywords: unprotect D, strip numbering, drop empty/pure-numbering rows
    const out = [];
    for (const p of pairs) {
      let k = unprotectDimensionalTokens(p.keyword);
      k = stripHeadingNumber(k);
      if (!k || isPureHeadingNumber(k)) continue;
      out.push({ keyword: k, pages: p.pages });
    }
    return out;
  }

  if (typeof window !== 'undefined') {
    window.parsePairs = wrappedParsePairs;
  } else {
    // fallback (if not in browser global)
    parsePairs = wrappedParsePairs; // eslint-disable-line no-global-assign
  }
})();
