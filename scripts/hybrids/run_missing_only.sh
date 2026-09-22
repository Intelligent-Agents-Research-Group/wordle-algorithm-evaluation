#!/bin/bash
#
# Run ONLY missing experiments (skips existing results)
#
# Usage:
#   ./run_missing_only.sh [wordle|mastermind|both]

set -e

TARGET=${1:-both}
NUM_GAMES=100

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Activate venv
source "$PROJECT_DIR/venv/bin/activate"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
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

# Function to check if a run exists
run_exists() {
    local dir=$1
    local config=$2
    local model=$3
    local pattern="${dir}/${config}_${model}_*.json"
    ls $pattern 2>/dev/null | head -1 > /dev/null 2>&1
}

echo "========================================================================"
echo "RUNNING MISSING EXPERIMENTS ONLY"
echo "========================================================================"
echo "Target: $TARGET"
echo ""

# ============================================================
# WORDLE - Missing Group C runs
# ============================================================
if [ "$TARGET" = "wordle" ] || [ "$TARGET" = "both" ]; then
    echo "================================================================"
    echo "WORDLE - Group C (Alternation) Missing Runs"
    echo "================================================================"

    # alt_css_start_cot - 5 missing
    CONFIG="alt_css_start_cot"
    SCHEDULE='{"1":"css","2":"llm","3":"css","4":"llm","5":"css","6":"llm"}'
    OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_c/alt_css_start_cot/raw_data"
    mkdir -p "$OUTPUT_DIR"

    for MODEL in "${MODELS[@]}"; do
        if run_exists "$OUTPUT_DIR" "alternating_algorithm_first" "${MODEL}_cot"; then
            echo "SKIP: $CONFIG $MODEL (exists)"
        else
            echo "RUN: $CONFIG $MODEL"
            CONFIG_NAME="alternating_algorithm_first" \
            SCHEDULE="$SCHEDULE" \
            NUM_GAMES="$NUM_GAMES" \
            MODEL="$MODEL" \
            PROMPT_TYPE="cot" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            python "$SCRIPT_DIR/flexible_hybrid.py" || echo "FAILED: $CONFIG $MODEL"
            sleep 2
        fi
    done

    # alt_voi_start_zs - 8 missing
    CONFIG="alt_voi_start_zs"
    SCHEDULE='{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm"}'
    OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_c/alt_voi_start_zs/raw_data"
    mkdir -p "$OUTPUT_DIR"

    for MODEL in "${MODELS[@]}"; do
        if run_exists "$OUTPUT_DIR" "alternating_algorithm_first" "${MODEL}"; then
            echo "SKIP: $CONFIG $MODEL (exists)"
        else
            echo "RUN: $CONFIG $MODEL"
            CONFIG_NAME="alternating_algorithm_first" \
            SCHEDULE="$SCHEDULE" \
            NUM_GAMES="$NUM_GAMES" \
            MODEL="$MODEL" \
            PROMPT_TYPE="zero-shot" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            python "$SCRIPT_DIR/flexible_hybrid.py" || echo "FAILED: $CONFIG $MODEL"
            sleep 2
        fi
    done

    # alt_voi_start_cot - 8 missing
    CONFIG="alt_voi_start_cot"
    SCHEDULE='{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm"}'
    OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_c/alt_voi_start_cot/raw_data"
    mkdir -p "$OUTPUT_DIR"

    for MODEL in "${MODELS[@]}"; do
        if run_exists "$OUTPUT_DIR" "alternating_algorithm_first" "${MODEL}_cot"; then
            echo "SKIP: $CONFIG $MODEL (exists)"
        else
            echo "RUN: $CONFIG $MODEL"
            CONFIG_NAME="alternating_algorithm_first" \
            SCHEDULE="$SCHEDULE" \
            NUM_GAMES="$NUM_GAMES" \
            MODEL="$MODEL" \
            PROMPT_TYPE="cot" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            python "$SCRIPT_DIR/flexible_hybrid.py" || echo "FAILED: $CONFIG $MODEL"
            sleep 2
        fi
    done

    echo ""
    echo "Wordle missing runs complete!"
fi

# ============================================================
# MASTERMIND - Missing Group B runs
# ============================================================
if [ "$TARGET" = "mastermind" ] || [ "$TARGET" = "both" ]; then
    echo ""
    echo "================================================================"
    echo "MASTERMIND - Group B Missing Runs"
    echo "================================================================"

    MM_SCRIPT="$PROJECT_DIR/scripts/mastermind/flexible_hybrid.py"

    # voi1_to_L - 5 missing
    CONFIG="voi1_to_L"
    SCHEDULE='{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    OUTPUT_DIR="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/voi1_to_L/raw_data"
    mkdir -p "$OUTPUT_DIR"

    for MODEL in "${MODELS[@]}"; do
        if run_exists "$OUTPUT_DIR" "$CONFIG" "$MODEL"; then
            echo "SKIP: $CONFIG $MODEL (exists)"
        else
            echo "RUN: $CONFIG $MODEL"
            CONFIG_NAME="$CONFIG" \
            SCHEDULE="$SCHEDULE" \
            NUM_GAMES="$NUM_GAMES" \
            MODEL="$MODEL" \
            PROMPT_TYPE="zero-shot" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            VARIANT="classic" \
            python "$MM_SCRIPT" || echo "FAILED: $CONFIG $MODEL"
            sleep 2
        fi
    done

    # voi2_to_L - 8 missing
    CONFIG="voi2_to_L"
    SCHEDULE='{"1":"voi","2":"voi","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    OUTPUT_DIR="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/voi2_to_L/raw_data"
    mkdir -p "$OUTPUT_DIR"

    for MODEL in "${MODELS[@]}"; do
        if run_exists "$OUTPUT_DIR" "$CONFIG" "$MODEL"; then
            echo "SKIP: $CONFIG $MODEL (exists)"
        else
            echo "RUN: $CONFIG $MODEL"
            CONFIG_NAME="$CONFIG" \
            SCHEDULE="$SCHEDULE" \
            NUM_GAMES="$NUM_GAMES" \
            MODEL="$MODEL" \
            PROMPT_TYPE="zero-shot" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            VARIANT="classic" \
            python "$MM_SCRIPT" || echo "FAILED: $CONFIG $MODEL"
            sleep 2
        fi
    done

    # voi3_to_L - 8 missing
    CONFIG="voi3_to_L"
    SCHEDULE='{"1":"voi","2":"voi","3":"voi","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    OUTPUT_DIR="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/voi3_to_L/raw_data"
    mkdir -p "$OUTPUT_DIR"

    for MODEL in "${MODELS[@]}"; do
        if run_exists "$OUTPUT_DIR" "$CONFIG" "$MODEL"; then
            echo "SKIP: $CONFIG $MODEL (exists)"
        else
            echo "RUN: $CONFIG $MODEL"
            CONFIG_NAME="$CONFIG" \
            SCHEDULE="$SCHEDULE" \
            NUM_GAMES="$NUM_GAMES" \
            MODEL="$MODEL" \
            PROMPT_TYPE="zero-shot" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            VARIANT="classic" \
            python "$MM_SCRIPT" || echo "FAILED: $CONFIG $MODEL"
            sleep 2
        fi
    done

    echo ""
    echo "Mastermind missing runs complete!"
fi

echo ""
echo "========================================================================"
echo "ALL MISSING RUNS COMPLETE"
echo "========================================================================"
