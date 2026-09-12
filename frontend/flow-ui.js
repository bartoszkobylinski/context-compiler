(() => {
  const baseline = document.querySelector('.baseline-panel .flow-mini');
  const compiler = document.querySelector('.compiler-panel .flow-mini');
  const runBtn = document.getElementById('runBtn');
  if (!baseline || !compiler || !runBtn) return;

  const baselineSteps = ['question','top-k chunks','answer'];
  const compilerSteps = ['requirements','search','inspect','temporal check','verify','repair','answer','unknown'];

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
    host.querySelectorAll('.flow-step.active').forEach(node => { node.classList.remove('active'); node.classList.add('done'); });
    target.classList.remove('done');
    target.classList.add('active');
  }

  function replay(host, sequence, delay = 280) {
    reset(host);
    host.classList.remove('idle');
    host.classList.add('replaying');
    sequence.forEach((step, i) => setTimeout(() => activate(host, step), i * delay));
  }

  function compilerSequence(data) {
    const seq = [];
    const push = step => { if (step && seq[seq.length - 1] !== step) seq.push(step); };
    for (const event of data.events || []) {
      if (event.type === 'EVIDENCE_REQUIREMENTS') push('requirements');
      else if (event.type === 'SEARCHING') push('search');
      else if (['DOCUMENT_FOUND','FOLLOWING_REFERENCE','VERSION_CHECK'].includes(event.type)) push('inspect');
      else if (['TEMPORAL_CHECK','OUTDATED_SOURCE'].includes(event.type)) push('temporal check');
      else if (event.type === 'VERIFYING') push('verify');
      else if (event.type === 'EVIDENCE_GAP') push('repair');
      else if (event.type === 'UNKNOWN') push('unknown');
      else if (['SUPPORTED','CONFLICT'].includes(event.type)) push('answer');
    }
    if (!seq.length) return data.status === 'UNKNOWN' ? ['requirements','unknown'] : ['requirements','answer'];
    if (data.status === 'SUPPORTED' && seq[seq.length - 1] !== 'answer') push('answer');
    if (data.status === 'UNKNOWN' && seq[seq.length - 1] !== 'unknown') push('unknown');
    return seq;
  }

  build(baseline, baselineSteps, 'baseline');
  build(compiler, compilerSteps, 'compiler');

  runBtn.addEventListener('click', () => {
    replay(baseline, baselineSteps, 340);
    reset(compiler);
    activate(compiler, 'requirements');
  }, true);

  window.addEventListener('context-compiler-result', event => {
    replay(compiler, compilerSequence(event.detail || {}), 260);
  });
})();
