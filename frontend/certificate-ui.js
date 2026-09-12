(() => {
  const API = window.CONTEXT_COMPILER_API || "http://localhost:4865";
  const host = document.getElementById("certificateCard");
  const queryDate = document.getElementById("queryDate");
  if (!host) return;

  let currentCertificate = null;

  const esc = (value = "") => String(value).replace(/[&<>'"]/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[c]));

  async function post(path, body) {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `${res.status} ${res.statusText}`);
    return data;
  }

  function shortHash(hash = "") {
    return hash ? `${hash.slice(0, 12)}…${hash.slice(-8)}` : "—";
  }

  function renderCertificate(cert) {
    currentCertificate = cert;
    host.classList.add("visible");
    host.innerHTML = `
      <div class="cert-head">
        <div>
          <div class="cert-kicker">EVIDENCE RELEASE RECEIPT</div>
          <div class="cert-title">Verified answer, replayable provenance.</div>
        </div>
        <div class="cert-status cert-valid">✓ ISSUED</div>
      </div>
      <div class="cert-grid">
        <div><span>query date</span><strong>${esc(cert.query_date || "not supplied")}</strong></div>
        <div><span>claims</span><strong>${esc(cert.verification?.claims_passed ?? 0)}/${esc(cert.verification?.claims_total ?? 0)}</strong></div>
        <div><span>sources</span><strong>${esc(cert.sources?.length || 0)}</strong></div>
        <div><span>model needed to verify</span><strong>NO</strong></div>
      </div>
      <div class="cert-hash"><span>SHA-256 receipt</span><code>${esc(shortHash(cert.certificate_hash))}</code></div>
      <div class="cert-actions">
        <button id="verifyCertificate" class="cert-btn cert-btn-primary">Verify receipt</button>
        <button id="tamperCertificate" class="cert-btn">Tamper with quote</button>
      </div>
      <div id="certificateVerification" class="cert-verification">Integrity is bound to the answer, claims, source fingerprints and query date.</div>
      <div class="dataset-handoff">
        <div class="dataset-arrow">↓</div>
        <div>
          <div class="dataset-kicker">VERIFIED DECISION DATASET</div>
          <div class="dataset-title">Receipt becomes a high-quality supervision record.</div>
          <div class="dataset-copy">request + evidence requirements + accepted claims + source fingerprints + verifier result + released decision → useful for retrieval tuning, routing and future requirement generation.</div>
        </div>
        <div class="dataset-status">TRAINING-READY</div>
      </div>`;

    document.getElementById("verifyCertificate")?.addEventListener("click", () => verify(cert, false));
    document.getElementById("tamperCertificate")?.addEventListener("click", () => {
      const tampered = JSON.parse(JSON.stringify(cert));
      if (tampered.claims?.[0]?.quote) tampered.claims[0].quote += " [tampered]";
      else tampered.answer += " [tampered]";
      verify(tampered, true);
    });
  }

  async function verify(cert, tampered) {
    const result = document.getElementById("certificateVerification");
    if (result) result.innerHTML = `<span class="spinner"></span> verifying without an LLM…`;
    try {
      const data = await post("/certificate/verify", {certificate: cert});
      if (!result) return;
      result.className = `cert-verification ${data.valid ? "cert-verify-ok" : "cert-verify-bad"}`;
      result.innerHTML = data.valid
        ? `<strong>✓ RECEIPT VALID</strong> — source fingerprints, quotes, temporal validity and payload hash all match. No model call.`
        : `<strong>✕ RECEIPT INVALID</strong> — ${esc((data.issues || []).slice(0, 2).join(" · ") || "integrity check failed")}${tampered ? "" : ""}`;
    } catch (err) {
      if (result) {
        result.className = "cert-verification cert-verify-bad";
        result.textContent = err.message || err;
      }
    }
  }

  async function issue(data) {
    if (data.status !== "SUPPORTED" || !(data.claims || []).length) {
      host.classList.remove("visible");
      host.innerHTML = "";
      currentCertificate = null;
      return;
    }

    const challengeResult = document.getElementById("challengeResult");
    if (challengeResult?.classList.contains("visible")) return;

    host.classList.add("visible");
    host.innerHTML = `<div class="cert-loading"><span class="spinner"></span> sealing verified answer into an evidence receipt…</div>`;
    try {
      const response = await post("/certificate/create", {
        query_date: queryDate?.value || null,
        answer: data.answer || "",
        claims: data.claims || [],
      });
      renderCertificate(response.certificate);
    } catch (err) {
      host.innerHTML = `<div class="cert-error">Receipt not issued: ${esc(err.message || err)}</div>`;
    }
  }

  window.addEventListener("context-run-start", () => {
    currentCertificate = null;
    host.innerHTML = "";
    host.classList.remove("visible");
  });

  window.addEventListener("context-compiler-result", event => issue(event.detail || {}));
})();