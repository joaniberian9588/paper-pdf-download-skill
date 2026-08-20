"""Small repository-local CI validator for the two packaged skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    agent_file = skill_dir / "agents" / "openai.yaml"
    if not skill_file.exists():
        return [f"{skill_dir}: missing SKILL.md"]
    text = skill_file.read_text(encoding="utf-8")
    if "TODO" in text:
        errors.append(f"{skill_file}: unresolved TODO")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        errors.append(f"{skill_file}: invalid YAML frontmatter fence")
        return errors
    frontmatter = match.group(1)
    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    description_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_match:
        errors.append(f"{skill_file}: missing name")
    else:
        name = name_match.group(1).strip()
        if name != skill_dir.name or not NAME_RE.fullmatch(name):
            errors.append(f"{skill_file}: name must match directory and use hyphen-case")
    if not description_match or len(description_match.group(1).strip()) < 40:
        errors.append(f"{skill_file}: description is missing or too short")
    if not agent_file.exists():
        errors.append(f"{agent_file}: missing agent interface metadata")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    for skill_dir in sorted((root / "skills").iterdir()):
        if skill_dir.is_dir():
            errors.extend(validate(skill_dir))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Packaged skills are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
