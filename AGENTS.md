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

```gitignore
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

4. **MD024/no-duplicate-heading**: Headings must be unique
   - No two headings in the document can have identical text
   - Use unique, descriptive heading names to differentiate sections
   - Example: Instead of two "#### Quick Validation", use "#### Markdown Validation" and "#### YAML Validation"

#### Additional Best Practices

1. **Consistent heading levels**: Don't skip heading levels (e.g., don't go from `##` to `####`)

2. **No trailing whitespace**: Lines should not end with spaces

3. **Single trailing newline**: Files should end with exactly one newline

4. **No hard tabs**: Use spaces for indentation (2 or 4 spaces)

5. **Proper list indentation**: Nested lists should be indented consistently (2-4 spaces)

#### Markdown Validation

Run this command to check all markdown files:

```bash
uv run pre-commit run markdownlint --all-files
```

<!-- <new-rule-1> -->

### MECE Markdownlint Compliance Checklist

**CRITICAL**: This checklist is MECE (Mutually Exclusive, Collectively Exhaustive) and covers ALL common markdownlint violations. Follow this checklist when writing ANY markdown documentation.

#### Pre-Write Checklist (Structure)

Before writing markdown content, plan:

- [ ] **Document structure**: Outline heading hierarchy (H1 → H2 → H3, no skipping)
- [ ] **Unique headings**: Ensure all headings have unique text within the document
- [ ] **Section boundaries**: Plan blank lines between all structural elements

#### During-Write Checklist (Content)

While writing, apply these rules:

- **Headings**
  - [ ] Use ATX-style headings (`#`, `##`, `###`) not Setext-style
  - [ ] Include exactly one space after `#` symbols
  - [ ] Never skip heading levels (don't go from `##` to `####`)
  - [ ] Ensure heading text is unique in the document (MD024)
  - [ ] Don't use trailing punctuation in headings (except `?`)

- **Lists (MD032 - MOST COMMON VIOLATION)**
  - [ ] **ALWAYS** insert a blank line BEFORE the first list item
  - [ ] **ALWAYS** insert a blank line AFTER the last list item
  - [ ] This applies to ALL list types: unordered (`-`), ordered (`1.`), checklists (`- [ ]`)
  - [ ] Pattern: `paragraph → blank → list → blank → paragraph`

  ```markdown
  <!-- CORRECT -->
  Here is some text.

  - Item 1
  - Item 2

  More text here.

  <!-- INCORRECT -->
  Here is some text.
  - Item 1
  - Item 2
  More text here.
  ```

- **Nested Lists**
  - [ ] Use consistent indentation (2 spaces recommended)
  - [ ] Blank lines not required between nested levels within the same list
  - [ ] Blank lines required before/after the entire list block

- **Code Blocks (MD040)**
  - [ ] **ALWAYS** specify language after opening backticks
  - [ ] Use `text` for plain output, `bash` for shell, `json` for JSON, etc.
  - [ ] Pattern: ` ```language ` never just ` ``` `

  ```markdown
  <!-- CORRECT -->
  ```bash
  echo "hello"
  ```

  <!-- INCORRECT -->
  ```
  echo "hello"
  ```
  ```

- **Emphasis (MD036)**
  - [ ] Don't use bold/italic as pseudo-headings
  - [ ] If emphasis looks like a heading, make it a real heading or prefix with `- `
  - [ ] Pattern: `- **Emphasis Heading**` not `**Emphasis Heading**`

- **Links and References**
  - [ ] Use proper link syntax `[text](url)`
  - [ ] Reference-style links must have matching definitions
  - [ ] No empty links or link text

- **Tables**
  - [ ] Include header row separator (`|---|---|`)
  - [ ] Consistent column counts across all rows
  - [ ] Surround with blank lines

- **Whitespace**
  - [ ] No trailing spaces on any line
  - [ ] No hard tabs (use spaces only)
  - [ ] Single newline at end of file
  - [ ] No multiple consecutive blank lines

#### Post-Write Checklist (Validation)

After writing, validate:

- [ ] Run `uv run pre-commit run markdownlint --files <your-file.md>`
- [ ] Fix ALL reported errors before committing
- [ ] Re-run validation to confirm fixes
- [ ] If errors persist, check this checklist item-by-item

#### Quick Reference: Common Violations → Fixes

| Rule | Error Message | Fix |
|------|---------------|-----|
| MD032 | Lists should be surrounded by blank lines | Add blank line before AND after list |
| MD040 | Fenced code blocks should have a language | Add `bash`, `python`, `json`, `text`, etc. |
| MD036 | Emphasis used instead of heading | Use real heading or prefix with `- ` |
| MD024 | Multiple headings with same content | Make heading text unique |
| MD022 | Headings should be surrounded by blank lines | Add blank line before AND after heading |
| MD031 | Fenced code blocks should be surrounded by blank lines | Add blank line before AND after code block |
| MD047 | Files should end with a single newline | Ensure exactly one `\n` at EOF |
| MD009 | Trailing spaces | Remove spaces at end of lines |
| MD010 | Hard tabs | Replace tabs with spaces |
| MD001 | Heading levels should only increment by one | Don't skip heading levels |

#### Cognitive Pattern for Markdown Writing

Apply this mental model: **"Every block needs breathing room"**

1. **Heading?** → blank before, blank after
2. **List?** → blank before, blank after
3. **Code block?** → blank before, blank after, specify language
4. **Table?** → blank before, blank after
5. **Between sections?** → blank line separates them

<!-- </new-rule-1> -->

### YAML and OpenAPI Standards

**All YAML files MUST pass schema validation.** OpenAPI specification files have additional requirements.

#### Required Rules for YAML Files

1. **Valid YAML syntax**: Proper indentation (2 spaces), no tabs, correct key-value formatting

2. **No typos in root-level keys**: Critical keys like `openapi`, `info`, `paths` must be spelled exactly correct
   - Common mistake: `eopenapi` instead of `openapi` (extra character)
   - Schema validators will report "Missing property" and "Property X is not allowed"

3. **Schema compliance**: Files with associated JSON schemas (like OpenAPI) must conform to the schema

#### OpenAPI-Specific Requirements

1. **Required root properties** (OpenAPI 3.0.x):
   - `openapi`: Version string (e.g., `"3.0.3"`)
   - `info`: Object with `title` and `version`
   - `paths`: Object containing API endpoints

2. **Operation requirements**: Each path operation should have:
   - `responses`: At least one response defined
   - `operationId`: Unique identifier (recommended)
   - `tags`: Array for grouping (recommended)

3. **Reference validation**: All `$ref` references must point to existing definitions

#### YAML Validation

Run this command to check YAML files:

```bash
uv run pre-commit run check-yaml --all-files
```

For comprehensive OpenAPI validation, use specialized tools:

```bash
# Install spectral for OpenAPI linting
npm install -g @stoplight/spectral-cli

# Validate OpenAPI spec
spectral lint docs/api/openapi.yaml
```

#### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Missing property 'openapi'" | Typo in key name | Check spelling of `openapi:` |
| "Property X is not allowed" | Typo or extra character | Remove typo, verify key names |
| "Array does not contain required item" | Missing required array element | Add required items to array |
| "$ref not found" | Broken reference path | Verify referenced component exists |

### Mandatory Verification Before Task Completion

**CRITICAL**: Before closing ANY task or claiming work is complete, you MUST verify it actually works. NO SHORTCUTS.

#### Verification Requirements

1. **Test the actual change** - Don't assume it works; prove it works
2. **Run in a clean environment** - If fixing shell/env issues, test in a NEW shell session
3. **Capture evidence** - Show output proving success, not just absence of errors
4. **End-to-end validation** - Test the full workflow, not just individual components

#### Verification Examples

- **Code changes**: Run the code and verify output
- **Configuration fixes**: Source the config in a fresh environment
- **Infrastructure changes**: Deploy and test the actual resources
- **Documentation**: Validate with linters AND review renders correctly

#### What NOT To Do

- ❌ Claim "it will work in a new terminal" without testing
- ❌ Run partial tests and assume the rest works
- ❌ Close tasks based on successful command execution without checking results
- ❌ Skip verification because "it should work"

#### What TO Do

- ✅ Open a new shell/environment and verify the fix
- ✅ Run the complete workflow end-to-end
- ✅ Show concrete output proving success
- ✅ If something can't be fully tested, explicitly document what was verified and what wasn't

**If you cannot fully verify a change, do NOT close the task. Document what was done and what remains to be verified.**

### Important Rules

- Be thorough and accurate when fixing reported errors - do not be sloppy, comprehensively assess all issues before attempting completion
- **VERIFY your work actually works before claiming completion** - no shortcuts
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
