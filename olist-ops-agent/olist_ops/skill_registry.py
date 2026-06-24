"""ADK Skill registry integration for the Olist Ops agent.

This module loads reusable agent skills from the repository `skills/` directory
and exposes a concrete ADK `SkillRegistry`. This demonstrates the Kaggle key
concept "Agent skills" in code while keeping skills state-aware and role-specific.

CLI proof:
    uv run python -m olist_ops.skill_registry --list
    uv run python -m olist_ops.skill_registry --show executive-briefing
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from google.adk.skills import SkillRegistry, load_skill_from_dir, list_skills_in_dir
from google.adk.skills.models import Frontmatter, Skill

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


class LocalSkillRegistry(SkillRegistry):
    """Small concrete SkillRegistry backed by local `skills/*/SKILL.md` files."""

    def __init__(self, skills_dir: Path = _SKILLS_DIR) -> None:
        self.skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        if not self.skills_dir.exists():
            return

        for name in list_skills_in_dir(self.skills_dir):
            skill_dir = self.skills_dir / name
            try:
                skill = load_skill_from_dir(skill_dir)
                self._skills[skill.frontmatter.name] = skill
            except Exception as exc:  # pragma: no cover - malformed skill guard
                print(f"⚠ Could not load skill '{name}': {exc}", file=sys.stderr)

    async def get_skill(self, *, name: str) -> Skill:
        """Return a full skill by name."""
        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"Skill '{name}' not found") from exc

    async def search_skills(self, *, query: str) -> list[Frontmatter]:
        """Search skills by name, description, agent metadata, or instructions."""
        q = query.lower().strip()
        if not q:
            return [skill.frontmatter for skill in self._skills.values()]

        matches: list[Frontmatter] = []
        for skill in self._skills.values():
            haystack = "\n".join(
                [
                    skill.frontmatter.name,
                    skill.frontmatter.description,
                    str(skill.frontmatter.metadata or {}),
                    skill.instructions,
                ]
            ).lower()
            if q in haystack:
                matches.append(skill.frontmatter)
        return matches

    def search_tool_description(self) -> str:
        return (
            "Search Olist Ops procedural skills by task, agent name, or KPI. "
            "Use before complex executive briefings, seller-risk audits, or "
            "freight-lane analyses."
        )

    def as_dict(self) -> dict[str, Skill]:
        """Return loaded skills for tests/CLI inspection."""
        return dict(self._skills)


def load_skills() -> LocalSkillRegistry:
    """Load all local skills into a concrete ADK SkillRegistry."""
    return LocalSkillRegistry()


async def _show_skill(registry: LocalSkillRegistry, name: str) -> None:
    skill = await registry.get_skill(name=name)
    print(f"# {skill.frontmatter.name}")
    print(f"Description: {skill.frontmatter.description}")
    print()
    print(skill.instructions)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Olist Ops ADK skill registry CLI")
    parser.add_argument("--list", action="store_true", help="List all loaded skills")
    parser.add_argument("--show", metavar="NAME", help="Show full instructions for a skill")
    args = parser.parse_args()

    registry = load_skills()
    skills = registry.as_dict()

    if args.show:
        asyncio.run(_show_skill(registry, args.show))
        return

    print(f"Skills loaded from {_SKILLS_DIR}:")
    if not skills:
        print("  (none)")
        return
    for name, skill in sorted(skills.items()):
        print(f"  {name}: {skill.frontmatter.description}")


if __name__ == "__main__":
    _cli()
