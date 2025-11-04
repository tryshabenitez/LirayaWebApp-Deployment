// ------------------------------
// Corrected JS: Pagination + Filters + Typeahead + Year dropdown
// ------------------------------

// ===== Year config & helpers =====
const YEAR_MIN = 1900;
const YEAR_MAX = new Date().getFullYear();

let yearDDActive = null; // { inputEl, reposition, teardown }

function filterYearKeydown(e) {
  const allowedKeys = ['Backspace','Delete','Tab','ArrowLeft','ArrowRight','Home','End'];
  if (allowedKeys.includes(e.key)) return;
  if ((e.ctrlKey || e.metaKey) && ['a','c','v','x','A','C','V','X'].includes(e.key)) return;
  if (!/^[0-9]$/.test(e.key)) e.preventDefault();
}
function sanitizeYearInput(e) {
  e.target.value = (e.target.value || '').replace(/\D+/g, '');
}
function sanitizeYearPaste(e) {
  e.preventDefault();
  const text = (e.clipboardData || window.clipboardData).getData('text') || '';
  document.execCommand('insertText', false, text.replace(/\D+/g, ''));
}
function clearYearOnFocus(e) { e.target.value = ''; }

// Create/fetch root
function ensureYearRoot() {
  let root = document.getElementById('year-dd-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'year-dd-root';
    document.body.appendChild(root);
  }
  return root;
}

function closeYearDropdown() {
  const root = document.getElementById('year-dd-root');
  if (yearDDActive && yearDDActive.teardown) yearDDActive.teardown();
  yearDDActive = null;
  if (root) root.innerHTML = '';
}

function positionForInput(inputEl, ddEl) {
  const rect = inputEl.getBoundingClientRect();
  // Use fixed positioning so we set viewport coords directly:
  ddEl.style.position = 'fixed';
  ddEl.style.top = `${rect.bottom + 4}px`;
  ddEl.style.left = `${rect.left}px`;
  ddEl.style.width = `${rect.width}px`;
}

function showYearDropdown(inputEl) {
  const root = ensureYearRoot();

  let cur = parseInt(inputEl.value, 10);
  if (isNaN(cur)) cur = YEAR_MAX;
  cur = Math.min(Math.max(cur, YEAR_MIN), YEAR_MAX);

  const years = [];
  for (let y = YEAR_MIN; y <= YEAR_MAX; y++) years.push(y);

  root.innerHTML = `
    <div class="year-dropdown" data-for="${inputEl.id}">
      <div class="year-dropdown-header">
        <span>min ${YEAR_MIN}&nbsp;&nbsp;max ${YEAR_MAX}</span>
        <button type="button" class="year-dd-close" aria-label="Close">×</button>
      </div>
      <div class="year-dropdown-list">
        ${years.map(y => `
          <button type="button" class="year-dd-item ${y===cur?'is-current':''}" data-year="${y}">
            ${y}
          </button>`).join('')}
      </div>
    </div>
  `;

  const dd = root.querySelector('.year-dropdown');
  const listEl = dd.querySelector('.year-dropdown-list');
  const closeBtn = dd.querySelector('.year-dd-close');

  // Initial position
  positionForInput(inputEl, dd);

  // Wire close
  closeBtn.addEventListener('click', closeYearDropdown);

  // Select year
  dd.querySelectorAll('.year-dd-item').forEach(btn => {
    btn.addEventListener('click', () => {
      inputEl.value = btn.dataset.year;
      closeYearDropdown();
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    });
  });

  // Scroll selected into view
  const curBtn = dd.querySelector('.year-dd-item.is-current');
  if (curBtn) {
    listEl.scrollTop = curBtn.offsetTop - listEl.clientHeight / 2 + curBtn.offsetHeight / 2;
  }

  // Reposition on any scroll (capture=true catches nested scroll containers) and on resize
  const reposition = () => positionForInput(inputEl, dd);
  const onScroll = () => reposition();
  const onResize = () => reposition();

  window.addEventListener('resize', onResize);
  document.addEventListener('scroll', onScroll, true);

  // Outside click closes
  const outside = (ev) => {
    if (!dd.contains(ev.target)) closeYearDropdown();
  };
  setTimeout(() => document.addEventListener('mousedown', outside, { once: true }), 0);

  yearDDActive = {
    inputEl,
    reposition,
    teardown() {
      window.removeEventListener('resize', onResize);
      document.removeEventListener('scroll', onScroll, true);
    }
  };
}

