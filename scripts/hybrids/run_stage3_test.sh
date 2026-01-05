#!/bin/bash

################################################################################
# Stage 3 Hybrid Strategy Comprehensive Evaluation
#
# Comprehensive evaluation across all 11 LLM models to demonstrate consistency
# and reproducibility of hybrid strategy performance.
#
# Research Goal: Show that hybrid performance is CONSISTENT across models,
# not to find improvement over CSS. This provides robust evidence that hybrids
# perform at ~4.0-4.2 avg attempts regardless of LLM choice.
#
# Test Configuration:
# - All 11 LLM models (same as pure LLM evaluation)
# - Best hybrid strategy from Stage 2: alternating_llm_first
# - 100 games per model (full canonical test set)
# - Total: 1,100 games with LLM calls
# - Estimated runtime: 2-3 hours
#
# Models tested (all 11):
# 1. llama-3.3-70b-instruct
# 2. llama-3.1-70b-instruct
# 3. llama-3.1-8b-instruct
# 4. llama-3.1-nemotron-nano-8B-v1
# 5. mistral-small-3.1
# 6. mistral-7b-instruct
# 7. codestral-22b
# 8. gemma-3-27b-it
# 9. granite-3.3-8b-instruct
# 10. gpt-oss-120b
# 11. gpt-oss-20b
#
# Expected Result: All models perform at ~4.0-4.2 avg attempts,
# consistently worse than pure CSS (3.79), demonstrating that
# hybrids do not improve performance regardless of LLM choice.
#
# Output: results/hybrids/stage3/
################################################################################

set -e  # Exit on error

# Load .env file if it exists
if [ -f "$(dirname "$0")/../../.env" ]; then
    set -a
    source "$(dirname "$0")/../../.env"
    set +a
    echo "Loaded .env file"
elif [ -f "$(dirname "$0")/.env" ]; then
    set -a
    source "$(dirname "$0")/.env"
    set +a
    echo "Loaded .env file"
fi

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "STAGE 3: HYBRID STRATEGY COMPREHENSIVE EVALUATION"
echo "================================================================================"
echo ""
echo "This test evaluates the best hybrid strategy across all 11 LLM models to"
echo "demonstrate consistency and reproducibility of performance."
echo ""
echo "Research Goal: Show consistent performance across models (~4.0-4.2 avg)"
echo "Strategy: alternating_llm_first (best from Stage 2: 4.05 avg with llama)"
echo "Models: All 11 LLMs from original evaluation"
echo "Games per model: 100"
echo "Total games: 1,100"
echo "Estimated time: 2-3 hours"
echo ""
echo "Performance Baselines:"
echo "  - Pure CSS: 3.79 avg (98% win)"
echo "  - Stage 2 hybrid best: 4.05 avg (92% win)"
echo ""
echo "Expected: All models perform at ~4.0-4.2 avg (consistently worse than CSS)"
echo ""
echo "================================================================================"

# Check for API key
if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo -e "${RED}ERROR: NAVIGATOR_UF_API_KEY environment variable not set${NC}"
    echo "Please set your API key:"
    echo "  export NAVIGATOR_UF_API_KEY='your-key-here'"
    exit 1
fi

# Configuration
export NUM_GAMES=100
export NAVIGATOR_API_ENDPOINT="${NAVIGATOR_API_ENDPOINT:-https://api.navigator.uf.edu/v1}"

# All 11 models (same as original LLM evaluation)
MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "llama-3.1-nemotron-nano-8B-v1"
    "mistral-small-3.1"
    "mistral-7b-instruct"
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "gpt-oss-120b"
    "gpt-oss-20b"
)

# Best strategy from Stage 2
STRATEGY="alternating_hybrid"

# Create output directory structure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$SCRIPT_DIR/../../results/hybrids/stage3"
RAW_DATA_DIR="$BASE_DIR/raw data"
SUMMARY_DIR="$BASE_DIR/summary stats"
LOG_DIR="$BASE_DIR/logs"

mkdir -p "$BASE_DIR"
mkdir -p "$RAW_DATA_DIR"
mkdir -p "$SUMMARY_DIR"
mkdir -p "$LOG_DIR"

