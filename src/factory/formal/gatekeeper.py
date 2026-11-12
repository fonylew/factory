"""Stage 3b (`Gatekeeper`): Deterministic Soundness, Axiom, Escape-Hatch & Spec-Integrity Verifier."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import List, Optional
from pydantic import BaseModel, Field

from factory.graph.models import CodeModelNode, FormalSpecNode
from factory.graph.validator import GraphValidator


class GatekeeperVerdict(BaseModel):
    passed: bool
    status: str  # "VERIFIED" or "REJECTED"
    spec_hash_valid: bool
    code_model_hash_valid: bool
    forbidden_constructs_found: List[str] = Field(default_factory=list)
    missing_theorems: List[str] = Field(default_factory=list)
    proved_theorems: List[str] = Field(default_factory=list)
    lean_kernel_checked: bool = False
    diagnostics: List[str] = Field(default_factory=list)


class FormalGatekeeper:
    """
    Trusted deterministic Gatekeeper (ZERO LLM trust).
    Verifies:
      1. FormalSpecNode is marked `trusted=True` (Human-approved) and `Spec.lean` matches locked SHA-256.
      2. CodeModelNode `CodeModel.lean` matches locked SHA-256.
      3. Candidate `Proofs.lean` contains ZERO forbidden escape hatches (`sorry`, `admit`, `axiom`,
         `opaque`, `unsafe`, `implemented_by`, `extern`, `native_decide`) outside comments.
      4. Every required theorem obligation in `FormalSpecNode.theorem_obligations` has a concrete
         `theorem <name> ... :=` proof in `Proofs.lean`.
      5. Executes the Lean 4 kernel (`lean`) when installed on the host.
    """

    FORBIDDEN_ESCAPE_HATCHES = [
        "sorry",
        "admit",
        "axiom",
        "opaque",
        "unsafe",
        "implemented_by",
        "extern",
        "native_decide",
    ]

    THEOREM_DEF_RE = re.compile(
        r"\btheorem\s+([A-Za-z0-9_']+)\b[^:]*:\s*([^:=]+):=\s*(.+)",
        re.DOTALL,
    )

    def __init__(self, lean_binary: Optional[str] = None, timeout_seconds: int = 60) -> None:
        env_path = f"{Path.home() / '.elan' / 'bin'}:{os.environ.get('PATH', '')}"
        self.lean_binary = lean_binary or shutil.which("lean", path=env_path)
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def strip_lean_comments(lean_source: str) -> str:
        """Strips Lean 4 nested block comments `/- ... -/` and line comments `-- ...`."""
        out: List[str] = []
        i = 0
        n = len(lean_source)
        block_depth = 0
        in_string = False

        while i < n:
            ch = lean_source[i]
            nxt = lean_source[i + 1] if i + 1 < n else ""

            if block_depth == 0:
                if ch == '"' and (i == 0 or lean_source[i - 1] != "\\"):
                    in_string = not in_string
                    out.append(ch)
                    i += 1
                    continue
                if not in_string:
                    if ch == "/" and nxt == "-":
                        block_depth += 1
                        i += 2
                        continue
                    if ch == "-" and nxt == "-":
                        # Skip until newline
                        while i < n and lean_source[i] != "\n":
                            i += 1
                        continue
                out.append(ch)
                i += 1
            else:
                if ch == "/" and nxt == "-":
                    block_depth += 1
                    i += 2
                elif ch == "-" and nxt == "/":
                    block_depth -= 1
                    i += 2
                else:
                    if ch == "\n":
                        out.append("\n")
                    i += 1

        return "".join(out)

    @classmethod
    def scan_forbidden_constructs(cls, clean_code: str) -> List[str]:
        found: List[str] = []
        for token in cls.FORBIDDEN_ESCAPE_HATCHES:
            pattern = re.compile(rf"\b{re.escape(token)}\b")
            if pattern.search(clean_code):
                found.append(token)
        return found

    @staticmethod
    def extract_proved_theorem_names(clean_code: str) -> List[str]:
        names = re.findall(
            r"\btheorem\s+([A-Za-z0-9_']+)\b[\s\S]*?:=",
            clean_code,
        )
        return list(dict.fromkeys(names))

    def verify_proof(
        self,
        formal_spec: FormalSpecNode,
        code_model: CodeModelNode,
        proof_file_path: Path,
    ) -> GatekeeperVerdict:
        diagnostics: List[str] = []

        # 1. Check Trusted Spec approval & SHA-256 lock
        spec_path = Path(formal_spec.lean_spec_path)
        if not formal_spec.trusted or not formal_spec.human_approved_by:
            diagnostics.append(
                f"UNTRUSTED_SPEC_ERROR: FormalSpecNode '{formal_spec.id}' has not been approved by a human."
            )
            return GatekeeperVerdict(
                passed=False,
                status="REJECTED",
                spec_hash_valid=False,
                code_model_hash_valid=False,
                diagnostics=diagnostics,
            )

        current_spec_hash = (
            GraphValidator.compute_file_sha256(spec_path) if spec_path.exists() else ""
        )
        spec_hash_valid = bool(
            formal_spec.spec_sha256 and current_spec_hash == formal_spec.spec_sha256
        )
        if not spec_hash_valid:
            diagnostics.append(
                f"SPEC_TAMPERING_DETECTED: '{spec_path}' SHA-256 mismatch against locked Trusted Lean Spec."
            )

        # 2. Check Trusted CodeModel SHA-256 lock
        model_path = Path(code_model.lean_model_path)
        current_model_hash = (
            GraphValidator.compute_file_sha256(model_path) if model_path.exists() else ""
        )
        code_model_hash_valid = bool(
            code_model.model_sha256 and current_model_hash == code_model.model_sha256
        )
        if not code_model_hash_valid:
            diagnostics.append(
                f"CODE_MODEL_TAMPERING_DETECTED: '{model_path}' SHA-256 mismatch against Trusted Processor Model."
            )

        # 3. Inspect candidate Proofs.lean
        proof_path = Path(proof_file_path)
        if not proof_path.exists():
            diagnostics.append(f"MISSING_PROOF_FILE: '{proof_path}' does not exist.")
            return GatekeeperVerdict(
                passed=False,
                status="REJECTED",
                spec_hash_valid=spec_hash_valid,
                code_model_hash_valid=code_model_hash_valid,
                diagnostics=diagnostics,
            )

        raw_proof = proof_path.read_text(encoding="utf-8")
        clean_proof = self.strip_lean_comments(raw_proof)

        # 4. Scan for `sorry`, `admit`, `axiom`, `unsafe`, etc.
        forbidden = self.scan_forbidden_constructs(clean_proof)
        if forbidden:
            diagnostics.append(
                f"FORBIDDEN_PROOF_ESCAPE_HATCH: Proof contains banned Lean tokens: {', '.join(forbidden)}"
            )

        # 5. Check theorem coverage against obligations in FormalSpecNode
        proved_theorems = self.extract_proved_theorem_names(clean_proof)
        missing = [
            req for req in formal_spec.theorem_obligations if req not in proved_theorems
        ]
        if missing:
            diagnostics.append(
                f"MISSING_THEOREM_PROOFS: Obligations not proved in '{proof_path.name}': {', '.join(missing)}"
            )

        # 6. Optional Live Lean 4 Kernel Typecheck (when `lean` binary is installed)
        lean_checked = False
        if self.lean_binary and not diagnostics:
            combined_check = proof_path.parent / "_gatekeeper_bundle.lean"
            bundle_src = (
                spec_path.read_text(encoding="utf-8")
                + "\n"
                + model_path.read_text(encoding="utf-8")
                + "\n"
                + raw_proof
            )
            combined_check.write_text(bundle_src, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [self.lean_binary, str(combined_check)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                lean_checked = True
                if proc.returncode != 0:
                    diagnostics.append(
                        f"LEAN_KERNEL_TYPECHECK_FAILED: {proc.stdout.strip()} {proc.stderr.strip()}"
                    )
            finally:
                if combined_check.exists():
                    combined_check.unlink()

        passed = (
            spec_hash_valid
            and code_model_hash_valid
            and not forbidden
            and not missing
            and not diagnostics
        )
        return GatekeeperVerdict(
            passed=passed,
            status="VERIFIED" if passed else "REJECTED",
            spec_hash_valid=spec_hash_valid,
            code_model_hash_valid=code_model_hash_valid,
            forbidden_constructs_found=forbidden,
            missing_theorems=missing,
            proved_theorems=proved_theorems,
            lean_kernel_checked=lean_checked,
            diagnostics=diagnostics,
        )
