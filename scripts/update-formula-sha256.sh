#!/bin/bash

# Script to update the SHA256 hash in the Homebrew formula
# Run this after creating a GitHub release tag

set -e

VERSION="0.1.0"
GITHUB_USER="p4puniya"
REPO="macolint"
TAP_REPO="homebrew-macolint"

echo "🔐 Getting SHA256 for v${VERSION} release"
echo ""

# Check if we're in the macolint directory
if [ ! -f "Formula/macolint.rb" ]; then
    echo "❌ Error: Formula/macolint.rb not found"
    echo "   Please run this script from the macolint project root"
    exit 1
fi

ORIGINAL_DIR="$(pwd)"
TAP_DIR="${ORIGINAL_DIR}/../${TAP_REPO}"

# Check if tap directory exists
if [ ! -d "$TAP_DIR" ]; then
    echo "❌ Error: Tap directory not found at ${TAP_DIR}"
    echo "   Please run ./scripts/setup-homebrew-tap.sh first"
    exit 1
fi

# Method 1: Try using brew fetch (requires tap to be tapped)
echo "Method 1: Trying brew fetch..."
if brew tap-info p4puniya/macolint >/dev/null 2>&1; then
    echo "Tap is installed, fetching SHA256..."
    SHA256=$(brew fetch --build-from-source p4puniya/macolint/macolint 2>&1 | grep -i "sha256" | head -1 | awk '{print $2}' || echo "")
    if [ -n "$SHA256" ]; then
        echo "✅ SHA256: $SHA256"
    else
        echo "⚠️  Could not get SHA256 from brew fetch, trying manual method..."
        SHA256=""
    fi
else
    echo "⚠️  Tap not installed, using manual method..."
    SHA256=""
fi

# Method 2: Manual calculation
if [ -z "$SHA256" ]; then
    echo ""
    echo "Method 2: Calculating SHA256 manually..."
    TARBALL_URL="https://github.com/${GITHUB_USER}/${REPO}/archive/v${VERSION}.tar.gz"
    echo "Downloading: $TARBALL_URL"
    SHA256=$(curl -sL "$TARBALL_URL" | shasum -a 256 | awk '{print $1}')
    echo "✅ SHA256: $SHA256"
fi

if [ -z "$SHA256" ]; then
    echo "❌ Error: Could not determine SHA256"
    echo "   Make sure the tag v${VERSION} exists on GitHub"
    exit 1
fi

# Update the formula in main repo
echo ""
echo "📝 Updating Formula/macolint.rb..."
sed -i.bak "s/sha256 \"\"/sha256 \"${SHA256}\"/" "${ORIGINAL_DIR}/Formula/macolint.rb"
rm -f "${ORIGINAL_DIR}/Formula/macolint.rb.bak"

# Update the formula in tap repo
echo "📝 Updating tap formula..."
cp "${ORIGINAL_DIR}/Formula/macolint.rb" "${TAP_DIR}/Formula/macolint.rb"

echo ""
echo "✅ SHA256 updated in both formulas!"
echo ""
echo "Next steps:"
echo "  1. Review the changes: git diff Formula/macolint.rb"
echo "  2. Commit in main repo: git add Formula/macolint.rb && git commit -m 'Update SHA256 for v${VERSION}'"
echo "  3. Commit in tap repo:"
echo "     cd ${TAP_DIR}"
echo "     git add Formula/macolint.rb"
echo "     git commit -m 'Update SHA256 for v${VERSION}'"
echo "     git push origin main"

