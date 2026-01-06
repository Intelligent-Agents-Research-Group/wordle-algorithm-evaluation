#!/bin/bash

# Quick test script to verify CoT hybrid setup
# Tests one model + one algorithm with 3 games

# Load .env file
set -a
source "$(dirname "$0")/../../.env"
set +a

echo "Testing CoT Hybrid Setup"
echo "========================"
echo "Model: mistral-small-3.1"
echo "Algorithm: CSS"
echo "Prompt Type: CoT"
echo "Games: 3"
echo "========================"

export MODEL="mistral-small-3.1"
export NUM_GAMES=3
export ALGORITHM="css"
export PROMPT_TYPE="cot"
export START_WITH="llm"

"$(dirname "$0")/../../venv/bin/python3" "$(dirname "$0")/alternating_hybrid.py"

echo ""
echo "Test complete! Check output above for any errors."
