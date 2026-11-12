"""Stage 3a (`Prover team`): Multi-Agent Proof Synthesis Loop with Gatekeeper Feedback."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional
from pydantic import BaseModel, Field

from factory.formal.gatekeeper import FormalGatekeeper, GatekeeperVerdict
from factory.graph.models import CodeModelNode, FormalSpecNode, TheoremProofNode
from factory.graph.store import TraceabilityGraphStore
from factory.graph.validator import GraphValidator
from factory.journal.task_ledger import TaskLedgerManager


class ProverRunResult(BaseModel):
    theorem_proof_id: str
    feature_id: str
    rounds_used: int
    verdict_history: List[GatekeeperVerdict] = Field(default_factory=list)
    final_verdict: GatekeeperVerdict
    proof_node: Optional[TheoremProofNode] = None


class ProverTeamCoordinator:
    """
    Coordinates an untrusted Prover Team (multi-agent tactic workers) attempting to discharge
    all theorem obligations in `FormalSpecNode` over `CodeModelNode`, gated by `FormalGatekeeper`.
    If the Gatekeeper rejects a candidate proof, diagnostics are fed back into the next round.
    """

    def __init__(
        self,
        proofs_base_dir: Path,
        gatekeeper: FormalGatekeeper,
        graph_store: TraceabilityGraphStore,
        max_proof_rounds: int = 4,
        prover_agents_count: int = 3,
        task_ledger: Optional[TaskLedgerManager] = None,
    ) -> None:
        self.proofs_base_dir = Path(proofs_base_dir)
        self.proofs_base_dir.mkdir(parents=True, exist_ok=True)
        self.gatekeeper = gatekeeper
        self.graph_store = graph_store
        self.max_proof_rounds = max_proof_rounds
        self.prover_agents_count = prover_agents_count
        self.task_ledger = task_ledger

    def run_prover_loop(
        self,
        theorem_proof_id: str,
        formal_spec: FormalSpecNode,
        code_model: CodeModelNode,
        candidate_generator: Optional[Callable[[int, List[str]], str]] = None,
        task_id: Optional[str] = None,
    ) -> ProverRunResult:
        feat_proof_dir = self.proofs_base_dir / formal_spec.feature_id
        feat_proof_dir.mkdir(parents=True, exist_ok=True)
        proof_file = feat_proof_dir / "Proofs.lean"

        verdict_history: List[GatekeeperVerdict] = []
        last_diagnostics: List[str] = []
        final_verdict: Optional[GatekeeperVerdict] = None
        rounds_used = 0

        for round_idx in range(1, self.max_proof_rounds + 1):
            rounds_used = round_idx
            if candidate_generator is not None:
                candidate_lean = candidate_generator(round_idx, last_diagnostics)
            else:
                candidate_lean = self._default_prover_synthesis(formal_spec)

            proof_file.write_text(candidate_lean, encoding="utf-8")
            verdict = self.gatekeeper.verify_proof(
                formal_spec=formal_spec,
                code_model=code_model,
                proof_file_path=proof_file,
            )
            verdict_history.append(verdict)
            final_verdict = verdict

            if verdict.passed:
                break
            last_diagnostics = list(verdict.diagnostics)

        assert final_verdict is not None
        proof_node: Optional[TheoremProofNode] = None
        if final_verdict.passed:
            proof_sha = GraphValidator.compute_file_sha256(proof_file)
            proof_node = TheoremProofNode(
                id=theorem_proof_id,
                title=f"Verified Theorems & Proofs for {formal_spec.feature_id}",
                feature_id=formal_spec.feature_id,
                formal_spec_id=formal_spec.id,
                code_model_id=code_model.id,
                proof_file_path=str(proof_file),
                theorems_proved=final_verdict.proved_theorems,
                prover_rounds_used=rounds_used,
                prover_agents_count=self.prover_agents_count,
                gatekeeper_status="VERIFIED",
                proof_sha256=proof_sha,
                status="VERIFIED",
            )
            self.graph_store.upsert_node(proof_node)

        if self.task_ledger and task_id:
            self.task_ledger.append_step_output(
                task_id=task_id,
                step_name="06-formal-verification-proofs",
                markdown_content=(
                    f"- **Theorem Proof Node**: `{theorem_proof_id}`\n"
                    f"- **Trusted Lean Spec**: `{formal_spec.id}` (`{formal_spec.spec_sha256[:16]}...`)\n"
                    f"- **Trusted Processor Model**: `{code_model.id}` (`{code_model.model_sha256[:16]}...`)\n"
                    f"- **Prover Team Agents**: `{self.prover_agents_count}`\n"
                    f"- **Prover Rounds Used**: `{rounds_used}/{self.max_proof_rounds}`\n"
                    f"- **Gatekeeper Verdict**: `{final_verdict.status}`\n"
                    f"- **Theorems Certified**: `{', '.join(final_verdict.proved_theorems)}`\n"
                ),
                actor="FormalGatekeeper",
            )

        return ProverRunResult(
            theorem_proof_id=theorem_proof_id,
            feature_id=formal_spec.feature_id,
            rounds_used=rounds_used,
            verdict_history=verdict_history,
            final_verdict=final_verdict,
            proof_node=proof_node,
        )

    @staticmethod
    def _default_prover_synthesis(formal_spec: FormalSpecNode) -> str:
        ns = formal_spec.feature_id.replace("-", "_")
        theorems_code = "\n\n".join(
            f"theorem {thm} (s : Nat) : {thm}_prop s s := by\n  rfl"
            for thm in formal_spec.theorem_obligations
        )
        return (
            f"-- Synthesized by Prover Team for `{formal_spec.id}`\n"
            f"namespace FactoryFormal.{ns}\n\n"
            f"{theorems_code}\n\n"
            f"end FactoryFormal.{ns}\n"
        )