function attachSpinnerDropdown(inputEl) {
  inputEl.addEventListener('mousedown', (e) => {
    const r = inputEl.getBoundingClientRect();
    const x = e.clientX - r.left;
    const spinnerZone = x >= r.width - 24;
    if (spinnerZone) {
      e.preventDefault();
      e.stopPropagation();
      inputEl.blur();
      // Close any existing then open
      closeYearDropdown();
      showYearDropdown(inputEl);
    }
  });
}

function toggleSortTutorial(forceHide = false) {
  const box = document.getElementById('sort-tutorial');
  if (!box) return;

  // respect "Don't show again"
  const hideKey = 'liraya_hide_sort_tutorial';
  const cb = document.getElementById('hide-sort-tutorial');
  if (forceHide) {
    if (cb && cb.checked) localStorage.setItem(hideKey, '1');
    box.hidden = true;
    return;
  }
  // toggle
  box.hidden = !box.hidden;
}

document.addEventListener('DOMContentLoaded', () => {
  const hideKey = 'liraya_hide_sort_tutorial';
  const box = document.getElementById('sort-tutorial');
  if (box && localStorage.getItem(hideKey) === '1') {
    box.hidden = true; // keep hidden
  }
});

// ===== LIRAYA Guided Tour (non-destructive highlight) =====
(function() {
  const steps = [
    {
      id:'sorting', title:'Sorting options', target:'#sidebar-sort',
      message:'Pick how results are ordered: Relevance, Title (Alphabetical), Author (Alphabetical), Newest→Oldest, or Oldest→Newest. Your current search & filters are kept.',
      placement:'right'
    },
    {
      id:'shelf', title:'Shelf Category', target:'#sec-shelf',
      message:'Filter results by shelf category. Click items to toggle: Search results will be filtered based on selected items.',
      placement:'right',
      highlightTarget: (anchor)=> anchor?.nextElementSibling || anchor
    },
    {
      id:'subjects', title:'Subjects / Keywords', target:'#sec-subjects',
      message:'Narrow by subjects/keywords. Use “See All” to expand, click to toggle subjects or keywords.',
      placement:'right',
      highlightTarget: (anchor)=> anchor?.nextElementSibling || anchor
    },
    {
      id:'year', title:'Year range', target:'#sec-year',
      message:'Type Min/Max year (1900 - Current Year) or open the arrow picker. Click “Apply Year Filter” to apply.',
      placement:'right',
      // Special: highlight union of min + max rows if present
      getCustomRect: () => {
        const minEl = document.getElementById('min-year')?.closest('.year-input');
        const maxEl = document.getElementById('max-year')?.closest('.year-input');
        const btnEl = document.querySelector('.year-button');
        const rects = [minEl, maxEl, btnEl].filter(Boolean).map(el => el.getBoundingClientRect());
        if (!rects.length) return null;
        const pad = 6;
        const left = Math.max(0, Math.min(...rects.map(r => r.left)) - pad);
        const top  = Math.max(0, Math.min(...rects.map(r => r.top)) - pad);
        const right = Math.min(window.innerWidth, Math.max(...rects.map(r => r.right)) + pad);
        const bottom= Math.min(window.innerHeight, Math.max(...rects.map(r => r.bottom)) + pad);
        return { left, top, width: right-left, height: bottom-top };
      }
    },
    {
      id:'resource', title:'Resource Type', target:'#sec-resource',
      message:'Filter by resource type (e.g., Book, Thesis, etc.). You can select multiple.',
      placement:'right',
      highlightTarget: (anchor)=> anchor?.nextElementSibling || anchor
    },
    {
      id:'pagination', title:'Pagination', target:'#pagination-top',
      message:'Use these controls to move between result pages. The current sorting and filters remain applied.',
      placement:'bottom'
    }
  ];

  let current = -1;
  let overlayEl, tooltipEl, ringEl;

  window.startLirayaTour = function() {
    ensureChrome();
    goTo(0);
  };

  function ensureChrome(){
    if (!overlayEl){
      overlayEl = document.createElement('div');
      overlayEl.id='liraya-tour-overlay'; overlayEl.style.display='none';
      overlayEl.addEventListener('click', endTour);
      document.body.appendChild(overlayEl);
    }
    if (!ringEl){
      ringEl = document.createElement('div');
      ringEl.id='liraya-tour-ring'; ringEl.style.display='none';
      document.body.appendChild(ringEl);
    }
    if (!tooltipEl){
      tooltipEl = document.createElement('div');
      tooltipEl.id='liraya-tour-tooltip'; tooltipEl.style.display='none';
      tooltipEl.innerHTML = `
        <button class="liraya-tour-close" aria-label="Close" type="button">×</button>
        <div class="liraya-tour-title"></div>
        <div class="liraya-tour-body"></div>
        <div class="liraya-tour-actions" style="display:flex;justify-content:space-between;gap:10px;margin-top:10px;">
          <button class="liraya-tour-btn liraya-tour-secondary" type="button" data-act="prev">Back</button>
          <button class="liraya-tour-btn" type="button" data-act="next">Next</button>
        </div>`;
      document.body.appendChild(tooltipEl);
      tooltipEl.querySelector('.liraya-tour-close').addEventListener('click', endTour);
      tooltipEl.querySelector('[data-act="prev"]').addEventListener('click', ()=> goTo(current-1));
      tooltipEl.querySelector('[data-act="next"]').addEventListener('click', ()=> goTo(current+1));
      window.addEventListener('resize', reposition, {passive:true});
      document.addEventListener('scroll', reposition, true);
      document.addEventListener('keydown', (e)=>{ if (e.key==='Escape') endTour(); });
    }
  }

  function endTour(){
    if (overlayEl) overlayEl.style.display='none';
    if (tooltipEl) tooltipEl.style.display='none';
    if (ringEl)    ringEl.style.display='none';
    current = -1;
  }

  function goTo(i){
    if (i < 0 || i >= steps.length) return endTour();
    current = i;
    const s = steps[i];

    const anchor = document.querySelector(s.target);
    if (!anchor) return goTo(i+1); // skip missing

    const hlTarget = (typeof s.highlightTarget==='function' ? s.highlightTarget(anchor) : anchor) || anchor;

    // Compute highlight rectangle
    let rect;
    if (typeof s.getCustomRect === 'function'){
      rect = s.getCustomRect();
    }
    if (!rect){
      const r = hlTarget.getBoundingClientRect();
      const pad = 6;
      rect = {
        left: Math.max(0, r.left - pad),
        top:  Math.max(0, r.top  - pad),
        width: Math.min(window.innerWidth, r.right + pad) - Math.max(0, r.left - pad),
        height: Math.min(window.innerHeight, r.bottom + pad) - Math.max(0, r.top - pad)
      };
    }

    // Show chrome
    overlayEl.style.display='block';
    ringEl.style.display='block';
    tooltipEl.style.display='block';

    // Position ring
    ringEl.style.left   = `${rect.left}px`;
    ringEl.style.top    = `${rect.top}px`;
    ringEl.style.width  = `${rect.width}px`;
    ringEl.style.height = `${rect.height}px`;

    // Content
    tooltipEl.querySelector('.liraya-tour-title').textContent = s.title;
    tooltipEl.querySelector('.liraya-tour-body').textContent  = s.message;

    // Buttons
    tooltipEl.querySelector('[data-act="prev"]').disabled = (i===0);
    tooltipEl.querySelector('[data-act="next"]').textContent = (i===steps.length-1) ? 'Finish' : 'Next';

    // Position tooltip
    positionTooltipAround(rect, s.placement || 'bottom');

    // Scroll into view
    hlTarget.scrollIntoView({behavior:'smooth', block:'center'});
  }

  function reposition(){
    if (current < 0) return;
    const s = steps[current];
    const anchor = document.querySelector(s.target);
    if (!anchor) return;

    const hlTarget = (typeof s.highlightTarget==='function' ? s.highlightTarget(anchor) : anchor) || anchor;

    let rect;
    if (typeof s.getCustomRect === 'function'){
      rect = s.getCustomRect();
    }
    if (!rect){
      const r = hlTarget.getBoundingClientRect();
      const pad = 6;
      rect = {
        left: Math.max(0, r.left - pad),
        top:  Math.max(0, r.top  - pad),
        width: Math.min(window.innerWidth, r.right + pad) - Math.max(0, r.left - pad),
        height: Math.min(window.innerHeight, r.bottom + pad) - Math.max(0, r.top - pad)
      };
    }

    ringEl.style.left   = `${rect.left}px`;
    ringEl.style.top    = `${rect.top}px`;
    ringEl.style.width  = `${rect.width}px`;
    ringEl.style.height = `${rect.height}px`;

    positionTooltipAround(rect, s.placement || 'bottom');
  }

  function positionTooltipAround(r, placement){
    const t = tooltipEl.getBoundingClientRect();
    let top = r.top + r.height + 8;
    let left = r.left + (r.width - t.width)/2;

    if (placement === 'right'){
      top = r.top + (r.height - t.height)/2;
      left = r.left + r.width + 12;
    } else if (placement === 'left'){
      top = r.top + (r.height - t.height)/2;
      left = r.left - t.width - 12;
    } else if (placement === 'top'){
      top = r.top - t.height - 8;
      left = r.left + (r.width - t.width)/2;
    }

    const pad = 8;
    top  = Math.max(pad, Math.min(top,  window.innerHeight - t.height - pad));
    left = Math.max(pad, Math.min(left, window.innerWidth  - t.width  - pad));
    tooltipEl.style.top  = `${top}px`;
    tooltipEl.style.left = `${left}px`;
  }
})();



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
function changePage(page, { push = true } = {}) {
  if (page < 1) page = 1;
  if (page > totalPages) page = totalPages;

  // Don't reload if it's the same page
  if (page === currentPage) return;

  currentPage = page;

  // Sync URL ?page=...
  if (push) {
    const params = new URLSearchParams(window.location.search);
    params.set('page', String(page));
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    history.pushState({ page }, '', newUrl);
  }

  fetchBooks(page);
  // We'll update pagination after the content is loaded
}

