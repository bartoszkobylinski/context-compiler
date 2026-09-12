const API = window.CONTEXT_COMPILER_API || "http://localhost:4865";

const el = (id) => document.getElementById(id);
const question = el("question");
const queryDate = el("queryDate");
const runBtn = el("runBtn");
const baselineAnswer = el("baselineAnswer");
const compilerAnswer = el("compilerAnswer");
const baselineBadge = el("baselineBadge");
const compilerBadge = el("compilerBadge");
const baselineSources = el("baselineSources");
const timeline = el("timeline");
const proof = el("proof");
const presets = el("presets");
const baselineMetrics = el("baselineMetrics");
const compilerMetrics = el("compilerMetrics");
const decisionCard = el("decisionCard");
const verdictStrip = el("verdictStrip");
const verdictMain = el("verdictMain");
const verdictMeta = el("verdictMeta");

function badge(node, text, kind = "neutral") {
  node.textContent = text;
  node.className = `badge ${kind}`;
}

function loading(node, text) {
  node.innerHTML = `<div class="empty"><span class="spinner"></span>${text}</div>`;
}

function escapeHtml(s = "") {
  return String(s).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
}

async function getJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

async function streamCompiler(payload) {
  const res = await fetch(`${API}/compiler-stream`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  if (!res.body) throw new Error("Streaming response body unavailable");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult = null;

  const handleLine = line => {
    if (!line.trim()) return;
    const item = JSON.parse(line);
    if (item.kind === "event" && item.event) {
      window.dispatchEvent(new CustomEvent("context-compiler-live-event", { detail: item.event }));
    } else if (item.kind === "result") {
      finalResult = item.result;
    } else if (item.kind === "error") {
      throw new Error(item.error || "Compiler stream failed");
    }
  };

  while (true) {
    const {value, done} = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) handleLine(line);
    if (done) break;
  }
  if (buffer.trim()) handleLine(buffer);
  if (!finalResult) throw new Error("Compiler stream ended without a final result");
  return finalResult;
}

