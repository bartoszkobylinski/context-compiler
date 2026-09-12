# 2-minute demo script

## 0:00–0:15 — Problem

> Enterprise AI has a strange failure mode: every retrieved document can be real, relevant, and still produce the wrong answer — because the evidence is incomplete or belongs to the wrong point in time.

Show the question:

> Can a contractor access customer data from a personal laptop using VPN?

Set the date to **2025-06-10**.

## 0:15–0:45 — Traditional RAG

Run the comparison.

Point to the left panel:

> Traditional RAG retrieves the three most similar chunks once and answers. In our corpus the current 2025 policy ranks first, while the policy actually valid on June 10 is only seventh.

Do not over-explain embeddings. The key phrase is:

> Similarity is not evidentiary sufficiency.

## 0:45–1:20 — Context Compiler

Point to the right-hand timeline:

1. **EVIDENCE REQUIREMENTS** — the agent declares what must be established.
2. **SEARCHING** — it looks for candidate sources.
3. **VERSION CHECK** — it detects multiple Security Policy versions.
4. **TEMPORAL CHECK** — the 2025 policy is rejected because it is not effective until July 1.
5. **TEMPORAL CHECK** — the 2024 policy is valid on June 10.
6. **VERIFYING** — every material claim must have a source, an exact quote and temporal validity.
7. **SUPPORTED** — only then is the answer released.

Say:

> We don't make the model know more. We make it prove that it knows enough.

## 1:20–1:40 — Temporal flip

Change the date to **2025-08-10** and run again.

> Same question. Same corpus. Different point in time. Now the correct answer flips to NO because the 2025 policy is effective.

## 1:40–1:55 — Abstention

Select **Knowledge boundary**:

> Can a contractor expense their spouse's breakfast?

Expected result: **UNKNOWN**.

Say:

> Abstention is not a failure. It is a successful outcome when approved evidence does not establish an answer.

## 1:55–2:00 — Close

> Context Compiler turns retrieval from a lookup into an evidence-building loop: decide what must be known, gather it, validate it in context and time, verify the claims, then answer — or refuse to guess.

Stop.
