#!/bin/bash
#
# Group B - K-Handoff Sweeps (ZS only, 9 models, k=1,2,3)
#
# B8:  L×k -> CSS   (k=1,2,3 rounds of LLM then CSS)
# B9:  L×k -> VOI   (k=1,2,3 rounds of LLM then VOI)
# B10: CSS×k -> L    (k=1,2,3 rounds of CSS then LLM)
# B11: VOI×k -> L    (k=1,2,3 rounds of VOI then LLM)
#
# Note: k=1 cases overlap with Group A (A1, A2, A6, A7).
# We run them anyway for completeness; dedup in analysis.
#
# Usage:
#   ./run_workshop_group_b.sh [num_games]

set -e

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Activate venv if present
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY not set"
    exit 1
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
    # "mistral-small-3.1"  # Excluded: hangs on API
)

# Build schedules dynamically
# Helper: generate schedule JSON for "first k rounds = strategy_a, rest = strategy_b"
make_schedule() {
    local k=$1
    local strat_a=$2
    local strat_b=$3
    local sched="{"
    for r in 1 2 3 4 5 6; do
        if [ $r -le $k ]; then
            sched+="\"$r\":\"$strat_a\""
        else
            sched+="\"$r\":\"$strat_b\""
        fi
        if [ $r -lt 6 ]; then
            sched+=","
        fi
    done
    sched+="}"
    echo "$sched"
}

# Configs: CONFIG_PREFIX STRAT_A STRAT_B DIR_PREFIX
declare -a RUN_LIST=()

for K in 1 2 3; do
    # B8: L×k -> CSS
    RUN_LIST+=("B8_k${K}|L${K}_to_css|$(make_schedule $K llm css)|group_b/L${K}_to_css")
    # B9: L×k -> VOI
    RUN_LIST+=("B9_k${K}|L${K}_to_voi|$(make_schedule $K llm voi)|group_b/L${K}_to_voi")
    # B10: CSS×k -> L
    RUN_LIST+=("B10_k${K}|css${K}_to_L|$(make_schedule $K css llm)|group_b/css${K}_to_L")
    # B11: VOI×k -> L
    RUN_LIST+=("B11_k${K}|voi${K}_to_L|$(make_schedule $K voi llm)|group_b/voi${K}_to_L")
done

TOTAL_RUNS=$(( ${#RUN_LIST[@]} * ${#MODELS[@]} ))
CURRENT=0
FAILED=()

echo "========================================"
echo "GROUP B - K-HANDOFF SWEEPS (ZS)"
echo "========================================"
echo "Configs: ${#RUN_LIST[@]}"
echo "Models: ${#MODELS[@]}"
echo "Games per run: $NUM_GAMES"
echo "Total runs: $TOTAL_RUNS"
echo "========================================"
echo ""

for ENTRY in "${RUN_LIST[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE DIR_SUFFIX <<< "$ENTRY"
    BASE_DIR="$PROJECT_DIR/results/workshop/$DIR_SUFFIX/raw_data"
    mkdir -p "$BASE_DIR"

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo ""
        echo "========================================"
        echo "[$CURRENT/$TOTAL_RUNS] $LABEL: $CONFIG_NAME | Model: $MODEL"
        echo "========================================"

        if CONFIG_NAME="$CONFIG_NAME" \
           SCHEDULE="$SCHEDULE" \
           NUM_GAMES="$NUM_GAMES" \
           MODEL="$MODEL" \
           PROMPT_TYPE="zero-shot" \
           OUTPUT_DIR="$BASE_DIR" \
           "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py"; then
            echo "SUCCESS: $LABEL $MODEL"
        else
            echo "FAILED: $LABEL $MODEL"
            FAILED+=("$LABEL:$MODEL")
        fi

        sleep 2
    done
done

echo ""
echo "========================================"
echo "GROUP B COMPLETE"
echo "========================================"
echo "Total runs: $TOTAL_RUNS"
echo "Successful: $((TOTAL_RUNS - ${#FAILED[@]}))"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed runs:"
    for F in "${FAILED[@]}"; do
        echo "  - $F"
    done
fi
echo "========================================"