function fmtTokens(usage = {}) {
  const input = Number(usage.input_tokens || 0);
  const output = Number(usage.output_tokens || 0);
  if (!input && !output) return "";
  const short = n => n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 1 : 2)}k` : String(n);
  return `${short(input)} in · ${short(output)} out`;
}

function answerPolarity(answer = "") {
  const text = answer.trim().toLowerCase();
  if (/^(no\b|no[,. —-]|not allowed|cannot\b)/.test(text)) return "NO";
  if (/^(yes\b|yes[,. —-]|under the security policy.*may\b)/.test(text)) return "YES";
  if (text.includes("does not contain") || text.includes("cannot be answered") || text.startsWith("unknown")) return "UNKNOWN";
  return "";
}

function friendlyEvent(event) {
  const type = event.type || "EVENT";
  const payload = event.payload || {};
  const input = payload.input || {};
  const result = payload.result || {};

  if (type === "EVIDENCE_REQUIREMENTS") {
    const reqs = result.requirements || input.requirements || [];
    return reqs.length ? `Need to establish: ${reqs.join(" · ")}` : event.message;
  }
  if (type === "SEARCHING") return input.query ? `Search: “${input.query}”` : event.message;
  if (type === "DOCUMENT_FOUND") return result.id ? `Opened ${result.title || result.id} · ${result.id}` : event.message;
  if (type === "VERSION_CHECK") {
    const versions = Array.isArray(result) ? result.map(v => v.id).filter(Boolean) : [];
    return versions.length ? `Found versions: ${versions.join(" → ")}` : event.message;
  }
  if (type === "TEMPORAL_CHECK") {
    if (result.document) {
      const verdict = result.valid ? "VALID" : "NOT VALID";
      return `${result.document} @ ${result.date}: ${verdict} · ${result.reason || ""}`;
    }
    return event.message;
  }
  if (type === "OUTDATED_SOURCE") return `Rejected as temporally invalid · ${payload.reason || event.message || "wrong point in time"}`;
  if (type === "FOLLOWING_REFERENCE") {
    return input.reference_id ? `Followed reference: ${input.document_id} → ${input.reference_id}` : event.message;
  }
  if (type === "VERIFYING") return event.message || "Checking every material claim against source evidence";
  if (type === "EVIDENCE_GAP") return event.message || "Evidence failed verification — continue retrieval";
  if (type === "SUPPORTED") return event.message || "All material claims verified";
  if (type === "UNKNOWN") return event.message || "Evidence boundary reached — abstaining";
  return event.message || type;
}

function isKeyEvent(event) {
  return ["EVIDENCE_REQUIREMENTS", "VERSION_CHECK", "TEMPORAL_CHECK", "OUTDATED_SOURCE", "FOLLOWING_REFERENCE", "VERIFYING", "EVIDENCE_GAP", "SUPPORTED", "UNKNOWN", "CONFLICT"].includes(event.type);
}

function renderEvents(events = []) {
  timeline.innerHTML = "";
  const keyEvents = events.filter(isKeyEvent);
  const shown = keyEvents.length ? keyEvents : events;
  shown.forEach((event, index) => {
    const item = document.createElement("div");
    item.className = `event event-${String(event.type || "").toLowerCase()}`;
    item.style.opacity = "0";
    item.style.transform = "translateY(5px)";
    item.innerHTML = `
      <div class="event-type">${escapeHtml(event.type)}</div>
      <div class="event-message">${escapeHtml(friendlyEvent(event))}</div>`;
    timeline.appendChild(item);
    setTimeout(() => {
      item.style.transition = "opacity .18s ease, transform .18s ease";
      item.style.opacity = "1";
      item.style.transform = "translateY(0)";
    }, Math.min(index * 95, 850));
  });
}

function renderDecision(data) {
  const events = data.events || [];
  const rejected = events.find(e => e.type === "OUTDATED_SOURCE");
  const validChecks = events.filter(e => e.type === "TEMPORAL_CHECK" && e.payload?.result?.valid);
  const accepted = validChecks[validChecks.length - 1]?.payload?.result;

  if (rejected && accepted) {
    const rejectedId = events.find(e => e.type === "TEMPORAL_CHECK" && e.payload?.result?.valid === false)?.payload?.result?.document || "future version";
    decisionCard.innerHTML = `
      <div class="decision-title">TEMPORAL RESOLUTION</div>
      <div class="decision-flow">
        <span class="decision-reject">× ${escapeHtml(rejectedId)}</span>
        <span class="decision-reason">not valid yet</span>
        <span class="decision-arrow">→</span>
        <span class="decision-accept">✓ ${escapeHtml(accepted.document)}</span>
        <span class="decision-reason">valid on ${escapeHtml(accepted.date)}</span>
      </div>`;
    decisionCard.classList.add("visible");
    return;
  }

  if (data.status === "UNKNOWN") {
    decisionCard.innerHTML = `
      <div class="decision-title">KNOWLEDGE BOUNDARY</div>
      <div class="decision-flow"><span class="decision-reject">UNKNOWN</span><span class="decision-reason">no approved evidence → no claim released</span></div>`;
    decisionCard.classList.add("visible");
    return;
  }

  decisionCard.innerHTML = "";
  decisionCard.classList.remove("visible");
}

function renderProof(data) {
  const checks = data?.verification?.checks || [];
  if (!checks.length) {
    proof.innerHTML = data.status === "UNKNOWN"
      ? `<div class="proof-head"><span>DETERMINISTIC VERIFIER</span><strong>0 unsupported claims released</strong></div>`
      : "";
    return;
  }

  const passed = checks.filter(c => c.ok).length;
  proof.innerHTML = `
    <div class="proof-head">
      <span>DETERMINISTIC VERIFIER</span>
      <strong>${passed}/${checks.length} claims passed</strong>
    </div>
    <div class="proof-list">
      ${checks.map(c => `
        <div class="proof-item ${c.ok ? "proof-ok" : "proof-fail"}">
          <div class="proof-mark">${c.ok ? "✓" : "×"}</div>
          <div>
            <div class="proof-claim">${escapeHtml(c.claim || "Claim")}</div>
            <div class="proof-source">${escapeHtml(c.source_id || "no source")} ${c.valid_at_query_time === true ? "· valid at query time" : c.valid_at_query_time === false ? "· NOT valid at query time" : ""}</div>
            ${c.quote ? `<div class="proof-quote">“${escapeHtml(c.quote)}”</div>` : ""}
            ${(c.errors || []).length ? `<div class="proof-errors">${(c.errors || []).map(escapeHtml).join(" · ")}</div>` : ""}
          </div>
        </div>`).join("")}
    </div>`;
}

function renderBaseline(data) {
  baselineAnswer.innerHTML = `<div class="answer">${escapeHtml(data.answer || "No answer")}</div>`;
  baselineSources.innerHTML = (data.hits || []).map((hit, i) =>
    `<div class="source-chip"><strong>#${i + 1}</strong> ${escapeHtml(hit.title)} · ${escapeHtml(hit.id)} · ${hit.score ?? "?"}</div>`
  ).join("");
  baselineMetrics.innerHTML = `<span>top-${(data.hits || []).length} once</span>${fmtTokens(data.usage) ? `<span>${escapeHtml(fmtTokens(data.usage))}</span>` : ""}`;
  badge(baselineBadge, "ONE-SHOT", "warn");
  window.dispatchEvent(new CustomEvent("context-baseline-result", { detail: data }));
}

