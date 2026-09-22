#!/bin/bash
#
# Group A - Single Handoff (ZS only, 8 models each)
#
# A1: L->C     (LLM R1, CSS R2-10)
# A2: L->V     (LLM R1, VOI R2-10)
# A3: L->C_Alt (LLM R1, CSS/VOI alternating R2-10)
# A4: L->(C then V) (LLM R1, CSS R2-5, VOI R6-10)
# A5: L->(V then C) (LLM R1, VOI R2-5, CSS R6-10)
# A6: C->L     (CSS R1, LLM R2-10)
# A7: V->L     (VOI R1, LLM R2-10)
#
# Usage:
#   ./run_workshop_group_a.sh [variant] [num_games]

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
    'A1|L_to_C|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'A2|L_to_V|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'A3|L_to_C_alt|{"1":"llm","2":"css","3":"voi","4":"css","5":"voi","6":"css","7":"voi","8":"css","9":"voi","10":"css"}'
    'A4|L_to_C_then_V|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'A5|L_to_V_then_C|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'A6|C_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'A7|V_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
)

TOTAL_RUNS=$(( ${#CONFIGS[@]} * ${#MODELS[@]} ))
CURRENT=0
FAILED=()

echo "========================================"
echo "GROUP A - SINGLE HANDOFF (ZS) - $VARIANT"
echo "========================================"
echo "Configs: ${#CONFIGS[@]}"
echo "Models: ${#MODELS[@]}"
echo "Games per run: $NUM_GAMES"
echo "Total runs: $TOTAL_RUNS"
echo "========================================"
echo ""

for ENTRY in "${CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    BASE_DIR="$PROJECT_DIR/results/mastermind/hybrids/$VARIANT/group_a/$CONFIG_NAME/raw_data"
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
echo "GROUP A COMPLETE ($VARIANT)"
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
