#!/bin/bash
#
# Group C - Alternation Patterns (ZS + CoT, 9 models)
#
# C12: L<->C, L starts (already done in Stage 3 - reference existing data)
# C13: L<->C, C starts (NEW - algorithm starts)
# C14: L<->V, L starts (already done in Stage 3 - reference existing data)
# C15: L<->V, V starts (NEW - algorithm starts)
#
# Uses existing alternating_hybrid.py with START_WITH="algorithm".
# Runs both ZS and CoT for each new config.
#
# Usage:
#   ./run_workshop_group_c.sh [num_games]

set -e

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Use venv Python explicitly
PYTHON="$PROJECT_DIR/venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    echo "ERROR: venv Python not found at $PYTHON"
    exit 1
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

PROMPT_TYPES=("zero-shot" "cot")

# Configs: LABEL|ALGORITHM
NEW_CONFIGS=(
    "C13|css"
    "C15|voi"
)

TOTAL_RUNS=$(( ${#NEW_CONFIGS[@]} * ${#PROMPT_TYPES[@]} * ${#MODELS[@]} ))
CURRENT=0
FAILED=()

echo "========================================"
echo "GROUP C - ALTERNATION PATTERNS (ZS + CoT)"
echo "========================================"
echo "New configs: ${#NEW_CONFIGS[@]}"
echo "Prompt types: ${#PROMPT_TYPES[@]}"
echo "Models: ${#MODELS[@]}"
echo "Games per run: $NUM_GAMES"
echo "Total new runs: $TOTAL_RUNS"
echo ""
echo "NOTE: C12 (L<->C, L starts) and C14 (L<->V, L starts)"
echo "already exist in Stage 3 results. Reference those."
echo "========================================"
echo ""

for CONFIG_ENTRY in "${NEW_CONFIGS[@]}"; do
    IFS='|' read -r LABEL ALGORITHM <<< "$CONFIG_ENTRY"

    for PROMPT_TYPE in "${PROMPT_TYPES[@]}"; do
        if [ "$PROMPT_TYPE" == "cot" ]; then
            DIR_SUFFIX="alt_${ALGORITHM}_start_cot"
        else
            DIR_SUFFIX="alt_${ALGORITHM}_start_zs"
        fi

        BASE_DIR="$PROJECT_DIR/results/workshop/group_c/$DIR_SUFFIX/raw_data"
        mkdir -p "$BASE_DIR"

        for MODEL in "${MODELS[@]}"; do
            CURRENT=$((CURRENT + 1))
            echo ""
            echo "========================================"
            echo "[$CURRENT/$TOTAL_RUNS] $LABEL ($PROMPT_TYPE): Alt $ALGORITHM-start | Model: $MODEL"
            echo "========================================"

            if MODEL="$MODEL" \
               NUM_GAMES="$NUM_GAMES" \
               START_WITH="algorithm" \
               PROMPT_TYPE="$PROMPT_TYPE" \
               ALGORITHM="$ALGORITHM" \
               OUTPUT_DIR="$BASE_DIR" \
               "$PYTHON" "$SCRIPT_DIR/alternating_hybrid.py"; then
                echo "SUCCESS: $LABEL ($PROMPT_TYPE) $MODEL"
            else
                echo "FAILED: $LABEL ($PROMPT_TYPE) $MODEL"
                FAILED+=("$LABEL:$PROMPT_TYPE:$MODEL")
            fi

            sleep 2
        done
    done
done

echo ""
echo "========================================"
echo "GROUP C COMPLETE"
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
