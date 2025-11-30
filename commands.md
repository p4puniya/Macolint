# Macolint Commands Reference

Complete reference for all Macolint commands with all possible use cases.

## Table of Contents

- [save](#save) - Save snippets or create modules
- [get](#get) - Retrieve snippets
- [edit](#edit) - Edit snippet content
- [update](#update) - Update Macolint to latest version
- [rename](#rename) - Rename snippets or modules
- [delete](#delete) - Delete snippets or modules
- [list](#list) - List snippets and modules
- [setup](#setup) - Set up shell wrapper
- [doctor](#doctor) - Diagnose installation issues

---

## save

Save a snippet or create an empty module.

### Syntax

```bash
snip save [NAME] [-m|--module MODULE_PATH]
```

### Use Cases

#### 1. Save a snippet with a name (root level)
```bash
snip save my_snippet
```
- Prompts for snippet content
- Saves at root level as `my_snippet`

#### 2. Save a snippet in a module (using path)
```bash
snip save module1/snippet_name
snip save module1/module2/nested_snippet
```
- Automatically creates missing modules in the path
- Prompts for snippet content
- Saves at the specified module path

#### 3. Interactive save (browse modules)
```bash
snip save
```
- Opens interactive module browser
- Navigate through modules by selecting entries ending with `/`
- Type a snippet name to save at current location
- Press `Esc` to go up one level or exit

**Interactive workflow:**
```
Save in: /
Select a module (ends with '/') or type a snippet name
> module1/              # Enter module1

Save in: module1
Select a module (ends with '/') or type a snippet name
> new_module/          # Creates new_module and enters it

Created module 'module1/new_module'
Save in: module1/new_module
Select a module (ends with '/') or type a snippet name
> my_snippet           # Save snippet here

Enter the snippet here...
> echo "hello"
Snippet 'module1/new_module/my_snippet' saved successfully.
```

#### 4. Create an empty module
```bash
snip save -m module1
snip save -m module1/module2
snip save -m module1/module2/module3
```
- Creates the module path (and parent modules if needed)
- Does not prompt for snippet content
- Useful for organizing structure before adding snippets

**Note:** Cannot use `-m` flag together with a snippet name.

---

## get

Retrieve a snippet by name or browse modules interactively.

### Syntax

```bash
snip get [NAME] [--raw] [--interactive-name] [-m|--module [MODULE_PATH]]
```

### Use Cases

#### 1. Get snippet by name (root level)
```bash
snip get my_snippet
```
- Retrieves and displays snippet content
- Works with full paths: `snip get module1/snippet_name`

#### 2. Get snippet by full path
```bash
snip get module1/snippet_name
snip get module1/module2/nested_snippet
```
- Directly retrieves snippet from nested modules

#### 3. Interactive get (fuzzy search)
```bash
snip get
```
- Shows interactive prompt with fuzzy search
- Type to filter snippets
- Tab completion available
- Select snippet to retrieve

#### 4. Browse modules interactively
```bash
snip get -m
snip get -m module1
snip get -m module1/module2
```
- Opens interactive module browser
- Shows modules (with `/` suffix) and snippets in current location
- Select a module to enter it
- Select a snippet to retrieve it
- Press `Esc` to go up one level
- Press `Esc` at root to exit

**Interactive browser workflow:**
```
Module: /
> module1/              # Enter module1

Module: module1
> module2/              # Enter module2

Module: module1/module2
> snippet_name          # Retrieve this snippet
```

#### 5. Raw output (for shell wrapper)
```bash
snip get my_snippet --raw
```
- Outputs snippet content without newline
- Used internally by shell wrapper
- Not typically used directly

#### 6. Interactive name only (for shell wrapper)
```bash
snip get --interactive-name
```
- Shows interactive prompt
- Outputs only the selected snippet name (no content)
- Used internally by shell wrapper
- Not typically used directly

**Note:** Cannot combine `-m` with `--raw` or `--interactive-name`.

---

## edit

Edit the content of an existing snippet.

### Syntax

```bash
snip edit [NAME]
```

### Use Cases

#### 1. Edit snippet by name
```bash
snip edit my_snippet
snip edit module1/snippet_name
```
- Retrieves existing snippet content
- Opens editor with existing content as default
- Save changes or press `Esc` to cancel

#### 2. Interactive edit
```bash
snip edit
```
- Shows interactive prompt to select snippet
- Fuzzy search and tab completion available
- Then prompts for new content

**Note:** `edit` only works for snippets, not modules. Use `rename` to rename modules.

---

## update

Update Macolint to the latest version from GitHub.

### Syntax

```bash
snip update
```

### Use Cases

#### 1. Check and update to latest version
```bash
snip update
```

**What it does:**
1. Checks your current installed version
2. Fetches the latest version from GitHub (from releases or main branch)
3. Compares versions
4. If an update is available, prompts for confirmation
5. Upgrades using pip: `pip install --upgrade git+https://github.com/p4puniya/Macolint.git`

**Example output:**
```
Current version: 0.1.0
Checking for updates on GitHub...
Latest version available: 0.2.0
Update from 0.1.0 to 0.2.0? [Y/n]: y
Updating Macolint...
Macolint updated successfully!
You may need to reload your shell or restart your terminal.
```

**Notes:**
- Requires internet connection to check GitHub
- Requires pip to be installed and accessible
- If already on latest version, shows a message and exits
- After update, you may need to reload your shell or restart your terminal

---

## rename

Rename a snippet or module, or move it to a different location.

### Syntax

```bash
snip rename [OLD_PATH] [NEW_PATH] [-m|--module]
```

### Use Cases

#### 1. Rename snippet at root level
```bash
snip rename old_name new_name
```
- Renames snippet from `old_name` to `new_name`
- Stays at root level

#### 2. Rename snippet in module
```bash
snip rename module1/old_name new_name
snip rename module1/old_name module1/new_name
```
- Renames snippet within the same module
- Can also move to different module: `snip rename module1/old module2/new`

#### 3. Move snippet between modules
```bash
snip rename module1/snippet_name module2/snippet_name
snip rename root_snippet module1/moved_snippet
```
- Moves snippet to different module
- Module paths are created automatically if needed

#### 4. Rename module
```bash
snip rename -m module1 module2
snip rename -m module1/sub module1/new_sub
```
- Renames module (use `-m` flag)
- All child modules and snippets automatically reflect new path
- Can move module to different parent: `snip rename -m module1/sub module2/moved_sub`

#### 5. Interactive rename
```bash
snip rename
snip rename -m
```
- Prompts for old path (shows list to select from)
- Prompts for new path
- Auto-detects if old path is a module (shows warning if `-m` not used)

**Examples:**
```bash
# Rename snippet
snip rename old_snippet new_snippet
snip rename module1/snippet new_name

# Rename module
snip rename -m old_module new_module
snip rename -m module1/sub module1/renamed_sub

# Move snippet to different module
snip rename root_snippet module1/moved_snippet

# Move module to different parent
snip rename -m module1/sub module2/moved_sub
```

---

## delete

Delete a snippet or an entire module tree.

### Syntax

```bash
snip delete [NAME] [-m|--module MODULE_PATH]
```

### Use Cases

#### 1. Delete snippet by name
```bash
snip delete my_snippet
snip delete module1/snippet_name
```
- Prompts for confirmation
- Deletes the specified snippet

#### 2. Interactive delete
```bash
snip delete
```
- Shows interactive prompt to select snippet
- Fuzzy search and tab completion available
- Prompts for confirmation before deleting

#### 3. Delete entire module
```bash
snip delete -m module1
snip delete -m module1/module2
```
- Deletes the module and **all** its contents:
  - All child modules (recursively)
  - All snippets in the module and sub-modules
- Prompts for confirmation (important!)
- Cannot be undone

**Warning:** Module deletion is permanent and cascades to all children.

**Note:** Cannot use `-m` flag together with a snippet name.

---

## list

List snippets and modules at a specific level.

### Syntax

```bash
snip list [KEYWORD] [-m|--module MODULE_PATH]
```

### Use Cases

#### 1. List root level
```bash
snip list
```
- Shows all top-level modules (with `/` suffix in yellow)
- Shows all top-level snippets (in cyan)
- Sorted alphabetically

**Output example:**
```
       Snippets
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ first_module/               │  (yellow)
│ module1/                    │  (yellow)
│ module_empty/               │  (yellow)
│ sz                          │  (cyan)
└─────────────────────────────┘
```

#### 2. List with keyword filter
```bash
snip list git
snip list deploy
```
- Filters results by keyword (case-insensitive)
- Matches both module names and snippet paths

#### 3. List contents of a module
```bash
snip list -m module1
snip list -m module1/module2
```
- Shows only direct children of the specified module
- Modules shown with `/` suffix (yellow)
- Snippets shown as full paths (cyan)
- Does not show nested descendants

**Output example:**
```
  Snippets in module1
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ module2/                    │  (yellow)
│ new_snippet                 │  (cyan)
└─────────────────────────────┘
```

#### 4. List module with keyword filter
```bash
snip list -m module1 deploy
```
- Filters contents of `module1` by keyword "deploy"

**Note:** `snip list` only shows direct children, not nested descendants. Use `snip get -m` to browse recursively.

---

## setup

Automatically set up shell wrapper for seamless snippet insertion.

### Syntax

```bash
snip setup [--shell SHELL] [--fix-path] [--force]
```

### Use Cases

#### 1. Automatic setup (recommended)
```bash
snip setup
```
- Auto-detects your shell (bash, zsh, or fish)
- Adds wrapper function to shell config file
- Detects and updates outdated wrappers automatically
- Provides instructions to reload shell

#### 2. Specify shell manually
```bash
snip setup --shell zsh
snip setup --shell bash
snip setup --shell fish
```
- Explicitly sets up for specified shell
- Useful if auto-detection fails

#### 3. Fix PATH and setup
```bash
snip setup --fix-path
```
- Automatically adds Python scripts directory to PATH
- Sets up shell wrapper
- Useful if `snip` command is not found

#### 4. Force update
```bash
snip setup --force
```
- Forces update even if wrapper is already installed
- Useful to get latest wrapper features

#### 5. Combined options
```bash
snip setup --shell zsh --fix-path --force
```
- Combines multiple options as needed

**After setup:**
```bash
source ~/.zshrc  # or ~/.bashrc for bash, ~/.config/fish/config.fish for fish
```

**What the wrapper does:**
- When you run `snip get <name>`, the snippet content automatically appears in your command line buffer
- Ready to edit and execute
- Works seamlessly with your shell

---

## doctor

Diagnose and report issues with Macolint installation.

### Syntax

```bash
snip doctor
```

### Use Cases

#### 1. Check installation health
```bash
snip doctor
```

**Checks:**
- ✓ `snip` command in PATH
- ✓ Shell wrapper installation status
- ✓ Database accessibility
- ✓ Snippet count

**Output example:**
```
Macolint Doctor

✓ snip command found: /usr/local/bin/snip
✓ Shell wrapper installed for zsh
  Config file: /Users/username/.zshrc
✓ Database accessible (15 snippets)
```

**Provides recommendations:**
- How to fix PATH issues
- How to set up shell wrapper
- Commands to run for fixes

**Use when:**
- `snip` command not found
- Shell wrapper not working
- Unexpected errors
- After installation

---

## Command Combinations and Tips

### Common Workflows

#### Organizing snippets into modules
```bash
# Create module structure
snip save -m git
snip save -m git/commit
snip save -m git/branch

# Add snippets to modules
snip save git/commit/template
snip save git/branch/create_feature
```

#### Browsing and using snippets
```bash
# Browse modules interactively
snip get -m git

# Or use direct path
snip get git/commit/template
```

#### Reorganizing structure
```bash
# Rename module
snip rename -m old_module new_module

# Move snippet to different module
snip rename module1/snippet module2/snippet

# Delete old structure
snip delete -m old_module
```

### Tips

1. **Use interactive mode** when unsure of exact names:
   - `snip save` - browse to save location
   - `snip get` - fuzzy search for snippets
   - `snip get -m` - browse modules folder-style

2. **Module paths** are hierarchical:
   - `module1/module2/snippet` means snippet is in module2, which is in module1

3. **Empty modules** are useful for organization:
   - Create structure first: `snip save -m project/frontend`
   - Add snippets later: `snip save project/frontend/component_template`

4. **List shows direct children only**:
   - Use `snip list -m module1` to see what's inside
   - Use `snip get -m module1` to browse recursively

5. **Renaming modules** automatically updates all child paths:
   - `snip rename -m git scripts` moves everything under `git` to `scripts`

---

## Error Handling

### Common Errors

**"Snippet 'name' not found"**
- Check spelling and path
- Use `snip list` to see available snippets
- Use `snip get` for interactive search

**"Module 'path' not found"**
- Verify module path is correct
- Use `snip list -m parent_module` to see child modules
- Modules are case-sensitive

**"No such option: -m"**
- Some commands don't support `-m` flag
- Check command syntax: `snip <command> --help`

**"When using -m/--module, do not also pass..."**
- `-m` flag and name argument are mutually exclusive
- Use either `-m` or provide a name, not both

---

## Quick Reference

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `save` | Save snippet or create module | `-m` for modules |
| `get` | Retrieve snippet | `-m` for browsing, `--raw` for wrapper |
| `edit` | Edit snippet content | None |
| `update` | Update Macolint to latest version | None |
| `rename` | Rename/move snippet or module | `-m` for modules |
| `delete` | Delete snippet or module | `-m` for modules |
| `list` | List snippets and modules | `-m` for specific module |
| `setup` | Set up shell wrapper | `--fix-path`, `--force`, `--shell` |
| `doctor` | Diagnose installation | None |

---

For more information, see the main [README.md](README.md).

