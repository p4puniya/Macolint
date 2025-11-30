# Macolint

A cloud-synced terminal snippet manager that helps developers reuse code faster across machines and teams.

## Features

- Save and retrieve code snippets instantly
- Interactive fuzzy search with tab completion
- Encrypted local storage
- **Cloud sync with end-to-end encryption** (new!)
- Fast CLI interface

## Quick Install

Install Macolint with a single command (macOS & Linux):

```bash
curl -fsSL https://raw.githubusercontent.com/p4puniya/Macolint/main/install.sh | sh
```

**Copy-paste ready:**
```bash
curl -fsSL https://raw.githubusercontent.com/p4puniya/Macolint/main/install.sh | sh
```

**Note:** If you see `-e` flags in the output, GitHub's CDN may be caching an old version. Wait 2-3 minutes and try again, or use the commit-specific URL:
```bash
curl -fsSL https://raw.githubusercontent.com/p4puniya/Macolint/4344e5d/install.sh | sh
```

This will:
- ✅ Automatically detect your OS and shell
- ✅ Install Macolint from GitHub
- ✅ Configure PATH and shell wrapper
- ✅ Set everything up for immediate use

After installation, reload your shell or open a new terminal, then try:
```bash
snip doctor  # Verify installation
snip save test  # Save your first snippet
```

**Troubleshooting:** If you encounter any issues, run `snip doctor` to diagnose problems.

---

## Manual Installation

If you prefer to install manually or the quick install doesn't work:

### From Source

```bash
# Clone the repository
git clone https://github.com/p4puniya/Macolint.git
cd Macolint

# Install
pip3 install -e .
# or
python3 -m pip install -e .
```

### From GitHub (without cloning)

```bash
pip3 install git+https://github.com/p4puniya/Macolint.git
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
snip edit [name]          # Edit snippet content
snip update                # Update Macolint to latest version from GitHub
snip rename <old> <new>   # Rename a snippet
snip rename -m <old> <new> # Rename a module
snip delete [name]        # Delete a snippet
snip delete -m <module>   # Delete a module and all its contents
snip list [keyword]       # List modules and snippets at root level
snip list -m <module>     # List contents of a specific module
snip setup                # Automatically set up shell wrapper (recommended!)
snip setup --fix-path     # Also fix PATH if snip command not found
snip doctor               # Diagnose installation issues
snip auth login           # Log in to enable cloud sync
snip auth logout          # Log out and clear session
snip sync push            # Push local snippets to cloud (encrypted)
snip sync pull            # Pull snippets from cloud and decrypt locally
snip set-passphrase       # Set up encryption passphrase for cloud sync
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

## Troubleshooting

### Installation Issues

If the quick install script fails:

1. **Check Python version:**
   ```bash
   python3 --version  # Should be 3.8 or higher
   ```

2. **Check pip:**
   ```bash
   pip3 --version
   ```

3. **Manual installation:**
   Follow the [Manual Installation](#manual-installation) section above.

### PATH Issues

If `snip` command is not found after installation:

```bash
# Diagnose the issue
python3 -m macolint.cli doctor

# Auto-fix PATH and shell wrapper
python3 -m macolint.cli setup --fix-path

# Reload your shell
source ~/.zshrc  # or ~/.bashrc for bash
```

### Shell Wrapper Not Working

If `snip get <name>` doesn't insert the snippet into your command line:

```bash
# Re-run setup
snip setup --force

