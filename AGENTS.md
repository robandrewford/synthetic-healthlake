# Agent Rules & Guidelines

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json
bd create "Subtask" --parent <epic-id> --json  # Hierarchical subtask (gets ID like epic-id.1)
```

**Claim and update:**

```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit the `.beads/issues.jsonl` file together with the code changes so issue state stays in sync with code state

### Pre-Commit Hooks and Git Workflow

**CRITICAL**: Pre-commit hooks may modify files automatically (formatting, trailing whitespace, etc.)

**Correct workflow when pre-commit hooks modify files:**

```bash
# Attempt to commit
git add <files> && git commit -m "message"

# If pre-commit hooks modify files, they will show "Failed" or "files were modified"
# The commit will NOT complete

# Re-add the modified files
git add <modified-files>

# Commit again (hooks will pass this time)
git commit -m "message"
```

**DO NOT** ignore hook failures or try to bypass them. If hooks modify files:

1. Read the hook output to see which files were modified
2. Re-add those files: `git add <files>`
3. Commit again: `git commit -m "message"`

**Common hooks that modify files:**

- `trailing-whitespace` - Fixes trailing whitespace
- `end-of-file-fixer` - Ensures files end with newline
- `ruff-format` - Auto-formats Python code
- `mixed-line-ending` - Fixes line endings

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### GitHub Copilot Integration

If using GitHub Copilot, also create `.github/copilot-instructions.md` for automatic instruction loading.
Run `bd onboard` to get the content, or see step 2 of the onboard instructions.

### MCP Server (Recommended)

If using Claude or MCP-compatible clients, install the beads MCP server:

```bash
pip install beads-mcp
```

Add to MCP config (e.g., `~/.config/claude/config.json`):

```json
{
  "beads": {
    "command": "beads-mcp",
    "args": []
  }
}
```

Then use `mcp__beads__*` functions instead of CLI commands.

### Managing AI-Generated Planning Documents

AI assistants often create planning and design documents during development:

- PLAN.md, IMPLEMENTATION.md, ARCHITECTURE.md
- DESIGN.md, CODEBASE_SUMMARY.md, INTEGRATION_PLAN.md
- TESTING_GUIDE.md, TECHNICAL_DESIGN.md, and similar files

#### Best Practice: Use a dedicated directory for these ephemeral files

**Recommended approach:**

- Create a `history/` directory in the project root
- Store ALL AI-generated planning/design docs in `history/`
- Keep the repository root clean and focused on permanent project files
- Only access `history/` when explicitly asked to review past planning

**Example .gitignore entry (optional):**

```m
# AI planning documents (ephemeral)
history/
```

**Benefits:**

- Clean repository root
- Clear separation between ephemeral and permanent documentation
- Easy to exclude from version control if desired
- Preserves planning history for archeological research
- Reduces noise when browsing the project

### CLI Help

Run `bd <command> --help` to see all available flags for any command.
For example: `bd create --help` shows `--parent`, `--deps`, `--assignee`, etc.

### Markdown Documentation Standards

**All Markdown (*.md) docs MUST follow these formatting rules.** Violations will cause pre-commit hooks to fail.

#### Required Rules

1. **MD032/blanks-around-lists**: Lists must be surrounded by blank lines
   - Insert a blank line before AND after every list
   - This applies to all list types (unordered `-`, ordered `1.`, and checklists `- [ ]`)
   - Example:

     ```markdown
     This is a paragraph.

     - List item 1
     - List item 2

     This is another paragraph.
     ```

2. **MD036/no-emphasis-as-heading**: Don't use emphasis as headings
   - When using **emphasis** as a heading, start the line with a dash "-"
   - Example: `- **Emphasis Heading**`

3. **MD040/fenced-code-language**: Code blocks must specify a language
   - Always specify the code language after opening backticks
   - Use `text` for plain text, `bash` for shell commands, `json` for JSON, etc.
   - Example: ` ```python ` or ` ```bash ` or ` ```text `

#### Additional Best Practices

4. **Consistent heading levels**: Don't skip heading levels (e.g., don't go from `##` to `####`)

5. **No trailing whitespace**: Lines should not end with spaces

6. **Single trailing newline**: Files should end with exactly one newline

7. **No hard tabs**: Use spaces for indentation (2 or 4 spaces)

8. **Proper list indentation**: Nested lists should be indented consistently (2-4 spaces)

#### Quick Validation

Run this command to check all markdown files:

```bash
uv run pre-commit run markdownlint --all-files
```

### Important Rules

- Use bd for ALL task tracking
- Always use `--json` flag for programmatic use
- Link discovered work with `discovered-from` dependencies
- Check `bd ready` before asking "what should I work on?"
- Store AI planning docs in `history/` directory
- Run `bd <cmd> --help` to discover available flags
- Follow markdown formatting standards (MD032, MD036, MD040)
- Do NOT create markdown TODO lists
- Do NOT use external issue trackers
- Do NOT duplicate tracking systems
- Do NOT clutter repo root with planning documents

For more details, see README.md and QUICKSTART.md.
