"""Parser and Validator for Enterprise Trello Kanban Card Templates."""

from __future__ import annotations

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class CardValidationError(Exception):
    """Raised when a Trello card is missing mandatory System Analysis, Design, or Acceptance Criteria."""

    def __init__(self, code: str, missing_sections: List[str], message: str) -> None:
        super().__init__(f"[{code}] {message}: {', '.join(missing_sections)}")
        self.code = code
        self.missing_sections = missing_sections
        self.message = message


class ParsedHumanDecision(BaseModel):
    question_id: str
    decision_text: str
    rationale: str = ""
    decided_by: str = ""
    wrapped_safe_input: str = ""


class CardParser:
    """Enforces the mandatory 5-section Enterprise System Analysis & Design Card Template."""

    DEFAULT_MANDATORY_SECTIONS = [
        "## 1. Problem Context & Goal",
        "## 2. System Analysis & Enterprise Design",
        "## 3. Acceptance Criteria (Gherkin Reference)",
        "## 4. Open Questions / Need Decision",
        "## 5. Human Decision",
    ]

    def __init__(self, mandatory_sections: Optional[List[str]] = None) -> None:
        self.mandatory_sections = mandatory_sections or self.DEFAULT_MANDATORY_SECTIONS

    def validate_card_description(self, description: str) -> List[str]:
        """Returns list of missing mandatory sections (empty if valid)."""
        missing: List[str] = []
        for section in self.mandatory_sections:
            if section not in description:
                missing.append(section)
            else:
                # Ensure sections 1, 2, and 3 have non-empty body content
                if section in self.mandatory_sections[:3]:
                    body = self._extract_section_body(description, section)
                    if len(body.strip()) < 5:
                        missing.append(f"{section} (empty body)")
        return missing

    def assert_ready_for_dev(self, description: str) -> None:
        missing = self.validate_card_description(description)
        if missing:
            raise CardValidationError(
                "MISSING_MANDATORY_CARD_SECTIONS",
                missing,
                "Card cannot transition to Ready for Dev without complete System Analysis, Design, and Gherkin Acceptance Criteria",
            )

    @staticmethod
    def _extract_section_body(description: str, heading: str) -> str:
        idx = description.find(heading)
        if idx == -1:
            return ""
        start = idx + len(heading)
        next_heading = re.search(r"\n##\s+\d+\.", description[start:])
        if next_heading:
            return description[start : start + next_heading.start()].strip()
        return description[start:].strip()

    @classmethod
    def render_card_template(
        cls,
        feature_id: str,
        title: str,
        problem_id: str,
        spec_id: str,
        problem_context: str,
        system_design: str,
        feature_file_path: str,
        scenarios: List[str],
        spec_sha256: str = "PENDING",
    ) -> str:
        scenario_lines = "\n".join(f"  - [ ] {s}" for s in scenarios) or "  - [ ] Default scenario"
        return f"""# [{feature_id}] {title}
**Traceability**: `{problem_id}` -> `{spec_id}` -> `{feature_id}`
**Git Branch**: `feat/{feature_id}` | **Spec SHA256**: `{spec_sha256}`

## 1. Problem Context & Goal
{problem_context}

## 2. System Analysis & Enterprise Design
{system_design}

## 3. Acceptance Criteria (Gherkin Reference)
- **Feature File**: `{feature_file_path}`
- **Scenarios**:
{scenario_lines}

## 4. Open Questions / Need Decision
None

## 5. Human Decision
**Decision**:
**Rationale**:
"""

    @classmethod
    def inject_open_question(
        cls,
        description: str,
        question_id: str,
        question_text: str,
        options: List[str],
    ) -> str:
        options_md = "\n".join(f"  {i + 1}. {opt}" for i, opt in enumerate(options))
        block = (
            f"- **Question ID**: `{question_id}`\n"
            f"- **Question**: {question_text}\n"
            f"- **Options**:\n{options_md}"
        )
        heading = "## 4. Open Questions / Need Decision"
        idx = description.find(heading)
        if idx == -1:
            return description + f"\n\n{heading}\n{block}\n"
        start = idx + len(heading)
        next_h = re.search(r"\n##\s+\d+\.", description[start:])
        if next_h:
            end = start + next_h.start()
            return description[:start] + "\n" + block + "\n" + description[end:]
        return description[:start] + "\n" + block + "\n"

    @classmethod
    def update_human_decision_section(
        cls,
        description: str,
        decision_text: str,
        rationale: str = "",
    ) -> str:
        heading = "## 5. Human Decision"
        block = f"**Decision**: {decision_text}\n**Rationale**: {rationale}"
        idx = description.find(heading)
        if idx == -1:
            return description + f"\n\n{heading}\n{block}\n"
        start = idx + len(heading)
        return description[:start] + "\n" + block + "\n"

    @classmethod
    def parse_human_decision(
        cls,
        description: str,
        decided_by: str,
    ) -> Optional[ParsedHumanDecision]:
        q_section = cls._extract_section_body(description, "## 4. Open Questions / Need Decision")
        d_section = cls._extract_section_body(description, "## 5. Human Decision")
        if not d_section:
            return None

        qid_match = re.search(r"Question ID\*\*:\s*`?([A-Za-z0-9_\-]+)`?", q_section)
        question_id = qid_match.group(1) if qid_match else "ADR-AUTO"

        dec_match = re.search(r"\*\*Decision\*\*:\s*(.+)", d_section)
        rat_match = re.search(r"\*\*Rationale\*\*:\s*(.*)", d_section)

        decision_val = dec_match.group(1).strip() if dec_match else d_section.strip()
        if not decision_val:
            return None
        rationale_val = rat_match.group(1).strip() if rat_match else ""

        # Wrap external Trello text in strict XML delimiters to mitigate prompt injection
        safe_wrapped = (
            f"<untrusted_trello_input author=\"{decided_by}\" question_id=\"{question_id}\">\n"
            f"Decision: {decision_val}\n"
            f"Rationale: {rationale_val}\n"
            f"</untrusted_trello_input>"
        )
        return ParsedHumanDecision(
            question_id=question_id,
            decision_text=decision_val,
            rationale=rationale_val,
            decided_by=decided_by,
            wrapped_safe_input=safe_wrapped,
        )
