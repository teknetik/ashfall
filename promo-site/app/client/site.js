// Ashfall promo site — progressive enhancement. Every feature degrades to working HTML without JS.
(() => {
  'use strict';
  const doc = document;
  const root = doc.documentElement;
  root.classList.remove('no-js');
  root.classList.add('js');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const isReduced = () => reduced.matches;
  /** @type {(sel: string, ctx?: ParentNode) => any} */
  const $ = (sel, ctx = doc) => ctx.querySelector(sel);
  /** @type {(sel: string, ctx?: ParentNode) => any[]} */
  const $$ = (sel, ctx = doc) => Array.from(ctx.querySelectorAll(sel));
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

  /* ---------- header solid on scroll ---------- */
  const header = $('.site-header');
  if (header && !header.classList.contains('site-header--solid')) {
    const onScroll = () => header.classList.toggle('is-solid', window.scrollY > 80);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---------- active section in nav ---------- */
  const navLinks = $$('.nav a[href^="/#"]');
  if (navLinks.length && 'IntersectionObserver' in window) {
    const map = new Map();
    for (const a of navLinks) {
      const el = doc.getElementById(a.getAttribute('href').slice(2));
      if (el) map.set(el, a);
    }
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        for (const a of navLinks) a.removeAttribute('aria-current');
        const a = map.get(e.target);
        if (a) a.setAttribute('aria-current', 'true');
      }
    }, { rootMargin: '-45% 0px -50% 0px' });
    for (const el of map.keys()) io.observe(el);
  }

  /* ---------- modal helper (menu + lightbox) ---------- */
  function trapFocus(container, e) {
    if (e.key !== 'Tab') return;
    const items = $$(FOCUSABLE, container).filter((el) => el.offsetParent !== null || el === doc.activeElement);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  const backgroundEls = () => $$('body > header, body > main, body > footer, body > .skip');
  function setBackgroundInert(on) {
    for (const el of backgroundEls()) {
      if (on) el.setAttribute('inert', ''); else el.removeAttribute('inert');
    }
    doc.body.classList.toggle('is-locked', on);
  }

  /* ---------- mobile menu (portalled sibling of header, not inside it) ---------- */
  const menuBtn = $('.menu-btn');
  const menu = $('#site-menu');
  if (menuBtn && menu) {
    if (menu.parentElement !== doc.body) doc.body.appendChild(menu);
    const close = (restore = true) => {
      menu.hidden = true;
      menuBtn.setAttribute('aria-expanded', 'false');
      setBackgroundInert(false);
      doc.removeEventListener('keydown', onKey);
      if (restore) menuBtn.focus();
    };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else trapFocus(menu, e);
    };
    const open = () => {
      menu.hidden = false;
      menuBtn.setAttribute('aria-expanded', 'true');
      setBackgroundInert(true);
      doc.addEventListener('keydown', onKey);
      const c = $('.menu__close', menu);
      if (c) c.focus();
    };
    menuBtn.addEventListener('click', () => (menu.hidden ? open() : close()));
    $$('.menu__close', menu).forEach((b) => b.addEventListener('click', () => close()));
    $$('a', menu).forEach((a) => a.addEventListener('click', () => close(false)));
    window.addEventListener('resize', () => { if (!menu.hidden && window.innerWidth >= 1180) close(false); });
  }

  /* ---------- status rails collapse to a disclosure on small screens ---------- */
  if (window.matchMedia('(max-width: 1023px)').matches) $$('.rail__details').forEach((d) => { d.open = false; });

  /* ---------- hero boot line ---------- */
  const boot = $('.hero__boot');
  if (boot) {
    const full = boot.getAttribute('data-text') || boot.textContent;
    const sr = $('.visually-hidden', boot);
    const vis = $('.hero__boot-text', boot);
    if (vis && !isReduced()) {
      vis.textContent = '';
      const caret = doc.createElement('span');
      caret.className = 'caret';
      boot.appendChild(caret);
      const start = performance.now();
      const dur = 1400;
      const step = (t) => {
        const n = Math.min(full.length, Math.round(((t - start) / dur) * full.length));
        vis.textContent = full.slice(0, n);
        if (n < full.length) requestAnimationFrame(step);
        else setTimeout(() => caret.remove(), 2400);
      };
      requestAnimationFrame(step);
    }
    if (sr) sr.textContent = full;
  }

  /* ---------- reveal on scroll + lattice typing ---------- */
  if ('IntersectionObserver' in window && !isReduced()) {
    const revealIo = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-in'); revealIo.unobserve(e.target); }
    }, { rootMargin: '0px 0px -10% 0px' });
    $$('.reveal').forEach((el) => revealIo.observe(el));

    const typeIo = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        typeIo.unobserve(e.target);
        const pre = e.target;
        const text = pre.textContent;
        // Original text stays in the accessibility tree; the visible typing is an aria-hidden overlay.
        const overlay = doc.createElement('pre');
        overlay.setAttribute('aria-hidden', 'true');
        overlay.className = 'lattice__overlay';
        pre.classList.add('is-typing');
        pre.parentElement.appendChild(overlay);
        const start = performance.now();
        const dur = Math.min(2600, 18 * text.length);
        const step = (t) => {
          const n = Math.min(text.length, Math.round(((t - start) / dur) * text.length));
          overlay.textContent = text.slice(0, n);
          if (n < text.length) requestAnimationFrame(step);
          else { pre.classList.remove('is-typing'); overlay.remove(); }
        };
        requestAnimationFrame(step);
      }
    }, { rootMargin: '0px 0px -15% 0px' });
    $$('.lattice pre[data-type]').forEach((el) => typeIo.observe(el));
  } else {
    $$('.reveal').forEach((el) => el.classList.add('is-in'));
  }

  /* ---------- relative dates ---------- */
  const rtf = 'Intl' in window && Intl.RelativeTimeFormat ? new Intl.RelativeTimeFormat('en-GB', { numeric: 'auto' }) : null;
  if (rtf) {
    const now = Date.now();
    for (const t of $$('time[data-relative]')) {
      const d = Date.parse(t.getAttribute('datetime'));
      if (!Number.isFinite(d)) continue;
      const s = Math.round((d - now) / 1000);
      const abs = Math.abs(s);
      let txt;
      if (abs < 60) txt = rtf.format(Math.round(s), 'second');
      else if (abs < 3600) txt = rtf.format(Math.round(s / 60), 'minute');
      else if (abs < 86400) txt = rtf.format(Math.round(s / 3600), 'hour');
      else if (abs < 86400 * 30) txt = rtf.format(Math.round(s / 86400), 'day');
      else continue;
      t.setAttribute('title', t.textContent.trim());
      t.textContent = txt;
    }
  }

  /* ---------- lightbox ---------- */
  const triggers = $$('a[data-lightbox]');
  if (triggers.length) {
    const lb = doc.createElement('div');
    lb.className = 'lightbox';
    lb.hidden = true;
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-labelledby', 'lb-title');
    lb.innerHTML = '<div class="lightbox__bar"><span class="lightbox__count" aria-live="polite"></span><button type="button" class="lightbox__close">Close <span aria-hidden="true">×</span></button></div>' +
      '<div class="lightbox__stage"><button type="button" class="lightbox__nav lightbox__nav--prev" aria-label="Previous image">‹</button><img alt=""><button type="button" class="lightbox__nav lightbox__nav--next" aria-label="Next image">›</button></div>' +
      '<div class="lightbox__meta"><span class="lightbox__badge"></span><h2 id="lb-title"></h2><p class="lightbox__caption"></p></div>';
    doc.body.appendChild(lb);
    const img = $('img', lb);
    const title = $('#lb-title', lb);
    const cap = $('.lightbox__caption', lb);
    const badge = $('.lightbox__badge', lb);
    const count = $('.lightbox__count', lb);
    const prev = $('.lightbox__nav--prev', lb);
    const next = $('.lightbox__nav--next', lb);
    let set = [];
    let idx = 0;
    let opener = null;
    const visibleSet = (name) => triggers.filter((a) => a.getAttribute('data-lightbox') === name && !a.closest('[hidden]'));
    const show = (i) => {
      idx = (i + set.length) % set.length;
      const a = set[idx];
      const fig = a.closest('figure');
      const thumb = $('img', a);
      img.src = a.getAttribute('href');
      img.alt = thumb ? thumb.alt : '';
      title.textContent = fig ? ($('.fig__title', fig)?.textContent || '').replace(/\.$/, '') : '';
      const capEl = fig ? $('figcaption', fig) : null;
      cap.textContent = capEl ? capEl.textContent.replace(title.textContent + '.', '').trim() : '';
      const b = fig ? $('.fig__badge .badge', fig) : null;
      badge.innerHTML = '';
      if (b) badge.appendChild(b.cloneNode(true));
      count.textContent = `${idx + 1} / ${set.length}`;
      prev.hidden = next.hidden = set.length < 2;
    };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'ArrowLeft' && set.length > 1) { e.preventDefault(); show(idx - 1); }
      else if (e.key === 'ArrowRight' && set.length > 1) { e.preventDefault(); show(idx + 1); }
      else trapFocus(lb, e);
    };
    const open = (a) => {
      opener = a;
      set = visibleSet(a.getAttribute('data-lightbox'));
      show(Math.max(0, set.indexOf(a)));
      lb.hidden = false;
      setBackgroundInert(true);
      doc.addEventListener('keydown', onKey);
      $('.lightbox__close', lb).focus();
    };
    const close = () => {
      lb.hidden = true;
      img.removeAttribute('src');
      setBackgroundInert(false);
      doc.removeEventListener('keydown', onKey);
      if (opener) opener.focus();
    };
    triggers.forEach((a) => a.addEventListener('click', (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      open(a);
    }));
    $('.lightbox__close', lb).addEventListener('click', close);
    prev.addEventListener('click', () => show(idx - 1));
    next.addEventListener('click', () => show(idx + 1));
    lb.addEventListener('click', (e) => { if (e.target === lb || (e.target instanceof Element && e.target.classList.contains('lightbox__stage'))) close(); });
    let sx = null;
    lb.addEventListener('touchstart', (e) => { if (e.touches.length === 1) sx = e.touches[0].clientX; }, { passive: true });
    lb.addEventListener('touchend', (e) => {
      if (sx === null || set.length < 2) return;
      const dx = e.changedTouches[0].clientX - sx;
      sx = null;
      if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
    });
  }

  /* ---------- gallery filters ---------- */
  const filters = $('.filters');
  if (filters) {
    const intro = $('.filter-intro');
    filters.hidden = false;
    filters.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-filter]');
      if (!b) return;
      const f = b.getAttribute('data-filter');
      $$('button', filters).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      let n = 0;
      for (const fig of $$('.gallery .fig')) {
        const show = f === 'all' || (fig.getAttribute('data-filters') || '').split(' ').includes(f);
        fig.hidden = !show;
        if (show) n++;
      }
      if (intro) intro.textContent = `${b.getAttribute('data-intro') || ''} Showing ${n} image${n === 1 ? '' : 's'}.`.trim();
    });
  }

  /* ---------- Lattice capacity explainer ---------- */
  for (const cap of $$('.capacity')) {
    const max = Number(cap.getAttribute('data-capacity')) || 100;
    const fill = $('.capacity__fill', cap);
    const readout = $('.capacity__readout', cap);
    const status = $('.capacity__status', cap);
    const update = () => {
      const on = $$('input:checked', cap).filter((i) => Number(i.value) > 0);
      const used = on.reduce((n, i) => n + Number(i.value), 0);
      fill.style.width = `${Math.min(100, (used / max) * 100)}%`;
      readout.textContent = `${used} / ${max}`;
      const over = used > max;
      cap.classList.toggle('is-over', over);
      const names = on.map((i) => i.getAttribute('data-label')).join(', ');
      status.textContent = over
        ? `CAPACITY EXCEEDED — using ${used} of ${max}. Drop a module or a companion link.`
        : `Using ${used} of ${max}. ${names ? `Running: ${names}.` : 'No modules running.'}`;
    };
    cap.addEventListener('change', update);
    update();
  }

  /* ---------- atlas map hotspots <-> region list ---------- */
  const spots = $$('.spot');
  if (spots.length) {
    /** @type {(slug: string) => HTMLDetailsElement | null} */
    const regionFor = (slug) => /** @type {HTMLDetailsElement | null} */ (doc.getElementById(`region-${slug}`));
    const spotFor = (slug) => $(`.spot[data-region="${slug}"]`);
    const hl = (slug, on) => {
      const r = regionFor(slug);
      const s = spotFor(slug);
      if (r) r.classList.toggle('is-active', on);
      if (s) s.classList.toggle('is-active', on);
    };
    for (const s of spots) {
      const slug = s.getAttribute('data-region');
      const r = regionFor(slug);
      if (r) s.setAttribute('aria-label', `${$('.region__name', r).textContent} — show details`);
      s.addEventListener('mouseenter', () => hl(slug, true));
      s.addEventListener('mouseleave', () => hl(slug, false));
      s.addEventListener('focus', () => hl(slug, true));
      s.addEventListener('blur', () => hl(slug, false));
      s.addEventListener('click', (e) => {
        if (!r) return;
        e.preventDefault();
        r.open = true;
        r.scrollIntoView({ behavior: isReduced() ? 'auto' : 'smooth', block: 'center' });
        $('summary', r).focus({ preventScroll: true });
      });
    }
    for (const r of $$('.region')) {
      const slug = r.getAttribute('data-region');
      r.addEventListener('mouseenter', () => hl(slug, true));
      r.addEventListener('mouseleave', () => hl(slug, false));
      $('summary', r).addEventListener('focus', () => hl(slug, true));
      $('summary', r).addEventListener('blur', () => hl(slug, false));
    }
    if (location.hash.startsWith('#region-')) {
      const r = doc.getElementById(location.hash.slice(1));
      if (r instanceof HTMLDetailsElement) r.open = true;
    }
  }

  /* ---------- forms: password toggles, counters, confirms ---------- */
  for (const wrap of $$('.pw')) {
    const input = $('input', wrap);
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.textContent = 'Show';
    btn.setAttribute('aria-pressed', 'false');
    btn.setAttribute('aria-label', 'Show password');
    btn.addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
      btn.setAttribute('aria-pressed', String(show));
      btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
    wrap.appendChild(btn);
  }
  for (const ta of $$('textarea[maxlength]')) {
    const max = Number(ta.getAttribute('maxlength'));
    const c = doc.createElement('p');
    c.className = 'counter';
    c.setAttribute('aria-hidden', 'true');
    const upd = () => { c.textContent = `${ta.value.length} / ${max}`; };
    ta.insertAdjacentElement('afterend', c);
    ta.addEventListener('input', upd);
    upd();
  }
  for (const f of $$('form[data-confirm]')) {
    f.addEventListener('submit', (e) => {
      if (!window.confirm(f.getAttribute('data-confirm'))) e.preventDefault();
    });
  }
  // Prevent double submits.
  for (const f of $$('form[method="post"]')) {
    f.addEventListener('submit', (e) => {
      if (e.defaultPrevented) return;
      if (f.dataset.submitting) { e.preventDefault(); return; }
      f.dataset.submitting = '1';
      setTimeout(() => { delete f.dataset.submitting; }, 4000);
    });
  }
  // Composer: show the feedback tag only for the feedback type.
  for (const comp of $$('.composer')) {
    const tag = $('.composer__tag', comp);
    if (!tag) continue;
    const upd = () => { tag.hidden = ($('input[name="type"]:checked', comp)?.value) !== 'feedback'; };
    comp.addEventListener('change', upd);
    upd();
  }
})();
