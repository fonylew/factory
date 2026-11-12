# Step 01: Grill-Me Discovery Conversation (`TASK-003`)

- **Task ID**: `TASK-003`
- **Date**: `2026-11-12`
- **Stakeholder**: Technical Lead / System Analyst

---

## 1. User Request & Reference Architecture Diagram
> *"I want to create agentic framework for formal verification according to this diagram. Please add this process to the software factory and the corresponding skills. Including a new skills for software verification."*

## 2. Analysis of the Reference Architecture Diagram
The uploaded architecture defines three interconnected stages with an explicit **Trust Boundary** separating **Agents with untrusted output** (Blue) from **Trusted** artifacts/verifiers (Yellow) and **Verified outputs** (Green):

1. **Stage 1: `1 Specification`**:
   - **Inputs**: Research papers / RFCs / Mathematical specs.
   - **Agents (Untrusted Output)**: **Spec-writer** $\leftrightarrow$ **Reviewers**, plus interactive dialogue with **User**.
   - **Human Trust Gate**: The **User** explicitly **Approves** the specification, elevating it into a **Trusted `Lean spec`**.
2. **Stage 2: `2 Code`**:
   - **Input**: Target implementation code (e.g., Signal's Rust code / systems code).
   - **Trusted Semantics (`Executable in Lean`)**: Compiles/lifts source code into **`Compiled machine code`** that *runs on* a **`Lean model of processor`** (or formal operational semantics in Lean).
3. **Stage 3: `3 Proof`**:
   - **Inputs**: Trusted `Lean spec` + Trusted `Executable in Lean` code/processor model.
   - **Prover team (Untrusted Output)**: Multi-agent swarm generating candidate Lean tactic proofs (`Proofs`).
   - **Gatekeeper (Trusted)**: Deterministic proof checker & soundness verifier. If invalid or incomplete, returns **`Rejected`** diagnostics back to the **Prover team**; if valid, certifies **`Theorems, proofs`** (Green).
