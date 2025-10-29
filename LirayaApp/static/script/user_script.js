// ------------------------------
// Corrected JS: Pagination + Filters + Typeahead + Year dropdown
// ------------------------------

// ===== Year config & helpers =====
const YEAR_MIN = 1900;
const YEAR_MAX = new Date().getFullYear();

function filterYearKeydown(e) {
  // Allow navigation/edit keys
  const allowedKeys = ['Backspace','Delete','Tab','ArrowLeft','ArrowRight','Home','End'];
  if (allowedKeys.includes(e.key)) return;

  // Allow Ctrl/Cmd combos
  if ((e.ctrlKey || e.metaKey) && ['a','c','v','x','A','C','V','X'].includes(e.key)) return;

  // Digits only
  if (!/^[0-9]$/.test(e.key)) e.preventDefault();
}

function sanitizeYearInput(e) {
  const v = (e.target.value || '').replace(/\D+/g, '');
  e.target.value = v;
}

function sanitizeYearPaste(e) {
  e.preventDefault();
  const text = (e.clipboardData || window.clipboardData).getData('text') || '';
  const digits = text.replace(/\D+/g, '');
  document.execCommand('insertText', false, digits);
}

// Build a small dropdown of years around the current input value (±2)
function showYearDropdown(inputEl) {
  const rect = inputEl.getBoundingClientRect();
  const root = document.getElementById('year-dd-root') || (() => {
    const d = document.createElement('div');
    d.id = 'year-dd-root';
    document.body.appendChild(d);
    return d;
  })();

  let cur = parseInt(inputEl.value, 10);
  if (isNaN(cur)) cur = YEAR_MAX;

  const years = [];
  for (let y = cur - 2; y <= cur + 2; y++) {
    if (y >= YEAR_MIN && y <= YEAR_MAX) years.push(y);
  }

  root.innerHTML = `
    <div class="year-dropdown" data-for="${inputEl.id}"
         style="top:${rect.bottom + window.scrollY + 4}px; left:${rect.left + window.scrollX}px; width:${rect.width}px">
      <div class="year-dropdown-header">min ${YEAR_MIN} &nbsp; max ${YEAR_MAX}</div>
      <div class="year-dropdown-list">
        ${years.map(y => `
          <button type="button" class="year-dd-item ${y===cur?'is-current':''}" data-year="${y}">
            ${y}
          </button>`).join('')}
      </div>
    </div>
  `;

  root.querySelectorAll('.year-dd-item').forEach(btn => {
    btn.addEventListener('click', () => {
      inputEl.value = btn.dataset.year;
      closeYearDropdown();
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    });
  });

  setTimeout(() => {
    const closer = (ev) => {
      const dd = document.querySelector('.year-dropdown');
      if (!dd) return document.removeEventListener('mousedown', closer);
      if (!dd.contains(ev.target)) closeYearDropdown();
    };
    document.addEventListener('mousedown', closer, { once: true });

    const esc = (ev) => { if (ev.key === 'Escape') { closeYearDropdown(); document.removeEventListener('keydown', esc); } };
    document.addEventListener('keydown', esc);
  }, 0);
}

function closeYearDropdown() {
  const root = document.getElementById('year-dd-root');
  if (root) root.innerHTML = '';
}

// Intercept clicks on the native spinner zone and show our dropdown
function attachSpinnerDropdown(inputEl) {
  inputEl.addEventListener('mousedown', (e) => {
    const r = inputEl.getBoundingClientRect();
    const x = e.clientX - r.left;
    const spinnerZone = x >= r.width - 24; // last ~24px
    if (spinnerZone) {
      e.preventDefault();
      e.stopPropagation();
      inputEl.blur();
      showYearDropdown(inputEl);
    }
  });
}

// ===== Pagination state =====
const paginationDataEl = document.getElementById('pagination-data');
let currentPage = 1;
let totalPages  = 1;
let totalCount  = 0;
let pageSize    = 5; // fallback

if (paginationDataEl) {
  const cur = parseInt(paginationDataEl.dataset.current, 10);
  const tot = parseInt(paginationDataEl.dataset.total, 10);
  const cnt = parseInt(paginationDataEl.dataset.count, 10);
  const pp  = parseInt(paginationDataEl.dataset.perPage, 10);
  if (!isNaN(cur)) currentPage = cur;
  if (!isNaN(tot)) totalPages  = tot;
  if (!isNaN(cnt)) totalCount  = cnt;
  if (!isNaN(pp))  pageSize    = pp;
}

