"""Installer for Global/Workspace Agent Skills (`software-factory`) and MCP Server Registration."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillInstallReport(BaseModel):
    installed_skills: List[str] = Field(default_factory=list)
    skills_target_dirs: List[str] = Field(default_factory=list)
    mcp_config_path: str = ""
    mcp_server_registered: bool = False


class FactorySkillInstaller:
    """Installs `software-factory`, `grill-me-analyst`, and `security-prod-auditor` skills and MCP config."""

    SKILL_NAMES = [
        "software-factory",
        "grill-me-analyst",
        "security-prod-auditor",
        "formal-software-verification",
    ]

    def __init__(self, factory_repo_root: Path) -> None:
        self.factory_repo_root = Path(factory_repo_root).resolve()
        self.source_skills_dir = self.factory_repo_root / ".agent" / "skills"

    def setup_agent_environment(
        self,
        gemini_config_dir: Optional[Path] = None,
        agents_skills_dir: Optional[Path] = None,
        use_symlinks: bool = False,
    ) -> SkillInstallReport:
        """Installs skills into `~/.gemini/config/skills/` (and `~/.agents/skills/`) and updates `mcp_config.json`."""
        home = Path.home()
        g_config = Path(gemini_config_dir) if gemini_config_dir else (home / ".gemini" / "config")
        g_skills_dir = g_config / "skills"
        g_skills_dir.mkdir(parents=True, exist_ok=True)

        target_dirs = [g_skills_dir]
        if agents_skills_dir is not None:
            a_dir = Path(agents_skills_dir)
            a_dir.mkdir(parents=True, exist_ok=True)
            target_dirs.append(a_dir)
        elif gemini_config_dir is None:
            default_agents_dir = home / ".agents" / "skills"
            default_agents_dir.mkdir(parents=True, exist_ok=True)
            target_dirs.append(default_agents_dir)

        installed: List[str] = []
        for skill_name in self.SKILL_NAMES:
            src = self.source_skills_dir / skill_name
            if not src.exists():
                continue
            for t_dir in target_dirs:
                dest = t_dir / skill_name
                if dest.is_symlink() or dest.exists():
                    if dest.is_symlink() or dest.is_file():
                        dest.unlink()
                    else:
                        shutil.rmtree(dest)
                if use_symlinks:
                    dest.symlink_to(src)
                else:
                    shutil.copytree(src, dest)
            installed.append(skill_name)

        mcp_config_path = g_config / "mcp_config.json"
        self._register_mcp_server(mcp_config_path)

        return SkillInstallReport(
            installed_skills=installed,
            skills_target_dirs=[str(d) for d in target_dirs],
            mcp_config_path=str(mcp_config_path),
            mcp_server_registered=True,
        )

    def _register_mcp_server(self, mcp_config_path: Path) -> None:
        mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
        existing_data: Dict[str, Any] = {}
        if mcp_config_path.exists():
            raw_text = mcp_config_path.read_text(encoding="utf-8").strip()
            if raw_text:
                try:
                    existing_data = json.loads(raw_text)
                except json.JSONDecodeError:
                    existing_data = {}

        if "mcpServers" not in existing_data or not isinstance(existing_data["mcpServers"], dict):
            existing_data["mcpServers"] = {}

        uv_bin = "/home/aimet/.local/bin/uv"
        if not Path(uv_bin).exists():
            uv_bin = "uv"

        existing_data["mcpServers"]["agentic-software-factory"] = {
            "command": uv_bin,
            "args": [
                "--directory",
                str(self.factory_repo_root),
                "run",
                "python",
                "-m",
                "factory.mcp_server",
            ],
            "env": {
                "FACTORY_CONFIG": str(self.factory_repo_root / "factory.yaml"),
            },
        }
        mcp_config_path.write_text(
            json.dumps(existing_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def init_target_project(self, target_dir: Path) -> Dict[str, Any]:
        """Scaffolds `factory.yaml`, `specs/`, `AGENTS.md`, and `.agent/skills/` into any project directory."""
        target = Path(target_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)

        for subdir in (
            "specs/problems",
            "specs/decisions",
            "specs/architecture",
            "specs/features",
            "specs/tasks",
            "specs/graph",
        ):
            (target / subdir).mkdir(parents=True, exist_ok=True)

        for filename in ("factory.yaml", "AGENTS.md", ".env.example"):
            src_file = self.factory_repo_root / filename
            dest_file = target / filename
            if src_file.exists() and not dest_file.exists():
                shutil.copy2(src_file, dest_file)

        dest_skills = target / ".agent" / "skills"
        dest_skills.mkdir(parents=True, exist_ok=True)
        for skill_name in self.SKILL_NAMES:
            src_skill = self.source_skills_dir / skill_name
            dst_skill = dest_skills / skill_name
            if src_skill.exists() and not dst_skill.exists():
                shutil.copytree(src_skill, dst_skill)

        return {
            "target_project": str(target),
            "factory_yaml": str(target / "factory.yaml"),
            "agents_md": str(target / "AGENTS.md"),
            "skills_installed": self.SKILL_NAMES,
        }
