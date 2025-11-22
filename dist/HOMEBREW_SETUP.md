# Homebrew Tap Setup for Macolint

## Quick Install Command

```bash
brew tap p4puniya/macolint && brew install macolint
```

That's it! After running this command, you can use `snip` anywhere in your terminal.

## Setting Up the Homebrew Tap (For Repository Maintainer)

To make Macolint installable via Homebrew, you need to create a Homebrew tap repository:

### Step 1: Create Tap Repository

1. Create a new GitHub repository named `homebrew-macolint`
   - Repository name must start with `homebrew-`
   - Make it public
   - Don't initialize with README (we'll add the formula)

2. Clone the repository:
   ```bash
   git clone https://github.com/p4puniya/homebrew-macolint.git
   cd homebrew-macolint
   ```

### Step 2: Add the Formula

1. Copy the formula file:
   ```bash
   mkdir -p Formula
   cp /path/to/macolint/Formula/macolint.rb Formula/
   ```

2. Update the SHA256 hash in the formula:
   - After creating your first release, get the SHA256:
     ```bash
     shasum -a 256 /path/to/v0.1.0.tar.gz
     ```
   - Update the `sha256` line in `Formula/macolint.rb`

3. Commit and push:
   ```bash
   git add Formula/macolint.rb
   git commit -m "Add macolint formula"
   git push origin main
   ```

### Step 3: Test Installation

Test the tap locally:
```bash
brew tap p4puniya/macolint
brew install macolint
```

### Step 4: Update Formula for New Releases

When releasing a new version:

1. Update the version and SHA256 in `Formula/macolint.rb`
2. Commit and push the changes
3. Users can update with: `brew upgrade macolint`

## Alternative: Install from Main Repository

If you haven't set up the tap yet, users can install directly from the main repository:

```bash
brew install --build-from-source https://raw.githubusercontent.com/p4puniya/macolint/main/Formula/macolint.rb
```

Or create a local tap:
```bash
brew tap-new p4puniya/macolint
brew create --tap p4puniya/macolint https://github.com/p4puniya/macolint/archive/v0.1.0.tar.gz
# Then edit the generated formula and install
```

