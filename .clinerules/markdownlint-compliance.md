# Claude Skill: Markdownlint Compliance

This skill ensures ALL markdown documentation passes markdownlint validation.

## When to Apply

Apply this skill whenever:

- Creating new markdown files (*.md)
- Modifying existing markdown files
- Writing documentation in any form

## Core Rule: "Every Block Needs Breathing Room"

When writing markdown, apply this mental model:

| Element | Rule |
|---------|------|
| Heading | Blank line before AND after |
| List | Blank line before AND after |
| Code block | Blank line before AND after, MUST specify language |
| Table | Blank line before AND after |
| Paragraph | Blank line separates from other elements |

## Quick Checklist

### Before Writing

- [ ] Plan heading hierarchy (H1 → H2 → H3, no skipping)
- [ ] Ensure all headings will be unique

### During Writing

- [ ] **MD032**: Blank line before/after EVERY list
- [ ] **MD040**: Always specify code block language (```bash, ```python, ```text)
- [ ] **MD024**: No duplicate heading text
- [ ] **MD036**: Don't use emphasis as headings (use `- **text**` instead)
- [ ] **MD001**: Don't skip heading levels

### After Writing

- [ ] Run: `uv run pre-commit run markdownlint --files <file.md>`
- [ ] Fix ALL errors before committing
- [ ] Re-validate after fixes

## Most Common Violations

### MD032: Lists Need Blank Lines

```markdown
<!-- WRONG -->
Some text.
- Item 1
- Item 2
More text.

<!-- CORRECT -->
Some text.

- Item 1
- Item 2

More text.
```

### MD040: Code Blocks Need Language

```markdown
<!-- WRONG -->
```
code here
```

<!-- CORRECT -->
```bash
code here
```
```

### MD036: Emphasis as Heading

```markdown
<!-- WRONG -->
**This is a pseudo-heading**

Content here.

<!-- CORRECT -->
- **This is a pseudo-heading**

Content here.

<!-- OR BETTER -->
### This is a real heading

Content here.
```

## Validation Command

```bash
# Single file
uv run pre-commit run markdownlint --files docs/your-file.md

# All files
uv run pre-commit run markdownlint --all-files
```

## Remember

**DO NOT** use `attempt_completion` until markdownlint passes on ALL modified markdown files.
