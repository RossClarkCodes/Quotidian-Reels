#!/bin/bash
# Quotidian Reel Generator - Full Workflow
# Exports quotes from main codebase and generates reel for yesterday's puzzle

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUOTIDIAN_DIR="$(dirname "$SCRIPT_DIR")"

echo "🎬 Quotidian Reel Generator - Full Workflow"
echo ""

# Step 1: Export quotes from main codebase
echo "Step 1: Exporting quotes from Quotidian..."
cd "$QUOTIDIAN_DIR"
npm run export-quotes

# Step 2: Generate reel
echo ""
echo "Step 2: Generating reel..."
cd "$SCRIPT_DIR"
python3 generate.py

echo ""
echo "✨ Complete!"
echo ""
echo "Output files:"
echo "  - Reel: output/quotidian-reel-$(date -v-1d +%Y-%m-%d).mp4"
echo "  - Cover: output/quotidian-cover-$(date -v-1d +%Y-%m-%d).png"
