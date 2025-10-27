// ------------------------------
// Corrected JS: Pagination + Filters + Typeahead (no extra CSS)
// ------------------------------

// Safely read pagination data if present
// Safely read pagination data if present
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

// Year filter + validation
function applyYearFilter() {
  const minYearInput = document.getElementById('min-year');
  const maxYearInput = document.getElementById('max-year');

  if (!minYearInput || !maxYearInput) return;

  const currentYear = new Date().getFullYear();
  let minYear = parseInt(minYearInput.value, 10);
  let maxYear = parseInt(maxYearInput.value, 10);

  if (isNaN(minYear) || minYear < 1900 || minYear > currentYear) {
    alert('Min Year must be between 1900 and ' + currentYear + '.');
    minYear = Math.max(1900, Math.min(minYear || 1900, currentYear));
    minYearInput.value = minYear;
    return;
  }
  if (isNaN(maxYear) || maxYear < 1900 || maxYear > currentYear) {
    alert('Max Year must be between 1900 and ' + currentYear + '.');
    maxYear = Math.max(1900, Math.min(maxYear || currentYear, currentYear));
    maxYearInput.value = maxYear;
    return;
  }
  if (minYear > maxYear) {
    alert('Min Year cannot be greater than Max Year.');
    return;
  }

  const params = new URLSearchParams(window.location.search);
  params.set('min_year', minYear);
  params.set('max_year', maxYear);
  params.set('page', 1);
  window.location.search = params.toString();
}

function toggleMenu(button) {
  const list = button.previousElementSibling;
  if (!list) return;

  const items = Array.from(list.querySelectorAll('.menu-item'));
  if (!items.length) { button.style.display = 'none'; return; }

  // how many are currently visible?
  const visibleCount = items.filter(it => window.getComputedStyle(it).display !== 'none').length;
  const nextEnd = Math.min(visibleCount + 4, items.length);

  // reveal the next 4
  for (let i = visibleCount; i < nextEnd; i++) {
    items[i].style.display = 'block';
  }

  // hide button if nothing left to reveal
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
    // non-matching chunk
    result += escapeHtml(text.slice(last, start));
    // matched chunk: UPPERCASE + <strong>
    const upper = m[0].toUpperCase();
    result += `<strong>${escapeHtml(upper)}</strong>`;
    last = end;
  }
  // tail
  result += escapeHtml(text.slice(last));
  return result;
}

// Simulate hover via click (and keyboard). Adds a class briefly, then removes.
function bindClickHover(el, {className = 'is-click-hover', duration = 900} = {}) {
  if (!el) return;
  let t;

  function activate() {
    el.classList.add(className);
    if (t) clearTimeout(t);
    t = setTimeout(() => el.classList.remove(className), duration);
  }

  // Mouse/touch
  el.addEventListener('click', activate);

  // Keyboard accessibility (Enter / Space)
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      activate();
      // also trigger action if it’s a button
      if (el.tagName === 'BUTTON') el.click?.();
    }
  }, { capture: true });
}


