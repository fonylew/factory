# Step 02: System Analysis & Enterprise Design (`TASK-003`)

- **Task ID**: `TASK-003`
- **Date**: `2026-11-12`
- **Linked Feature**: `FEAT-008`

---

## 1. Subsystem Design (`src/factory/formal/`)
1. **`spec_pipeline.py` (`FormalSpecPipeline`)**:
   - Coordinates the untrusted **Spec-writer** and adversarial **Reviewer** critiques to draft `specs/formal/<FEAT-ID>/Spec.lean` referencing research papers.
   - Enforces that `FormalSpecNode.trusted == False` until an authorized human approves it (via Trello `2. Need Decision` $\rightarrow$ `3. Human Decision` or `approve_spec`), at which point its SHA-256 is recorded and locked.
2. **`code_model.py` (`ExecutableLeanCodeModeler`)**:
   - Compiles/lifts Rust or systems source code (invoking `rustc --emit=asm` / inspectable binary bytes when available, or deterministic instruction lifting) into `specs/formal/<FEAT-ID>/CodeModel.lean` containing both the compiled instruction stream and the Lean processor state machine (`ProcessorState`, `step`, `run`).
   - Locks `CodeModel.lean` with a SHA-256 checksum (`CodeModelNode`).
3. **`gatekeeper.py` (`FormalGatekeeper`)**:
   - **Deterministic, zero-LLM soundness gate** checking 5 invariants:
     1. `Spec.lean` is marked **Trusted** (Human-approved) and its SHA-256 matches the locked hash.
     2. `CodeModel.lean` SHA-256 matches the locked hash.
     3. Strips all Lean line comments (`-- ...`) and nested block comments (`/- ... -/`) before scanning `Proofs.lean` for forbidden soundness escape hatches: `sorry`, `admit`, `axiom`, `opaque`, `unsafe`, `implemented_by`, `extern`, `native_decide`.
     4. Verifies every `theorem <name>` obligation declared in `Spec.lean` is proved with a matching `theorem <name>` (and zero `sorry`) in `Proofs.lean`.
     5. Runs the configured Lean 4 kernel (`lean` / `lake env lean`) if present on PATH (with explicit timeout).
4. **`prover_team.py` (`ProverTeamCoordinator`)**:
   - Runs iterative multi-agent proof synthesis rounds (`Prover team` $\rightarrow$ `Gatekeeper` $\dashrightarrow$ `Rejected` retry loop $\rightarrow$ `VERIFIED`), recording `TheoremProofNode` (`THM-XXX`) in the Traceability Graph and `06-formal-verification-proofs.md` in the Task Ledger.

---

## 2. STRIDE Security & Soundness Threat Model for Formal Verification
| Threat Vector | Category | Mitigation in `FormalGatekeeper` |
| :--- | :--- | :--- |
| **Prover Agent Weakens Theorem Statement** (e.g., changes theorem to `True` in `Spec.lean`) | Tampering | `Spec.lean` and `CodeModel.lean` are POSIX read-only (`chmod a-w`) AND verified via cryptographic SHA-256 against `FormalSpecNode.spec_sha256` before Gatekeeper runs. |
| **Axiom / `sorry` Smuggling** (Prover adds `axiom magic : False` or `native_decide` or `implemented_by`) | Elevation of Trust / Soundness Bypass | Comment-aware lexical scanner bans `sorry`, `admit`, `axiom`, `opaque`, `unsafe`, `implemented_by`, `extern`, and `native_decide` anywhere in `Proofs.lean`. |
| **Unapproved LLM Spec Hallucination** (Proving a theorem that doesn't match the research paper / user intent) | Specification Drift | `FormalGatekeeper` refuses to verify any `FormalSpecNode` where `trusted == False` or `human_approved_by` is empty. |
| **Runaway Prover Loop / Kernel Hang** (Non-terminating Lean tactic `simp` / `omega` loop) | Denial of Service | Hard `timeout_seconds` on Lean kernel execution and `max_proof_rounds` circuit breaker on `ProverTeamCoordinator`. |
