#!/usr/bin/env bash
# First-time setup script for PrecisionOncology Portal (Linux/macOS/Git Bash).
# On Windows, use scripts/setup.ps1 instead, or run this under Git Bash.
# Creates .env from .env.example if it doesn't exist,
# then creates data directories.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Create .env if missing
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Done. Edit .env to set API tokens and paths before running the pipeline."
else
    echo ".env already exists, skipping."
fi

# Create data directories
mkdir -p data/uploads data/cache data/reference data/cases

echo ""
echo "Setup complete. Next steps:"
echo "  docker compose build"
echo "  docker compose up -d"
