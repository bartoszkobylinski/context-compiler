# Real Anthropic API evaluation

Evidence-collection run against the live API. No corpus, prompt, or implementation changes were made for this run.

- Model: `claude-sonnet-5`
- Cases: 4
- Generated: 2026-09-12T10:47:54+00:00
- Raw results: [`latest-results.json`](latest-results.json), saved exactly as the runner produced them

**Baseline 3/4 · Context Compiler 3/4**

| case | expected | baseline | compiler | baseline correct? | compiler correct? |
|---|---|---|---|---|---|
| `personal_device_june` | YES_WITH_CONTROLS | No. Per the Security Policy (security-policy-2025), customer data may… | SUPPORTED | no | yes |
| `personal_device_august` | NO_MANAGED_DEVICE_REQUIRED | No. Per the Security Policy (security-policy-2025), customer data may… | SUPPORTED | yes | yes |
| `spouse_breakfast` | UNKNOWN | UNKNOWN — the retrieved chunks contain no information about meal or s… | UNKNOWN | yes | no |
| `external_ai_customer_data` | NO_UNLESS_APPROVED | No — customer data is classified as Confidential (data-classification… | SUPPORTED | yes | yes |

## Findings

- `personal_device_june` — baseline **failed** as the design predicts. Its top-k was `security-policy-2025`, `remote-access-quickstart`, `data-classification-policy`, so the one-shot path answered from the wrong policy version.
- `personal_device_august` — baseline **passed**. Its top-k already contained the governing document, so retrieval alone was sufficient and this case does not separate the two systems.
- `spouse_breakfast` — baseline **passed**. Recorded as-is: the one-shot path abstained correctly here, so this case does not separate the two systems.
- `spouse_breakfast` — compiler scored **FAIL**, but the failure is in the grader, not the behaviour. Status was `UNKNOWN`, which equals the expected `UNKNOWN`, and 0 claims were released — the correct abstention. `_answer_matches` is a literal substring test requiring `unknown` in the prose, and the compiler phrased its abstention without that token. Recorded, not fixed: changing `cases.json` would be tuning, which this run excludes.
- `external_ai_customer_data` — baseline **passed**. Its top-k already contained the governing document, so retrieval alone was sufficient and this case does not separate the two systems.

## Token usage

Baseline calls, summed across all cases: **1588 input / 496 output tokens**.

Compiler usage is **not recorded**. `run_compiler` in `backend/agent.py` does not return a usage field, so per-step token counts were never captured by this run. No estimate is given here — the number would be invented. Adding usage accounting would be an implementation change, which this evidence run deliberately avoided.

---

## `personal_device_june`

- **Question:** Can a contractor access customer data from a personal laptop using VPN?
- **Query date:** 2025-06-10
- **Expected:** YES_WITH_CONTROLS

### Baseline — FAIL

> No. Per the Security Policy (security-policy-2025), customer data may only be accessed from company-managed devices—a VPN connection is mandatory for remote access but does not make a personal device eligible for customer-data access. The Remote Access Quickstart (remote-access-quickstart) confirms this by noting that its guidance on using personal laptops via VPN is operational only and does not override the Security Policy's restrictions on accessing restricted or customer data.

- Top-k retrieved: `security-policy-2025`, `remote-access-quickstart`, `data-classification-policy`
- Tokens: 420 input / 147 output

### Context Compiler — PASS

- **Status:** `SUPPORTED`
- **Steps:** 8

> Yes, as of 2025-06-10 a contractor may access customer (restricted client) data from a personal laptop, but only under strict conditions: the connection must use the corporate VPN tunnel and the device must have whole-disk encryption enabled. This is governed by the Security Policy version in force on that date (effective 2024-02-01 through 2025-06-30), which explicitly allows BYOD access to restricted client records under these conditions. VPN alone is mandatory for any remote connection but is not sufficient by itself to grant access to restricted data — the additional encryption requirement must also be met. Note that a stricter Security Policy takes effect on 2025-07-01 that would eliminate this personal-device allowance, but since it is not yet in effect on the query date, it does not govern this situation.

- **Cited sources:** `contractor-handbook`, `security-policy-2024`, `vpn-policy`
- **Verification:** 3/3 claims verified, complete=True

<details><summary>Tool / event sequence</summary>

| # | event | tool | detail |
|---|---|---|---|
| 1 | `EVIDENCE_REQUIREMENTS` | `declare_requirements` | Need to establish: Policy defining rules for contractor access to customer data • Policy on use of personal devices (BYOD) for accessing corporate/customer dat… |
| 2 | `SEARCHING` | `semantic_search` | Search: contractor access customer data personal laptop VPN |
| 3 | `SEARCHING` | `semantic_search` | Search: personal device policy BYOD access company data |
| 4 | `DOCUMENT_FOUND` | `open_document` | Opened Security Policy |
| 5 | `DOCUMENT_FOUND` | `open_document` | Opened Contractor Handbook |
| 6 | `DOCUMENT_FOUND` | `open_document` | Opened VPN Policy |
| 7 | `VERSION_CHECK` | `get_versions` | Versions found: security-policy-2024 → security-policy-2025 |
| 8 | `TEMPORAL_CHECK` | `valid_at` | security-policy-2025 @ 2025-06-10: NOT VALID · effective only from 2025-07-01 |
| 9 | `OUTDATED_SOURCE` | `—` | Rejected security-policy-2025 for this point in time |
| 10 | `TEMPORAL_CHECK` | `valid_at` | security-policy-2024 @ 2025-06-10: VALID · document is valid at query time |
| 11 | `VERIFYING` | `—` | Deterministically verifying 5 material claims |
| 12 | `EVIDENCE_GAP` | `—` | Verifier rejected the proposed final answer |
| 13 | `TEMPORAL_CHECK` | `valid_at` | contractor-handbook @ 2025-06-10: VALID · document is valid at query time |
| 14 | `TEMPORAL_CHECK` | `valid_at` | vpn-policy @ 2025-06-10: VALID · document is valid at query time |
| 15 | `VERIFYING` | `—` | Deterministically verifying 3 material claims |
| 16 | `SUPPORTED` | `—` | 3/3 material claims passed deterministic verification |

</details>

## `personal_device_august`

- **Question:** Can a contractor access customer data from a personal laptop using VPN?
- **Query date:** 2025-08-10
- **Expected:** NO_MANAGED_DEVICE_REQUIRED

### Baseline — PASS

> No. Per the Security Policy (security-policy-2025), customer data may only be accessed from company-managed devices — a VPN connection is mandatory for remote access but does not make a personal device eligible for customer-data access. The Remote Access Quickstart (remote-access-quickstart) confirms that while contractors may use a personal laptop with VPN for general remote access, access to customer data remains subject to the Security Policy, which excludes personal devices.

- Top-k retrieved: `security-policy-2025`, `remote-access-quickstart`, `data-classification-policy`
- Tokens: 420 input / 145 output

### Context Compiler — PASS

- **Status:** `SUPPORTED`
- **Steps:** 8

> No. As of 2025-08-10, the current Security Policy requires that customer data only be accessed from company-managed devices. Using a VPN does not change this — VPN connectivity is mandatory for remote access but does not make a personal (contractor-owned) laptop eligible to access customer data. The Contractor Handbook confirms that contractors must comply with the security requirements defined in the current Security Policy.

- **Cited sources:** `contractor-handbook`, `security-policy-2025`, `vpn-policy`
- **Verification:** 4/4 claims verified, complete=True

<details><summary>Tool / event sequence</summary>

| # | event | tool | detail |
|---|---|---|---|
| 1 | `EVIDENCE_REQUIREMENTS` | `declare_requirements` | Need to establish: Policy defining rules for contractor access to customer data • Policy on use of personal devices (BYOD) for accessing company/customer data … |
| 2 | `SEARCHING` | `semantic_search` | Search: contractor access customer data personal laptop VPN |
| 3 | `SEARCHING` | `semantic_search` | Search: BYOD personal device policy remote access |
| 4 | `DOCUMENT_FOUND` | `open_document` | Opened VPN Policy |
| 5 | `DOCUMENT_FOUND` | `open_document` | Opened Security Policy |
| 6 | `TEMPORAL_CHECK` | `valid_at` | security-policy-2025 @ 2025-08-10: VALID · document is valid at query time |
| 7 | `FOLLOWING_REFERENCE` | `follow_reference` | Following reference: security-policy-2025 → contractor-handbook |
| 8 | `VERSION_CHECK` | `get_versions` | Versions found: security-policy-2024 → security-policy-2025 |
| 9 | `VERIFYING` | `—` | Deterministically verifying 5 material claims |
| 10 | `EVIDENCE_GAP` | `—` | Verifier rejected the proposed final answer |
| 11 | `TEMPORAL_CHECK` | `valid_at` | security-policy-2024 @ 2025-08-10: NOT VALID · expired after 2025-06-30 |
| 12 | `OUTDATED_SOURCE` | `—` | Rejected security-policy-2024 for this point in time |
| 13 | `VERIFYING` | `—` | Deterministically verifying 4 material claims |
| 14 | `SUPPORTED` | `—` | 4/4 material claims passed deterministic verification |

</details>

## `spouse_breakfast`

- **Question:** Can a contractor expense their spouse's breakfast?
- **Query date:** 2025-08-10
- **Expected:** UNKNOWN

### Baseline — PASS

> UNKNOWN — the retrieved chunks contain no information about meal or spouse expense policies.

- Top-k retrieved: `contractor-handbook`, `security-policy-2025`, `security-policy-2024`
- Tokens: 429 input / 34 output

### Context Compiler — FAIL

- **Status:** `UNKNOWN`
- **Steps:** 5

> The available corpus does not contain any policy addressing contractor expense reimbursement, meal expenses, or spousal/family expenses, so this question cannot be answered from the approved documents.

- **Cited sources:** none — no claims released
- **Verification:** no claims released, complete=True
- **Unresolved:** No document in the corpus defines contractor expense/reimbursement rules (e.g., an Expense Policy or T&E Policy) covering meals.; No document addresses whether spouse/family member expenses can be claimed by contractors.; The Contractor Handbook only covers remote access and security requirements, not expenses.; The Conference Travel Guide covers only hotel booking for employees and explicitly states it does not define approval thresholds; it does not mention contractors, meals, or spouses.
- **Failure mode:** answer shape did not match expected outcome

<details><summary>Tool / event sequence</summary>

| # | event | tool | detail |
|---|---|---|---|
| 1 | `EVIDENCE_REQUIREMENTS` | `declare_requirements` | Need to establish: Definition of eligible expenses for contractors (as opposed to employees) • Whether meal expenses are reimbursable for contractors • Whether… |
| 2 | `SEARCHING` | `semantic_search` | Search: contractor expense policy meals reimbursement |
| 3 | `SEARCHING` | `semantic_search` | Search: spouse or family member expenses not reimbursable |
| 4 | `DOCUMENT_FOUND` | `open_document` | Opened Contractor Handbook |
| 5 | `DOCUMENT_FOUND` | `open_document` | Opened Conference Travel Guide |
| 6 | `SEARCHING` | `keyword_search` | Search: expense reimbursement policy |
| 7 | `SEARCHING` | `keyword_search` | Search: spouse expense |
| 8 | `SEARCHING` | `semantic_search` | Search: travel and expense policy meals per diem |
| 9 | `VERIFYING` | `—` | Deterministically verifying 0 material claims |
| 10 | `UNKNOWN` | `—` | Approved corpus does not establish the answer |

</details>

## `external_ai_customer_data`

- **Question:** Can an employee paste customer data into an external AI assistant?
- **Query date:** 2025-08-10
- **Expected:** NO_UNLESS_APPROVED

### Baseline — PASS

> No — customer data is classified as Confidential (data-classification-policy), and Confidential data must not be sent to external AI providers unless that provider has been explicitly approved for handling Confidential data (ai-security-addendum). The AI Usage Guidelines permit external AI tools only for ordinary productivity tasks in compliance with the Data Classification Policy (ai-usage-guidelines), so pasting customer data into an external AI assistant is not allowed unless that specific tool has been explicitly approved for Confidential data.

- Top-k retrieved: `ai-security-addendum`, `data-classification-policy`, `ai-usage-guidelines`
- Tokens: 319 input / 170 output

### Context Compiler — PASS

- **Status:** `SUPPORTED`
- **Steps:** 5

> No. Customer data is classified as Confidential, and company policy prohibits sending Confidential data to external AI providers unless that specific provider has been explicitly approved for Confidential data. Since general-purpose external AI assistants are typically not on that approved list, an employee should not paste customer data into an external AI assistant unless it has been explicitly approved to handle Confidential data.

- **Cited sources:** `ai-security-addendum`, `ai-usage-guidelines`, `data-classification-policy`
- **Verification:** 3/3 claims verified, complete=True

<details><summary>Tool / event sequence</summary>

| # | event | tool | detail |
|---|---|---|---|
| 1 | `EVIDENCE_REQUIREMENTS` | `declare_requirements` | Need to establish: Existence of a policy governing use of external AI assistants/tools by employees • Whether the policy explicitly addresses pasting/entering … |
| 2 | `SEARCHING` | `semantic_search` | Search: employee use of external AI assistants customer data |
| 3 | `SEARCHING` | `keyword_search` | Search: AI assistant customer data policy |
| 4 | `VERSION_CHECK` | `get_versions` | Versions found: ai-usage-guidelines |
| 5 | `VERSION_CHECK` | `get_versions` | Versions found: ai-security-addendum |
| 6 | `VERSION_CHECK` | `get_versions` | Versions found: data-classification-policy |
| 7 | `TEMPORAL_CHECK` | `valid_at` | ai-usage-guidelines @ 2025-08-10: VALID · document is valid at query time |
| 8 | `TEMPORAL_CHECK` | `valid_at` | ai-security-addendum @ 2025-08-10: VALID · document is valid at query time |
| 9 | `TEMPORAL_CHECK` | `valid_at` | data-classification-policy @ 2025-08-10: VALID · document is valid at query time |
| 10 | `VERIFYING` | `—` | Deterministically verifying 3 material claims |
| 11 | `SUPPORTED` | `—` | 3/3 material claims passed deterministic verification |

</details>

