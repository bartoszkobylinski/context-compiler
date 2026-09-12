const API = window.CONTEXT_COMPILER_API || "http://localhost:8000";

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
const presets = el("presets");

function badge(node, text, kind = "neutral") {
  node.textContent = text;
  node.className = `badge ${kind}`;
}

function loading(node, text) {
  node.innerHTML = `<div class="empty"><span class="spinner"></span>${text}</div>`;
}

function escapeHtml(s = "") {
  return s.replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
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

function renderEvents(events = []) {
  timeline.innerHTML = "";
  events.forEach((event, index) => {
    const item = document.createElement("div");
    item.className = "event";
    item.style.opacity = "0";
    item.style.transform = "translateY(5px)";
    item.innerHTML = `
      <div class="event-type">${escapeHtml(event.type)}</div>
      <div class="event-message">${escapeHtml(event.message)}</div>`;
    timeline.appendChild(item);
    setTimeout(() => {
      item.style.transition = "opacity .18s ease, transform .18s ease";
      item.style.opacity = "1";
      item.style.transform = "translateY(0)";
    }, Math.min(index * 120, 1200));
  });
}

function renderBaseline(data) {
  baselineAnswer.innerHTML = `<div class="answer">${escapeHtml(data.answer || "No answer")}</div>`;
  baselineSources.innerHTML = (data.hits || []).map(hit =>
    `<div class="source-chip">${escapeHtml(hit.title)} · ${escapeHtml(hit.id)} · score ${hit.score ?? "?"}</div>`
  ).join("");
  badge(baselineBadge, "ONE-SHOT", "warn");
}

function renderCompiler(data) {
  compilerAnswer.innerHTML = `<div class="answer">${escapeHtml(data.answer || "No answer")}</div>`;
  const kind = data.status === "SUPPORTED" ? "good" : data.status === "UNKNOWN" ? "warn" : "bad";
  badge(compilerBadge, data.status || "DONE", kind);
  renderEvents(data.events || []);
}

async function runComparison() {
  const payload = {
    question: question.value.trim(),
    query_date: queryDate.value || null,
  };
  if (!payload.question) return;

  runBtn.disabled = true;
  badge(baselineBadge, "RUNNING", "neutral");
  badge(compilerBadge, "RUNNING", "neutral");
  loading(baselineAnswer, "Retrieving top-k once…");
  loading(compilerAnswer, "Building evidence iteratively…");
  baselineSources.innerHTML = "";
  timeline.innerHTML = "";

  const opts = {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  };

  const [baselineResult, compilerResult] = await Promise.allSettled([
    getJson(`${API}/baseline`, opts),
    getJson(`${API}/compiler`, opts),
  ]);

  if (baselineResult.status === "fulfilled") renderBaseline(baselineResult.value);
  else {
    baselineAnswer.innerHTML = `<div class="error">${escapeHtml(baselineResult.reason.message)}</div>`;
    badge(baselineBadge, "ERROR", "bad");
  }

  if (compilerResult.status === "fulfilled") renderCompiler(compilerResult.value);
  else {
    compilerAnswer.innerHTML = `<div class="error">${escapeHtml(compilerResult.reason.message)}</div>`;
    badge(compilerBadge, "ERROR", "bad");
  }

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
question.addEventListener("keydown", e => {
  if (e.key === "Enter") runComparison();
});

init();
