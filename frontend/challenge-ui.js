(() => {
  const API = window.CONTEXT_COMPILER_API || "http://localhost:4865";
  const resultHost = document.getElementById("challengeResult");
  const question = document.getElementById("question");
  const queryDate = document.getElementById("queryDate");
  const compilerAnswer = document.getElementById("compilerAnswer");
  const compilerBadge = document.getElementById("compilerBadge");

  const esc = (value = "") => String(value).replace(/[&<>'"]/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[c]));

  async function postChallenge(type, button) {
    document.querySelectorAll(".challenge-btn").forEach(btn => btn.disabled = true);
    button.classList.add("active");
    resultHost.classList.add("visible");
    resultHost.innerHTML = `<div class="challenge-loading"><span class="spinner"></span>Injecting bad candidate → verifier → rebuilding evidence…</div>`;

    try {
      const res = await fetch(`${API}/challenge`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          question: question.value.trim(),
          query_date: queryDate.value || null,
          challenge_type: type,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `${res.status} ${res.statusText}`);

      const challenge = data.challenge || {};
      const verification = challenge.verification || {};
      const repaired = data.repaired || {};
      const reasons = verification.missing || [];
      const codes = challenge.reason_codes || [];
      const checks = repaired.verification?.checks || [];
      const passed = checks.filter(c => c.ok).length;
      const challengeDate = challenge.challenge_date || queryDate.value || "query date";

      // Keep the visible demo state aligned with the deterministic challenge run.
      if (challenge.challenge_date) queryDate.value = challenge.challenge_date;

      resultHost.innerHTML = `
        <div class="challenge-stage challenge-stage-bad">
          <div class="challenge-stage-top">
            <span>INJECTED CANDIDATE · ${esc(challengeDate)}</span><strong>✕ BLOCKED</strong>
          </div>
          <div class="challenge-candidate">${esc(challenge.candidate?.answer || "")}</div>
          <div class="challenge-codes">${codes.map(code => `<span>${esc(code)}</span>`).join("")}</div>
          <div class="challenge-reasons">${reasons.slice(0, 3).map(r => `<div>• ${esc(r)}</div>`).join("")}</div>
        </div>
        <div class="challenge-arrow">↓ verifier feedback / agent rebuilds evidence</div>
        <div class="challenge-stage challenge-stage-good">
          <div class="challenge-stage-top">
            <span>CONTEXT COMPILER · ${esc(challengeDate)}</span><strong>✓ ${esc(repaired.status || "RELEASED")}</strong>
          </div>
          <div class="challenge-candidate">${esc(repaired.answer || "")}</div>
          <div class="challenge-release-meta">${passed}/${checks.length} claims verified · ${repaired.steps ?? "?"} agent steps</div>
        </div>`;

      compilerAnswer.innerHTML = `<div class="answer">${esc(repaired.answer || "")}</div>`;
      compilerBadge.textContent = repaired.status || "DONE";
      compilerBadge.className = `badge ${repaired.status === "SUPPORTED" ? "good" : repaired.status === "UNKNOWN" ? "warn" : "bad"}`;

      window.dispatchEvent(new CustomEvent("context-compiler-result", { detail: repaired }));
    } catch (err) {
      resultHost.innerHTML = `<div class="challenge-error">${esc(err.message || err)}</div>`;
    } finally {
      document.querySelectorAll(".challenge-btn").forEach(btn => {
        btn.disabled = false;
        btn.classList.remove("active");
      });
    }
  }

  document.querySelectorAll(".challenge-btn").forEach(button => {
    button.addEventListener("click", () => postChallenge(button.dataset.challenge, button));
  });

  // Fix the temporal-resolution card to compare versions of the same document family,
  // rather than whichever valid temporal check happened to run last.
  window.addEventListener("context-compiler-result", event => {
    const data = event.detail || {};
    const events = data.events || [];
    const versionEvent = events.find(e => e.type === "VERSION_CHECK" && Array.isArray(e.payload?.result));
    if (!versionEvent) return;

    const versionIds = new Set(versionEvent.payload.result.map(item => item.id));
    const rejected = events.find(e => e.type === "TEMPORAL_CHECK" && e.payload?.result?.valid === false && versionIds.has(e.payload?.result?.document));
    const accepted = events.find(e => e.type === "TEMPORAL_CHECK" && e.payload?.result?.valid === true && versionIds.has(e.payload?.result?.document));
    if (!rejected || !accepted) return;

    const card = document.getElementById("decisionCard");
    if (!card) return;
    card.innerHTML = `
      <div class="decision-title">TEMPORAL RESOLUTION</div>
      <div class="decision-flow">
        <span class="decision-reject">× ${esc(rejected.payload.result.document)}</span>
        <span class="decision-reason">${esc(rejected.payload.result.reason || "not valid")}</span>
        <span class="decision-arrow">→</span>
        <span class="decision-accept">✓ ${esc(accepted.payload.result.document)}</span>
        <span class="decision-reason">valid on ${esc(accepted.payload.result.date || "query date")}</span>
      </div>`;
    card.classList.add("visible");
  });
})();
