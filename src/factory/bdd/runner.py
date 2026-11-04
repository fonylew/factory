"""Language-Agnostic Gherkin BDD Test Runner."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
from typing import Dict, Optional
from pydantic import BaseModel

from factory.config import BDDConfig


class BDDExecutionResult(BaseModel):
    adapter: str
    command: str
    exit_code: int
    passed: bool
    stdout: str
    stderr: str


class LanguageAgnosticBDDRunner:
    """Executes Gherkin regression suites via configurable per-project adapters."""

    def __init__(self, bdd_config: Optional[BDDConfig] = None) -> None:
        self.bdd_config = bdd_config or BDDConfig()

    def run(
        self,
        cwd: Path,
        adapter_name: Optional[str] = None,
        extra_args: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 120,
    ) -> BDDExecutionResult:
        adapter_key = adapter_name or self.bdd_config.default_adapter
        adapter = self.bdd_config.adapters.get(adapter_key)
        if not adapter:
            raise ValueError(f"Unknown BDD adapter '{adapter_key}'.")

        cmd_str = adapter.command
        if extra_args:
            cmd_str = f"{cmd_str} {extra_args}"

        run_env = dict(env if env is not None else os.environ)
        local_bin = "/home/aimet/.local/bin"
        if local_bin not in run_env.get("PATH", ""):
            run_env["PATH"] = f"{local_bin}:{run_env.get('PATH', '/usr/bin:/bin')}"

        proc = subprocess.run(
            shlex.split(cmd_str),
            cwd=str(cwd),
            env=run_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return BDDExecutionResult(
            adapter=adapter_key,
            command=cmd_str,
            exit_code=proc.returncode,
            passed=(proc.returncode == 0),
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