function updateResultsSummary() {
  const el = document.getElementById('results-summary');
  if (!el) return;

  if (!totalCount || totalCount < 1) {
    el.innerHTML = '<strong>Showing <em>0</em> out of <em>0</em> results</strong>';
    return;
  }

  const start = (currentPage - 1) * pageSize + 1;
  const end   = Math.min(currentPage * pageSize, totalCount);

  el.innerHTML = `<strong>Showing <em>${start}</em>–<em>${end}</em> out of <em>${totalCount}</em> results</strong>`;
}

// Change page (AJAX)
function changePage(page) {
  if (page < 1) page = 1;
  if (page > totalPages) page = totalPages;

  currentPage = page;
  updatePagination();
  fetchBooks(page);
}

// Build/update pagination UI (top and optional bottom)
function updatePagination() {
  const containers = [
    document.getElementById('pagination-top'),
    document.getElementById('pagination-bottom')
  ].filter(Boolean);

  if (!containers.length) return;

  containers.forEach(paginationElement => {
    // Clear
    paginationElement.innerHTML = '';

    // Prev button
    const prevButton = document.createElement('button');
    prevButton.className = 'nav-button';
    prevButton.textContent = '<';
    prevButton.disabled = currentPage === 1;
    prevButton.addEventListener('click', (e) => {
      e.preventDefault();
      changePage(currentPage - 1);
    });
    paginationElement.appendChild(prevButton);

    // Page links (current +/- 2)
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    for (let page = startPage; page <= endPage; page++) {
      const a = document.createElement('a');
      a.href = '#';
      a.className = `page-item ${page === currentPage ? 'active' : ''}`;
      a.dataset.page = String(page);
      a.textContent = page;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        changePage(page);
      });
      paginationElement.appendChild(a);
    }

    // Next button
    const nextButton = document.createElement('button');
    nextButton.className = 'nav-button';
    nextButton.textContent = '>';
    nextButton.disabled = currentPage === totalPages;
    nextButton.addEventListener('click', (e) => {
      e.preventDefault();
      changePage(currentPage + 1);
    });
    paginationElement.appendChild(nextButton);
  });
}

// Fetch new page via AJAX while preserving current query params
function fetchBooks(page) {
  const params = new URLSearchParams(window.location.search);
  params.set('page', page);
  const url = `${window.location.pathname}?${params.toString()}`;

  fetch(url)
    .then(response => response.text())
    .then(html => {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = html;

      // Replace book list
      const newMain = tempDiv.querySelector('.main-content');
      const curMain = document.querySelector('.main-content');
      if (newMain && curMain) {
        curMain.innerHTML = newMain.innerHTML;
      }

      // Update pagination data (current/total/count/per-page) from new HTML
      const newPagData = tempDiv.querySelector('#pagination-data');
      if (newPagData) {
        const cur = parseInt(newPagData.dataset.current, 10);
        const tot = parseInt(newPagData.dataset.total, 10);
        const cnt = parseInt(newPagData.dataset.count, 10);
        const pp  = parseInt(newPagData.dataset.perPage, 10);
        if (!isNaN(cur)) currentPage = cur;
        if (!isNaN(tot)) totalPages  = tot;
        if (!isNaN(cnt)) totalCount  = cnt;
        if (!isNaN(pp))  pageSize    = pp;
      }

      updatePagination();
      updateResultsSummary();
    })
    .catch(error => {
      console.error('Error fetching books:', error);
    });
}

// Sidebar toggle (guards for nulls)
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const mainContent = document.querySelector('.main-content');
  const pagination = document.querySelector('.pagination');

  if (!sidebar || !mainContent) return;

  sidebar.classList.toggle('open');

  if (sidebar.classList.contains('open')) {
    mainContent.style.marginLeft = '270px';
    if (pagination) pagination.style.marginLeft = '270px';
  } else {
    mainContent.style.marginLeft = '0';
    if (pagination) pagination.style.marginLeft = '0';
  }
}

// ------------------------------
// Menu / Filter helpers
// ------------------------------

