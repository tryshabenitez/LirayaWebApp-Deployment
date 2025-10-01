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
    theCoauthors    = metaEl?.dataset.coauthor || '';
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

  const modal      = document.getElementById('pages-modal');
  const modalBody  = document.getElementById('pages-modal-body');
  const modalClose = document.getElementById('close-pages-modal');

  if (!modal || !modalBody || !wrap || !btn) return;

  let built = false;

  function normalizeText(text) {
    if (!text) return '';
    let s = text;

    // Normalize ALL odd spaces to a regular space (NBSP, en/em space, thin/hair, etc.)
    s = s.replace(/[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000]/g, ' ');

    // Remove zero-width characters (ZWNJ, ZWJ, BOM)
    s = s.replace(/[\u200C\u200D\uFEFF]/g, '');

    // Normalize dash/minus/hyphen variants to a simple hyphen
    s = s.replace(/[\u2010-\u2015\u2212\uFE63\uFF0D]/g, '-');

    // Collapse extra spaces
    s = s.replace(/\s{2,}/g, ' ');

    // "Electron, 57-58" -> "Electron 57-58"
    s = s.replace(/,\s*(?=\d)/g, ' ');

    // Ensure digits and letters are separated BOTH ways
    // letter)(digit -> "letter digit"
    s = s.replace(/([A-Za-z\)\]\.])(\d)/g, '$1 $2');
    // digit)(letter or '(' -> "digit letter"
    s = s.replace(/(\d)(?=[A-Za-z(])/g, '$1 ');
    // and if next is an uppercase start of a new term (safety)
    s = s.replace(/(\d)(?=[A-Z])/g, '$1 ');

    return s.trim();
  }

  function parsePairs(text) {
    const cleaned = normalizeText(text);
    if (!cleaned) return [];

    const tokens = cleaned.split(/\s+/);
    const pairs = [];
    let words = [];
    let i = 0;

    // Accept only clean page tokens: "12", "12,13,15", or "12-14"
    const isPageChunk = (rawTok) => {
      const t = String(rawTok).replace(/,$/, ''); // drop trailing comma
      return /^\d+(?:[-,]\d+)*$/.test(t);
    };

    while (i < tokens.length) {
      const tok = tokens[i];

      if (!isPageChunk(tok)) {
        // keep building the keyword
        words.push(tok.replace(/,$/, ''));
        i++;
        continue;
      }
      if (words.length === 0) { i++; continue; }

      // collect contiguous page-like chunks
      const pageParts = [];
      while (i < tokens.length && isPageChunk(tokens[i])) {
        pageParts.push(tokens[i].replace(/,$/, ''));
        i++;
      }

      // Keep only the first number of each range (e.g., "57-59" -> "57")
      const firstOnly = [];
      pageParts.forEach((part) => {
        part.split(',').forEach(chunk => {
          const c = chunk.trim();
          if (!c) return;
          const firstRaw = c.split('-')[0];
          if (/^0{2,}\d+$/.test(firstRaw)) return; // ignore artifact like "0002"
          let num = firstRaw.replace(/^0+/, '');
          if (num === '') num = '0';
          firstOnly.push(num);
        });
      });

      const keyword = words.join(' ').replace(/\s+/g, ' ').trim();
      const pages = firstOnly.length ? firstOnly.join(', ') : '—';

      if (keyword) pairs.push({ keyword, pages });
      words = [];
    }

    if (words.length) {
      pairs.push({ keyword: words.join(' ').trim(), pages: '—' });
    }

    return pairs;
  }

  function buildTable() {
    const tbody = document.querySelector('#pages-table tbody');
    if (!tbody) return;

    const pairs = parsePairs(raw);
    if (!pairs.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="2">No page index available.</td>';
      tbody.appendChild(tr);
      built = true;
      return;
    }

    pairs.forEach((p, idx) => {
      const tr = document.createElement('tr');
      tr.className = idx % 2 === 0 ? 'row-odd' : 'row-even';
      const esc = (v) => String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
      tr.innerHTML = `<td>${esc(p.keyword)}</td><td>${esc(p.pages)}</td>`;
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
