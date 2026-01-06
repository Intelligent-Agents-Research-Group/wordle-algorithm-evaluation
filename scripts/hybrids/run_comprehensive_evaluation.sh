#!/bin/bash

# Comprehensive Hybrid Evaluation Script
# Runs both zero-shot and CoT evaluations across all algorithms

# Load .env file
set -a
source "$(dirname "$0")/../../.env"
set +a

echo "========================================"
echo "COMPREHENSIVE HYBRID EVALUATION"
echo "========================================"
echo "Strategy: alternating_llm_first"
echo "Prompt Types: Zero-shot + CoT"
echo "Algorithms: CSS, VOI, Random (filtered)"
echo ""
echo "ZERO-SHOT EVALUATIONS:"
echo "  - VOI: 9 models × 100 games = 900 games"
echo "  - Random: 9 models × 100 games = 900 games"
echo "  - (CSS already completed)"
echo ""
echo "CoT EVALUATIONS:"
echo "  - CSS: 9 models × 100 games = 900 games"
echo "  - VOI: 9 models × 100 games = 900 games"
echo "  - Random: 9 models × 100 games = 900 games"
echo ""
echo "TOTAL: 4,500 games"
echo "========================================"
echo ""

# Create output directories
RESULTS_DIR_ZEROSHOT="$(dirname "$0")/../../results/hybrids/stage3"
RESULTS_DIR_COT="$(dirname "$0")/../../results/hybrids/stage3-cot"

mkdir -p "$RESULTS_DIR_ZEROSHOT/raw data"
mkdir -p "$RESULTS_DIR_ZEROSHOT/summary stats"
mkdir -p "$RESULTS_DIR_ZEROSHOT/logs"

mkdir -p "$RESULTS_DIR_COT/raw data"
mkdir -p "$RESULTS_DIR_COT/summary stats"
mkdir -p "$RESULTS_DIR_COT/logs"

# Array of models to test (same 9 models from Stage 3)
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

# Export common configuration
export NUM_GAMES=100
export START_WITH="llm"

TOTAL_MODELS=${#MODELS[@]}
TOTAL_RUNS=0
CURRENT=0

# Calculate total runs
# Zero-shot: VOI + Random = 2 algorithms × 9 models = 18 runs
# CoT: CSS + VOI + Random = 3 algorithms × 9 models = 27 runs
# Total = 45 runs
TOTAL_RUNS=$((TOTAL_MODELS * 2 + TOTAL_MODELS * 3))

echo "Starting evaluation..."
echo "Total runs: $TOTAL_RUNS"
echo ""

# ============================================
# PART 1: ZERO-SHOT EVALUATIONS (VOI + Random)
# ============================================

echo ""
echo "========================================"
echo "PART 1: ZERO-SHOT EVALUATIONS"
echo "========================================"
echo ""

export PROMPT_TYPE="zero-shot"

for ALGORITHM in "voi" "random"; do
    export ALGORITHM="$ALGORITHM"
    ALGO_UPPER=$(echo $ALGORITHM | tr '[:lower:]' '[:upper:]')

    echo ""
    echo "========================================"
    echo "ALGORITHM: $ALGO_UPPER (Zero-shot)"
    echo "========================================"
    echo ""

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))

        echo "========================================"
        echo "Run $CURRENT/$TOTAL_RUNS: $MODEL + $ALGO_UPPER (zero-shot)"
        echo "========================================"

        export MODEL="$MODEL"

        # Create log file
        LOG_FILE="$RESULTS_DIR_ZEROSHOT/logs/alternating_hybrid_${MODEL}_${ALGORITHM}_zeroshot_$(date +%Y%m%d_%H%M%S).log"

        # Run evaluation
        "$(dirname "$0")/../../venv/bin/python3" "$(dirname "$0")/alternating_hybrid.py" 2>&1 | tee "$LOG_FILE"

        EXIT_CODE=${PIPESTATUS[0]}

        if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ ERROR: $MODEL + $ALGO_UPPER (zero-shot) failed with exit code $EXIT_CODE"
            echo "Check log: $LOG_FILE"
        else
            echo "✅ $MODEL + $ALGO_UPPER (zero-shot) completed successfully"
        fi

        # Move output files to appropriate directories
        mv "$(dirname "$0")/../../results/hybrids"/alternating_llm_first_${MODEL}_${ALGORITHM}_*.csv "$RESULTS_DIR_ZEROSHOT/raw data/" 2>/dev/null || true
        mv "$(dirname "$0")/../../results/hybrids"/summary_alternating_llm_first_${MODEL}_${ALGORITHM}_*.json "$RESULTS_DIR_ZEROSHOT/summary stats/" 2>/dev/null || true

        echo ""
    done
