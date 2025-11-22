#!/bin/bash

# Script to create a GitHub release tag for Macolint
# This is needed for Homebrew to download the source tarball

set -e

VERSION="0.1.0"
GITHUB_USER="p4puniya"
REPO="macolint"

echo "🏷️  Creating release tag v${VERSION} for Macolint"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if tag already exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo "⚠️  Tag v${VERSION} already exists locally"
    read -p "Do you want to push it to GitHub? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin "v${VERSION}"
        echo "✅ Tag pushed to GitHub"
    fi
    exit 0
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create the tag
echo "📝 Creating tag v${VERSION}..."
git tag -a "v${VERSION}" -m "Release v${VERSION}"

# Push the tag
echo "📤 Pushing tag to GitHub..."
git push origin "v${VERSION}"

echo ""
echo "✅ Tag v${VERSION} created and pushed!"
echo ""
echo "Next steps:"
echo "1. Go to: https://github.com/${GITHUB_USER}/${REPO}/releases/new"
echo "2. Select tag: v${VERSION}"
echo "3. Release title: v${VERSION}"
echo "4. Click 'Publish release'"
echo ""
echo "After creating the release, update the SHA256 in Formula/macolint.rb:"
echo "  brew fetch --build-from-source https://raw.githubusercontent.com/${GITHUB_USER}/homebrew-macolint/main/Formula/macolint.rb"
echo "  # Copy the SHA256 from the output and update the formula"

