"""Parser for Gherkin `.feature` files to extract traceability tags and scenarios."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List
from pydantic import BaseModel, Field


class GherkinFeatureSpec(BaseModel):
    file_path: str
    feature_title: str
    tags: List[str] = Field(default_factory=list)
    scenarios: List[str] = Field(default_factory=list)


class GherkinParser:
    """Extracts `@PROB-`, `@SPEC-`, `@FEAT-` tags, Feature titles, and Scenario names."""

    TAG_RE = re.compile(r"@([A-Za-z0-9_\-]+)")
    FEATURE_RE = re.compile(r"^\s*Feature:\s*(.+)$")
    SCENARIO_RE = re.compile(r"^\s*Scenario(?: Outline)?:\s*(.+)$")

    @classmethod
    def parse_file(cls, path: Path) -> GherkinFeatureSpec:
        text = Path(path).read_text(encoding="utf-8")
        tags: List[str] = []
        feature_title = ""
        scenarios: List[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("@"):
                tags.extend(cls.TAG_RE.findall(stripped))
            f_match = cls.FEATURE_RE.match(line)
            if f_match and not feature_title:
                feature_title = f_match.group(1).strip()
            s_match = cls.SCENARIO_RE.match(line)
            if s_match:
                scenarios.append(s_match.group(1).strip())

        return GherkinFeatureSpec(
            file_path=str(path),
            feature_title=feature_title or path.stem,
            tags=tags,
            scenarios=scenarios,
        )
