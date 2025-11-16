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

  // === Helpers just for citations ===

  // Whole-field NA like "N/A", "NA", "None", "-"
  const isNAField = (v) => /^(?:n\/?a|n\.?\s*a\.?|na|none|-)\s*$/i.test(String(v || '').trim());
  const cleanField = (v) => (isNAField(v) ? '' : String(v || '').trim());

  // Protect N/A before parseAuthors (so "/"-split won't break it)
  const SENTINEL_SLASH = '\u2215'; // looks like '/', used to protect
  const protectNA = (s) => String(s || '').replace(/\bn\s*\/\s*a\b/gi, m =>
    m.replace('/', SENTINEL_SLASH).replace(/\s+/g, '')
  );

  // Strip leading/trailing punctuation for token checks
  const stripPunct = (s) => String(s || '').replace(/^[\s,.;:]+|[\s,.;:]+$/g, '').trim();

  // Token-level NA: catch N/A, N & A, N and A, lone N / A, with optional periods
  const isNAToken = (v) => {
    const s = stripPunct(v).replace(/\./g, '');
    return /^\s*n\s*(?:\/|&|\+|and)?\s*a\s*$/i.test(s) || /^(?:n|a)$/i.test(s);
  };

  // Normalize any NA variant to literal "N/A"
  const normalizeNAToken = (v) => (isNAToken(v) ? 'N/A' : stripPunct(v));

  // Expand "Smith, John, Doe, Jane" → ["Smith, John", "Doe, Jane"]
  function explodeCommaAuthors(token) {
    const s = String(token || '').trim();
    if (!s) return [];
    const pairs = s.match(/[^,]+,\s*[^,]+/g);
    if (pairs && pairs.length >= 2) return pairs.map(t => t.trim());
    if (s.includes(',') && s.split(',').length > 2) {
      return s.split(',').map(t => t.trim()).filter(Boolean);
    }
    return [s];
  }

  // --- MLA: ensure single-letter initials in the given/middle names get a trailing period (e.g., "C." not "C") ---
  function ensureInitialPeriods(givenPart) {
    return String(givenPart || '')
      .split(/\s+/)
      .filter(Boolean)
      .map(tok => {
        // If token is a single letter (with or without a dot), force "X."
        const m = tok.match(/^([A-Za-z])\.?$/);
        if (m) return m[1].toUpperCase() + '.';
        return tok; // leave full words as-is
      })
      .join(' ');
  }

  // MLA full names (invert to "Last, First Middle" if not already inverted) + add periods to one-letter tokens
  function toFullNameInverted(rawName) {
    if (!rawName) return '';
    if (rawName === 'N/A') return 'N/A';

    let name = String(rawName)
      .replace(/[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000]/g, ' ')
      .replace(/\s+(Jr\.?|Sr\.?|III|II|IV)\s*$/i, '')
      .replace(/\s{2,}/g, ' ')
      .trim();

    if (!name) return '';

    if (name.includes(',')) {
      // Already "Last, First Middle" -> normalize the given/middle side
      const [last, given = ''] = name.split(',', 2).map(s => s.trim());
      const fixedGiven = ensureInitialPeriods(given);
      return `${last}, ${fixedGiven}`;
    }

    // "First Middle Last" -> invert and fix initials on the given part
    const parts = name.split(/\s+/);
    if (parts.length === 1) return parts[0];
    const last  = parts.pop();
    const given = ensureInitialPeriods(parts.join(' '));
    return `${last}, ${given}`;
  }

  function mlaFullAuthorList(authorArray) {
    const items = authorArray.map(toFullNameInverted).filter(Boolean);
    if (items.length <= 1) return items.join('');
    if (items.length === 2) return `${items[0]} and ${items[1]}`;
    return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
  }

  function buildCitations() {
    // Pull metadata; treat NA-like whole fields as empty
    const titleRaw     = metaEl?.dataset.title || '';
    const authorRaw    = metaEl?.dataset.author || '';
    const coauthorsRaw = metaEl?.dataset.coauthor || '';
    const yearRaw      = metaEl?.dataset.year || '';
    const publisherRaw = metaEl?.dataset.publisher || '';

    const title     = cleanField(titleRaw);
    const year      = cleanField(yearRaw);
    const publisher = cleanField(publisherRaw);

    // Build authors: protect N/A before parseAuthors, then normalize tokens to "N/A"
    let authorList = parseAuthors(protectNA(authorRaw), protectNA(coauthorsRaw));
    authorList = authorList
      .flatMap(explodeCommaAuthors)
      .map(s => s.replace(new RegExp(SENTINEL_SLASH, 'g'), '/')) // restore "/"
      .map(normalizeNAToken)
      .filter(Boolean);

    // Dedupe authors (so multiple identical entries collapse to one)
    const seen = new Set();
    authorList = authorList.filter(a => {
      const key = a.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // If the remaining "authors" are effectively N/A / NA / NONE / blank, treat as no authors
    const hasRealAuthors = authorList.some(a => !isNAField(a));
    if (!hasRealAuthors) {
      authorList = [];
    }


    // Strings for rendering
    const apaAuthorsStr = formatApaAuthorList(authorList);   // APA initials; "N/A" stays "N/A"
    const mlaAuthorsStr = mlaFullAuthorList(authorList);     // MLA full names; "N/A" stays "N/A"

    const eApaAuthors = escapeHtml(apaAuthorsStr);
    const eMlaAuthors = escapeHtml(mlaAuthorsStr);
    const eYearAPA    = escapeHtml(year || 'n.d.');          // APA -> (n.d.)
    const eYearMLA    = escapeHtml(year || 'n.d.');          // MLA prints n.d.
    const ePubl       = escapeHtml(publisher);
    const titleAPA    = escapeHtml(sentenceCase(title));      // APA sentence case
    const titleMLA    = escapeHtml(headlineCase(title));      // MLA title case (approx.)

    // ---------- APA 7th ----------
    let apaLine = '<strong>APA (7th ed.)</strong><br>';
    if (authorList.length && eApaAuthors) {
      apaLine += `${eApaAuthors}. `;
    } else if (titleAPA) {
      apaLine += `<em>${titleAPA}</em>. `;
    }
    apaLine += `(${eYearAPA}). `;
    if (authorList.length && titleAPA) {
      apaLine += `<em>${titleAPA}</em>. `;
    }
    if (ePubl) apaLine += `${ePubl}.`;
    const apa = `<div style="margin-bottom:10px;">${apaLine}</div>`;

    // ---------- MLA 9th ----------
    const mlaParts = [];
    if (authorList.length && eMlaAuthors) mlaParts.push(`${eMlaAuthors}.`);
    if (titleMLA) mlaParts.push(`<em>${titleMLA}</em>.`);
    const tail = [ePubl, eYearMLA].filter(Boolean).join(', ');
    if (tail) mlaParts.push(tail + '.');
    const mla = `
      <div style="margin-bottom:10px;">
        <strong>MLA (9th ed.)</strong><br>
        ${mlaParts.join(' ')}
      </div>
    `;

    return apa + mla;
  }

  function openCiteModal() {
    bodyEl.innerHTML = buildCitations();

    // --- PATCH: restore original title casing for APA using data-title ---
    try {
      const rawTitle = (metaEl && metaEl.dataset && metaEl.dataset.title
        ? metaEl.dataset.title
        : ''
      ).trim();

      if (rawTitle) {
        // Assumption: first citation block produced by buildCitations() is APA
        const apaBlock = bodyEl.querySelector('div');
        if (apaBlock) {
          const emEls = apaBlock.querySelectorAll('em');
          if (emEls && emEls.length) {
            emEls.forEach(function (el) {
              // Force APA title to use the original casing (e.g., "Computer Engineering")
              el.textContent = rawTitle;
            });
          }
        }
      }
    } catch (e) {
      // Fail silent; do not impact modal behavior if anything goes wrong
    }
    // --- END PATCH ---

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

  // Hide Show Pages for Thesis types (do not wire up modal at all)
  const meta = document.getElementById('book-meta');
  const bookType = (meta?.dataset?.type || '').trim().toLowerCase();
  if (bookType === 'thesis') {
    if (btn) btn.style.display = 'none';
    return; // do not wire up modal at all
  }
  
  const raw = decodeJsUnicodeEscapes(rawAttr);



  const modal      = document.getElementById('pages-modal');
  const modalBody  = document.getElementById('pages-modal-body');
  const modalClose = document.getElementById('close-pages-modal');

  if (!modal || !modalBody || !wrap || !btn) return;

  let built = false;

  function normalizeText(text) {
    if (!text) return '';
    let s = text;

    // Remove discretionary/soft hyphen so words don't split (e.g., "SOL­ID" -> "SOLID")
    s = s.replace(/\u00AD/g, '');
    
    // Remove zero-width and joiners entirely (do NOT turn into spaces)
    s = s.replace(/[\u200B\u200C\u200D\u2060\uFEFF]/g, '');
  
    // Remove micro/uncommon spaces ONLY when they appear between letters
    // (prevents A C K … artifacts from OCR)
    s = s.replace(/([A-Za-z])[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+(?=[A-Za-z])/g, '$1');
  
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
    // --- Protect 1D/2D/3D (and 1-D/2-D/3-D, 1 D/2 D/3 D) before normalization so "3" isn't seen as a page ---
    const SENTINEL_D = '\u1E0E'; // Latin capital D with dot below
    function protectDimensionalTokens(s) {
      return String(s || '')
        .replace(/\b([123])\s*-\s*D\b/gi, '$1D')                  // normalize "3 - D" -> "3D"
        .replace(/\b([123])\s*D\b/gi, (_, d) => `${d}${SENTINEL_D}`); // "3D"/"3 D" -> "3Ḏ"
    }
    function unprotectDimensionalTokens(s) {
      return String(s || '').replace(new RegExp(SENTINEL_D, 'g'), 'D');
    }
  
    // --- Strip leading outline numbering like "1.", "1.1", "1.1.2", "3.1,3", optionally with trailing "." or ")" ---
    function stripHeadingNumber(s) {
      return String(s || '')
        .replace(/^\s*\d+(?:[.,]\s*\d+)*(?:[.)])?\s*/ , '')
        .trim();
    }
    function isPureHeadingNumber(s) {
      return /^\s*\d+(?:[.,]\s*\d+)*\.?\s*$/.test(String(s || ''));
    }
  
    // Protect first, then normalize
    const protectedText = protectDimensionalTokens(text);
    const cleaned = normalizeText(protectedText);
    if (!cleaned) return [];
  
    // Tokenize
    const tokens = cleaned.split(/\s+/);
    const pairs = [];
    let words = [];
    let i = 0;
  
    // Accept page tokens: "12", "12,13,15", "12-14", "12–14", "12—14"
    // Also tolerate trailing ";" or "," on each token.
    const isPageChunk = (rawTok) => {
      const t = String(rawTok).replace(/[;,]$/, ''); // drop trailing semicolon/comma
      return /^\d+(?:(?:[,\-–—]\d+)+)?$/.test(t);
    };
  
    // Split glued tokens, but don't touch the protected "Ḏ"
    function splitTokenIfGlued(tok) {
      // Avoid splitting the protected dimensional tokens like "3Ḏ"
      if (/^[123]$/.test(tok) || /^[123]$/.test(tok[0]) && tok[1] === SENTINEL_D) return null;
  
      let m;
      m = tok.match(/^(chapter|chaptr|chaptre|ciapter|figure|figuer|figre)(\d+)$/i);
      if (m) return [m[1], m[2]];
  
      m = tok.match(/^([A-Za-z]+)(\d+)$/);
      if (m) return [m[1], m[2]];
  
      m = tok.match(/^([A-Za-z]{3,})([ivxlcdm]{2,})$/i);
      if (m) return [m[1], m[2]];
  
      m = tok.match(/^([ivxlcdm]{2,})(chapter|chaptr|chaptre|ciapter|figure|figuer|figre)$/i);
      if (m) return [m[1], m[2]];
  
      return null;
    }
  
    // Titles that should be ignored entirely as keywords
    function isIgnorableKeyword(str) {
      const s = str.trim();
  
      // Chapter/Figure headings
      if (/^(chapter|chaptr|chaptre|ciapter)\s*\d+$/i.test(s)) return true;
      if (/^(figure|figuer|figre)\s*\d+$/i.test(s)) return true;
  
      // Front matter with Roman numerals
      if (/^(foreword|acknowledgments?|introduction)\s+[ivxlcdm]+$/i.test(s)) return true;
      if (/^[A-Za-z]{3,}\s+[ivxlcdm]{2,}$/i.test(s)) return true;
  
      // Standalone year (any 4 digits)
      if (/^\d{4}$/.test(s)) return true;
  
      // Exactly "1D/2D/3D" only (not phrases containing them)
      if (/^[123]\s*D$/i.test(s)) return true;
  
      // MODULE n
      if (/^module\s+\d+$/i.test(s)) return true;
  
      return false;
    }
  
    while (i < tokens.length) {
      let tok = tokens[i];
  
      // If token is glued, split in-place so subsequent logic sees parts separately
      const split = splitTokenIfGlued(tok);
      if (split) {
        tokens.splice(i, 1, split[0], split[1]);
        tok = tokens[i];
      }
  
      if (!isPageChunk(tok)) {
        // Strip trailing separators from word tokens as well
        words.push(tok.replace(/[;,]$/, ''));
        i++;
        continue;
      }
      if (words.length === 0) { i++; continue; }
  
      // Collect contiguous page-like chunks ("12", "12-14", "12,13", including en/em dashes)
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
  
      // Build keyword, then unprotect "Ḏ"->"D" and strip leading numbering like "1.1.2 "
      let keyword = words.join(' ').replace(/\s+/g, ' ').trim();
      keyword = unprotectDimensionalTokens(keyword);
      keyword = stripHeadingNumber(keyword);
  
      // Drop rows that are pure numbering or ignorable headings
      if (!keyword || isPureHeadingNumber(keyword) || isIgnorableKeyword(keyword)) {
        words = [];
        continue;
      }
  
      pairs.push({ keyword, pages });
      words = [];
    }
  
    // Any trailing words without pages (rare), clean & push as "—"
    if (words.length) {
      let keyword = words.join(' ').trim();
      keyword = unprotectDimensionalTokens(keyword);
      keyword = stripHeadingNumber(keyword);
      if (keyword && !isPureHeadingNumber(keyword) && !isIgnorableKeyword(keyword)) {
        pairs.push({ keyword, pages: '—' });
      }
    }
  
    return pairs;
  }



  function buildTable() {
    const tbody = document.querySelector('#pages-table tbody');
    if (!tbody) return;
  
    const pairs = parsePairs(raw);

    // --- PATCH: merge numeric-only / hyphen-fragment "keywords" into previous row ---
    (function () {
      if (!Array.isArray(pairs) || pairs.length === 0) return;

      function isPureNumericOrRange(s) {
        const v = String(s || '').trim();
        // "349", "330-349", "330–349", optionally with trailing "."
        return /^\d+(?:\s*[-–—]\s*\d+)?\.?$/.test(v);
      }

      function isHyphenNumeric(s) {
        const v = String(s || '').trim();
        // "-349", "- 349", "-349.", "- 349."
        return /^-+\s*\d+\.?$/.test(v);
      }

      function isNumericTrailingHyphen(s) {
        const v = String(s || '').trim();
        // "486-", "486 -", "486-.", "486 -."
        return /^\d+\s*-\s*\.?$/.test(v);
      }

      function isJustHyphen(s) {
        // Treat ",-", "-.", ",-." etc. as just hyphen noise
        const v = String(s || '').trim().replace(/[.,]/g, '');
        return v === '-' || v === '—';
      }

      function extractLeadingDigits(s) {
        const m = String(s || '').trim().match(/^(\d+)/);
        return m ? m[1] : '';
      }

      function appendPages(target, extra) {
        const extraTrimmed = String(extra || '').trim();
        if (!extraTrimmed) return;

        if (!target.pages || target.pages === '—') {
          target.pages = extraTrimmed;
        } else {
          target.pages += ', ' + extraTrimmed;
        }
      }

      const cleaned = [];

      for (const p of pairs) {
        const kRaw  = p.keyword != null ? String(p.keyword) : '';
        const k     = kRaw.trim();
        const pages = String(p.pages || '').trim();

        // If first row is just numeric/hyphen noise, drop it
        if (
          !cleaned.length &&
          (isPureNumericOrRange(k) ||
           isHyphenNumeric(k) ||
           isNumericTrailingHyphen(k) ||
           isJustHyphen(k))
        ) {
          continue;
        }

        // Case 1: "349" / "330-349" row → treat as extra pages for previous keyword
        if (cleaned.length && isPureNumericOrRange(k)) {
          const prev = cleaned[cleaned.length - 1];
          const base = k.replace(/\.$/, ''); // strip trailing dot
          const composite =
            pages && pages !== '—'
              ? base + ', ' + pages
              : base;
          appendPages(prev, composite);
          continue;
        }

        // Case 2: "-349" / "-349." row → treat "349" as pages of previous keyword
        if (cleaned.length && isHyphenNumeric(k)) {
          const prev = cleaned[cleaned.length - 1];
          const digitPart = k
            .replace(/^\s*-+\s*/, '')
            .replace(/\.$/, '');
          const composite =
            pages && pages !== '—'
              ? digitPart + ', ' + pages
              : digitPart;
          appendPages(prev, composite);
          continue;
        }

        // Case 3: "486-" row variants → treat leading digits as pages of previous keyword
        if (cleaned.length && isNumericTrailingHyphen(k)) {
          const prev = cleaned[cleaned.length - 1];
          const digitPart = extractLeadingDigits(k);
          const composite =
            digitPart
              ? (pages && pages !== '—'
                  ? digitPart + ', ' + pages
                  : digitPart)
              : pages;
          if (composite) appendPages(prev, composite);
          continue;
        }

        // Case 4: bare hyphen-like ",-" / "-." etc. → fold its pages into previous row
        if (cleaned.length && isJustHyphen(k)) {
          const prev = cleaned[cleaned.length - 1];
          if (pages && pages !== '—') appendPages(prev, pages);
          continue;
        }

        // Normal row: carry forward as-is
        cleaned.push({
          keyword: k,
          pages: pages || '—'
        });
      }

      // Overwrite original array in-place so downstream grouping logic remains unchanged
      pairs.length = 0;
      cleaned.forEach(function (item) {
        pairs.push(item);
      });
    })();
    // --- END PATCH ---
  
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
  document.addEventListener('DOMContentLoaded', function () {
    const meta = document.getElementById('book-meta');
    const btn  = document.getElementById('show-pages-btn');
    if (!meta || !btn) return;

    const bookType = (meta.dataset.type || '').trim().toLowerCase();
    if (bookType === 'thesis') {
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

// --- ADD-ONLY: prevent "N/A" from being split into "N" and "A" in parseAuthors ---
(function () {
  // Use division slash U+2215 as a temporary sentinel (looks like "/")
  const SENTINEL_SLASH = '\u2215';

  // Canonicalize and protect N/A variants: "N/A", "n / a", "N /A", etc.
  function protectNA(s) {
    if (s == null) return s;
    return String(s).replace(/\bn\s*\/\s*a\b/gi, m =>
      // keep visible "N/A" but swap the slash to SENTINEL so splitting on "/" won't fire
      m.replace('/', SENTINEL_SLASH).replace(/\s+/g, '').toUpperCase() // -> "N\u2215A"
    );
  }

  // Restore sentinel back to a normal slash
  function restoreNA(s) {
    if (s == null) return s;
    return String(s).replace(new RegExp(SENTINEL_SLASH, 'g'), '/');
  }

  // Preserve original, then wrap
  const _origParseAuthors = (typeof window !== 'undefined' && window.parseAuthors) ? window.parseAuthors : parseAuthors;

  window.parseAuthors = function (primaryAuthor, coAuthors) {
    const protectedPrimary = protectNA(primaryAuthor);
    const protectedCo      = protectNA(coAuthors);
    const list = _origParseAuthors(protectedPrimary, protectedCo) || [];
    // Restore "N/A" tokens exactly; trim strays
    return list.map(a => restoreNA(a).trim());
  };
})();
