(() => {
  const host = document.getElementById('compilerAnswer');
  if (!host) return;

  const esc = (value = '') => String(value).replace(/[&<>'"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[c]));

  const state = { startedAt: 0, count: 0, history: [], currentEvent: null, timer: null };

  function labelFor(event) {
    const p = event.payload || {};
    const input = p.input || {};
    const result = p.result || {};
    switch (event.type) {
      case 'EVIDENCE_REQUIREMENTS': return 'Defining what must be proven';
      case 'SEARCHING': return input.query ? `Searching: ${input.query}` : 'Searching approved corpus';
      case 'DOCUMENT_FOUND': return `Inspecting: ${result.title || result.id || input.document_id || 'document'}`;
      case 'VERSION_CHECK': {
        const ids = Array.isArray(result) ? result.map(x => x.id).filter(Boolean) : [];
        return ids.length ? `Resolving versions: ${ids.join(' → ')}` : 'Resolving document versions';
      }
      case 'TEMPORAL_CHECK': {
        const id = result.document || input.document_id || 'source';
        const verdict = result.valid === true ? 'VALID' : result.valid === false ? 'NOT VALID' : 'checking';
        return `Checking validity: ${id} · ${verdict}`;
      }
      case 'OUTDATED_SOURCE': return 'Rejecting source: wrong point in time';
      case 'FOLLOWING_REFERENCE': return `Following reference: ${input.document_id || 'source'} → ${input.reference_id || 'dependency'}`;
      case 'VERIFYING': return 'Verifier checking every material claim';
      case 'EVIDENCE_GAP': return 'Verifier blocked draft — agent is repairing evidence';
      case 'SUPPORTED': return 'Evidence sufficient — releasing verified answer';
      case 'UNKNOWN': return 'Evidence insufficient — abstaining';
      case 'CONFLICT': return 'Conflicting evidence — withholding answer';
      default: return event.message || event.type || 'Working';
    }
  }

  function classFor(event) {
    if (event.type === 'EVIDENCE_GAP' || event.type === 'OUTDATED_SOURCE') return 'warn';
    if (event.type === 'SUPPORTED') return 'good';
    if (event.type === 'UNKNOWN' || event.type === 'CONFLICT') return 'boundary';
    return 'active';
  }

  function elapsedText() {
    return state.startedAt ? `${((performance.now() - state.startedAt) / 1000).toFixed(1)}s` : '0.0s';
  }

  function updateElapsedOnly() {
    const node = host.querySelector('.live-elapsed');
    if (!node || !state.startedAt) return;
    node.textContent = `${elapsedText()} · step ${state.count}`;
  }

  function startTimer() {
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(updateElapsedOnly, 100);
  }

  function stopTimer() {
    if (state.timer) clearInterval(state.timer);
    state.timer = null;
  }

  function render(event) {
    state.currentEvent = event;
    state.count += 1;
    const text = labelFor(event);
    state.history.push({ text, type: event.type });
    if (state.history.length > 4) state.history.shift();

    host.innerHTML = `
      <div class="live-evidence-card ${classFor(event)}">
        <div class="live-evidence-top">
          <span class="live-kicker">LIVE AGENT ACTIVITY</span>
          <span class="live-elapsed">${esc(elapsedText())} · step ${state.count}</span>
        </div>
        <div class="live-current">${esc(text)}</div>
        <div class="live-history">
          ${state.history.slice(0, -1).map(item => `<div><span>✓</span>${esc(item.text)}</div>`).join('')}
        </div>
      </div>`;
  }

  window.addEventListener('context-run-start', () => {
    stopTimer();
    state.startedAt = performance.now();
    state.count = 0;
    state.history = [];
    state.currentEvent = null;
    host.innerHTML = `
      <div class="live-evidence-card active">
        <div class="live-evidence-top">
          <span class="live-kicker">LIVE AGENT ACTIVITY</span>
          <span class="live-elapsed">0.0s · step 0</span>
        </div>
        <div class="live-current">Waiting for first agent action…</div>
      </div>`;
    startTimer();
  });

  window.addEventListener('context-compiler-live-event', event => render(event.detail || {}));
  window.addEventListener('context-compiler-result', () => {
    updateElapsedOnly();
    stopTimer();
  });
})();