# Reload your shell
source ~/.zshrc  # or ~/.bashrc for bash, or ~/.config/fish/config.fish for fish
```

For more help, run `snip doctor` to get detailed diagnostics.

## Cloud Sync Setup

Macolint now supports cloud sync with end-to-end encryption! Your snippets are encrypted on your device before being uploaded, so only you can decrypt them.

### For Users (Most Common)

**Good news:** If you're using the official Macolint installation, cloud sync is already configured! Just:

1. **Set up your passphrase**:
   ```bash
   snip set-passphrase
   ```

2. **Sign up and log in**:
   ```bash
   snip auth login
   ```
   This will open your browser where you can sign up with your email (or sign in if you already have an account).

3. **Start syncing**:
   ```bash
   snip sync push    # Upload your snippets
   snip sync pull    # Download snippets on other devices
   ```

That's it! No Supabase setup required - the Macolint maintainer has already configured the cloud service.

### For Macolint Maintainers (Setting Up the Shared Service)

If you're setting up Macolint's cloud sync service for all users:

1. **Create a Supabase account** (free tier available):
   - Visit [https://app.supabase.com](https://app.supabase.com)
   - Create a new project

2. **Configure Supabase**:
   - In your project, go to **Authentication → Settings**
   - Enable **Email Magic Link** sign-in
   - Go to **Project Settings → API**
   - Copy your `SUPABASE_URL` and `SUPABASE_ANON_KEY`

3. **Set up database schema**:
   Run this SQL in your Supabase SQL editor:

   ```sql
   -- users_meta: one row per supabase auth user (stores metadata)
   CREATE TABLE IF NOT EXISTS users_meta (
     id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     last_seen TIMESTAMPTZ DEFAULT NOW(),
     salt BYTEA  -- Base64-encoded salt for key derivation
   );

   -- devices table (for device-specific metadata)
   CREATE TABLE IF NOT EXISTS devices (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
     name TEXT,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     last_sync TIMESTAMPTZ
   );

   -- snippets table
   CREATE TABLE IF NOT EXISTS snippets (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
     module TEXT,          -- module/folder
     name TEXT NOT NULL,
     content_encrypted BYTEA NOT NULL, -- encrypted content
     nonce BYTEA NOT NULL,              -- AES-GCM nonce/iv
     salt BYTEA NOT NULL,               -- pbkdf2 salt for this snippet
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE (user_id, module, name)
   );

   -- Enable Row-Level Security
   ALTER TABLE snippets ENABLE ROW LEVEL SECURITY;
   CREATE POLICY "Users can manage their snippets"
     ON snippets
     FOR ALL
     USING ( auth.uid() = user_id )
     WITH CHECK ( auth.uid() = user_id );

   ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
   CREATE POLICY "device owner" ON devices FOR ALL 
     USING (auth.uid() = user_id) 
     WITH CHECK (auth.uid() = user_id);

   ALTER TABLE users_meta ENABLE ROW LEVEL SECURITY;
   CREATE POLICY "users meta" ON users_meta FOR ALL 
     USING (auth.uid() = id) 
     WITH CHECK (auth.uid() = id);
   ```

4. **Configure the package with your Supabase credentials**:
   
   Edit `macolint/supabase_client.py` and set the default values:
   
   ```python
   DEFAULT_SUPABASE_URL = "https://yourproject.supabase.co"
   DEFAULT_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```
   
   **Security Note:** The Supabase anon key is designed to be public and safe to include in client applications. Security is enforced by Row-Level Security (RLS) policies that ensure users can only access their own data.

5. **Deploy the updated package**:
   - Users who install Macolint will automatically use your Supabase instance
   - Users can still override with their own `.env` file if they want a private instance

### For Advanced Users (Using Your Own Supabase Instance)

If you prefer to use your own Supabase project instead of the shared service:

1. Create your own Supabase project (follow steps 1-3 above)
2. Create a `.env` file in your project root or `~/.macolint/`:

   ```bash
   SUPABASE_URL=https://yourproject.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

   This will override the default shared service.

### Getting Started with Cloud Sync (For End Users)

1. **Set up your passphrase**:
   ```bash
   snip set-passphrase
   ```
   This passphrase is used to encrypt your snippets. **Remember it** - you'll need it to decrypt snippets on other devices!

2. **Log in**:
   ```bash
   snip auth login
   ```
   This will open your browser for authentication. Follow the instructions to copy your access token.

3. **Push your snippets to the cloud**:
   ```bash
   snip sync push
   ```
   Enter your passphrase when prompted. Your snippets will be encrypted and uploaded.

4. **On another device, pull your snippets**:
   ```bash
   snip auth login      # Log in with the same account
   snip sync pull       # Enter the same passphrase
   ```

### How It Works

- **End-to-End Encryption**: Your snippets are encrypted using AES-256-GCM with a key derived from your passphrase using PBKDF2 (200,000 iterations). The passphrase never leaves your device.
- **Local-First**: Snippets are always saved locally first. Cloud sync is optional and manual.
- **Security**: Even if someone gains access to your Supabase database, they cannot decrypt your snippets without your passphrase.

### Security Notes

- **Passphrase Management**: Your passphrase is never stored. If you forget it, you cannot recover your encrypted snippets. Consider using a password manager.
- **Token Storage**: Your authentication token is stored locally in `~/.macolint/session.json` with restricted permissions (600).
- **Salt Storage**: Each user has a unique salt stored in the database (not secret, used for key derivation).

### Troubleshooting Cloud Sync

**"Not logged in" error:**
- Run `snip auth login` to authenticate

**"Supabase is not configured" error:**
- If you're a regular user: The Macolint maintainer needs to configure the shared service. Contact them or use your own Supabase instance.
- If you're using your own instance: Make sure your `.env` file exists with `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- Check that the file is in the correct location (project root or `~/.macolint/`)

**Decryption failures:**
- Verify you're using the correct passphrase
- The passphrase must match exactly (case-sensitive)

**"Failed to fetch snippets" error:**
- Check your internet connection
- Verify your Supabase project is active
- Make sure RLS policies are correctly configured

## MVP Status

✅ Local storage with encryption  
✅ Cloud sync with end-to-end encryption  
🚧 Team sharing (coming in Phase 2)