# Track start time
START_TIME=$(date +%s)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "Output directories:"
echo "  Base: $BASE_DIR"
echo "  Raw data (CSV): $RAW_DATA_DIR"
echo "  Summary stats (JSON): $SUMMARY_DIR"
echo "  Logs: $LOG_DIR"
echo ""
echo "================================================================================"

# Counter for progress
TOTAL_RUNS=${#MODELS[@]}
CURRENT_RUN=0

# Run evaluations
for MODEL in "${MODELS[@]}"; do
    CURRENT_RUN=$((CURRENT_RUN + 1))

    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}[$CURRENT_RUN/$TOTAL_RUNS] MODEL: $MODEL${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""

    # Set model
    export MODEL="$MODEL"

    # Log file
    LOG_FILE="$LOG_DIR/${STRATEGY}_${MODEL}_${TIMESTAMP}.log"

    # Run strategy
    echo "Started: $(date)"
    if "$SCRIPT_DIR/../../venv/bin/python3" "$SCRIPT_DIR/${STRATEGY}.py" > "$LOG_FILE" 2>&1; then
        echo -e "${GREEN}✓ Completed successfully${NC}"

        # Extract and show summary from the log
        echo -e "${YELLOW}Summary:${NC}"
        tail -10 "$LOG_FILE" | grep -E "Win Rate|Average Attempts|Total Games" | head -3 || echo "  (see log for details)"
    else
        echo -e "${RED}✗ Failed - check log: $LOG_FILE${NC}"
    fi
    echo "Log: $LOG_FILE"

    # Brief pause between runs
    sleep 2
done

# Calculate runtime
END_TIME=$(date +%s)
RUNTIME=$((END_TIME - START_TIME))
HOURS=$((RUNTIME / 3600))
MINUTES=$(((RUNTIME % 3600) / 60))
SECONDS=$((RUNTIME % 60))

echo ""
echo "================================================================================"
echo -e "${GREEN}STAGE 3 TESTING COMPLETE${NC}"
echo "================================================================================"
echo ""
echo "Runtime: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Total runs: $TOTAL_RUNS"
echo ""

# Organize output files
echo "Organizing output files..."
PARENT_DIR="$SCRIPT_DIR/../../results/hybrids"

# Move CSV files to raw data directory
mv "$PARENT_DIR"/*.csv "$RAW_DATA_DIR/" 2>/dev/null && echo "  ✓ Moved CSV files to raw data/" || echo "  • No CSV files to move"

# Move JSON files to summary stats directory
mv "$PARENT_DIR"/summary_*.json "$SUMMARY_DIR/" 2>/dev/null && echo "  ✓ Moved JSON files to summary stats/" || echo "  • No JSON files to move"

echo ""
echo "Results organized in: $BASE_DIR"
echo "  - Raw data (CSV): $RAW_DATA_DIR"
echo "  - Summary stats (JSON): $SUMMARY_DIR"
echo "  - Logs: $LOG_DIR"
echo ""
echo "================================================================================"
echo "ANALYSIS SUMMARY"
echo "================================================================================"
echo ""
echo "Stage 3 provides comprehensive evidence across all 11 models."
echo ""
echo "Expected findings:"
echo "  1. Consistent performance: All models at ~4.0-4.2 avg attempts"
echo "  2. All worse than CSS: None beat 3.79 avg baseline"
echo "  3. Model-independent: Finding holds regardless of LLM choice"
echo "  4. Reproducible: Results consistent with Stage 2"
echo ""
echo "This demonstrates that hybrid approaches do not improve Wordle-solving"
echo "performance, regardless of which LLM is used."
echo ""
echo "================================================================================"
echo "NEXT STEPS:"
echo "================================================================================"
echo ""
echo "1. Analyze all 11 model results in summary stats directory"
echo ""
echo "2. Generate comprehensive summary document:"
echo "   - Performance distribution across models"
echo "   - Comparison to pure CSS and pure LLM baselines"
echo "   - Statistical analysis of consistency"
echo "   - Final conclusions for publication"
echo ""
echo "3. Create final summary: docs/hybrids_stage3_results.md"
echo ""
echo "4. Update main results documentation with hybrid findings"
echo ""
echo "5. Prepare publication figures comparing:"
echo "   - Pure CSS vs Pure LLMs vs Hybrids"
echo "   - Consistency across models"
echo "   - Cost-benefit analysis"
echo ""
echo "================================================================================"
