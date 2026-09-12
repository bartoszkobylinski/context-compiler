(() => {
  const baseline = document.querySelector('.baseline-panel .flow-mini');
  const compiler = document.querySelector('.compiler-panel .flow-mini');
  const runBtn = document.getElementById('runBtn');
  if (!baseline || !compiler || !runBtn) return;

  const baselineSteps = ['question','retrieve 1','identify gap','retrieve 2','answer'];
  const compilerSteps = ['requirements','retrieve','resolve','candidate plans','close contract','verify','repair','release / hold','receipt','dataset'];
  let liveCompilerEvents = false;

  function build(host, steps, kind) {
    host.classList.add('flow-track','idle');
    host.dataset.kind = kind;
    host.innerHTML = steps.map((step, i) => `${i ? '<span class="flow-arrow">→</span>' : ''}<span class="flow-step flow-${step.replace(/[^a-z0-9]+/gi,'-').replace(/^-|-$/g,'')}" data-step="${step}">${step}</span>`).join('');
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

  function replay(host, sequence, delay = 220) {
    reset(host);
    host.classList.remove('idle');
    host.classList.add('replaying');
    sequence.forEach((step, i) => setTimeout(() => activate(host, step), i * delay));
  }

  function compilerStepForEvent(event = {}) {
    if (event.type === 'EVIDENCE_REQUIREMENTS') return 'requirements';
    if (['SEARCHING','DOCUMENT_FOUND'].includes(event.type)) return 'retrieve';
    if (['FOLLOWING_REFERENCE','VERSION_CHECK','TEMPORAL_CHECK','OUTDATED_SOURCE'].includes(event.type)) return 'resolve';
    if (event.type === 'REQUIREMENTS_CLOSED') return 'close contract';
    if (event.type === 'VERIFYING') return 'verify';
    if (event.type === 'EVIDENCE_GAP') return 'repair';
    if (['SUPPORTED','UNKNOWN','CONFLICT'].includes(event.type)) return 'release / hold';
    return null;
  }

  function compilerSequence(data) {
    const seq = [];
    const push = step => { if (step && seq[seq.length - 1] !== step) seq.push(step); };
    for (const event of data.events || []) push(compilerStepForEvent(event));
    if (Array.isArray(data.plan_candidates) && data.plan_candidates.length) {
      const closeIndex = seq.indexOf('close contract');
      if (closeIndex >= 0 && !seq.includes('candidate plans')) seq.splice(closeIndex, 0, 'candidate plans');
    }
    if (!seq.length) return ['requirements','release / hold'];
    if (seq[seq.length - 1] !== 'release / hold') push('release / hold');
    return seq;
  }

  build(baseline, baselineSteps, 'baseline');
  build(compiler, compilerSteps, 'compiler');

  window.addEventListener('context-run-start', () => {
    liveCompilerEvents = false;
    reset(baseline);
    reset(compiler);
    activate(baseline, 'question');
    activate(compiler, 'requirements');
  });

  window.addEventListener('context-baseline-live-event', event => {
    const e = event.detail || {};
    if (e.type === 'QUESTION') activate(baseline, 'question');
    else if (e.type === 'RETRIEVING' && e.payload?.pass === 1) activate(baseline, 'retrieve 1');
    else if (e.type === 'GAP_QUERY') activate(baseline, 'identify gap');
    else if (e.type === 'RETRIEVING' && e.payload?.pass === 2) activate(baseline, 'retrieve 2');
    else if (e.type === 'ANSWERING') activate(baseline, 'answer');
  });

  window.addEventListener('context-baseline-result', () => activate(baseline, 'answer'));

  window.addEventListener('context-compiler-live-event', event => {
    liveCompilerEvents = true;
    const step = compilerStepForEvent(event.detail || {});
    if (step) activate(compiler, step);
  });

  window.addEventListener('context-compiler-result', event => {
    const data = event.detail || {};
    if (liveCompilerEvents) {
      if (Array.isArray(data.plan_candidates) && data.plan_candidates.length) activate(compiler, 'candidate plans');
      activate(compiler, 'release / hold');
      liveCompilerEvents = false;
      return;
    }
    replay(compiler, compilerSequence(data));
  });

  window.addEventListener('context-receipt-issued', () => {
    activate(compiler, 'receipt');
    setTimeout(() => activate(compiler, 'dataset'), 180);
  });
})();
