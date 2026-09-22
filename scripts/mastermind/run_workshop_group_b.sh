#!/bin/bash
#
# Group B - K-Handoff Sweeps (ZS only, 8 models, k=1,2,3)
#
# B1-B3: Lk_to_css  (LLM for k rounds, then CSS)
# B4-B6: Lk_to_voi  (LLM for k rounds, then VOI)
# B7-B9: cssk_to_L  (CSS for k rounds, then LLM)
# B10-B12: voik_to_L (VOI for k rounds, then LLM)
#
# Usage:
#   ./run_workshop_group_b.sh [variant] [num_games]

set -e

VARIANT=${1:-classic}
NUM_GAMES=${2:-100}

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
    "llama-3.1-nemotron-nano-8B-v1"
    "mistral-7b-instruct"
)

# Configs: LABEL|CONFIG_NAME|SCHEDULE (10 rounds for Mastermind)
CONFIGS=(
    # Lk_to_css: LLM for k rounds, then CSS
    'B1|L1_to_css|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'B2|L2_to_css|{"1":"llm","2":"llm","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'B3|L3_to_css|{"1":"llm","2":"llm","3":"llm","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'

    # Lk_to_voi: LLM for k rounds, then VOI
    'B4|L1_to_voi|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'B5|L2_to_voi|{"1":"llm","2":"llm","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'B6|L3_to_voi|{"1":"llm","2":"llm","3":"llm","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'

    # cssk_to_L: CSS for k rounds, then LLM
    'B7|css1_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B8|css2_to_L|{"1":"css","2":"css","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B9|css3_to_L|{"1":"css","2":"css","3":"css","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'

    # voik_to_L: VOI for k rounds, then LLM
    'B10|voi1_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B11|voi2_to_L|{"1":"voi","2":"voi","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B12|voi3_to_L|{"1":"voi","2":"voi","3":"voi","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
)

TOTAL_RUNS=$(( ${#CONFIGS[@]} * ${#MODELS[@]} ))
CURRENT=0
FAILED=()

echo "========================================"
echo "GROUP B - K-HANDOFF SWEEPS (ZS) - $VARIANT"
echo "========================================"
echo "Configs: ${#CONFIGS[@]}"
echo "Models: ${#MODELS[@]}"
echo "Games per run: $NUM_GAMES"
echo "Total runs: $TOTAL_RUNS"
echo "========================================"
echo ""

for ENTRY in "${CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    BASE_DIR="$PROJECT_DIR/results/mastermind/hybrids/$VARIANT/group_b/$CONFIG_NAME/raw_data"
    mkdir -p "$BASE_DIR"

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo ""
        echo "========================================"
        echo "[$CURRENT/$TOTAL_RUNS] $LABEL: $CONFIG_NAME | Model: $MODEL | Variant: $VARIANT"
        echo "========================================"

        if CONFIG_NAME="$CONFIG_NAME" \
           SCHEDULE="$SCHEDULE" \
           NUM_GAMES="$NUM_GAMES" \
           MODEL="$MODEL" \
           PROMPT_TYPE="zero-shot" \
           OUTPUT_DIR="$BASE_DIR" \
           "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py" --variant "$VARIANT"; then
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
echo "GROUP B COMPLETE ($VARIANT)"
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