// Handle browser back/forward to the correct page (no extra push)
window.addEventListener('popstate', () => {
  const params = new URLSearchParams(location.search);
  const p = parseInt(params.get('page') || '1', 10);
  changePage(isNaN(p) ? 1 : p, { push: false });
});


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

    // First page
    if (currentPage > 1) {
      const firstButton = document.createElement('button');
      firstButton.className = 'nav-button';
      firstButton.textContent = '<<';
      firstButton.addEventListener('click', (e) => {
        e.preventDefault();
        changePage(1);
      });
      paginationElement.appendChild(firstButton);
    }

    // Prev
    if (currentPage > 1) {
      const prevButton = document.createElement('button');
      prevButton.className = 'nav-button';
      prevButton.textContent = '<';
      prevButton.addEventListener('click', (e) => {
        e.preventDefault();
        changePage(currentPage - 1);
      });
      paginationElement.appendChild(prevButton);
    }

    // Calculate page range to show 10 pages
    let startPage = Math.max(1, currentPage - 4);
    let endPage = Math.min(totalPages, startPage + 9);
    
    // Adjust start if we're near the end
    if (endPage - startPage < 9) {
      startPage = Math.max(1, endPage - 9);
    }

    // Pages
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

    // Next
    if (currentPage < totalPages) {
      const nextButton = document.createElement('button');
      nextButton.className = 'nav-button';
      nextButton.textContent = '>';
      nextButton.addEventListener('click', (e) => {
        e.preventDefault();
        changePage(currentPage + 1);
      });
      paginationElement.appendChild(nextButton);
    }

    // Last page
    if (currentPage < totalPages) {
      const lastButton = document.createElement('button');
      lastButton.className = 'nav-button';
      lastButton.textContent = '>>';
      lastButton.addEventListener('click', (e) => {
        e.preventDefault();
        changePage(totalPages);
      });
      paginationElement.appendChild(lastButton);
    }
  });

  // ✅ Reveal only after JS finished rendering
  document.querySelectorAll('.pagination').forEach(el => {
    el.style.visibility = 'visible';
  });
}