function renderCompiler(data) {
  compilerAnswer.innerHTML = `<div class="answer">${escapeHtml(data.answer || "No answer")}</div>`;
  const kind = data.status === "SUPPORTED" ? "good" : data.status === "UNKNOWN" ? "warn" : "bad";
  badge(compilerBadge, data.status || "DONE", kind);
  compilerMetrics.innerHTML = `<span>${data.steps ?? "?"} agent steps</span>${fmtTokens(data.usage) ? `<span>${escapeHtml(fmtTokens(data.usage))}</span>` : ""}`;
  renderDecision(data);
  renderEvents(data.events || []);
  renderProof(data);
  window.dispatchEvent(new CustomEvent("context-compiler-result", { detail: data }));
}

function renderVerdict(baseline, compiler) {
  const bp = answerPolarity(baseline?.answer || "");
  const cp = answerPolarity(compiler?.answer || "");
  verdictStrip.className = "verdict-strip";

  const outdated = (compiler?.events || []).some(e => e.type === "OUTDATED_SOURCE");
  if (outdated && bp && cp && bp !== cp) {
    verdictStrip.classList.add("verdict-alert");
    verdictMain.innerHTML = `<strong>Same corpus. Different evidence process. Opposite answer.</strong> One-shot says ${escapeHtml(bp)}; verified evidence says ${escapeHtml(cp)}.`;
    verdictMeta.textContent = "The top-ranked policy is real — but not yet effective on the query date.";
    return;
  }
  if (compiler?.status === "UNKNOWN") {
    verdictStrip.classList.add("verdict-boundary");
    verdictMain.innerHTML = `<strong>Abstention is a successful result.</strong> The corpus cannot establish the answer.`;
    verdictMeta.textContent = "No unsupported claim leaves the verifier.";
    return;
  }
  verdictMain.innerHTML = `<strong>Evidence compiled and verified.</strong> ${compiler?.verification?.checks?.filter(c => c.ok).length || 0}/${compiler?.verification?.checks?.length || 0} material claims passed.`;
  verdictMeta.textContent = outdated ? "A temporally invalid source was rejected before answering." : "Answer released only after evidence checks passed.";
}

async function runComparison() {
  const payload = { question: question.value.trim(), query_date: queryDate.value || null };
  if (!payload.question) return;

  window.dispatchEvent(new CustomEvent("context-run-start"));
  runBtn.disabled = true;
  badge(baselineBadge, "RUNNING", "neutral");
  badge(compilerBadge, "RUNNING", "neutral");
  loading(baselineAnswer, "Retrieving top-k once…");
  loading(compilerAnswer, "Compiling evidence live…");
  baselineSources.innerHTML = "";
  baselineMetrics.innerHTML = "";
  compilerMetrics.innerHTML = "";
  decisionCard.innerHTML = "";
  decisionCard.classList.remove("visible");
  timeline.innerHTML = "";
  proof.innerHTML = "";
  verdictMain.textContent = "Running both paths against the same corpus…";
  verdictMeta.textContent = "";
  verdictStrip.className = "verdict-strip";

  const opts = { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) };
  const [baselineResult, compilerResult] = await Promise.allSettled([
    getJson(`${API}/baseline`, opts),
    streamCompiler(payload),
  ]);

  let baselineData = null;
  let compilerData = null;

  if (baselineResult.status === "fulfilled") {
    baselineData = baselineResult.value;
    renderBaseline(baselineData);
  } else {
    baselineAnswer.innerHTML = `<div class="error">${escapeHtml(baselineResult.reason.message)}</div>`;
    badge(baselineBadge, "ERROR", "bad");
  }

  if (compilerResult.status === "fulfilled") {
    compilerData = compilerResult.value;
    renderCompiler(compilerData);
  } else {
    compilerAnswer.innerHTML = `<div class="error">${escapeHtml(compilerResult.reason.message)}</div>`;
    badge(compilerBadge, "ERROR", "bad");
  }

  if (baselineData && compilerData) renderVerdict(baselineData, compilerData);
  runBtn.disabled = false;
}

async function init() {
  try {
    const health = await getJson(`${API}/health`);
    el("health").textContent = health.anthropic_key
      ? `${health.documents} docs · ${health.model} · API ready`
      : `${health.documents} docs · Anthropic key missing`;
  } catch (err) {
    el("health").textContent = "API offline";
  }

  try {
    const cases = await getJson(`${API}/demo-cases`);
    cases.forEach(c => {
      const b = document.createElement("button");
      b.className = "preset";
      b.textContent = c.label;
      b.title = c.expected;
      b.addEventListener("click", () => {
        question.value = c.question;
        queryDate.value = c.query_date;
      });
      presets.appendChild(b);
    });
  } catch (_) {}
}

runBtn.addEventListener("click", runComparison);
question.addEventListener("keydown", e => { if (e.key === "Enter") runComparison(); });

init();
