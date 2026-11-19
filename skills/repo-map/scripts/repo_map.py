#!/usr/bin/env python3
"""Generate a compact AST skeleton of Python files in a repository."""

from __future__ import annotations

import argparse
import ast
import subprocess
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "build",
    "dist",
    ".tox",
    ".eggs",
}


def get_python_files(root: Path) -> list[Path]:
    """Return sorted Python files under root, respecting gitignore when available."""
    res = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0 and res.stdout.strip():
        files = [root / line for line in res.stdout.splitlines() if line.strip()]
        return sorted(f for f in files if f.is_file())

    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(
            part in IGNORED_DIRS or part.endswith(".egg-info") for part in path.parts
        )
    )


def format_arguments(args: ast.arguments) -> str:
    """Format function arguments with type annotations and default markers."""
    parts: list[str] = []

    positional = list(args.posonlyargs) + list(args.args)
    defaults_offset = len(positional) - len(args.defaults)

    for idx, arg in enumerate(positional):
        text = arg.arg
        if arg.annotation:
            text += f": {ast.unparse(arg.annotation)}"
        if idx >= defaults_offset:
            text += "=..."
        parts.append(text)
        if idx == len(args.posonlyargs) - 1 and args.posonlyargs:
            parts.append("/")

    if args.vararg:
        vararg = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            vararg += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(vararg)
    elif args.kwonlyargs:
        parts.append("*")

    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        text = arg.arg
        if arg.annotation:
            text += f": {ast.unparse(arg.annotation)}"
        if default is not None:
            text += "=..."
        parts.append(text)

    if args.kwarg:
        kwarg = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            kwarg += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(kwarg)

    return ", ".join(parts)


def format_func(node: ast.FunctionDef | ast.AsyncFunctionDef, indent: str = "") -> str:
    """Format a function or method signature."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    params = format_arguments(node.args)
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    decorators = [f"{indent}@{ast.unparse(d)}" for d in node.decorator_list]
    sig = f"{indent}{prefix} {node.name}({params}){ret}"
    return "\n".join([*decorators, sig])


def summarize_class(node: ast.ClassDef, include_private: bool) -> list[str]:
    """Extract class header, annotated attributes, and method signatures."""
    bases = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
    decorators = [f"@{ast.unparse(d)}" for d in node.decorator_list]
    lines = [*decorators, f"class {node.name}{bases}:"]

    body_lines: list[str] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            name = item.target.id
            if include_private or not name.startswith("_"):
                body_lines.append(f"  {name}: {ast.unparse(item.annotation)}")
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_dunder = item.name.startswith("__") and item.name.endswith("__")
            if include_private or not item.name.startswith("_") or is_dunder:
                body_lines.append(format_func(item, indent="  "))

    if not body_lines:
        body_lines.append("  ...")
    return lines + body_lines


def summarize_file(path: Path, root: Path, include_private: bool) -> str | None:
    """Parse a single Python file and return its structural skeleton."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return None

    rel_path = path.relative_to(root)
    doc = ast.get_docstring(tree, clean=True)
    first_doc_line = f"  # {doc.splitlines()[0]}" if doc else ""
    out: list[str] = [f"{rel_path}{first_doc_line}"]

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if include_private or not node.name.startswith("_"):
                out.extend(summarize_class(node, include_private))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if include_private or not node.name.startswith("_"):
                out.append(format_func(node))

    if len(out) == 1:
        return None
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a compact AST skeleton of Python files."
    )
    parser.add_argument(
        "target", nargs="?", default=".", help="Directory to scan (default: .)"
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

    root = Path(args.target).resolve()
    if not root.exists():
        print(f"Path not found: {root}")
        return

    files = [root] if root.is_file() else get_python_files(root)
    base = root.parent if root.is_file() else root

    sections: list[str] = []
    for file_path in files:
        summary = summarize_file(file_path, base, args.include_private)
        if summary:
            sections.append(summary)

    if not sections:
        print("No Python definitions found.")
        return

    output = "\n\n".join(sections).splitlines()
    if len(output) > args.max_lines:
        hidden = len(output) - args.max_lines
        output = [
            *output[: args.max_lines],
            f"... (+{hidden} more lines; pass a subdirectory to narrow scope)",
        ]

    print("\n".join(output))


if __name__ == "__main__":
    main()
