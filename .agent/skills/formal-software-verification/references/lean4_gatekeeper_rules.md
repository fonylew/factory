# Lean 4 Soundness & Gatekeeper Verification Rules

## 1. Banned Escape Hatches in `Proofs.lean`
The `FormalGatekeeper` strips all line comments (`-- ...`) and nested block comments (`/- ... -/`) and **immediately rejects** any proof file containing any of the following tokens:
- `sorry` / `admit`: Incomplete proof placeholders that prove `False`.
- `axiom` / `opaque`: Custom axioms that bypass constructive proof obligations.
- `unsafe`: Bypasses termination and positivity checks in the Lean kernel.
- `implemented_by` / `extern`: Replaces verified Lean functions with unverified C/FFI code.
- `native_decide`: Trusts the native compiler runtime rather than kernel reduction.

## 2. Spec-Writer & Reviewer Checklist (Stage 1)
Because an LLM Spec-writer has **untrusted output**, Reviewer agents and the Human approver must check for:
1. **Vacuous Truths**: Ensure theorem hypotheses are satisfiable (no contradictory preconditions that make `H -> Conclusion` trivially true).
2. **Helper Function Fidelity**: Definitions inside `Spec.lean` must be clean, readable, and minimal so a human reviewer can audit every line before locking `Spec.lean` as Trusted.
3. **Immutability**: Once `Spec.lean` and `CodeModel.lean` are locked, prover agents may add helper lemmas **only** inside `Proofs.lean`—never by mutating `Spec.lean`.
