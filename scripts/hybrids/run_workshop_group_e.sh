#!/bin/bash
#
# Group E - Controls (No LLM)
#
# E20: Random R1, CSS R2-6
# E21: Random R1, VOI R2-6
#
# These use no LLM calls, making them fast baseline controls.
#
# Usage:
#   ./run_workshop_group_e.sh [num_games]
#
# Examples:
#   ./run_workshop_group_e.sh 100   # Full evaluation
#   ./run_workshop_group_e.sh 5     # Quick test

set -e

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Activate venv if present
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

echo "========================================"
echo "GROUP E - CONTROLS (No LLM)"
echo "========================================"
echo "Games per config: $NUM_GAMES"
echo "========================================"
echo ""

FAILED=()
TOTAL=2
CURRENT=0

# --- E20: Random -> CSS ---
CURRENT=$((CURRENT + 1))
CONFIG_NAME="random_to_css"
SCHEDULE='{"1":"random","2":"css","3":"css","4":"css","5":"css","6":"css"}'
OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_e/random_to_css/raw_data"
mkdir -p "$OUTPUT_DIR"

echo "[$CURRENT/$TOTAL] E20: Random R1, CSS R2-6"
if CONFIG_NAME="$CONFIG_NAME" \
   SCHEDULE="$SCHEDULE" \
   NUM_GAMES="$NUM_GAMES" \
   MODEL="none" \
   PROMPT_TYPE="zero-shot" \
   OUTPUT_DIR="$OUTPUT_DIR" \
   "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py"; then
    echo "SUCCESS: E20 completed"
else
    echo "FAILED: E20"
    FAILED+=("E20")
fi

# --- E21: Random -> VOI ---
CURRENT=$((CURRENT + 1))
CONFIG_NAME="random_to_voi"
SCHEDULE='{"1":"random","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi"}'
OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_e/random_to_voi/raw_data"
mkdir -p "$OUTPUT_DIR"

echo ""
echo "[$CURRENT/$TOTAL] E21: Random R1, VOI R2-6"
if CONFIG_NAME="$CONFIG_NAME" \
   SCHEDULE="$SCHEDULE" \
   NUM_GAMES="$NUM_GAMES" \
   MODEL="none" \
   PROMPT_TYPE="zero-shot" \
   OUTPUT_DIR="$OUTPUT_DIR" \
   "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py"; then
    echo "SUCCESS: E21 completed"
else
    echo "FAILED: E21"
    FAILED+=("E21")
fi

echo ""
echo "========================================"
echo "GROUP E COMPLETE"
echo "========================================"
echo "Total: $TOTAL"
echo "Successful: $((TOTAL - ${#FAILED[@]}))"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed configs:"
    for F in "${FAILED[@]}"; do
        echo "  - $F"
    done
fi
echo "========================================"
