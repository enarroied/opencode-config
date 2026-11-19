# opencode-config

Personal configuration, reusable agent skills, slash commands, and custom tools for [OpenCode](https://opencode.ai/).

## Structure

```text
opencode-config/
├── README.md
├── .gitignore
├── opencode.json          # Global model, provider, and permission defaults
├── skills/                # Reusable SKILL.md workflows loaded on demand
│   └── pre-commit-clean-code-review/
│       └── SKILL.md
├── commands/              # Custom slash commands (e.g., /review, /commit)
├── themes/                # Custom themes
└── tools/                 # Custom TypeScript/JavaScript tools and plugins

```


## Setup

Symlink this repository to OpenCode's global configuration directory (`~/.config/opencode`) so changes take effect immediately across all projects:

```bash
REPO=~/path/to/opencode-config
CONF=~/.config/opencode

ln -s "$REPO/skills" "$CONF/skills"
ln -s "$REPO/themes" "$CONF/themes"
ln -s "$REPO/tools" "$CONF/tools"
ln -s "$REPO/agents" "$CONF/agents"
```
