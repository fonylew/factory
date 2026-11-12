---
name: formal-software-verification
description: >-
  Agentic Formal Software Verification skill implementing the 3-stage Lean 4 verification framework:
  (1) Specification: Research papers -> Spec-writer <-> Reviewers <-> Human Approval -> Trusted Lean spec;
  (2) Code: Source/Rust code -> Compiled machine code running on a Lean model of processor;
  (3) Proof: Multi-agent Prover team -> Deterministic Gatekeeper -> Verified Theorems & Proofs.
  Activate whenever the user or task requires formal verification, mathematical proofs, Lean 4 specs,
  cryptographic/protocol verification, machine-code semantics lifting, or Gatekeeper proof auditing.
---

# Agentic Formal Software Verification Skill

This skill governs high-assurance formal software verification inside the **Enterprise Spec-Driven Software Factory**.

## Core Trust Architecture (Strict Trust Boundary)
- **Agents with Untrusted Output**: `Spec-writer`, `Reviewers`, and the `Prover team` are LLM agents whose outputs are **NEVER** trusted on faith.
- **Trusted Artifacts & Verifiers**:
  1. **`Lean spec` (`specs/formal/<FEAT-ID>/Spec.lean`)**: Becomes **Trusted** ONLY after adversarial `Reviewers` critique it AND an authorized **User / Tech Lead** approves it via Trello (`2. Need Decision` $\rightarrow$ `3. Human Decision`), locking its SHA-256 checksum.
  2. **`Executable in Lean` Code Model (`specs/formal/<FEAT-ID>/CodeModel.lean`)**: Deterministically lifted from source/compiled machine code (e.g., Rust via `rustc --emit=asm` / ISA lifter) onto a formal **Lean model of processor**, locked read-only with SHA-256.
  3. **`Gatekeeper` (`FormalGatekeeper`)**: 100% deterministic code + Lean kernel checker that rejects any proof tampering with `Spec.lean`/`CodeModel.lean` or introducing forbidden escape hatches (`sorry`, `admit`, `axiom`, `opaque`, `unsafe`, `implemented_by`, `extern`, `native_decide`).

---

## 3-Stage Execution Workflow

### Stage 1: Specification (`1 Specification`)
1. Gather research papers, RFCs, and security invariants linked to `PROB-XXX` / `FEAT-XXX`.
2. Draft the candidate Lean specification and run adversarial **Reviewer** checks (checking for vacuous preconditions like `False -> P`, under-specification, or mismatch with the paper):
   - **MCP Tool**: `factory_formal_init_spec`
   - **CLI**:
     ```bash
     uv run factory formal init-spec \
       --spec-id FSPEC-008 \
       --feature-id FEAT-008 \
       --title "Constant-Time Key Ratchet Verification" \
       --paper "Signal PQXDH Specification" \
       --obligation "constant_time_ratchet_step"
     ```
3. **Wait for Human Approval**: The card moves to Trello **`2. Need Decision`**. Once the Tech Lead approves, lock the spec as **Trusted**:
   - **MCP Tool**: `factory_formal_approve_spec`
   - **CLI**: `uv run factory formal approve-spec FSPEC-008 --approved-by tech_lead_01`

### Stage 2: Code & Processor Model (`2 Code`)
Lift the implementation code (e.g., Rust source file) into compiled machine instructions executing on the Lean processor state model:
- **MCP Tool**: `factory_formal_lift_code`
- **CLI**:
  ```bash
  uv run factory formal lift-code \
    --model-id CMOD-008 \
    --feature-id FEAT-008 \
    --source-path src/crypto_ratchet.rs \
    --language rust
  ```

### Stage 3: Multi-Agent Prover Team & Gatekeeper (`3 Proof`)
1. Dispatch the **Prover team** (parallel/iterative tactic agents) to write `Proofs.lean` (`src/formal/<FEAT-ID>/Proofs.lean`) while `Spec.lean` and `CodeModel.lean` remain read-only:
   - **MCP Tool**: `factory_formal_run_prover_team`
   - **CLI**:
     ```bash
     uv run factory formal prove \
       --proof-id THM-008 \
       --spec-id FSPEC-008 \
       --model-id CMOD-008 \
       --task-id TASK-003
     ```
2. Run standalone **Gatekeeper** verification at any time:
   - **MCP Tool**: `factory_formal_gatekeep`
   - **CLI**: `uv run factory formal gatekeep FSPEC-008 CMOD-008 src/formal/FEAT-008/Proofs.lean`
3. When the Gatekeeper returns `VERIFIED`, `TheoremProofNode` (`THM-XXX`) is linked to `FSPEC-XXX` and `CMOD-XXX` in the Traceability Graph and logged to `06-formal-verification-proofs.md`.

---

## Soundness & Gatekeeper Rules Reference
Read [references/lean4_gatekeeper_rules.md](./references/lean4_gatekeeper_rules.md) before writing or reviewing Lean specifications and proofs.
