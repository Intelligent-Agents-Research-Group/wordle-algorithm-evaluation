#!/bin/bash
#
# Run remaining workshop experiments: Group D + Sanity
# Waits for Group C (PID 14554) to finish first, then proceeds.
#
# Usage:
#   nohup bash scripts/hybrids/run_remaining_workshop.sh 100 &

set -e

NUM_GAMES=${1:-100}
GROUP_C_PID=14554

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "========================================================================"
echo "REMAINING WORKSHOP EXPERIMENTS: Group D + Sanity"
echo "========================================================================"
echo "Waiting for Group C (PID $GROUP_C_PID) to finish..."

# Wait for Group C to complete
while kill -0 $GROUP_C_PID 2>/dev/null; do
    sleep 30
done
echo "Group C finished. Proceeding with Group D..."

# ── Group D ──────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "RUNNING GROUP D - Repair Hybrids"
echo "================================================================"
bash "$SCRIPT_DIR/run_workshop_group_d.sh" "$NUM_GAMES"

# ── Sanity Check ─────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "RUNNING SANITY CHECK"
echo "================================================================"

# Activate venv if present
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "llama-3.1-nemotron-nano-8b-v1"
    "mistral-7b-instruct"
)

SANITY_SCHEDULE='{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
SANITY_DIR="$PROJECT_DIR/results/workshop/sanity/raw_data"
mkdir -p "$SANITY_DIR"
SANITY_FAILED=()
SANITY_CURRENT=0
SANITY_TOTAL=${#MODELS[@]}

for MODEL in "${MODELS[@]}"; do
    SANITY_CURRENT=$((SANITY_CURRENT + 1))
    echo ""
    echo "[$SANITY_CURRENT/$SANITY_TOTAL] Sanity: L->CSS CoT | Model: $MODEL"

    if CONFIG_NAME="sanity_L_to_css_cot" \
       SCHEDULE="$SANITY_SCHEDULE" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$MODEL" \
       PROMPT_TYPE="cot" \
       OUTPUT_DIR="$SANITY_DIR" \
       python3 "$SCRIPT_DIR/flexible_hybrid.py"; then
        echo "SUCCESS: Sanity $MODEL"
    else
        echo "FAILED: Sanity $MODEL"
        SANITY_FAILED+=("$MODEL")
    fi

    sleep 2
done

echo ""
echo "========================================================================"
echo "ALL REMAINING EXPERIMENTS COMPLETE"
echo "========================================================================"
echo "Sanity failures: ${#SANITY_FAILED[@]} out of $SANITY_TOTAL"
echo "Results: $PROJECT_DIR/results/workshop/"
echo "========================================================================"
