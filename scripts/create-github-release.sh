#!/bin/bash

# Script to create a GitHub release using the GitHub API
# This ensures the tarball is available for Homebrew

set -e

VERSION="0.1.0"
GITHUB_USER="p4puniya"
REPO="Macolint"  # Note: capital M based on actual repo name

echo "🚀 Creating GitHub release v${VERSION}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo ""
    echo "Install it with: brew install gh"
    echo "Then authenticate: gh auth login"
    echo ""
    echo "Alternatively, create the release manually:"
    echo "  1. Go to: https://github.com/${GITHUB_USER}/${REPO}/releases/new"
    echo "  2. Select tag: v${VERSION}"
    echo "  3. Release title: v${VERSION}"
    echo "  4. Click 'Publish release'"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Check if tag exists on GitHub
if ! git ls-remote --tags origin | grep -q "refs/tags/v${VERSION}"; then
    echo "❌ Error: Tag v${VERSION} does not exist on GitHub"
    echo "Run: ./scripts/create-release.sh first"
    exit 1
fi

# Check if release already exists
if gh release view "v${VERSION}" --repo "${GITHUB_USER}/${REPO}" &> /dev/null; then
    echo "⚠️  Release v${VERSION} already exists"
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gh release delete "v${VERSION}" --repo "${GITHUB_USER}/${REPO}" --yes
    else
        echo "Release already exists, skipping..."
        exit 0
    fi
fi

# Create the release
echo "📦 Creating release v${VERSION}..."
gh release create "v${VERSION}" \
    --repo "${GITHUB_USER}/${REPO}" \
    --title "v${VERSION}" \
    --notes "Release v${VERSION}" \
    --target "v${VERSION}"

echo ""
echo "✅ Release created successfully!"
echo ""
echo "Waiting a few seconds for GitHub to generate the tarball..."
sleep 5

# Verify the tarball is available
echo "🔍 Verifying tarball availability..."
if curl -sI "https://github.com/${GITHUB_USER}/${REPO}/archive/v${VERSION}.tar.gz" | grep -q "200 OK"; then
    echo "✅ Tarball is now available!"
    echo ""
    echo "You can now update the tap repository and test installation:"
    echo "  cd ../homebrew-macolint"
    echo "  git pull origin main"
    echo "  brew install p4puniya/macolint/macolint"
else
    echo "⚠️  Tarball might not be available yet. Wait a minute and try again."
    echo "   URL: https://github.com/${GITHUB_USER}/${REPO}/archive/v${VERSION}.tar.gz"
fi

