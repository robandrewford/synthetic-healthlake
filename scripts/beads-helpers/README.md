# Beads Helper Scripts

This directory contains useful scripts from the [beads examples](../../beads/examples/) collection, adapted for this project.

## Available Scripts

### 1. `bd-version-check.sh` - Automatic BD Upgrade Detection

Detects when `bd` (beads) has been upgraded and shows what changed, helping AI agents adapt their workflows.

**Usage:**

```bash
# Source at session start (recommended)
source scripts/beads-helpers/bd-version-check.sh

# Or execute directly
bash scripts/beads-helpers/bd-version-check.sh
```

**Integration with shell:**

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Auto-detect bd upgrades when entering beads projects
if [ -d ".beads" ]; then
  source /path/to/synthetic-healthlake/scripts/beads-helpers/bd-version-check.sh
fi
```

### 2. `md2jsonl.py` - Markdown to BD Issues Converter

Converts markdown planning documents (like ACTION_PLAN.md) into bd issues.

**Usage:**

```bash
# Convert ACTION_PLAN.md to bd issues
python scripts/beads-helpers/md2jsonl.py ACTION_PLAN.md | bd import

# Preview first
python scripts/beads-helpers/md2jsonl.py ACTION_PLAN.md | jq .

# Save to file
python scripts/beads-helpers/md2jsonl.py ACTION_PLAN.md > history/action-plan-issues.jsonl
bd import -i history/action-plan-issues.jsonl
```

### 3. `example-feature.md` - Example Markdown Format

Example of how to format markdown files for conversion to bd issues. Use as a template.

## Other Useful Examples (Not Copied)

These examples are available in `beads/examples/` if needed:

| Example | Description | When to Use |
|---------|-------------|-------------|
| `monitor-webui/` | Web dashboard for issue visualization | When you want a visual UI for tracking |
| `multi-phase-development/` | Patterns for phased projects | Reference for organizing 8-phase projects like this one |
| `python-agent/` | Python agent for autonomous work | For CI/CD automation |
| `bash-agent/` | Bash agent for task processing | For simple automation scripts |

## Already Configured

The following are already set up in this project:

- ✅ **Git hooks** - Pre-commit, pre-push, post-merge, post-checkout
- ✅ **Beads daemon** - Running for auto-sync
- ✅ **AGENTS.md** - BD workflow documentation

## Building the Monitor WebUI (Optional)

If you want a visual dashboard:

```bash
cd beads/examples/monitor-webui
go build
./monitor-webui -port 8080
# Open http://localhost:8080
```

## Quick Reference

```bash
# Check ready work
bd ready --json

# Create issue with description
bd create "Issue title" --description="Details" -t task -p 1 --json

# Link discovered work
bd create "Found bug" --description="Details" -t bug -p 1 --deps discovered-from:bd-xxx --json

# View dependency tree
bd dep tree bd-xxx

# Sync at end of session
bd sync
```

## See Also

- [AGENTS.md](../../AGENTS.md) - Full bd workflow documentation
- [beads/docs/](../../beads/docs/) - Complete beads documentation
- [beads/examples/](../../beads/examples/) - All available examples
