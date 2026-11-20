#!/usr/bin/env python3
"""Print a compact AST skeleton of Python files in a repository."""

from __future__ import annotations

import argparse
import ast
import subprocess
from pathlib import Path

IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "build",
        "dist",
        ".tox",
        ".eggs",
    }
)
FUNC_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)


def get_python_files(root: Path) -> list[Path]:
    """Return sorted Python files under root, respecting .gitignore when possible."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        paths = (root / line for line in result.stdout.splitlines() if line.strip())
        return sorted(p for p in paths if p.is_file())

    return sorted(p for p in root.rglob("*.py") if not _is_ignored(p, root))


def _is_ignored(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts  # only check parts below root
    return any(part in IGNORED_DIRS or part.endswith(".egg-info") for part in parts)


def _is_visible(name: str, include_private: bool) -> bool:
    is_dunder = name.startswith("__") and name.endswith("__")
    return include_private or is_dunder or not name.startswith("_")


def _annotated(name: str, annotation: ast.expr | None) -> str:
    return f"{name}: {ast.unparse(annotation)}" if annotation else name


def format_arguments(args: ast.arguments) -> str:
    """Format an argument list, marking defaults as '=...'."""
    parts: list[str] = []

    positional = [*args.posonlyargs, *args.args]
    first_default = len(positional) - len(args.defaults)
    for i, arg in enumerate(positional):
        text = _annotated(arg.arg, arg.annotation)
        if i >= first_default:
            text += "=..."
        parts.append(text)
        if args.posonlyargs and i == len(args.posonlyargs) - 1:
            parts.append("/")

    if args.vararg:
        parts.append("*" + _annotated(args.vararg.arg, args.vararg.annotation))
    elif args.kwonlyargs:
        parts.append("*")

    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        text = _annotated(arg.arg, arg.annotation)
        parts.append(text + ("=..." if default is not None else ""))

    if args.kwarg:
        parts.append("**" + _annotated(args.kwarg.arg, args.kwarg.annotation))

    return ", ".join(parts)


def format_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef, indent: str = ""
) -> str:
    """Format decorators and the signature of a function or method."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    params = format_arguments(node.args)
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""

    lines = [f"{indent}@{ast.unparse(d)}" for d in node.decorator_list]
    lines.append(f"{indent}{prefix} {node.name}({params}){ret}")
    return "\n".join(lines)


def summarize_class(node: ast.ClassDef, include_private: bool) -> list[str]:
    """Return the class header, annotated attributes, and method signatures."""
    bases = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
    header = [f"@{ast.unparse(d)}" for d in node.decorator_list]
    header.append(f"class {node.name}{bases}:")

    body: list[str] = []
    for item in node.body:
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and _is_visible(item.target.id, include_private)
        ):
            body.append(f"  {item.target.id}: {ast.unparse(item.annotation)}")
        elif isinstance(item, FUNC_TYPES) and _is_visible(item.name, include_private):
            body.append(format_signature(item, indent="  "))

    return header + (body or ["  ..."])


def summarize_file(path: Path, base: Path, include_private: bool) -> str | None:
    """Return the skeleton for one file, or None if it has nothing to show."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None

    doc = ast.get_docstring(tree, clean=True)
    comment = f"  # {doc.splitlines()[0]}" if doc else ""
    lines = [f"{path.relative_to(base)}{comment}"]

    for node in tree.body:
        if not _is_visible(getattr(node, "name", "_"), include_private):
            continue
        if isinstance(node, ast.ClassDef):
            lines.extend(summarize_class(node, include_private))
        elif isinstance(node, FUNC_TYPES):
            lines.append(format_signature(node))

    return "\n".join(lines) if len(lines) > 1 else None


def build_skeleton(target: Path, include_private: bool, max_lines: int) -> str:
    """Build the full skeleton text for a file or directory."""
    root = target.resolve()
    if root.is_file():
        files, base = [root], root.parent
    else:
        files, base = get_python_files(root), root

    sections = [s for f in files if (s := summarize_file(f, base, include_private))]
    if not sections:
        return "No Python definitions found."

    lines = "\n\n".join(sections).splitlines()
    if len(lines) > max_lines:
        hidden = len(lines) - max_lines
        lines = [
            *lines[:max_lines],
            f"... (+{hidden} more lines; pass a subdirectory to narrow scope)",
        ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a compact AST skeleton of Python files."
    )
    parser.add_argument(
        "target", nargs="?", default=".", help="Directory or file to scan (default: .)"
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include _private functions, methods, and attributes",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=250,
        help="Maximum output lines before truncating (default: 250)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"Path not found: {target.resolve()}")
        return

    print(build_skeleton(target, args.include_private, args.max_lines))


if __name__ == "__main__":
    main()
