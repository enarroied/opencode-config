#!/usr/bin/env python3
"""Run the checks a project declares in [tool.review] against staged files.

Full output goes to .review/<name>.log. The printed report is short.
Exit status is 1 if any check fails, so this can gate a commit.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

LOG_DIR = Path(".review")
SHOW_LINES = 15
TAIL_LINES = 3
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
UV = shutil.which("uv")

# Used only when a project has no [tool.review] table.
DEFAULT_CHECKS = [
    {"name": "ruff", "cmd": "ruff check --output-format=concise {py}", "when": "py"},
    {"name": "ruff format", "cmd": "ruff format --check {py}", "when": "py"},
    {"name": "pytest", "cmd": "pytest -q --tb=line", "when": "py"},
]


def load_pyproject() -> dict:
    path = Path("pyproject.toml")
    return tomllib.loads(path.read_text()) if path.exists() else {}


def declared_packages(data: dict) -> set[str]:
    project = data.get("project", {})
    specs: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    for group in data.get("dependency-groups", {}).values():
        specs.extend(item for item in group if isinstance(item, str))

    names = set()
    for spec in specs:
        match = NAME_RE.match(spec.strip())
        if match:
            names.add(match.group(0).lower().replace("_", "-").replace(".", "-"))
    return names


def run(cmd: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
    full_env = {**os.environ, **(env or {})}
    res = subprocess.run(cmd, capture_output=True, text=True, check=False, env=full_env)
    return res.returncode, f"{res.stdout}\n{res.stderr}".strip()


def staged_files() -> list[str]:
    code, out = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if code != 0:
        return []
    return [f for f in out.splitlines() if f and Path(f).exists()]


def is_selected(check: dict, changed: list[str]) -> bool:
    if "requires" in check and not Path(check["requires"]).exists():
        return False
    when = check.get("when", "any")
    if when == "py":
        return any(f.endswith(".py") for f in changed)
    if when == "deps":
        return any(Path(f).name in {"pyproject.toml", "uv.lock"} for f in changed)
    return True


def build_command(
    check: dict, declared: set[str], changed: list[str]
) -> tuple[list[str] | None, str]:
    tokens: list[str] = []
    for tok in shlex.split(check["cmd"]):
        if tok == "{py}":
            tokens.extend(f for f in changed if f.endswith(".py"))
        elif tok == "{all}":
            tokens.extend(changed)
        else:
            tokens.append(tok)

    exe = tokens[0]
    if exe in declared:
        if not UV:
            return None, f"{exe} is declared but uv is not installed"
        return [UV, "run", *tokens], ""
    if shutil.which(exe):
        return tokens, ""
    return None, f"{exe} not found"


def summarize(out: str, log: Path) -> str:
    lines = [line for line in out.splitlines() if line.strip()]
    if len(lines) <= SHOW_LINES:
        return "\n".join(lines)
    head = lines[: SHOW_LINES - TAIL_LINES]
    tail = lines[-TAIL_LINES:]
    hidden = len(lines) - len(head) - len(tail)
    return "\n".join([*head, f"... {hidden} more lines in {log}", *tail])


def execute(check: dict, cmd: list[str]) -> bool:
    name = check["name"]
    code, out = run(cmd, check.get("env"))
    slug = re.sub(r"\W+", "-", name).strip("-").lower()
    log = LOG_DIR / f"{slug}.log"
    log.write_text(out + "\n")
    if code == 0:
        print(f"PASS {name}")
        return True
    print(f"FAIL {name} (exit {code}, log: {log})")
    print(summarize(out, log))
    return False


def main() -> int:
    changed = staged_files()
    if not changed:
        print("No staged files.")
        return 0

    data = load_pyproject()
    checks = data.get("tool", {}).get("review", {}).get("checks", DEFAULT_CHECKS)
    declared = declared_packages(data)
    LOG_DIR.mkdir(exist_ok=True)

    failed = False
    for check in checks:
        if not is_selected(check, changed):
            continue
        cmd, reason = build_command(check, declared, changed)
        if cmd is None:
            print(f"SKIP {check['name']}: {reason}")
            continue
        failed |= not execute(check, cmd)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
