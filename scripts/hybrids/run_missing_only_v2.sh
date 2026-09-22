#!/bin/bash
#
# Run ONLY missing experiments (v2 - fixed pattern matching)
#

set -e

NUM_GAMES=100

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_DIR"

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

echo "========================================================================"
echo "RUNNING MISSING EXPERIMENTS ONLY (v2)"
echo "========================================================================"
echo ""

# ============================================================
# WORDLE - Missing Group C: alt_voi_start_zs and alt_voi_start_cot
# ============================================================
echo "================================================================"
echo "WORDLE - Group C: alt_voi_start_zs (8 runs)"
echo "================================================================"

CONFIG="alt_voi_start_zs"
SCHEDULE='{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm"}'
OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_c/alt_voi_start_zs/raw_data"
mkdir -p "$OUTPUT_DIR"

for MODEL in "${MODELS[@]}"; do
    # Check if file exists for this specific model
    EXISTING=$(ls "$OUTPUT_DIR"/*"$MODEL"*.json 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 0 ]; then
        echo "SKIP: $CONFIG $MODEL (exists)"
    else
        echo ""
        echo "========================================"
        echo "RUN: $CONFIG $MODEL"
        echo "========================================"
        CONFIG_NAME="alternating_algorithm_first" \
        SCHEDULE="$SCHEDULE" \
        NUM_GAMES="$NUM_GAMES" \
        MODEL="$MODEL" \
        PROMPT_TYPE="zero-shot" \
        OUTPUT_DIR="$OUTPUT_DIR" \
        "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py" || echo "FAILED: $CONFIG $MODEL"
        sleep 2
    fi
done

echo ""
echo "================================================================"
echo "WORDLE - Group C: alt_voi_start_cot (8 runs)"
echo "================================================================"

CONFIG="alt_voi_start_cot"
SCHEDULE='{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm"}'
OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_c/alt_voi_start_cot/raw_data"
mkdir -p "$OUTPUT_DIR"

for MODEL in "${MODELS[@]}"; do
    EXISTING=$(ls "$OUTPUT_DIR"/*"$MODEL"*.json 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 0 ]; then
        echo "SKIP: $CONFIG $MODEL (exists)"
    else
        echo ""
        echo "========================================"
        echo "RUN: $CONFIG $MODEL"
        echo "========================================"
        CONFIG_NAME="alternating_algorithm_first" \
        SCHEDULE="$SCHEDULE" \
        NUM_GAMES="$NUM_GAMES" \
        MODEL="$MODEL" \
        PROMPT_TYPE="cot" \
        OUTPUT_DIR="$OUTPUT_DIR" \
        "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py" || echo "FAILED: $CONFIG $MODEL"
        sleep 2
    fi
done

echo ""
echo "Wordle Group C complete!"

# ============================================================
# MASTERMIND - Missing Group B: voi1_to_L (5), voi2_to_L (8), voi3_to_L (8)
# ============================================================
echo ""
echo "================================================================"
echo "MASTERMIND - Group B: voi1_to_L (5 remaining)"
echo "================================================================"

MM_SCRIPT="$PROJECT_DIR/scripts/mastermind/flexible_hybrid.py"

CONFIG="voi1_to_L"
SCHEDULE='{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
OUTPUT_DIR="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/voi1_to_L/raw_data"
mkdir -p "$OUTPUT_DIR"

for MODEL in "${MODELS[@]}"; do
    EXISTING=$(ls "$OUTPUT_DIR"/*"$MODEL"*.json 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 0 ]; then
        echo "SKIP: $CONFIG $MODEL (exists)"
    else
        echo ""
        echo "========================================"
        echo "RUN: $CONFIG $MODEL"
        echo "========================================"
        CONFIG_NAME="$CONFIG" \
        SCHEDULE="$SCHEDULE" \
        NUM_GAMES="$NUM_GAMES" \
        MODEL="$MODEL" \
        PROMPT_TYPE="zero-shot" \
        OUTPUT_DIR="$OUTPUT_DIR" \
        VARIANT="classic" \
        "$PROJECT_DIR/venv/bin/python" "$MM_SCRIPT" || echo "FAILED: $CONFIG $MODEL"
        sleep 2
    fi
done

echo ""
echo "================================================================"
echo "MASTERMIND - Group B: voi2_to_L (8 runs)"
echo "================================================================"

CONFIG="voi2_to_L"
SCHEDULE='{"1":"voi","2":"voi","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
OUTPUT_DIR="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/voi2_to_L/raw_data"
mkdir -p "$OUTPUT_DIR"

for MODEL in "${MODELS[@]}"; do
    EXISTING=$(ls "$OUTPUT_DIR"/*"$MODEL"*.json 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 0 ]; then
        echo "SKIP: $CONFIG $MODEL (exists)"
    else
        echo ""
        echo "========================================"
        echo "RUN: $CONFIG $MODEL"
        echo "========================================"
        CONFIG_NAME="$CONFIG" \
        SCHEDULE="$SCHEDULE" \
        NUM_GAMES="$NUM_GAMES" \
        MODEL="$MODEL" \
        PROMPT_TYPE="zero-shot" \
        OUTPUT_DIR="$OUTPUT_DIR" \
        VARIANT="classic" \
        "$PROJECT_DIR/venv/bin/python" "$MM_SCRIPT" || echo "FAILED: $CONFIG $MODEL"
        sleep 2
    fi
done

echo ""
echo "================================================================"
echo "MASTERMIND - Group B: voi3_to_L (8 runs)"
echo "================================================================"

CONFIG="voi3_to_L"
SCHEDULE='{"1":"voi","2":"voi","3":"voi","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
OUTPUT_DIR="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/voi3_to_L/raw_data"
mkdir -p "$OUTPUT_DIR"

for MODEL in "${MODELS[@]}"; do
    EXISTING=$(ls "$OUTPUT_DIR"/*"$MODEL"*.json 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 0 ]; then
        echo "SKIP: $CONFIG $MODEL (exists)"
    else
        echo ""
        echo "========================================"
        echo "RUN: $CONFIG $MODEL"
        echo "========================================"
        CONFIG_NAME="$CONFIG" \
        SCHEDULE="$SCHEDULE" \
        NUM_GAMES="$NUM_GAMES" \
        MODEL="$MODEL" \
        PROMPT_TYPE="zero-shot" \
        OUTPUT_DIR="$OUTPUT_DIR" \
        VARIANT="classic" \
        "$PROJECT_DIR/venv/bin/python" "$MM_SCRIPT" || echo "FAILED: $CONFIG $MODEL"
        sleep 2
    fi
done

echo ""
echo "========================================================================"
echo "ALL MISSING RUNS COMPLETE"
echo "========================================================================"
echo "Total runs attempted:"
echo "  - Wordle alt_voi_start_zs: 8"
echo "  - Wordle alt_voi_start_cot: 8"
echo "  - Mastermind voi1_to_L: 5"
echo "  - Mastermind voi2_to_L: 8"
echo "  - Mastermind voi3_to_L: 8"
echo "========================================================================"
