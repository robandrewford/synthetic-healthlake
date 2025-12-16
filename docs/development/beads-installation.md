# Beads (bd) CLI Installation Guide

This guide provides reproducible installation instructions for the `bd` CLI tool used for issue tracking in this project.

## What is Beads?

Beads (bd) is a Git-friendly, dependency-aware issue tracker that syncs to JSONL files. It's used in this project for ALL task tracking and issue management.

**Repository**: [github.com/steveyegge/beads](https://github.com/steveyegge/beads)

## Installation Methods

### Quick Install (Recommended)

#### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
```

This will:
- Detect your platform automatically
- Download the latest release
- Install to `~/.local/bin/bd`
- Re-sign the binary for macOS (if applicable)

#### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/steveyegge/beads/main/install.ps1 | iex
```

### Alternative Methods

#### npm (Node.js environments)

```bash
npm install -g @beads/bd
```

#### Go Install (if you have Go installed)

```bash
go install github.com/steveyegge/beads/cmd/bd@latest
```

**Important**: Add Go binaries to your PATH:

```bash
export PATH="$PATH:$HOME/go/bin"
```

Add this to your `~/.zshrc` or `~/.bashrc` to make it permanent.

#### Homebrew (macOS) - Coming Soon

```bash
# Not yet available, use quick install above
brew install steveyegge/tap/bd
```

## Verification

After installation, verify it works:

```bash
# Check version
bd --version

# Should output something like:
# bd version 0.30.0 (bc3e8f63)

# Check project status
cd /path/to/synthetic-healthlake
bd status
```

Expected output:
```
Issue Database Status
=====================

Summary:
  Total Issues:      XX
  Open:              XX
  In Progress:       X
  Blocked:           X
  Closed:            XX
  Ready to Work:     XX
```

## Troubleshooting

### Command Not Found

If you get `bd: command not found`, add the installation directory to your PATH:

```bash
# For quick install method
export PATH="$PATH:$HOME/.local/bin"

# For Go install method
export PATH="$PATH:$HOME/go/bin"

# For npm install method (usually auto-added)
export PATH="$PATH:$(npm config get prefix)/bin"
```

Make it permanent by adding to your shell config:

```bash
# For zsh (macOS default)
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.zshrc
source ~/.zshrc

# For bash
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

### macOS Security Warning

If you see "bd cannot be opened because the developer cannot be verified":

The quick install script automatically re-signs the binary. If you installed another way:

```bash
xattr -cr ~/.local/bin/bd
```

Or use the quick install script which handles this automatically.

### Permission Denied

If you get permission errors:

```bash
chmod +x ~/.local/bin/bd
```

## Quick Start with This Project

Once installed, get started:

```bash
# View ready work
bd ready

# View all issues
bd list

# Create a new issue
bd create "Task description" -t task -p 1

# View a specific issue
bd show bd-XXX

# Update an issue
bd update bd-XXX --status in_progress

# Close an issue
bd close bd-XXX --reason "Completed"
```

## Git Integration

The project already has Git hooks configured. When you commit:

```bash
git commit -m "Your commit message"
```

The pre-commit hook will automatically flush beads state, syncing the `.beads/issues.jsonl` file.

**Important**: Always commit the `.beads/issues.jsonl` file with your code changes to keep issue state in sync.

## MCP Server (Optional - For Claude Desktop)

If using Claude Desktop, you can install the beads MCP server for enhanced integration:

```bash
pip install beads-mcp
```

Add to `~/.config/claude/config.json`:

```json
{
  "mcpServers": {
    "beads": {
      "command": "beads-mcp",
      "args": []
    }
  }
}
```

## Reference Projects

- **Beads Repository**: [github.com/steveyegge/beads](https://github.com/steveyegge/beads)
- **Reference Implementation**: [github.com/robandrewford/enterprise_vibe_code](https://github.com/robandrewford/enterprise_vibe_code)

## See Also

- [AGENTS.md](../../AGENTS.md) - Full bd workflow documentation for this project
- [scripts/beads-helpers/README.md](../../scripts/beads-helpers/README.md) - Helper scripts and utilities
- [Beads Official Docs](https://github.com/steveyegge/beads#readme) - Complete beads documentation

## Support

For issues with beads itself, see:
- [Beads GitHub Issues](https://github.com/steveyegge/beads/issues)
- [Beads Examples](https://github.com/steveyegge/beads/tree/main/examples)