// (Legacy client-side highlighter; separate from URL-param filter)
function toggleActiveClient(element) {
  element.classList.toggle('active');

  const menuItems = document.querySelectorAll('.menu-item');
  const activeCats = Array.from(menuItems)
    .filter(it => it.classList.contains('active'))
    .map(it => it.textContent.trim().split(' ')[0]);

  const books = document.querySelectorAll('.book-info');

  if (!activeCats.length) {
    books.forEach(b => b.style.visibility = 'visible');
    return;
  }

  books.forEach(book => {
    const bookCategory = book.getAttribute('data-shelf-category');
    book.style.visibility = activeCats.includes(bookCategory) ? 'visible' : 'hidden';
  });
}

// Update URL params for resource-type OR category-style items
function toggleActive(element) {
  element.classList.toggle('active');

  const params = new URLSearchParams(window.location.search);

  if (element.hasAttribute('data-resource-type')) {
    // Resource Type facet
    const value = element.getAttribute('data-resource-type');
    let list = params.get('active_resource_types');
    let arr = list ? list.split(',').filter(Boolean) : [];

    if (element.classList.contains('active')) {
      if (!arr.includes(value)) arr.push(value);
    } else {
      arr = arr.filter(v => v !== value);
    }
    params.set('active_resource_types', arr.join(','));
  } else if (element.hasAttribute('data-category')) {
    // Shelf Category facet (DO NOT split words)
    const value = element.getAttribute('data-category');
    let list = params.get('active_categories');
    let arr = list ? list.split(',').filter(Boolean) : [];

    if (element.classList.contains('active')) {
      if (!arr.includes(value)) arr.push(value);
    } else {
      arr = arr.filter(v => v !== value);
    }
    params.set('active_categories', arr.join(','));
  }

  params.set('page', 1);
  window.location.search = params.toString();
}

function toggleResourceType(event, resourceType) {
  event.preventDefault();
  const params = new URLSearchParams(window.location.search);
  let active = params.get('active_resource_types');
  let list = active ? active.split(',').filter(Boolean) : [];
  if (list.includes(resourceType)) list = list.filter(t => t !== resourceType);
  else list.push(resourceType);
  params.set('active_resource_types', list.join(','));
  params.set('page', 1);
  window.location.search = params.toString();
}

// Year filter — VALIDATE ONLY WHEN BUTTON CLICKED
function applyYearFilter() {
  const minYearInput = document.getElementById('min-year');
  const maxYearInput = document.getElementById('max-year');
  if (!minYearInput || !maxYearInput) return;

  let minYear = parseInt((minYearInput.value || '').replace(/\D+/g, ''), 10);
  let maxYear = parseInt((maxYearInput.value || '').replace(/\D+/g, ''), 10);

  if (isNaN(minYear)) minYear = YEAR_MIN;
  if (isNaN(maxYear)) maxYear = YEAR_MAX;

  // clamp
  if (minYear < YEAR_MIN) minYear = YEAR_MIN;
  if (maxYear > YEAR_MAX) maxYear = YEAR_MAX;

  if (minYear > maxYear) {
    alert('Min Year cannot be greater than Max Year.');
    return;
  }

  // write back clean values
  minYearInput.value = String(minYear);
  maxYearInput.value = String(maxYear);

  const params = new URLSearchParams(window.location.search);
  params.set('min_year', minYear);
  params.set('max_year', maxYear);
  params.set('page', 1);
  window.location.search = params.toString();
}

// Incremental "See All" reveal (kept)
function toggleMenu(button) {
  const list = button.previousElementSibling;
  if (!list) return;

  const items = Array.from(list.querySelectorAll('.menu-item'));
  if (!items.length) { button.style.display = 'none'; return; }

  const visibleCount = items.filter(it => window.getComputedStyle(it).display !== 'none').length;
  const nextEnd = Math.min(visibleCount + 4, items.length);

  for (let i = visibleCount; i < nextEnd; i++) {
    items[i].style.display = 'block';
  }

  if (nextEnd >= items.length) {
    button.style.display = 'none';
  }
}

// ------------------------------
// Typeahead Suggestions (works on both pages)
// ------------------------------
function debounce(fn, delay) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), delay);
  };
}

