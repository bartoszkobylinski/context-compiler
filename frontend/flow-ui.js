(() => {
  const baseline = document.querySelector('.baseline-panel .flow-mini');
  const compiler = document.querySelector('.compiler-panel .flow-mini');
  const runBtn = document.getElementById('runBtn');
  const queryDate = document.getElementById('queryDate');
  const dateField = document.getElementById('dateField');
  const dateFocus = document.getElementById('dateFocus');
  if (!baseline || !compiler || !runBtn) return;

  const baselineSteps = ['question','top-k chunks','answer'];
  const compilerSteps = ['requirements','search','inspect','temporal check','verify','repair','answer','unknown'];
  let liveCompilerEvents = false;
  let baselineTimer = null;

  function build(host, steps, kind) {
    host.classList.add('flow-track','idle');
    host.dataset.kind = kind;
    host.innerHTML = steps.map((step, i) => `${i ? '<span class="flow-arrow">→</span>' : ''}<span class="flow-step flow-${step.replace(/\s+/g,'-')}" data-step="${step}">${step}</span>`).join('');
  }

  function reset(host) {
    host.classList.remove('replaying');
    host.classList.add('idle');
    host.querySelectorAll('.flow-step').forEach(node => node.classList.remove('active','done'));
  }

  function activate(host, step) {
    const target = host.querySelector(`[data-step="${step}"]`);
    if (!target) return;
    host.classList.remove('idle');
    host.querySelectorAll('.flow-step.active').forEach(node => {
      if (node !== target) {
        node.classList.remove('active');
        node.classList.add('done');
      }
    });
    target.classList.remove('done');
    target.classList.add('active');
  }

  function replay(host, sequence, delay = 260) {
    reset(host);
    host.classList.remove('idle');
    host.classList.add('replaying');
    sequence.forEach((step, i) => setTimeout(() => activate(host, step), i * delay));
  }

  function stepForEvent(event = {}) {
    if (event.type === 'EVIDENCE_REQUIREMENTS') return 'requirements';
    if (event.type === 'SEARCHING') return 'search';
    if (['DOCUMENT_FOUND','FOLLOWING_REFERENCE','VERSION_CHECK'].includes(event.type)) return 'inspect';
    if (['TEMPORAL_CHECK','OUTDATED_SOURCE'].includes(event.type)) return 'temporal check';
    if (event.type === 'VERIFYING') return 'verify';
    if (event.type === 'EVIDENCE_GAP') return 'repair';
    if (event.type === 'UNKNOWN') return 'unknown';
    if (['SUPPORTED','CONFLICT'].includes(event.type)) return 'answer';
    return null;
  }

  function compilerSequence(data) {
    const seq = [];
    const push = step => { if (step && seq[seq.length - 1] !== step) seq.push(step); };
    for (const event of data.events || []) push(stepForEvent(event));
    if (!seq.length) return data.status === 'UNKNOWN' ? ['requirements','unknown'] : ['requirements','answer'];
    if (data.status === 'SUPPORTED' && seq[seq.length - 1] !== 'answer') push('answer');
    if (data.status === 'UNKNOWN' && seq[seq.length - 1] !== 'unknown') push('unknown');
    return seq;
  }

  function formatDate(value) {
    if (!value) return 'NO DATE';
    const [y,m,d] = value.split('-').map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d));
    return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(dt).toUpperCase();
  }

  let lastDate = queryDate?.value || '';
  function showDateChange(force = false) {
    if (!queryDate || !dateField || !dateFocus) return;
    dateFocus.querySelector('strong').textContent = formatDate(queryDate.value);
    if (!force && queryDate.value === lastDate) return;
    lastDate = queryDate.value;
    dateField.classList.remove('date-changed');
    void dateField.offsetWidth;
    dateField.classList.add('date-changed');
    setTimeout(() => dateField.classList.remove('date-changed'), 1100);
  }

  build(baseline, baselineSteps, 'baseline');
  build(compiler, compilerSteps, 'compiler');
  showDateChange(true);

  queryDate?.addEventListener('change', () => showDateChange());
  document.getElementById('presets')?.addEventListener('click', () => setTimeout(() => showDateChange(), 0));

  window.addEventListener('context-run-start', () => {
    liveCompilerEvents = false;
    if (baselineTimer) clearTimeout(baselineTimer);
    reset(baseline);
    reset(compiler);
    activate(baseline, 'question');
    activate(compiler, 'requirements');
    baselineTimer = setTimeout(() => activate(baseline, 'top-k chunks'), 140);
    if (dateField) {
      dateField.classList.add('date-running');
      setTimeout(() => dateField.classList.remove('date-running'), 1800);
    }
  });

  window.addEventListener('context-baseline-result', () => {
    if (baselineTimer) clearTimeout(baselineTimer);
    activate(baseline, 'answer');
  });

  window.addEventListener('context-compiler-live-event', event => {
    liveCompilerEvents = true;
    const step = stepForEvent(event.detail || {});
    if (step) activate(compiler, step);
  });

  window.addEventListener('context-compiler-result', event => {
    const data = event.detail || {};
    if (liveCompilerEvents) {
      activate(compiler, data.status === 'UNKNOWN' ? 'unknown' : 'answer');
      liveCompilerEvents = false;
      return;
    }
    // Challenge Mode still returns a completed trace, so replay it there.
    replay(compiler, compilerSequence(data), 240);
  });
})();
