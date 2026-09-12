(() => {
  const queryCard = document.querySelector('.query-card');
  const presets = document.getElementById('presets');
  const question = document.getElementById('question');
  const challengeCard = document.querySelector('.challenge-card');
  if (!queryCard || !presets || !question) return;

  const esc = (value = '') => String(value).replace(/[&<>'"]/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  }[c]));

  const host = document.createElement('section');
  host.id = 'shippingOps';
  host.className = 'shipping-ops';
  host.innerHTML = `
    <div class="shipping-ops-head">
      <div>
        <div class="shipping-ops-kicker">OPERATIONAL DECISION MODE</div>
        <div class="shipping-ops-title">Can we actually ship Order #4821?</div>
        <div class="shipping-ops-sub">The agent must turn scattered operational knowledge into a verified action plan.</div>
      </div>
      <div class="shipping-ops-state" id="shippingState">READY</div>
    </div>
    <div class="shipping-grid">
      <div class="shipping-order">
        <div class="shipping-label">PROPOSED ACTION</div>
        <div class="shipping-order-row"><span>Action</span><strong>Ship complete order today</strong></div>
        <div class="shipping-order-row"><span>Destination</span><strong>Tromsø, Norway</strong></div>
        <div class="shipping-order-row"><span>Service</span><strong>PolarExpress Air Next-Day</strong></div>
        <div class="shipping-order-row"><span>Parcel</span><strong>1 parcel</strong></div>
        <div class="shipping-order-row"><span>Contents</span><strong>Perfume 100 ml + PB20 power bank 20,000 mAh</strong></div>
      </div>
      <div class="shipping-path">
        <div class="shipping-label">LIVE DECISION PATH</div>
        <div class="shipping-live"><span class="shipping-dot"></span><span id="shippingNow">Ready to compile this shipment.</span></div>
        <div class="shipping-events" id="shippingEvents"></div>
      </div>
    </div>
    <div class="shipping-result" id="shippingResult">
      <div class="shipping-result-title">DECISION</div>
      <div class="shipping-result-answer" id="shippingResultAnswer"></div>
      <div class="shipping-result-foot" id="shippingResultFoot"></div>
    </div>`;
  queryCard.insertAdjacentElement('afterend', host);

  const stateNode = document.getElementById('shippingState');
  const nowNode = document.getElementById('shippingNow');
  const eventsNode = document.getElementById('shippingEvents');
  const resultNode = document.getElementById('shippingResult');
  const resultAnswer = document.getElementById('shippingResultAnswer');
  const resultFoot = document.getElementById('shippingResultFoot');

  let active = false;
  let steps = [];

  function isShippingQuestion() {
    return /order\s*#?4821|polarexpress|fjord mist|pb20/i.test(question.value || '');
  }

  function setVisible(show) {
    active = show;
    host.classList.toggle('visible', show);
    if (challengeCard) challengeCard.style.display = show ? 'none' : '';
  }

  function resetShipping() {
    if (!active) return;
    stateNode.textContent = 'READY';
    stateNode.className = 'shipping-ops-state';
    nowNode.textContent = 'Order loaded. Ready to compile an executable shipping decision.';
    steps = [];
    renderSteps();
    resultNode.className = 'shipping-result';
    resultAnswer.textContent = '';
    resultFoot.textContent = '';
  }

  function friendly(event) {
    const payload = event.payload || {};
    const input = payload.input || {};
    const result = payload.result || {};
    switch (event.type) {
      case 'EVIDENCE_REQUIREMENTS': {
        const reqs = result.requirements || input.requirements || [];
        return reqs.length ? `Define checks: ${reqs.join(' · ')}` : 'Define what must be proven before shipping';
      }
      case 'SEARCHING': return input.query ? `Search operational knowledge: “${input.query}”` : 'Search operational knowledge';
      case 'DOCUMENT_FOUND': return `Inspect ${result.title || result.id || input.document_id || 'source'}`;
      case 'VERSION_CHECK': return 'Resolve which operational rule/version applies';
      case 'FOLLOWING_REFERENCE': return `Follow dependency ${input.document_id || 'source'} → ${input.reference_id || 'rule'}`;
      case 'TEMPORAL_CHECK': {
        const id = result.document || input.document_id || 'source';
        const verdict = result.valid === true ? 'valid now' : result.valid === false ? 'not valid now' : 'checking validity';
        return `Check ${id}: ${verdict}`;
      }
      case 'OUTDATED_SOURCE': return 'Reject rule that is not valid for this shipment date';
      case 'VERIFYING': return 'Verify every claim in the proposed shipping decision';
      case 'EVIDENCE_GAP': return 'Decision blocked — missing evidence, agent continues';
      case 'SUPPORTED': return 'Evidence sufficient — release verified shipping plan';
      case 'UNKNOWN': return 'Cannot establish a safe shipping plan';
      case 'CONFLICT': return 'Conflicting rules — hold shipment';
      default: return event.message || event.type || 'Working';
    }
  }

  function markFor(event) {
    if (event.type === 'EVIDENCE_GAP' || event.type === 'UNKNOWN' || event.type === 'CONFLICT' || event.type === 'OUTDATED_SOURCE') return '×';
    if (event.type === 'SUPPORTED') return '✓';
    return '→';
  }

  function renderSteps() {
    eventsNode.innerHTML = steps.slice(-8).map(step => `
      <div class="shipping-event"><div class="shipping-event-mark">${esc(step.mark)}</div><div><b>${esc(step.text)}</b></div></div>`
    ).join('');
  }

  presets.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    setTimeout(() => {
      setVisible(isShippingQuestion());
      resetShipping();
    }, 0);
  });

  question.addEventListener('input', () => {
    setVisible(isShippingQuestion());
    if (active) resetShipping();
  });

  window.addEventListener('context-run-start', () => {
    setVisible(isShippingQuestion());
    if (!active) return;
    steps = [{mark:'✓', text:'Load Order #4821 and requested one-parcel Air Next-Day plan'}];
    renderSteps();
    stateNode.textContent = 'COMPILING';
    stateNode.className = 'shipping-ops-state running';
    nowNode.textContent = 'Building the evidence requirements for this shipment…';
    resultNode.className = 'shipping-result';
  });

  window.addEventListener('context-compiler-live-event', event => {
    if (!active) return;
    const e = event.detail || {};
    const text = friendly(e);
    nowNode.textContent = text;
    steps.push({mark: markFor(e), text});
    renderSteps();
    if (e.type === 'EVIDENCE_GAP') {
      stateNode.textContent = 'REPLANNING';
      stateNode.className = 'shipping-ops-state running';
    }
  });

  window.addEventListener('context-compiler-result', event => {
    if (!active) return;
    const data = event.detail || {};
    const supported = data.status === 'SUPPORTED';
    stateNode.textContent = supported ? 'VERIFIED PLAN' : (data.status || 'HELD');
    stateNode.className = `shipping-ops-state ${supported ? 'good' : 'bad'}`;
    nowNode.textContent = supported ? 'Operational decision released with verified evidence.' : 'Shipment held: evidence was not sufficient.';
    resultNode.className = `shipping-result visible ${supported ? 'good' : 'bad'}`;
    resultNode.querySelector('.shipping-result-title').textContent = supported
      ? 'ORIGINAL PLAN CHECKED → VERIFIED SHIPPING DECISION'
      : 'SHIPMENT HELD';
    resultAnswer.textContent = data.answer || 'No verified shipping decision available.';
    const passed = (data.verification?.checks || []).filter(x => x.ok).length;
    const total = (data.verification?.checks || []).length;
    resultFoot.textContent = supported
      ? `${passed}/${total} material claims verified · operational evidence receipt available below`
      : 'No unsafe action is released when the evidence contract fails.';
  });

  // Shipping is now the primary demo, so activate it immediately when the default
  // Order #4821 question is present. This does not depend on /demo-cases being fresh.
  setVisible(isShippingQuestion());
  resetShipping();
})();