// Escape HTML
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Escape for regex
function escapeRegExp(str) {
  return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Uppercase only the matched query parts (case-insensitive), with proper escaping
function highlightMatchesBoldUpper(text, query) {
  if (!query) return escapeHtml(text);

  const re = new RegExp(escapeRegExp(String(query)), 'ig');
  let result = '';
  let last = 0;
  let m;

  while ((m = re.exec(text)) !== null) {
    const start = m.index;
    const end = start + m[0].length;
    result += escapeHtml(text.slice(last, start));
    const upper = m[0].toUpperCase();
    result += `<strong>${escapeHtml(upper)}</strong>`;
    last = end;
  }
  result += escapeHtml(text.slice(last));
  return result;
}

function bindClickHover(el, { className = 'is-click-hover', duration = 900 } = {}) {
  if (!el) return;
  let t;

  const activate = () => {
    // force repaint
    // eslint-disable-next-line no-unused-expressions
    el.offsetHeight;
    el.classList.add(className);
    if (t) clearTimeout(t);
    t = setTimeout(() => el.classList.remove(className), duration);
  };

  el.addEventListener('pointerdown', activate, { capture: true });
  el.addEventListener('pointerup',   activate);
  el.addEventListener('pointercancel', activate);
  el.addEventListener('focusin', activate);
  el.addEventListener('input',  activate);
  el.addEventListener('change', activate);
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') activate();
  });
}

document.addEventListener('DOMContentLoaded', function () {
  // --- Pagination + summary ---
  if (paginationDataEl) updatePagination();
  updateResultsSummary();

  // --- "See More" label (if present) ---
  const seeMoreBtn = document.querySelector('.see-more-btn');
  if (seeMoreBtn) seeMoreBtn.textContent = 'See More';

  // --- Year inputs + UI bits ---
  const minYearInput = document.getElementById('min-year');
  const maxYearInput = document.getElementById('max-year');
  const applyBtn     = document.querySelector('.year-button');    // "Apply Year Filter"
  const refineHdr    = document.querySelector('.refine-search');  // "Refine Search Results"

  bindClickHover(minYearInput);
  bindClickHover(maxYearInput);
  bindClickHover(applyBtn);
  bindClickHover(refineHdr);

  if (refineHdr) {
    refineHdr.setAttribute('tabindex', '0');
    refineHdr.setAttribute('role', 'button');
  }

  // Allow typing; validate only on Apply; hook spinner dropdown
  if (minYearInput) {
    minYearInput.setAttribute('min', YEAR_MIN);
    minYearInput.setAttribute('max', YEAR_MAX);
    if (!minYearInput.value) minYearInput.value = YEAR_MIN;
    minYearInput.addEventListener('keydown', filterYearKeydown);
    minYearInput.addEventListener('paste', sanitizeYearPaste);
    minYearInput.addEventListener('input', sanitizeYearInput);
    attachSpinnerDropdown(minYearInput);
  }
  if (maxYearInput) {
    maxYearInput.setAttribute('min', YEAR_MIN);
    maxYearInput.setAttribute('max', YEAR_MAX);
    if (!maxYearInput.value) maxYearInput.value = YEAR_MAX;
    maxYearInput.addEventListener('keydown', filterYearKeydown);
    maxYearInput.addEventListener('paste', sanitizeYearPaste);
    maxYearInput.addEventListener('input', sanitizeYearInput);
    attachSpinnerDropdown(maxYearInput);
  }

  // Hide "See All" buttons when < 4 items
  const sections = document.querySelectorAll('.section-title');
  sections.forEach(section => {
    const menuItemsWrap = section.nextElementSibling;
    const seeMoreButton = menuItemsWrap ? menuItemsWrap.nextElementSibling : null;
    const menuItems = menuItemsWrap ? menuItemsWrap.querySelectorAll('.menu-item') : [];
    if (menuItems.length < 4 && seeMoreButton) {
      seeMoreButton.style.display = 'none';
    }
  });

  // --- Auto-open sidebar ---
  const sidebar = document.querySelector('.sidebar');
  const mainContent = document.querySelector('.main-content');
  const paginationEl = document.querySelector('.pagination');
  if (sidebar && mainContent) {
    sidebar.classList.add('open');
    mainContent.style.marginLeft = '270px';
    if (paginationEl) paginationEl.style.marginLeft = '270px';
  }

  // --- Typeahead init (safe on both pages) ---
  const forms = document.querySelectorAll('form.search-form');
  forms.forEach(form => {
    if (form.__typeaheadInit) return;

    const suggestUrl = form.getAttribute('data-suggest-url') || '/suggest/';
    const input = form.querySelector('.search-box');
    if (!input) return;

    let wrap = form.querySelector('.search-box-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'search-box-wrap';
      input.parentNode.insertBefore(wrap, input);
      wrap.appendChild(input);
    }

    let dropdown = wrap.querySelector('.typeahead');
    if (!dropdown) {
      dropdown = document.createElement('div');
      dropdown.className = 'typeahead';
      wrap.appendChild(dropdown);
    }

    const fieldSelect = form.querySelector('select[name="field"]');
    initTypeaheadForForm({ form, input, fieldSelect, wrap, dropdown, suggestUrl });
    form.__typeaheadInit = true;
  });
});

