# Project 2 v0.1 — Review Sheet (Signed)

## Review Decision

**Reviewer:** boiledfishz  
**Review Date:** 2026-10-05  
**Decision:** Approved to proceed from specification/preregistration into implementation, subject to the frozen decisions below.

---

## CL-03 — Course / Operation Scope

**Decision:** Keep Project 2 **read-only**. Do **not** implement or claim a real or fake `publish`/write operation as part of the accepted system.

**Approved interpretation:**
- Only registered read-only analysis operations are allowed.
- Unregistered write-like operations such as `publish` must be rejected before Worker execution.
- No Fake Publish is needed merely to demonstrate a write path.
- If a later explicit course requirement mandates a write operation, it must be specified separately with authorization, idempotency, rollback/audit boundaries, and its own acceptance evidence.

**Rationale:** The current assignment evidence does not establish that a real write/publish capability is required. Adding one would increase risk without improving compliance.

---

## CL-05 — Core Worker Selection

**Decision:** Select the **Database Worker** as the core independent online Worker, alongside the reused RAG Worker under the centralized Supervisor.

**Approved responsibilities:**
- Exact read-only document counting over the authorized TechQA snapshot.
- Optional bounded sample return.
- Deterministic query scope and version reporting.
- Independent operation without requiring LLM, vector, or RAG dependencies.
- Structured states compatible with the Supervisor contract:
  `completed`, `partial`, `no_data`, `permission_denied`, `timeout`, `failed`.

**Rationale:** This Worker provides genuinely independent capability and evidence, is easy to verify against the underlying corpus, and directly supports the existing acceptance scenarios for independence, count correctness, partial completion, and combined responses.

---

## CL-08 — Calibration / Budget Protocol

**Decision:** Use a **preregistered calibration-then-freeze protocol**. Calibration is for operational limits only and must not be presented as a course grading threshold.

**Approved protocol:**
1. Use a designated development/calibration run to measure normal dependency latency and resource usage.
2. Freeze the operational limits before real acceptance execution.
3. Enforce the currently preregistered caps on the default API path:
   - maximum **16 total dependency attempts**
   - maximum **6 LLM attempts**
4. Failed, retried, timed-out, and cancelled internal attempts all consume budget.
5. A request may not start attempt 17 or LLM attempt 7.
6. Deadline exhaustion cancels in-flight work and stops new work.
7. Unknown token/cost values remain `null`; they must not be silently converted to zero.
8. Acceptance evidence must record nested/internal attempts rather than only the outer HTTP request.
9. No gold answer, official Y/N label, or acceptance outcome may be used to tune the frozen limits.
10. If empirical latency calibration changes the wall-clock timeout value, the chosen value and calibration evidence must be recorded before acceptance runs and then remain frozen.

**Rationale:** This gives deterministic budget behavior without inventing a course-mandated accuracy/F1 cutoff, and matches the existing timeout/cancellation/budget acceptance scenarios.

---

## Approved Baseline

**requirements_v0.1.md SHA-256**  
`7aa3441bf33c7d3b94501d99d6a7e99e0ba486e03413abf3e530c6a847f6ea7b`

**task_preregistration.json SHA-256**  
`ecd190e06afc173ab485ccba8c1a16e6256ede19b575ecd1ceb00891de86d63f`

The above hashes are approved as the specification/preregistration baseline for implementation. Any change that alters the approved requirements, preregistered acceptance logic, or the three decisions above must be versioned and reviewed again.

---

## Signature

**Signed by:** boiledfishz  
**Date:** 2026-10-05  
**Status:** APPROVED
