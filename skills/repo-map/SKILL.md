---
name: repo-map
description: Map a Python repository's structure (modules, classes, function and method signatures, annotations) without reading full source. Python files only; use grep or file listing for SQL, templates, and configs. Trigger when exploring an unfamiliar Python codebase, locating where logic lives, or planning changes across Python modules.
---

# Repo Map

## Workflow
1. Run `~/.config/opencode/skills/repo-map/scripts/repo_map.py` via bash (optionally pass a subdirectory like `src/` or `--include-private` if internal helpers are needed).
2. Use the returned module and signature map to identify the exact 1–3 files relevant to the user's request.
3. Read **only** those target files in full before making edits—avoid broad `grep` or recursive file reads unless searching for non-Python assets (SQL, templates, configs).