done

# ============================================
# PART 2: CoT EVALUATIONS (CSS + VOI + Random)
# ============================================

echo ""
echo "========================================"
echo "PART 2: CoT EVALUATIONS"
echo "========================================"
echo ""

export PROMPT_TYPE="cot"

for ALGORITHM in "css" "voi" "random"; do
    export ALGORITHM="$ALGORITHM"
    ALGO_UPPER=$(echo $ALGORITHM | tr '[:lower:]' '[:upper:]')

    echo ""
    echo "========================================"
    echo "ALGORITHM: $ALGO_UPPER (CoT)"
    echo "========================================"
    echo ""

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))

        echo "========================================"
        echo "Run $CURRENT/$TOTAL_RUNS: $MODEL + $ALGO_UPPER (CoT)"
        echo "========================================"

        export MODEL="$MODEL"

        # Create log file
        LOG_FILE="$RESULTS_DIR_COT/logs/alternating_hybrid_${MODEL}_${ALGORITHM}_cot_$(date +%Y%m%d_%H%M%S).log"

        # Run evaluation
        "$(dirname "$0")/../../venv/bin/python3" "$(dirname "$0")/alternating_hybrid.py" 2>&1 | tee "$LOG_FILE"

        EXIT_CODE=${PIPESTATUS[0]}

        if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ ERROR: $MODEL + $ALGO_UPPER (CoT) failed with exit code $EXIT_CODE"
            echo "Check log: $LOG_FILE"
        else
            echo "✅ $MODEL + $ALGO_UPPER (CoT) completed successfully"
        fi

        # Move output files to appropriate directories
        if [ "$ALGORITHM" == "css" ]; then
            mv "$(dirname "$0")/../../results/hybrids"/alternating_llm_first_${MODEL}_cot_*.csv "$RESULTS_DIR_COT/raw data/" 2>/dev/null || true
            mv "$(dirname "$0")/../../results/hybrids"/summary_alternating_llm_first_${MODEL}_cot_*.json "$RESULTS_DIR_COT/summary stats/" 2>/dev/null || true
        else
            mv "$(dirname "$0")/../../results/hybrids"/alternating_llm_first_${MODEL}_${ALGORITHM}_cot_*.csv "$RESULTS_DIR_COT/raw data/" 2>/dev/null || true
            mv "$(dirname "$0")/../../results/hybrids"/summary_alternating_llm_first_${MODEL}_${ALGORITHM}_cot_*.json "$RESULTS_DIR_COT/summary stats/" 2>/dev/null || true
        fi

        echo ""
    done
done

echo ""
echo "========================================"
echo "COMPREHENSIVE EVALUATION COMPLETE"
echo "========================================"
echo "Total runs completed: $TOTAL_RUNS"
echo "Total games played: $((TOTAL_RUNS * 100))"
echo ""
echo "ZERO-SHOT Results saved to:"
echo "  Raw data: $RESULTS_DIR_ZEROSHOT/raw data/"
echo "  Summary stats: $RESULTS_DIR_ZEROSHOT/summary stats/"
echo "  Logs: $RESULTS_DIR_ZEROSHOT/logs/"
echo ""
echo "CoT Results saved to:"
echo "  Raw data: $RESULTS_DIR_COT/raw data/"
echo "  Summary stats: $RESULTS_DIR_COT/summary stats/"
echo "  Logs: $RESULTS_DIR_COT/logs/"
echo "========================================"
