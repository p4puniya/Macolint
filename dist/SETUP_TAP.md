# Setting Up Homebrew Tap for Macolint

## Step 1: Create the Tap Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `homebrew-macolint` (must start with `homebrew-`)
3. Make it **Public**
4. **Don't** initialize with README, .gitignore, or license
5. Click "Create repository"

## Step 2: Clone and Set Up Locally

```bash
# Clone the empty repository
git clone https://github.com/p4puniya/homebrew-macolint.git
cd homebrew-macolint

# Create the Formula directory
mkdir -p Formula

# Copy the formula file from your main macolint repo
cp /path/to/macolint/Formula/macolint.rb Formula/

# Or if you're in the macolint directory:
cp Formula/macolint.rb ../homebrew-macolint/Formula/
```

## Step 3: Commit and Push

```bash
cd homebrew-macolint
git add Formula/macolint.rb
git commit -m "Add macolint formula"
git push origin main
```

## Step 4: Test Installation

Now users can install with:

```bash
brew tap p4puniya/macolint && brew install macolint
```

## Updating the Formula

When you release a new version:

1. Update the version and SHA256 in `Formula/macolint.rb` in your main repo
2. Copy the updated formula to the tap repo:
   ```bash
   cp /path/to/macolint/Formula/macolint.rb /path/to/homebrew-macolint/Formula/
   ```
3. Commit and push:
   ```bash
   cd /path/to/homebrew-macolint
   git add Formula/macolint.rb
   git commit -m "Update macolint to v0.2.0"
   git push origin main
   ```

## Getting SHA256 for Releases

After creating a release tarball:

```bash
shasum -a 256 macolint-0.1.0.tar.gz
```

Then update the `sha256` line in the formula.

