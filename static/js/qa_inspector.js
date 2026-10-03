/* Mobile QA inspector. Enabled only with ?qa=1. */
(() => {
  const params = new URLSearchParams(location.search);
  if (params.get('qa') !== '1') return;

  document.documentElement.classList.add('qa-mode');

  const panel = document.createElement('aside');
  panel.id = 'qa-inspector';
  panel.innerHTML = `
    <div class="qa-head">
      <strong>Mobile QA</strong>
      <button data-qa="collapse">−</button>
    </div>
    <div class="qa-presets">
      <button data-size="360,800">360</button>
      <button data-size="390,844">390</button>
      <button data-size="412,915">412</button>
      <button data-size="reset">Live</button>
    </div>
    <pre id="qa-stats"></pre>
    <div class="qa-actions">
      <button data-qa="overflow">Overflow</button>
      <button data-qa="targets">Targets</button>
      <button data-qa="player">Player</button>
      <button data-qa="search">Search</button>
    </div>`;
  document.body.appendChild(panel);

  const stats = panel.querySelector('#qa-stats');
  let highlightMode = '';

  function visible(el) {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  }

  function getOverflowing() {
    return [...document.querySelectorAll('body *')].filter(el => {
      if (!visible(el) || el.closest('#qa-inspector')) return false;
      const r = el.getBoundingClientRect();
      return r.left < -1 || r.right > innerWidth + 1;
    });
  }

  function getSmallTargets() {
    return [...document.querySelectorAll('button,a,input,[onclick],[role="button"]')].filter(el => {
      if (!visible(el) || el.closest('#qa-inspector')) return false;
      const r = el.getBoundingClientRect();
      return r.width < 44 || r.height < 44;
    });
  }

  function update() {
    const vv = window.visualViewport;
    const video = document.querySelector('#video-modal video');
    const vr = video && visible(video) ? video.getBoundingClientRect() : null;
    const overflow = getOverflowing();
    const small = getSmallTargets();
    const active = document.activeElement;
    stats.textContent = [
      `viewport  ${innerWidth}×${innerHeight}`,
      `visual    ${Math.round(vv?.width || innerWidth)}×${Math.round(vv?.height || innerHeight)}`,
      `dpr       ${devicePixelRatio}`,
      `orient    ${innerWidth > innerHeight ? 'landscape' : 'portrait'}`,
      `overflow  ${overflow.length}`,
      `<44px     ${small.length}`,
      `focus     ${active?.id || active?.tagName || '-'}`,
      vr ? `video     ${Math.round(vr.width)}×${Math.round(vr.height)}` : 'video     closed'
    ].join('\n');

    document.querySelectorAll('.qa-overflow,.qa-small-target').forEach(el => el.classList.remove('qa-overflow','qa-small-target'));
    if (highlightMode === 'overflow') overflow.forEach(el => el.classList.add('qa-overflow'));
    if (highlightMode === 'targets') small.forEach(el => el.classList.add('qa-small-target'));
  }

  panel.addEventListener('click', e => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const size = btn.dataset.size;
    if (size) {
      if (size === 'reset') {
        document.documentElement.style.removeProperty('--qa-width');
        document.documentElement.style.removeProperty('--qa-height');
        document.body.classList.remove('qa-emulate');
      } else {
        const [w,h] = size.split(',');
        document.documentElement.style.setProperty('--qa-width', w + 'px');
        document.documentElement.style.setProperty('--qa-height', h + 'px');
        document.body.classList.add('qa-emulate');
      }
      update();
      return;
    }
    const action = btn.dataset.qa;
    if (action === 'collapse') panel.classList.toggle('qa-collapsed');
    if (action === 'overflow' || action === 'targets') {
      highlightMode = highlightMode === action ? '' : action;
      update();
    }
    if (action === 'player') document.querySelector('.movie-card')?.click();
    if (action === 'search') document.getElementById('search')?.focus();
  });

  ['resize','orientationchange','focusin','focusout'].forEach(evt => addEventListener(evt, update));
  window.visualViewport?.addEventListener('resize', update);
  new MutationObserver(() => requestAnimationFrame(update)).observe(document.body, {subtree:true, childList:true, attributes:true, attributeFilter:['class','style']});
  update();
})();