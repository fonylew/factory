# Step 03: Human Decisions & ADR (`TASK-003`)

- **Task ID**: `TASK-003`
- **Date**: `2026-11-12`
- **Decided By**: Technical Lead / System Analyst
- **Status**: APPROVED

---

## `ADR-011`: Agentic Formal Verification Trust Architecture (`FEAT-008`)
- **Question**: How should the Software Factory integrate multi-agent formal verification while guaranteeing mathematical soundness when LLM agents produce untrusted outputs?
- **Decision**:
  1. Treat **Spec-writer**, **Reviewers**, and the **Prover team** strictly as **Untrusted Agents**.
  2. Require explicit **Human Approval** (via Trello `Human Decision` / authorized Tech Lead sign-off) before locking `Spec.lean` as **Trusted**.
  3. Model compiled code execution on a **Trusted Lean Processor Model** (`CodeModel.lean`) locked with SHA-256.
  4. Enforce a 100% deterministic **Gatekeeper** (`FormalGatekeeper`) that rejects spec tampering, unapproved specs, incomplete theorem coverage, or any forbidden Lean escape hatches (`sorry`, `admit`, `axiom`, `unsafe`, `native_decide`), looping diagnostics back to the **Prover team** until verified.
  5. Package a dedicated **`formal-software-verification`** skill alongside updates to `software-factory`, `grill-me-analyst`, and `security-prod-auditor`.
