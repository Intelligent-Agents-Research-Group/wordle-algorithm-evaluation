#!/bin/bash
#
# Group D - Repair Hybrids (ZS + CoT, 9 models)
#
# D18:   Constraint Filter (CSS) - LLM proposes; if invalid, CSS picks
# D18b:  Constraint Filter (VOI) - LLM proposes; if invalid, VOI picks
# D19a:  Rerank LLM-first (CSS) - LLM suggests top-k, CSS selects best (LLM=prior, algo=gate)
# D19a:  Rerank LLM-first (VOI) - LLM suggests top-k, VOI selects best
# D19b:  Rerank Algo-first (CSS) - CSS generates top-5, LLM picks from them
# D19b:  Rerank Algo-first (VOI) - VOI generates top-5, LLM picks from them
#
# Each config runs with both ZS and CoT prompting.
#
# Usage:
#   ./run_workshop_group_d.sh [num_games]

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

PROMPT_TYPES=("zero-shot" "cot")

# Config definitions: LABEL|REPAIR_MODE|ALGORITHM|DIR_BASE
# D18:  Constraint Filter - LLM proposes, algo replaces if invalid
# D19a: Rerank LLM-first - LLM suggests top-k, algorithm selects best (LLM=prior, algo=gate)
# D19b: Rerank Algo-first - Algorithm generates top-k, LLM picks from them
REPAIR_CONFIGS=(
    "D18|constraint_filter|css|constraint_filter_css"
    "D18b|constraint_filter|voi|constraint_filter_voi"
    "D19a|rerank_llm_first|css|rerank_llm_first_css"
    "D19a_voi|rerank_llm_first|voi|rerank_llm_first_voi"
    "D19b|rerank|css|rerank_css"
    "D19b_voi|rerank|voi|rerank_voi"
)

TOTAL_RUNS=$(( ${#REPAIR_CONFIGS[@]} * ${#PROMPT_TYPES[@]} * ${#MODELS[@]} ))
CURRENT=0
FAILED=()

echo "========================================"
echo "GROUP D - REPAIR HYBRIDS (ZS + CoT)"
echo "========================================"
echo "Configs: ${#REPAIR_CONFIGS[@]}"
echo "Prompt types: ${#PROMPT_TYPES[@]}"
echo "Models: ${#MODELS[@]}"
echo "Games per run: $NUM_GAMES"
echo "Total runs: $TOTAL_RUNS"
echo "========================================"
echo ""

for CONFIG_ENTRY in "${REPAIR_CONFIGS[@]}"; do
    IFS='|' read -r LABEL REPAIR_MODE ALGORITHM DIR_BASE <<< "$CONFIG_ENTRY"

    for PROMPT_TYPE in "${PROMPT_TYPES[@]}"; do
        if [ "$PROMPT_TYPE" == "cot" ]; then
            DIR_SUFFIX="${DIR_BASE}_cot"
            CONFIG_NAME="${DIR_BASE}_cot"
        else
            DIR_SUFFIX="${DIR_BASE}"
            CONFIG_NAME="${DIR_BASE}"
        fi

        BASE_DIR="$PROJECT_DIR/results/workshop/group_d/$DIR_SUFFIX/raw_data"
        mkdir -p "$BASE_DIR"

        for MODEL in "${MODELS[@]}"; do
            CURRENT=$((CURRENT + 1))
            echo ""
            echo "========================================"
            echo "[$CURRENT/$TOTAL_RUNS] $LABEL ($PROMPT_TYPE): $REPAIR_MODE + $ALGORITHM | Model: $MODEL"
            echo "========================================"

            if MODEL="$MODEL" \
               NUM_GAMES="$NUM_GAMES" \
               PROMPT_TYPE="$PROMPT_TYPE" \
               REPAIR_MODE="$REPAIR_MODE" \
               ALGORITHM="$ALGORITHM" \
               CONFIG_NAME="$CONFIG_NAME" \
               TOP_K="5" \
               OUTPUT_DIR="$BASE_DIR" \
               "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/repair_hybrid.py"; then
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
echo "GROUP D COMPLETE"
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
