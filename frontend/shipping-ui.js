(() => {
  const queryCard = document.querySelector('.query-card');
  const presets = document.getElementById('presets');
  const question = document.getElementById('question');
  const challengeCard = document.querySelector('.challenge-card');
  if (!queryCard || !presets || !question) return;

  const esc = (value = '') => String(value).replace(/[&<>'"]/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  }[c]));

  const CASES = {
    '4821': {
      title: 'Can we actually ship Order #4821?',
      action: 'Ship complete order today', destination: 'Tromsø, Norway', service: 'PolarExpress Air Next-Day',
      constraint: '1 parcel', contents: 'Perfume 100 ml + PB20 power bank 20,000 mAh',
      start: 'Load Order #4821 · mixed restricted goods · one-parcel express request'
    },
    '5902': {
      title: 'Can cold-chain Order #5902 ship safely?',
      action: 'Meet next-business-day promise', destination: 'Tromsø, Norway', service: 'PolarExpress Air Next-Day',
      constraint: 'Continuous 2–8°C', contents: 'ArcticBio BIO-28 research kit',
      start: 'Load Order #5902 · cold-chain requirement · packaging inventory · weather constraints'
    },
    '6107': {
      title: 'Can live-animal Order #6107 leave today?',
      action: 'Dispatch live gecko today', destination: 'Tromsø, Norway', service: 'Requested express service',
      constraint: 'Live animal · weekend', contents: 'Ornamental gecko',
      start: 'Load Order #6107 · live animal · species limits · weekend and weather acceptance'
    },
    '7710': {
      title: 'Can fragile Order #7710 use the cheapest service?',
      action: 'Ship cheapest, no signature', destination: 'Bergen, Norway', service: 'Standard Economy',
      constraint: 'Declared value NOK 8,900', contents: 'Hand-blown glass vase',
      start: 'Load Order #7710 · fragile glass · insurance threshold · customer preference'
    },
    '8820': {
      title: 'Can high-value Order #8820 meet the requested delivery?',
      action: 'Leave at door before 10:00 Sunday', destination: 'Senja rural address', service: 'PolarExpress Air Next-Day',
      constraint: 'Declared value NOK 24,900', contents: 'ProCam X camera body',
      start: 'Load Order #8820 · high value · remote address · Sunday last-mile request'
    }
  };

  const host = document.createElement('section');
  host.id = 'shippingOps';
  host.className = 'shipping-ops';
  host.innerHTML = `
    <div class="shipping-ops-head">
      <div>
        <div class="shipping-ops-kicker">OPERATIONAL DECISION MODE</div>
        <div class="shipping-ops-title" id="shippingTitle"></div>
        <div class="shipping-ops-sub">The agent must reconcile scattered, sometimes conflicting operational constraints before releasing an action.</div>
      </div>
      <div class="shipping-ops-state" id="shippingState">READY</div>
    </div>
    <div class="shipping-grid">
      <div class="shipping-order">
        <div class="shipping-label">PROPOSED ACTION</div>
        <div class="shipping-order-row"><span>Action</span><strong id="shippingAction"></strong></div>
        <div class="shipping-order-row"><span>Destination</span><strong id="shippingDestination"></strong></div>
        <div class="shipping-order-row"><span>Service</span><strong id="shippingService"></strong></div>
        <div class="shipping-order-row"><span>Conflict surface</span><strong id="shippingConstraint"></strong></div>
        <div class="shipping-order-row"><span>Contents</span><strong id="shippingContents"></strong></div>
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

  const titleNode = document.getElementById('shippingTitle');
  const actionNode = document.getElementById('shippingAction');
  const destinationNode = document.getElementById('shippingDestination');
  const serviceNode = document.getElementById('shippingService');
  const constraintNode = document.getElementById('shippingConstraint');
  const contentsNode = document.getElementById('shippingContents');
  const stateNode = document.getElementById('shippingState');
  const nowNode = document.getElementById('shippingNow');
  const eventsNode = document.getElementById('shippingEvents');
  const resultNode = document.getElementById('shippingResult');
  const resultAnswer = document.getElementById('shippingResultAnswer');
  const resultFoot = document.getElementById('shippingResultFoot');

  let active = false;
  let steps = [];

  function currentCase() {
    const m = (question.value || '').match(/order\s*#?(4821|5902|6107|7710|8820)/i);
    return m ? { id: m[1], ...CASES[m[1]] } : null;
  }

  function syncCaseCard() {
    const c = currentCase();
    if (!c) return;
    titleNode.textContent = c.title;
    actionNode.textContent = c.action;
    destinationNode.textContent = c.destination;
    serviceNode.textContent = c.service;
    constraintNode.textContent = c.constraint;
    contentsNode.textContent = c.contents;
  }

  function setVisible(show) {
    active = show;
    host.classList.toggle('visible', show);
    if (challengeCard) challengeCard.style.display = show ? 'none' : '';
    if (show) syncCaseCard();
  }

  function resetShipping() {
    if (!active) return;
    syncCaseCard();
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
      case 'OUTDATED_SOURCE': return 'Reject rule that is not valid for this decision date';
      case 'VERIFYING': return 'Verify every material claim in the proposed operational plan';
      case 'EVIDENCE_GAP': return 'Decision blocked — missing evidence, agent continues';
      case 'SUPPORTED': return 'Evidence sufficient — release verified operational plan';
      case 'UNKNOWN': return 'Cannot establish a safe operational plan';
      case 'CONFLICT': return 'Conflicting evidence — hold action';
      default: return event.message || event.type || 'Working';
    }
  }

  function markFor(event) {
    if (event.type === 'EVIDENCE_GAP' || event.type === 'UNKNOWN' || event.type === 'CONFLICT' || event.type === 'OUTDATED_SOURCE') return '×';
    if (event.type === 'SUPPORTED') return '✓';
    return '→';
  }

  function renderSteps() {
    eventsNode.innerHTML = steps.slice(-9).map(step => `
      <div class="shipping-event"><div class="shipping-event-mark">${esc(step.mark)}</div><div><b>${esc(step.text)}</b></div></div>`
    ).join('');
  }

  presets.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    setTimeout(() => {
      setVisible(Boolean(currentCase()));
      resetShipping();
    }, 0);
  });

  question.addEventListener('input', () => {
    setVisible(Boolean(currentCase()));
    if (active) resetShipping();
  });

  window.addEventListener('context-run-start', () => {
    const c = currentCase();
    setVisible(Boolean(c));
    if (!active || !c) return;
    steps = [{mark:'✓', text:c.start}];
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
      ? 'REQUEST CHECKED → VERIFIED OPERATIONAL DECISION'
      : 'ACTION HELD';
    resultAnswer.textContent = data.answer || 'No verified operational decision available.';
    const passed = (data.verification?.checks || []).filter(x => x.ok).length;
    const total = (data.verification?.checks || []).length;
    resultFoot.textContent = supported
      ? `${passed}/${total} material claims verified · evidence release receipt available below`
      : 'No action is released when the evidence contract fails.';
  });

  setVisible(Boolean(currentCase()));
  resetShipping();
})();
