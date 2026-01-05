#!/bin/bash

# Load .env file
set -a
source "$(dirname "$0")/../../.env"
set +a

echo "Running missing gpt-oss models..."
echo ""

# Run gpt-oss-120b
echo "================================"
echo "Model 1/2: gpt-oss-120b"
echo "================================"
export MODEL="gpt-oss-120b"
export NUM_GAMES=100
"$(dirname "$0")/../../venv/bin/python3" "$(dirname "$0")/alternating_hybrid.py"
echo ""

# Run gpt-oss-20b
echo "================================"
echo "Model 2/2: gpt-oss-20b"
echo "================================"
export MODEL="gpt-oss-20b"
export NUM_GAMES=100
"$(dirname "$0")/../../venv/bin/python3" "$(dirname "$0")/alternating_hybrid.py"
echo ""

echo "================================"
echo "Both models complete!"
echo "================================"