// Per-book Keywords: See More / See Less
function toggleKeywords(bookId, btnEl) {
  const el = document.getElementById('keywords-' + bookId);
  if (!el) return;
  const expanded = el.classList.toggle('keywords-expanded');
  if (btnEl) btnEl.textContent = expanded ? 'See Less' : 'See More';
}

function initTypeaheadForForm({ form, input, fieldSelect, wrap, dropdown, suggestUrl }) {
  let items = [];
  let activeIndex = -1;

  const render = (list, query) => {
    items = list || [];
    activeIndex = -1;
    if (!items.length) {
      dropdown.innerHTML = '';
      dropdown.classList.remove('visible');
      return;
    }
    dropdown.innerHTML = items.map(it => `
      <div class="typeahead-item" data-text="${escapeHtml(it.text)}" data-type="${it.type}">
        <span class="label">${highlightMatchesBoldUpper(it.text, query)}</span>
        <span class="badge">${it.type === 'keywords' ? 'KEYWORD' : it.type.toUpperCase()}</span>
      </div>
    `).join('');
    dropdown.classList.add('visible');
  };

  const fetchSuggestions = debounce(function () {
    const q = input.value.trim();
    const field = (fieldSelect && fieldSelect.value) || 'allFields';
    if (q.length < 2) { render([], q); return; }

    const url = new URL(suggestUrl, window.location.origin);
    url.searchParams.set('q', q);
    url.searchParams.set('field', field);

    fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.ok ? r.json() : { results: [] })
      .then(data => render((data && data.results) || [], q))
      .catch(() => render([], q));
  }, 150);

  input.addEventListener('input', fetchSuggestions);

  input.addEventListener('keydown', function (e) {
    if (!dropdown.classList.contains('visible') || !items.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActive();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActive();
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && activeIndex < items.length) {
        e.preventDefault();
        choose(items[activeIndex]);
      }
    } else if (e.key === 'Escape') {
      hide();
    }
  });

  dropdown.addEventListener('mousedown', function (e) {
    const itemEl = e.target.closest('.typeahead-item');
    if (!itemEl) return;
    e.preventDefault();
    choose({ text: itemEl.dataset.text, type: itemEl.dataset.type });
  });

  document.addEventListener('click', function (e) {
    if (!wrap.contains(e.target)) hide();
  });

  function updateActive() {
    const els = dropdown.querySelectorAll('.typeahead-item');
    els.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
    if (activeIndex >= 0) {
      const activeEl = els[activeIndex];
      const top = activeEl.offsetTop;
      const bottom = top + activeEl.offsetHeight;
      if (top < dropdown.scrollTop) dropdown.scrollTop = top;
      else if (bottom > dropdown.scrollTop + dropdown.clientHeight) dropdown.scrollTop = bottom - dropdown.clientHeight;
    }
  }

  function choose(item) {
    input.value = item.text;
    hide();
    form.submit(); // auto-submit on choose
  }

  function hide() {
    dropdown.classList.remove('visible');
    dropdown.innerHTML = '';
    items = [];
    activeIndex = -1;
  }
}

function toggleSubject(element) {
  element.classList.toggle('active');

  const value = element.getAttribute('data-subject');
  const params = new URLSearchParams(window.location.search);

  let list = params.get('active_subjects');
  let arr = list ? list.split(',').filter(Boolean) : [];

  if (element.classList.contains('active')) {
    if (!arr.includes(value)) arr.push(value);
  } else {
    arr = arr.filter(v => v !== value);
  }

  params.set('active_subjects', arr.join(','));
  params.set('page', 1); // reset to first page on filter change
  window.location.search = params.toString();
}
