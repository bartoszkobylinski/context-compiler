(() => {
  const originalFetch = window.fetch.bind(window);

  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";

    if (url.includes("/compiler") && response.ok) {
      response.clone().json().then(data => {
        window.dispatchEvent(new CustomEvent("context-compiler-result", { detail: data }));
      }).catch(() => {});
    }

    return response;
  };

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[c]));

  function reasonCode(text = "") {
    const value = text.toLowerCase();
    if (value.includes("not valid at") || value.includes("temporally") || value.includes("effective only")) return "TEMPORAL_INVALID";
    if (value.includes("not verbatim") || value.includes("quote")) return "QUOTE_MISMATCH";
    if (value.includes("not covered by a declared claim")) return "ANSWER_COVERAGE";
    if (value.includes("unknown source")) return "SOURCE_MISSING";
    if (value.includes("no material claims")) return "NO_EVIDENCE";
    return "EVIDENCE_INCOMPLETE";
  }

  function actionText(event) {
    const payload = event.payload || {};
    const input = payload.input || {};
    const result = payload.result || {};

    switch (event.type) {
      case "SEARCHING":
        return input.query ? `Search again: “${input.query}”` : "Search for missing evidence";
      case "DOCUMENT_FOUND":
        return `Inspect ${result.id || input.document_id || "document"}`;
      case "VERSION_CHECK": {
        const ids = Array.isArray(result) ? result.map(item => item.id).filter(Boolean) : [];
        return ids.length ? `Resolve versions: ${ids.join(" → ")}` : "Resolve document versions";
      }
      case "TEMPORAL_CHECK":
        return result.document ? `Check ${result.document} at ${result.date}: ${result.valid ? "VALID" : "NOT VALID"}` : "Check temporal validity";
      case "FOLLOWING_REFERENCE":
        return `Follow reference: ${input.document_id || "source"} → ${input.reference_id || "dependency"}`;
      case "OUTDATED_SOURCE":
        return event.message || "Reject source for wrong point in time";
      default:
        return event.message || event.type;
    }
  }

  function repairStory(events = []) {
    const attempts = [];
    let current = null;

    events.forEach((event, index) => {
      if (event.type === "VERIFYING") {
        current = {
          number: attempts.length + 1,
          verify: event,
          gap: null,
          actions: [],
          released: false,
          index,
        };
        attempts.push(current);
        return;
      }

      if (event.type === "EVIDENCE_GAP" && current && !current.gap) {
        current.gap = event;
        return;
      }

      if (current?.gap && ["SEARCHING", "DOCUMENT_FOUND", "VERSION_CHECK", "TEMPORAL_CHECK", "FOLLOWING_REFERENCE", "OUTDATED_SOURCE"].includes(event.type)) {
        current.actions.push(event);
      }

      if (event.type === "SUPPORTED" && current) current.released = true;
    });

    return attempts;
  }

  function render(data) {
    const host = document.getElementById("repairLoop");
    if (!host) return;

    const attempts = repairStory(data.events || []);
    if (!attempts.length) {
      host.innerHTML = "";
      host.classList.remove("visible");
      return;
    }

    const hadRepair = attempts.some(attempt => attempt.gap);
    const finalReleased = data.status === "SUPPORTED";

    host.innerHTML = `
      <div class="repair-head">
        <div>
          <div class="repair-kicker">AGENT SELF-REPAIR LOOP</div>
          <div class="repair-title">Verifier blocks. Agent repairs. Only verified answers ship.</div>
        </div>
        <div class="repair-summary ${hadRepair ? "repair-summary-active" : ""}">${hadRepair ? `${attempts.filter(a => a.gap).length} draft blocked` : "first draft passed"}</div>
      </div>
      <div class="repair-flow">
        ${attempts.map((attempt, idx) => {
          const missing = attempt.gap?.payload?.missing || [];
          const codes = [...new Set(missing.map(reasonCode))];
          const actions = attempt.actions.slice(0, 4);
          const blocked = Boolean(attempt.gap);
          const released = !blocked && (attempt.released || (idx === attempts.length - 1 && finalReleased));

          return `
            <div class="repair-attempt ${blocked ? "repair-blocked" : released ? "repair-released" : ""}">
              <div class="repair-attempt-top">
                <span class="repair-attempt-label">DRAFT ${attempt.number}</span>
                <span class="repair-state">${blocked ? "✕ BLOCKED" : released ? "✓ RELEASED" : "CHECKED"}</span>
              </div>
              <div class="repair-verify">${escapeHtml(attempt.verify.message || "Verifier checks candidate answer")}</div>
              ${codes.length ? `<div class="repair-codes">${codes.map(code => `<span>${escapeHtml(code)}</span>`).join("")}</div>` : ""}
              ${missing.length ? `<div class="repair-reason">${escapeHtml(missing[0])}</div>` : ""}
              ${blocked ? `
                <div class="repair-agent-label">AGENT CHOOSES NEXT ACTIONS</div>
                <div class="repair-actions">
                  ${actions.length
                    ? actions.map(action => `<div><span>→</span>${escapeHtml(actionText(action))}</div>`).join("")
                    : `<div><span>→</span>Repair evidence or remove unsupported prose</div>`}
                </div>` : ""}
            </div>
            ${idx < attempts.length - 1 ? `<div class="repair-arrow">↻</div>` : ""}`;
        }).join("")}
      </div>
      ${hadRepair && finalReleased ? `<div class="repair-footer"><strong>Closed loop:</strong> external verifier rejected a draft, the agent changed its next actions, and a later draft passed.</div>` : ""}
    `;
    host.classList.add("visible");
  }

  window.addEventListener("context-compiler-result", event => render(event.detail || {}));
})();
