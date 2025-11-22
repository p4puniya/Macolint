#!/bin/bash

# Script to set up Homebrew tap for Macolint
# This will help you create and configure the tap repository

set -e

echo "🍺 Setting up Homebrew tap for Macolint"
echo ""

# Check if we're in the macolint directory
if [ ! -f "Formula/macolint.rb" ]; then
    echo "❌ Error: Formula/macolint.rb not found"
    echo "   Please run this script from the macolint project root"
    exit 1
fi

# Store original directory
ORIGINAL_DIR="$(pwd)"

TAP_REPO="homebrew-macolint"
GITHUB_USER="p4puniya"
# Use SSH URL with the correct GitHub account alias
TAP_URL="git@github.com-${GITHUB_USER}:${GITHUB_USER}/${TAP_REPO}.git"
TAP_DIR="${ORIGINAL_DIR}/../${TAP_REPO}"

echo "Step 1: Create the GitHub repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: ${TAP_REPO}"
echo "3. Make it PUBLIC"
echo "4. DO NOT initialize with README, .gitignore, or license"
echo "5. Click 'Create repository'"
echo ""
read -p "Press Enter after you've created the repository..."

echo ""
echo "Step 2: Setting up local tap repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Clone the repository or use existing
if [ -d "$TAP_DIR" ]; then
    echo "⚠️  Directory ${TAP_DIR} already exists."
    echo "   Updating remote URL to use correct GitHub account..."
    (cd "$TAP_DIR" && git remote set-url origin "$TAP_URL")
else
    echo "📦 Cloning using SSH (github.com-p4puniya)..."
    git clone "$TAP_URL" "$TAP_DIR"
fi

# Create Formula directory and copy formula
echo "📋 Copying formula file..."
mkdir -p "${TAP_DIR}/Formula"
cp "${ORIGINAL_DIR}/Formula/macolint.rb" "${TAP_DIR}/Formula/"

# Commit and push
echo "💾 Committing and pushing..."
cd "$TAP_DIR"
# Ensure remote is set correctly
git remote set-url origin "$TAP_URL"
git add Formula/macolint.rb
# Commit if there are changes
if ! git diff --staged --quiet; then
    git commit -m "Add macolint formula"
elif [ -z "$(git log --oneline -1 2>/dev/null)" ]; then
    # No commits yet, create initial commit
    git commit -m "Add macolint formula"
fi
git push origin main

echo ""
echo "✅ Homebrew tap setup complete!"
echo ""
echo "⚠️  IMPORTANT: Before users can install, you need to create a GitHub release tag!"
echo ""
echo "To create the release tag, run:"
echo "  ./scripts/create-release.sh"
echo ""
echo "Or manually:"
echo "  1. Create tag: git tag -a v0.1.0 -m 'Release v0.1.0'"
echo "  2. Push tag: git push origin v0.1.0"
echo "  3. Create release on GitHub: https://github.com/${GITHUB_USER}/macolint/releases/new"
echo ""
echo "After creating the release, update the SHA256 in the tap formula:"
echo "  1. cd ${TAP_DIR}"
echo "  2. Run: brew fetch --build-from-source Formula/macolint.rb"
echo "  3. Copy the SHA256 from output and update Formula/macolint.rb"
echo "  4. Commit and push the updated formula"
echo ""
echo "Once the release exists, users can install with:"
echo "  brew tap p4puniya/macolint && brew install macolint"
echo ""
echo "For now, users can install from HEAD (development version):"
echo "  brew tap p4puniya/macolint"
echo "  brew install --HEAD macolint"

