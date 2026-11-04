"""Enterprise Security (STRIDE/OWASP) & Production Readiness Static/Pattern Analyzer."""

from __future__ import annotations

import re
from typing import List
from pydantic import BaseModel

from factory.graph.models import IssueCategory, IssueSeverity


class ScanFinding(BaseModel):
    rule_id: str
    title: str
    severity: IssueSeverity
    category: IssueCategory
    description: str
    remediation: str
    line_number: int = 1


class EnterpriseSecurityAndProdAnalyzer:
    """Detects security vulnerabilities and production hazards during `agy` PR reviews."""

    # Security & Production Rules
    SECRET_REGEXES = [
        re.compile(r"(?i)(api_key|secret_key|password|token|ghp_)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    ]
    HTTP_CALL_REGEX = re.compile(
        r"\b(requests\.(?:get|post|put|delete|request)|httpx\.(?:get|post|put|delete|Client))\s*\(([^)]*)\)"
    )
    UNSAFE_EXEC_REGEX = re.compile(r"\b(eval|exec|pickle\.loads|yaml\.load\s*\([^)]*\))\b")
    BARE_EXCEPT_REGEX = re.compile(r"^\s*except\s*:\s*$")
    SQL_CONCAT_REGEX = re.compile(r"(?i)(SELECT|INSERT|UPDATE|DELETE)\s+.*(\+|f['\"])")

    def analyze_code_text(self, code_text: str, file_path: str = "unknown.py") -> List[ScanFinding]:
        findings: List[ScanFinding] = []
        lines = code_text.splitlines()

        for idx, line in enumerate(lines, start=1):
            # 1. Hardcoded Secret Check
            if any(rx.search(line) for rx in self.SECRET_REGEXES):
                findings.append(
                    ScanFinding(
                        rule_id="HARDCODED_SECRET",
                        title=f"Hardcoded secret or token in {file_path}",
                        severity=IssueSeverity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        description=f"Detected hardcoded credential or API token at {file_path}:{idx}.",
                        remediation="Move secrets to environment variables or Secret Manager and rotate compromised token.",
                        line_number=idx,
                    )
                )

            # 2. Missing HTTP Timeout Check (Production Resilience)
            http_match = self.HTTP_CALL_REGEX.search(line)
            if http_match:
                args_str = http_match.group(2)
                if "timeout" not in args_str:
                    findings.append(
                        ScanFinding(
                            rule_id="MISSING_HTTP_TIMEOUT",
                            title=f"External HTTP call missing explicit timeout in {file_path}",
                            severity=IssueSeverity.HIGH,
                            category=IssueCategory.PROD_RISK,
                            description=(
                                f"Unbounded network call `{http_match.group(1)}(...)` at {file_path}:{idx} "
                                "can hang worker threads indefinitely in production."
                            ),
                            remediation="Add an explicit `timeout=10.0` parameter and circuit breaker policy.",
                            line_number=idx,
                        )
                    )

            # 3. Unsafe Deserialization / Eval Check
            if self.UNSAFE_EXEC_REGEX.search(line) and "SafeLoader" not in line and "safe_load" not in line:
                findings.append(
                    ScanFinding(
                        rule_id="UNSAFE_CODE_EXECUTION",
                        title=f"Unsafe dynamic code execution or deserialization in {file_path}",
                        severity=IssueSeverity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        description=f"Unsafe execution/deserialization primitive found at {file_path}:{idx}.",
                        remediation="Use `yaml.safe_load` or structured Pydantic JSON parsing instead of `eval`/`pickle`.",
                        line_number=idx,
                    )
                )

            # 4. Bare Except Check (Production Observability Risk)
            if self.BARE_EXCEPT_REGEX.match(line):
                findings.append(
                    ScanFinding(
                        rule_id="SWALLOWED_EXCEPTION",
                        title=f"Bare except clause swallowing exceptions in {file_path}",
                        severity=IssueSeverity.MEDIUM,
                        category=IssueCategory.PROD_RISK,
                        description=f"Bare `except:` at {file_path}:{idx} catches SystemExit and masks production failures.",
                        remediation="Catch specific exception types and log structured error context.",
                        line_number=idx,
                    )
                )

            # 5. Potential SQL Injection via String Interpolation
            if self.SQL_CONCAT_REGEX.search(line):
                findings.append(
                    ScanFinding(
                        rule_id="SQL_INJECTION_RISK",
                        title=f"Potential SQL injection via string formatting in {file_path}",
                        severity=IssueSeverity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        description=f"Dynamic SQL query construction detected at {file_path}:{idx}.",
                        remediation="Use parameterized SQL queries (`?` or `:param` placeholders).",
                        line_number=idx,
                    )
                )

        return findings
