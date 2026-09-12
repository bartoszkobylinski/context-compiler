(() => {
  const host = document.getElementById('baselineAnswer');
  if (!host) return;

  const esc = (value = '') => String(value).replace(/[&<>'"]/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  }[c]));

  let history = [];
  let startedAt = 0;
  let timer = null;

  function elapsed() {
    return startedAt ? ((performance.now() - startedAt) / 1000).toFixed(1) : '0.0';
  }

  function titleFor(event) {
    if (event.type === 'QUESTION') return 'Question received';
    if (event.type === 'RETRIEVING') return 'Searching top-k once';
    if (event.type === 'TOP_K_READY') return 'Top-k fixed';
    if (event.type === 'ANSWERING') return 'Model answering from fixed context';
    if (event.type === 'ANSWER_READY') return 'One-shot answer ready';
    return event.message || event.type;
  }

  function detailFor(event) {
    if (event.type === 'RETRIEVING') return event.message;
    if (event.type === 'TOP_K_READY') {
      const hits = event.payload?.hits || [];
      return hits.map((h, i) => `#${i + 1} ${h.title || h.id} · ${h.score ?? '?'}`).join(' · ');
    }
    if (event.type === 'ANSWERING') return 'No version graph · no temporal check · no second retrieval pass';
    return event.message || '';
  }

  function render(event) {
    const title = titleFor(event);
    const detail = detailFor(event);
    history.push({title, detail});
    history = history.slice(-4);
    host.innerHTML = `
      <div class="baseline-live-card">
        <div class="baseline-live-head"><span>ONE-SHOT ACTIVITY</span><strong>${esc(event.type)}</strong></div>
        <div class="baseline-live-now"><span class="spinner"></span><div><strong>${esc(title)}</strong><div>${esc(detail)}</div></div></div>
        <div class="baseline-live-history">${history.map((item, i) => `<div class="baseline-live-row ${i === history.length - 1 ? 'current' : ''}"><span>${i === history.length - 1 ? '→' : '✓'}</span><div><strong>${esc(item.title)}</strong>${item.detail ? `<small>${esc(item.detail)}</small>` : ''}</div></div>`).join('')}</div>
        <div class="baseline-live-foot"><span>single retrieval pass</span><span id="baselineElapsed">${elapsed()}s</span></div>
      </div>`;
  }

  window.addEventListener('context-run-start', () => {
    history = [];
    startedAt = performance.now();
    clearInterval(timer);
    timer = setInterval(() => {
      const node = document.getElementById('baselineElapsed');
      if (node) node.textContent = `${elapsed()}s`;
    }, 100);
  });

  window.addEventListener('context-baseline-live-event', event => render(event.detail || {}));
  window.addEventListener('context-baseline-result', () => clearInterval(timer));
})();