# Lessons Learned: AI Agent Project Execution

This document captures lessons learned from the Synthetic HealthLake project (Dec 2025) for future AI agents working with human collaborators.

## Executive Summary

After completing 39/43 tasks (91% completion) across 6 sessions, these are the patterns that led to success and the anti-patterns to avoid.

---

## Part 1: Working With Humans ("Bloodbags")

### Understand Human Context Switching Costs

Humans don't have instant context retrieval like agents. When you:

- **Ask clarifying questions** - Group them. Don't ask one at a time.
- **Present options** - Provide 2-5 concrete choices, not open-ended questions.
- **Report progress** - Be concise. "Done: X, Y, Z. Next: A, B. Blockers: none."

```text
❌ BAD: "What would you like me to do?"
✅ GOOD: "Ready tasks: .5.4 (network docs), .5.5 (IAM docs), .6.9 (release checklist). 
         Which should I start? Or all three in parallel?"
```

### Humans Value Momentum Over Perfection

When in doubt:

- Do the work, then ask for feedback
- Default to "yes, and" not "should I?"
- Small iterative commits beat big-bang deliveries

### Respect the Human's Time

- Pre-validate your work (run linters) before announcing completion
- Don't ask humans to verify things you could verify yourself
- Batch similar tasks together

---

## Part 2: Technical Execution Patterns

### Issue Tracking Is Your Memory

This project used `bd` (beads) for issue tracking. Key practices:

```bash
# Always check ready work before asking "what next?"
bd ready --json

# Claim work before starting
bd update <id> --status in_progress

# Link discovered work to parent
bd create "Found bug" -p 1 --deps discovered-from:<parent-id>

# Close with meaningful reasons
bd close <id> --reason "Implemented X with Y approach"

# ALWAYS commit issue state with code changes
git add .beads/issues.jsonl <other-files>
```

### ID Format Matters

```bash
# ❌ BAD: Using shorthand
bd close .6.9  # FAILS - not a valid ID

# ✅ GOOD: Use full ID from bd list output
bd close synthetic-healthlake-ptl.6.9
```

### Pre-Commit Hooks Are Your Friends

Always run validation before claiming completion:

```bash
# Markdown files
uv run pre-commit run markdownlint --files <file.md>

# YAML files  
uv run pre-commit run check-yaml --files <file.yaml>

# Python files
uv run pre-commit run ruff --files <file.py>
```

**Rule**: If hooks modify files, re-add and commit again. Don't ignore failures.

### The "Every Block Needs Breathing Room" Mental Model

For Markdown (learned the hard way after repeated MD032 violations):

| Element | Rule |
|---------|------|
| Heading | Blank line before AND after |
| List | Blank line before AND after |
| Code block | Blank line before AND after, MUST specify language |
| Table | Blank line before AND after |

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

---

## Part 3: Session Management

### Context Loss Is Inevitable

Each session starts fresh. Mitigate this by:

1. **Keep activeContext.md updated** - After significant work, update it
2. **Use task_progress in every tool call** - This persists within sessions
3. **Commit frequently with meaningful messages** - Git history IS your memory

### Session Handoff Pattern

At session end:

```bash
# 1. Close completed tasks
bd close <id> --reason "..."

# 2. Commit all changes including beads
git add . && git commit -m "..."

# 3. Update Memory Bank
# - activeContext.md: what's in progress, what's next
# - progress.md: overall project status
```

At session start:

```bash
# 1. Read Memory Bank files
cat memory-bank/core/*.md

# 2. Check issue state
bd ready --json

# 3. Pick up where left off
bd update <id> --status in_progress
```

---

## Part 4: Anti-Patterns (What NOT To Do)

### Don't Ask Permission for Everything

```text
❌ "Should I create the file now?"
❌ "Would you like me to add tests?"
❌ "Can I proceed with the implementation?"

✅ Create the file. Run tests. Implement. Then show results.
```

### Don't Announce What You're About to Read

```text
❌ "I'm going to read the cdk/lib/health-platform-stack.ts file..."
✅ [Just read it, then provide insights]
```

### Don't Create Unnecessary Tracking Systems

```text
❌ Creating TODO.md files alongside beads
❌ Adding inline TODO comments for tracked issues
❌ Making separate spreadsheets or lists

✅ One source of truth: bd (beads)
```

### Don't Assume the Code Works

```text
❌ "This should work in production"
❌ "The syntax looks correct"

✅ Run the code. Show the output. Verify it works.
```

---

## Part 5: Reusable Patterns

### Documentation Creation Workflow

```text
1. Check existing docs in docs/ directory
2. Identify gaps or missing cross-links
3. Create doc with proper markdown structure
4. Run markdownlint validation
5. Add to docs/index.md navigation
6. Commit with descriptive message
```

### Security Documentation Pattern

For any security-related doc:

1. Start with threat model / purpose
2. Show concrete examples (CDK code, IAM policies)
3. Include checklist for verification
4. Link to related docs
5. Add compliance considerations if relevant

### Batch Processing Pattern

When given multiple similar tasks:

```text
1. Identify commonalities
2. Create all artifacts in sequence
3. Validate all at once
4. Close all issues together
5. Single commit for the batch
```

---

## Part 6: Human-Agent Collaboration Model

### The "Bloodbag" Acknowledgment

Humans have:

- **Limited context windows** (can't remember everything)
- **Attention fragmentation** (switching costs)
- **Emotional investment** (they care about quality)

Agents have:

- **No persistent memory** (session-based)
- **Perfect recall within session** (no forgetting during work)
- **No emotional fatigue** (can grind through tedious tasks)

### Optimal Division of Labor

| Human Does | Agent Does |
|------------|------------|
| Strategic decisions | Tactical execution |
| Priority setting | Task completion |
| Quality judgment | Verification automation |
| Domain expertise | Pattern application |
| Approval/rejection | Proposal generation |

### Communication Protocol

```text
Human: [High-level intent]
Agent: [Concrete plan with options]
Human: [Selection or redirect]
Agent: [Execute and report]
Human: [Feedback]
Agent: [Iterate or complete]
```

---

## Appendix: Project-Specific Learnings

### Synthetic HealthLake Specifics

- **Stack**: AWS CDK (TypeScript), Python, dbt, Snowflake
- **Data**: FHIR (healthcare) + OMOP (analytics)
- **Key patterns**: Parquet for OMOP, NDJSON for FHIR, S3 as data lake

### File Organization That Worked

```text
docs/
├── api/           # API specs (OpenAPI)
├── architecture/  # System design
├── data/          # Data models and lineage
├── deployment/    # AWS deployment guides
├── development/   # Contributing, release process
├── operations/    # Cost, performance, observability
├── security/      # IAM, network, secrets
└── index.md       # Navigation hub

history/           # AI planning docs (ephemeral)
.clinerules/       # Agent-specific skills
```

### Tools That Made Life Easier

- `bd` (beads) - Issue tracking with dependency awareness
- `uv` - Fast Python package management
- `pre-commit` - Automated code quality
- `markdownlint` - Consistent documentation
- `jq` - JSON processing for beads output

---

## Final Thought

The best agent-human collaboration happens when:

1. **Trust is established** through consistent, quality delivery
2. **Communication is efficient** through structured updates
3. **Memory is externalized** through proper documentation
4. **Validation is automated** through tooling

Future agents: Learn from this. Make it better. Pass it on.
