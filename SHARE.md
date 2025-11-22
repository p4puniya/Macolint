# Macolint - Terminal Snippet Manager

**Save, search, and retrieve code snippets directly from your terminal.**

## Install (One Command)

```bash
brew tap p4puniya/macolint && brew install macolint
```

## Quick Usage

### Save a snippet
```bash
# From clipboard
snip save deploy-prod

# With content
snip save deploy-prod "kubectl apply -f deployment.yaml"
```

### List snippets
```bash
snip list
```

### Get snippet (copies to clipboard)
```bash
# By name
snip get deploy-prod

# Fuzzy search (interactive)
snip get
```

## Example Workflow

```bash
# 1. Copy command to clipboard
echo "docker-compose up -d" | pbcopy

# 2. Save it
snip save docker-up

# 3. Later, get it instantly
snip get docker-up
# Now paste anywhere (Cmd+V)
```

## Features

- ✅ Encrypted storage (AES-256-GCM)
- ✅ Fuzzy search (fzf integration)
- ✅ Works with any text (commands, notes, configs)
- ✅ Fast and lightweight

**GitHub**: https://github.com/p4puniya/macolint