// ===== Loading overlay helpers =====
function ensureLoadingOverlay() {
  let el = document.getElementById('liraya-loading');
  if (!el) {
    el = document.createElement('div');
    el.id = 'liraya-loading';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.style.display = 'none';
    el.style.position = 'fixed';
    el.style.left = '0';
    el.style.right = '0';
    el.style.bottom = '0';
    el.style.top = '0'; // will be corrected to header height right before show
    el.style.background = 'rgba(0,0,0,0.45)';
    el.style.zIndex = '9990'; // header should be above; we also start overlay below header
    el.style.alignItems = 'center';
    el.style.justifyContent = 'center';
    el.style.backdropFilter = 'blur(1px)';
    el.innerHTML = `
      <div class="box">
        <div class="liraya-spinner" role="status" aria-label="Loading"></div>
      </div>
    `;

    document.body.appendChild(el);
  }
  return el;
}

function setOverlayTopToHeader(el) {
  const header = document.querySelector('header');
  // Use offsetHeight which includes borders/padding and works with position:sticky/fixed
  const h = header ? header.offsetHeight : 0;
  el.style.top = `${h}px`;  // start *below* the header so it never covers it
  el.style.left = '0';
  el.style.right = '0';
  el.style.bottom = '0';
  el.style.position = 'fixed';
}

