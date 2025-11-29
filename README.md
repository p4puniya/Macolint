# Macolint

A cloud-synced terminal snippet manager that helps developers reuse code faster across machines and teams.

## Features

- Save and retrieve code snippets instantly
- Interactive fuzzy search with tab completion
- Encrypted local storage
- Fast CLI interface

## Installation

```bash
pip3 install -e .
# or
python3 -m pip install -e .
```

### Fixing PATH Issues

If `snip` command is not found after installation, you can automatically fix it:

```bash
# First, diagnose the issue (use Python module syntax if snip isn't in PATH)
python3 -m macolint.cli doctor

# Automatically detect and fix PATH + set up shell wrapper
python3 -m macolint.cli setup --fix-path

# After fixing, reload your shell
source ~/.zshrc  # or ~/.bashrc for bash

# Now snip should work!
snip doctor
```

**Manual options:**

1. **Add Python's bin directory to PATH** (recommended):
   ```bash
   export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH"
   ```
   Add this to your `~/.zshrc` (or `~/.bashrc`) to make it permanent.

2. **Use the full path**:
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/snip [command]
   ```

3. **Use Python module syntax**:
   ```bash
   python3 -m macolint.cli [command]
   ```

## Usage

```bash
snip save <name>          # Save a snippet (supports paths like module1/module2/snippet)
snip save -m <module>     # Create an empty module path (e.g. module1/module2)
snip get [name]           # Retrieve a snippet (paths work here too)
snip get -m [module]      # Open interactive module browser (folder-style navigation)
snip update [name]        # Update snippet content
snip rename <old> <new>   # Rename a snippet
snip rename -m <old> <new> # Rename a module
snip delete [name]        # Delete a snippet
snip delete -m <module>   # Delete a module and all its contents
snip list [keyword]       # List modules and snippets at root level
snip list -m <module>     # List contents of a specific module
snip setup                # Automatically set up shell wrapper (recommended!)
snip setup --fix-path     # Also fix PATH if snip command not found
snip doctor               # Diagnose installation issues
```

### Module examples

- Save inside a nested module:
  - `snip save git/commit/template`
  - `snip save` (interactive: browse modules and select location)
- Fetch directly by path:
  - `snip get git/commit/template`
- Browse within modules:
  - `snip get -m` (start at root)
  - `snip get -m git` (start inside `git`)
  - Select entries ending with `/` to enter sub-modules.
  - Press `Esc` to go up one level, or exit when at the root.
- List module contents:
  - `snip list` (shows root level: modules with `/` and top-level snippets)
  - `snip list -m module1` (shows contents of `module1`)
  - `snip list -m module1/module2` (shows contents of nested module)
- Rename snippets and modules:
  - `snip rename old_name new_name` (rename snippet)
  - `snip rename module1/snippet new_name` (rename snippet in module)
  - `snip rename -m module1 module2` (rename module)
  - `snip rename -m module1/sub module1/new_sub` (rename nested module)

## Shell Wrapper Setup (Recommended)

For the best experience, set up the shell wrapper so that `snip get <name>` automatically places the snippet content in your command line buffer, ready to edit and execute.

### Automatic Setup (Easiest)

Simply run:

```bash
snip setup
```

This will:
- Auto-detect your shell (bash, zsh, or fish)
- Add the wrapper function to your shell config file
- Automatically update if an outdated version is detected
- Provide instructions to reload your shell

You can also specify a shell manually:

```bash
snip setup --shell zsh    # For zsh
snip setup --shell bash   # For bash
snip setup --shell fish   # For fish
```

**Updating an existing installation:**

The `snip setup` command automatically detects and updates outdated wrappers. You can also force an update:

```bash
snip setup --force    # Force update even if already installed
```

### Manual Setup

If you prefer to set it up manually:

### Zsh (macOS default)

Add to your `~/.zshrc`:

```bash
source /path/to/macolint/shell-wrappers/zsh.sh
```

Or copy the contents directly:

```bash
snip() {
  if [ "$1" = "get" ] && [ -n "$2" ]; then
    local cmd
    cmd=$(command snip get "$2" --raw 2>/dev/null) || return
    print -z "$cmd"
  else
    command snip "$@"
  fi
}
```

Then reload: `source ~/.zshrc`

### Bash

Add to your `~/.bashrc`:

```bash
source /path/to/macolint/shell-wrappers/bash.sh
```

Or copy the contents directly:

```bash
snip() {
  if [ "$1" = "get" ] && [ -n "$2" ]; then
    local cmd
    cmd=$(command snip get "$2" --raw 2>/dev/null) || return
    history -s "$cmd"
  else
    command snip "$@"
  fi
}
```

Then reload: `source ~/.bashrc`

**Note:** In Bash, the snippet will be added to history. Press **Up arrow** after running `snip get <name>` to retrieve it.

### Fish

Add to your `~/.config/fish/config.fish`:

```fish
source /path/to/macolint/shell-wrappers/fish.fish
```

Or copy the contents directly:

```fish
function snip
    if [ "$argv[1]" = "get" ] && [ -n "$argv[2]" ]
        set cmd (command snip get "$argv[2]" --raw 2>/dev/null)
        if test $status -eq 0
            commandline --replace $cmd
        end
    else
        command snip $argv
    end
end
```

### How It Works

After setup, when you run:

```bash
$ snip get deploy_staging
```

The snippet content (e.g., `git push origin HEAD`) will automatically appear in your command line, ready to edit and execute. Just press **Enter** to run it, or edit it first.

**Note:** The `snip setup` command is idempotent and smart:
- It detects if the wrapper is already installed
- It automatically detects and updates outdated versions
- You can force an update with `--force` flag
- Safe to run multiple times - won't duplicate entries

## MVP Status

Currently supports local storage with encryption. Cloud sync and team sharing coming in Phase 2.

