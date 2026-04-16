#!/bin/bash
# CitationTrace — Backend Setup & Start Script
# Run from the backend/ directory: bash start.sh

set -e

echo "╔══════════════════════════════════════╗"
echo "║       CitationTrace Backend          ║"
echo "╚══════════════════════════════════════╝"

# ── 1. Python version check ──────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "✗ Python 3 not found. Install from https://www.python.org/downloads/"
  exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Python $PYTHON_VERSION found"

# ── 2. Virtual environment ────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv venv
  echo "✓ Virtual environment created"
else
  echo "✓ Virtual environment already exists"
fi

# Activate
source venv/bin/activate
echo "✓ Virtual environment activated"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo "→ Installing dependencies (this may take a minute on first run)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "✓ Dependencies installed"

# ── 4. Environment file ───────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "⚠  .env file created from .env.example"
  echo "   LangSmith tracing is optional — the backend works without it."
  echo "   To enable it, open backend/.env and add your LANGSMITH_API_KEY."
  echo ""
fi

# ── 5. Start server ───────────────────────────────────────────────────────────
echo ""
echo "✓ Starting FastAPI server on http://localhost:8000"
echo "  Health check: http://localhost:8000/health"
echo "  Press Ctrl+C to stop"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
