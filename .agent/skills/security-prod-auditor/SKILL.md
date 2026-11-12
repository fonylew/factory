---
name: security-prod-auditor
description: Principal Enterprise Security and Production Readiness Reviewer skill for agy (Gemini 4 Argon). Audits Pull Requests submitted by pi coding agents against Gherkin specs, Traceability Graph links, STRIDE threats, and production failure modes.
---

# Principal Security & Production Auditor Skill (`agy` + Gemini 4 Argon)

Activate this skill when reviewing Pull Requests or code changes in `6. PR & Security Review (agy)`.

## Mandatory Audit Checklist
1. **Spec & Tamper Integrity**:
   - Verify `factory verify-specs` passes (zero modifications to `specs/` or `.feature` files by `pi`).
   - Verify all Gherkin scenarios in `specs/features/` pass via the BDD Runner.
   - Verify every changed code artifact links to an active `FeatureNode` -> `SystemSpecNode` -> `ProblemNode` in the Traceability Graph.
2. **Security Audit (STRIDE / OWASP)**:
   - Hardcoded secrets, API keys, tokens, or private keys (`HARDCODED_SECRET`).
   - SQL/Command/Prompt injection vectors (`INJECTION_RISK`).
   - Missing authentication/authorization checks or IDOR vulnerabilities.
   - Unsafe deserialization (`pickle`, `yaml.load` without `SafeLoader`, `eval`/`exec`).
3. **Production Readiness & Reliability Audit**:
   - Network/HTTP/RPC calls missing explicit timeouts (`MISSING_HTTP_TIMEOUT`).
   - Unbounded retries, infinite loops, or missing pagination (`UNBOUNDED_OPERATION`).
   - Bare `except:` blocks swallowing errors silently (`SWALLOWED_EXCEPTION`).
   - Missing transaction boundaries or non-idempotent state mutations.
4. **Dual-Track Issue Emission & Task Ledger**:
   - Record every finding as an `IssueNode` (`ISS-XXX`) in the Traceability Graph AND sync to the Trello Kanban `Issues & Security Findings` column + PR comments.
   - Write the full review output to `specs/tasks/<YYYY-MM-DD>_<TASK-ID>_<slug>/05-agy-security-pr-review.md`.
5. **Formal Verification & Gatekeeper Audit (When `FormalSpecNode` Exists)**:
   - Activate `formal-software-verification` rules and verify `FormalGatekeeper` passed (`TheoremProofNode.gatekeeper_status == "VERIFIED"`).
   - Confirm `Spec.lean` was human-approved (`trusted == True`), SHA-256 hashes of `Spec.lean` and `CodeModel.lean` are intact, and `Proofs.lean` has zero forbidden escape hatches (`sorry`, `admit`, `axiom`, `unsafe`, `native_decide`).
