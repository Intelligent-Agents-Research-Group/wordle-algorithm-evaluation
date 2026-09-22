#!/bin/bash
#
# Group C - Alternation Patterns (ZS + CoT, 8 models each)
#
# C1: alt_css_start     (CSS, LLM, CSS, LLM, ...)
# C2: alt_voi_start     (VOI, LLM, VOI, LLM, ...)
# C3: alt_llm_start_css (LLM, CSS, LLM, CSS, ...)
# C4: alt_llm_start_voi (LLM, VOI, LLM, VOI, ...)
#
# Each config runs with both zero-shot and CoT prompting.
#
# Usage:
#   ./run_workshop_group_c.sh [variant] [num_games]

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

PROMPT_TYPES=("zero-shot" "cot")

# Configs: LABEL|CONFIG_NAME|SCHEDULE (10 rounds for Mastermind)
CONFIGS=(
    # alt_css_start: CSS, LLM, CSS, LLM, ...
    'C1|alt_css_start|{"1":"css","2":"llm","3":"css","4":"llm","5":"css","6":"llm","7":"css","8":"llm","9":"css","10":"llm"}'

    # alt_voi_start: VOI, LLM, VOI, LLM, ...
    'C2|alt_voi_start|{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm","7":"voi","8":"llm","9":"voi","10":"llm"}'

    # alt_llm_start_css: LLM, CSS, LLM, CSS, ...
    'C3|alt_llm_start_css|{"1":"llm","2":"css","3":"llm","4":"css","5":"llm","6":"css","7":"llm","8":"css","9":"llm","10":"css"}'

    # alt_llm_start_voi: LLM, VOI, LLM, VOI, ...
    'C4|alt_llm_start_voi|{"1":"llm","2":"voi","3":"llm","4":"voi","5":"llm","6":"voi","7":"llm","8":"voi","9":"llm","10":"voi"}'
)

TOTAL_RUNS=$(( ${#CONFIGS[@]} * ${#MODELS[@]} * ${#PROMPT_TYPES[@]} ))
CURRENT=0
FAILED=()

echo "========================================"
echo "GROUP C - ALTERNATION PATTERNS (ZS+CoT) - $VARIANT"
echo "========================================"
echo "Configs: ${#CONFIGS[@]}"
echo "Models: ${#MODELS[@]}"
echo "Prompt types: ${#PROMPT_TYPES[@]} (zero-shot, cot)"
echo "Games per run: $NUM_GAMES"
echo "Total runs: $TOTAL_RUNS"
echo "========================================"
echo ""

for ENTRY in "${CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"

    for PROMPT_TYPE in "${PROMPT_TYPES[@]}"; do
        SUFFIX=""
        if [ "$PROMPT_TYPE" == "cot" ]; then
            SUFFIX="_cot"
        fi

        BASE_DIR="$PROJECT_DIR/results/mastermind/hybrids/$VARIANT/group_c/${CONFIG_NAME}${SUFFIX}/raw_data"
        mkdir -p "$BASE_DIR"

        for MODEL in "${MODELS[@]}"; do
            CURRENT=$((CURRENT + 1))
            echo ""
            echo "========================================"
            echo "[$CURRENT/$TOTAL_RUNS] $LABEL: $CONFIG_NAME ($PROMPT_TYPE) | Model: $MODEL | Variant: $VARIANT"
            echo "========================================"

            if CONFIG_NAME="${CONFIG_NAME}${SUFFIX}" \
               SCHEDULE="$SCHEDULE" \
               NUM_GAMES="$NUM_GAMES" \
               MODEL="$MODEL" \
               PROMPT_TYPE="$PROMPT_TYPE" \
               OUTPUT_DIR="$BASE_DIR" \
               "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py" --variant "$VARIANT"; then
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
echo "GROUP C COMPLETE ($VARIANT)"
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
