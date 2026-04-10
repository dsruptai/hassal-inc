#!/bin/bash
# Hassal Inc — Local Development Server
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║         HASSAL INC                        ║"
echo "  ║   SA M&A & Liquidity Event Monitor        ║"
echo "  ║                                           ║"
echo "  ║   Running at: http://localhost:8000       ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

uvicorn app:app --reload --host 0.0.0.0 --port 8000
