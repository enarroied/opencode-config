---
name: repo-map
description: Generate a compact structural skeleton of the repository (files, classes, function signatures, type annotations) without reading full source files. Trigger when exploring an unfamiliar codebase, locating where logic lives, or planning changes across multiple modules.
---

# Repo Map

## Workflow
1. Run `~/.config/opencode/skills/repo-map/scripts/repo_map.py` via bash (optionally pass a subdirectory like `src/` or `--include-private` if internal helpers are needed).
2. Use the returned module and signature map to identify the exact 1–3 files relevant to the user's request.
3. Read **only** those target files in full before making edits—avoid broad `grep` or recursive file reads unless searching for non-Python assets (SQL, templates, configs).