document.addEventListener('DOMContentLoaded', function () {
  // Init pagination UI if present
  if (paginationDataEl) updatePagination();

  // Init results summary on first load
  updateResultsSummary();

  // Initial "See More" button label (if present)
  const seeMoreBtn = document.querySelector('.see-more-btn');
  if (seeMoreBtn) seeMoreBtn.textContent = 'See More';

  // Year inputs init (guards if not present on the page)
  const minYearInput = document.getElementById('min-year');
  const maxYearInput = document.getElementById('max-year');
  const applyBtn     = document.querySelector('.year-button');   // "Apply Year Filter"
  const refineHdr    = document.querySelector('.refine-search'); // "Refine Search Results"

  // Simulate hover on click for min/max year inputs.
  // Note: your disableTypingNumberInput keeps typing blocked; clicks on the spinner still work.
  bindClickHover(minYearInput);
  bindClickHover(maxYearInput);

  // Simulate hover on click for the Apply button & section header
  bindClickHover(applyBtn);
  bindClickHover(refineHdr);
  
  if (minYearInput && maxYearInput) {
    const currentYear = new Date().getFullYear();
    minYearInput.setAttribute('min', 1900);
    minYearInput.setAttribute('max', currentYear);
    maxYearInput.setAttribute('min', 1900);
    maxYearInput.setAttribute('max', currentYear);
    if (!minYearInput.value) minYearInput.value = 1900;
    if (!maxYearInput.value) maxYearInput.value = currentYear;
    disableTypingNumberInput(minYearInput);
    disableTypingNumberInput(maxYearInput);


    const sections = document.querySelectorAll('.section-title');
    sections.forEach(section => {
      const menuItemsWrap = section.nextElementSibling;
      const seeMoreButton = menuItemsWrap ? menuItemsWrap.nextElementSibling : null;
      const menuItems = menuItemsWrap ? menuItemsWrap.querySelectorAll('.menu-item') : [];
      if (menuItems.length < 4 && seeMoreButton) {
        seeMoreButton.style.display = 'none';
      }
    });

    // Year inputs: Enter key validation
    minYearInput.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        const currentYear = new Date().getFullYear();
        const v = parseInt(this.value, 10);
        if (v > currentYear) {
          alert('Year cannot exceed the current year.');
          this.value = currentYear;
        } else if (v < 1900) {
          alert('Year cannot be earlier than 1900.');
          this.value = 1900;
        }
      }
    });

    maxYearInput.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        const currentYear = new Date().getFullYear();
        const v = parseInt(this.value, 10);
        if (v > currentYear) {
          alert('Year cannot exceed the current year.');
          this.value = currentYear;
        } else if (v < 1900) {
          alert('Year cannot be earlier than 1900.');
          this.value = 1900;
        }
      }
    });

    // Prevent out-of-range years on input
    ['min-year', 'max-year'].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('input', function () {
        const currentYear = new Date().getFullYear();
        let val = parseInt(this.value, 10);
        if (val < 1900) {
          alert('Year cannot be earlier than 1900.');
          this.value = 1900;
        } else if (val > currentYear) {
          alert('Year cannot exceed the current year.');
          this.value = currentYear;
        }
      });
    });
  }

  // Auto-open sidebar if present on this page
  const sidebar = document.querySelector('.sidebar');
  const mainContent = document.querySelector('.main-content');
  const paginationEl = document.querySelector('.pagination');
  if (sidebar && mainContent) {
    sidebar.classList.add('open');
    mainContent.style.marginLeft = '270px';
    if (paginationEl) paginationEl.style.marginLeft = '270px';
  }

  // Typeahead init
  const forms = document.querySelectorAll('form.search-form');
  forms.forEach(form => {
    if (form.__typeaheadInit) return;

    let suggestUrl = form.getAttribute('data-suggest-url') || '/suggest/';
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

function disableTypingNumberInput(el) {
  if (!el) return;

  // 1) Block keyboard typing (but allow Tab to move focus)
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') return;
    e.preventDefault();
  });

  // 2) Block typing-related events
  el.addEventListener('keypress', (e) => e.preventDefault());
  el.addEventListener('paste',   (e) => e.preventDefault());
  el.addEventListener('drop',    (e) => e.preventDefault());

  // 3) Prevent mouse wheel value changes
  el.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });

  // 4) Let ONLY the spinner zone be clickable
  //    Approximate the spinner as the rightmost 24px of the input.
  function allowOnlySpinnerPointer(e) {
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const isSpinnerZone = x >= rect.width - 24; // right-most 24px
    if (!isSpinnerZone) {
      e.preventDefault();  // no focusing/caret on text area
      // Keep it unfocused so no caret shows up
      el.blur();
    }
  }

  el.addEventListener('mousedown', allowOnlySpinnerPointer);
  el.addEventListener('touchstart', (e) => {
    // For touch, use the first touch point
    if (!e.touches || !e.touches.length) return;
    const touch = e.touches[0];
    const rect = el.getBoundingClientRect();
    const x = touch.clientX - rect.left;
    const isSpinnerZone = x >= rect.width - 24;
    if (!isSpinnerZone) {
      e.preventDefault();
      el.blur();
    }
  }, { passive: false });

  // 5) Cosmetic: hide the caret & disable text selection to reduce UI noise
  el.style.caretColor = 'transparent';
  el.style.userSelect = 'none';
}