let _overlayResizeHandler = null;

function showLoadingOverlay() {
  const el = ensureLoadingOverlay();
  setOverlayTopToHeader(el);
  el.style.display = 'flex';

  // Keep overlay aligned under header if window resizes (or header height changes)
  _overlayResizeHandler = () => {
    const visible = el && el.style.display !== 'none';
    if (visible) setOverlayTopToHeader(el);
  };
  window.addEventListener('resize', _overlayResizeHandler, { passive: true });


}

function hideLoadingOverlay() {
  const el = document.getElementById('liraya-loading');
  if (el) el.style.display = 'none';

  if (_overlayResizeHandler) {
    window.removeEventListener('resize', _overlayResizeHandler);
    _overlayResizeHandler = null;
  }

}



// Fetch new page via AJAX while preserving current query params
function fetchBooks(page) {
  // 👉 show overlay immediately on page change
  showLoadingOverlay();

  const params = new URLSearchParams(window.location.search);
  params.set('page', page);
  const url = `${window.location.pathname}?${params.toString()}`;

  // Keep layout from jumping while loading (optional nicety)
  const curMain = document.querySelector('.main-content');
  if (curMain) {
    const currentHeight = curMain.offsetHeight;
    curMain.style.minHeight = `${currentHeight}px`;
  }

  fetch(url)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.text();
    })
    .then(html => {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = html;

      // Replace book list
      const newMain = tempDiv.querySelector('.main-content');
      if (newMain && curMain) {
        curMain.innerHTML = newMain.innerHTML;
        curMain.style.minHeight = '';
      }

      // Sync the "No results" overlay with the new page
      const existingNoRes = document.getElementById('no-results-overlay');
      if (existingNoRes) existingNoRes.remove();
      
      const newNoRes = tempDiv.querySelector('#no-results-overlay');
      if (newNoRes) {
        // Reinsert and ensure it doesn't cover header (safety if template changes)
        newNoRes.style.top = `${(document.querySelector('header')?.offsetHeight || 0)}px`;
        document.body.appendChild(newNoRes);
      }


      // Update pagination data (current/total/count/per-page)
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
    .catch(err => {
      console.error('Error fetching books:', err);
      // Keep pagination usable even on error
      updatePagination();
    })
    .finally(() => {
      // 👉 hide overlay only after DOM + pagination updated (or error handled)
      hideLoadingOverlay();
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
    const value = element.getAttribute('data-resource-type');
    const set = new Set(params.getAll('active_resource_types'));
    if (element.classList.contains('active')) set.add(value); else set.delete(value);
    params.delete('active_resource_types');
    [...set].forEach(v => params.append('active_resource_types', v));
  } else if (element.hasAttribute('data-category')) {
    const value = element.getAttribute('data-category');
    const set = new Set(params.getAll('active_categories'));
    if (element.classList.contains('active')) set.add(value); else set.delete(value);
    params.delete('active_categories');
    [...set].forEach(v => params.append('active_categories', v));
  } else if (element.hasAttribute('data-subject')) {
    const value = element.getAttribute('data-subject');
    const set = new Set(params.getAll('active_subjects'));
    if (element.classList.contains('active')) set.add(value); else set.delete(value);
    params.delete('active_subjects');
    [...set].forEach(v => params.append('active_subjects', v));
  }

  params.set('page', 1);

  // 👇 Show overlay before navigating
  showLoadingOverlay();
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
  showLoadingOverlay();
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

  // --- Always show overlay on form submits (sidebar & header search)
  document.querySelectorAll('.sidebar form, form.search-form').forEach(form => {
    form.addEventListener('submit', () => {
      showLoadingOverlay();
    }, { capture: true });
  });
  
  // --- Specifically show overlay when sidebar sort changes (it auto-submits)
  const sidebarSort = document.getElementById('sidebar-sort');
  if (sidebarSort) {
    sidebarSort.addEventListener('change', () => {
      showLoadingOverlay(); // form will submit via onchange attribute
    });
  }


  bindClickHover(minYearInput);
  bindClickHover(maxYearInput);
  bindClickHover(applyBtn);
  bindClickHover(refineHdr);

  if (refineHdr) {
    refineHdr.setAttribute('tabindex', '0');
    refineHdr.setAttribute('role', 'button');
  }

  // Allow typing; validate only on Apply; hook spinner dropdown; clear on focus/click
  if (minYearInput) {
    minYearInput.setAttribute('min', YEAR_MIN);
    minYearInput.setAttribute('max', YEAR_MAX);
    if (!minYearInput.value) minYearInput.value = YEAR_MIN;
    minYearInput.addEventListener('keydown', filterYearKeydown);
    minYearInput.addEventListener('paste', sanitizeYearPaste);
    minYearInput.addEventListener('input', sanitizeYearInput);
    minYearInput.addEventListener('focus', clearYearOnFocus);
    minYearInput.addEventListener('click', clearYearOnFocus);
    attachSpinnerDropdown(minYearInput);
  }
  if (maxYearInput) {
    maxYearInput.setAttribute('min', YEAR_MIN);
    maxYearInput.setAttribute('max', YEAR_MAX);
    if (!maxYearInput.value) maxYearInput.value = YEAR_MAX;
    maxYearInput.addEventListener('keydown', filterYearKeydown);
    maxYearInput.addEventListener('paste', sanitizeYearPaste);
    maxYearInput.addEventListener('input', sanitizeYearInput);
    maxYearInput.addEventListener('focus', clearYearOnFocus);
    maxYearInput.addEventListener('click', clearYearOnFocus);
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

  const set = new Set(params.getAll('active_subjects'));
  if (element.classList.contains('active')) set.add(value); else set.delete(value);
  params.delete('active_subjects');
  [...set].forEach(v => params.append('active_subjects', v));

  params.set('page', 1);

  // 👇 Show overlay before navigating
  showLoadingOverlay();
  window.location.search = params.toString();
}


function isOverlayVisible() {
  const el = document.getElementById('liraya-loading');
  return !!(el && el.style.display !== 'none');
}

