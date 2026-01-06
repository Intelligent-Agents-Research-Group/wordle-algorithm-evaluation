#!/bin/bash

# Load .env file
set -a
source "$(dirname "$0")/../../.env"
set +a

echo "========================================"
echo "STAGE 3 CoT HYBRID EVALUATION"
echo "========================================"
echo "Strategy: alternating_llm_first"
echo "Prompt Type: CoT (Chain-of-Thought)"
echo "Algorithms: CSS, VOI, Random (filtered)"
echo "Games per model-algorithm: 100"
echo "Total models: 9"
echo "Total algorithms: 3"
echo "Total games: 2,700 (9 models × 3 algorithms × 100 games)"
echo "========================================"
echo ""

# Create output directories
RESULTS_DIR="$(dirname "$0")/../../results/hybrids/stage3-cot"
mkdir -p "$RESULTS_DIR/raw data"
mkdir -p "$RESULTS_DIR/summary stats"
mkdir -p "$RESULTS_DIR/logs"

# Array of models to test (same 9 models from zero-shot Stage 3)
MODELS=(
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "llama-3.1-nemotron-nano-8B-v1"
    "llama-3.3-70b-instruct"
    "mistral-7b-instruct"
    "mistral-small-3.1"
)

# Array of algorithms to test
ALGORITHMS=(
    "css"
    "voi"
    "random"
)

# Export common configuration
export NUM_GAMES=100
export START_WITH="llm"
export PROMPT_TYPE="cot"

TOTAL_MODELS=${#MODELS[@]}
TOTAL_ALGORITHMS=${#ALGORITHMS[@]}
TOTAL_RUNS=$((TOTAL_MODELS * TOTAL_ALGORITHMS))
CURRENT=0

for ALGORITHM in "${ALGORITHMS[@]}"; do
    export ALGORITHM="$ALGORITHM"

    echo ""
    echo "========================================"
    echo "ALGORITHM: $(echo $ALGORITHM | tr '[:lower:]' '[:upper:]')"
    echo "========================================"
    echo ""

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))

        echo "========================================"
        echo "Run $CURRENT/$TOTAL_RUNS: $MODEL + $(echo $ALGORITHM | tr '[:lower:]' '[:upper:]')"
        echo "========================================"

        export MODEL="$MODEL"

        # Create log file
        LOG_FILE="$RESULTS_DIR/logs/alternating_hybrid_${MODEL}_${ALGORITHM}_cot_$(date +%Y%m%d_%H%M%S).log"

        # Run evaluation
        "$(dirname "$0")/../../venv/bin/python3" "$(dirname "$0")/alternating_hybrid.py" 2>&1 | tee "$LOG_FILE"

        EXIT_CODE=${PIPESTATUS[0]}

        if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ ERROR: Model $MODEL + $(echo $ALGORITHM | tr '[:lower:]' '[:upper:]') failed with exit code $EXIT_CODE"
            echo "Check log: $LOG_FILE"
        else
            echo "✅ Model $MODEL + $(echo $ALGORITHM | tr '[:lower:]' '[:upper:]') completed successfully"
        fi

        # Move output files to appropriate directories
        # CSV files to raw data
        if [ "$ALGORITHM" == "css" ]; then
            mv "$(dirname "$0")/../../results/hybrids"/alternating_llm_first_${MODEL}_cot_*.csv "$RESULTS_DIR/raw data/" 2>/dev/null || true
            mv "$(dirname "$0")/../../results/hybrids"/summary_alternating_llm_first_${MODEL}_cot_*.json "$RESULTS_DIR/summary stats/" 2>/dev/null || true
        else
            mv "$(dirname "$0")/../../results/hybrids"/alternating_llm_first_${MODEL}_${ALGORITHM}_cot_*.csv "$RESULTS_DIR/raw data/" 2>/dev/null || true
            mv "$(dirname "$0")/../../results/hybrids"/summary_alternating_llm_first_${MODEL}_${ALGORITHM}_cot_*.json "$RESULTS_DIR/summary stats/" 2>/dev/null || true
        fi

        echo ""
    done
done

echo "========================================"
echo "STAGE 3 CoT EVALUATION COMPLETE"
echo "========================================"
echo "Models tested: $TOTAL_MODELS"
echo "Algorithms tested: $TOTAL_ALGORITHMS"
echo "Total runs: $TOTAL_RUNS"
echo "Total games: $((TOTAL_RUNS * 100))"
echo ""
echo "Results saved to:"
echo "  Raw data: $RESULTS_DIR/raw data/"
echo "  Summary stats: $RESULTS_DIR/summary stats/"
echo "  Logs: $RESULTS_DIR/logs/"
echo "========================================"
