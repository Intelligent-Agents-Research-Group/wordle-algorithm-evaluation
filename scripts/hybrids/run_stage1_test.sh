#!/bin/bash

################################################################################
# Stage 1 Hybrid Strategy Validation
#
# Quick validation test to determine if hybrid LLM-algorithm strategies show
# promise compared to pure approaches.
#
# Test Configuration:
# - 3 representative LLM models
# - 4 hybrid strategies
# - 10 games per combination (30 total games per strategy)
# - Total: 120 games with LLM calls
# - Estimated runtime: 2-3 hours
#
# Models tested:
# 1. mistral-small-3.1 (best pure LLM: 100% win, 4.30 avg attempts)
# 2. llama-3.3-70b-instruct (popular, strong: 93-95% win)
# 3. mistral-7b-instruct (smaller/faster: 95-98% win)
#
# Output: results/hybrids/stage1/
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
echo "STAGE 1: HYBRID STRATEGY VALIDATION TEST"
echo "================================================================================"
echo ""
echo "This test runs a quick validation (10 games each) with 3 representative models"
echo "to determine if hybrid strategies show promise before full evaluation."
echo ""
echo "Models: mistral-small-3.1, llama-3.3-70b-instruct, mistral-7b-instruct"
echo "Strategies: 4 (llm-then-css, css-then-llm, threshold, alternating)"
echo "Games per run: 10"
echo "Total games: 120"
echo "Estimated time: 2-3 hours"
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
export NUM_GAMES=10
export NAVIGATOR_API_ENDPOINT="${NAVIGATOR_API_ENDPOINT:-https://api.navigator.uf.edu/v1}"

# Models to test
MODELS=(
    "mistral-small-3.1"
    "llama-3.3-70b-instruct"
    "mistral-7b-instruct"
)

# Strategies to test
STRATEGIES=(
    "llm_then_css"
    "css_then_llm"
    "threshold_hybrid"
    "alternating_hybrid"
)

# Create output directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OUTPUT_DIR="$SCRIPT_DIR/../../results/hybrids/stage1"
mkdir -p "$OUTPUT_DIR"

# Create log directory
LOG_DIR="$OUTPUT_DIR/logs"
mkdir -p "$LOG_DIR"

# Track start time
START_TIME=$(date +%s)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "Output directory: $OUTPUT_DIR"
echo "Log directory: $LOG_DIR"
echo ""
echo "================================================================================"

# Counter for progress
TOTAL_RUNS=$((${#MODELS[@]} * ${#STRATEGIES[@]}))
CURRENT_RUN=0

# Run evaluations
for MODEL in "${MODELS[@]}"; do
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}MODEL: $MODEL${NC}"
    echo -e "${BLUE}============================================================${NC}"

    for STRATEGY in "${STRATEGIES[@]}"; do
        CURRENT_RUN=$((CURRENT_RUN + 1))

        echo ""
        echo -e "${GREEN}[$CURRENT_RUN/$TOTAL_RUNS] Running: $STRATEGY with $MODEL${NC}"
        echo "-----------------------------------------------------------"

        # Set model
        export MODEL="$MODEL"

        # Log file
        LOG_FILE="$LOG_DIR/${STRATEGY}_${MODEL}_${TIMESTAMP}.log"

        # Run strategy
        echo "Started: $(date)"
        if "$SCRIPT_DIR/../../venv/bin/python3" "$SCRIPT_DIR/${STRATEGY}.py" > "$LOG_FILE" 2>&1; then
            echo -e "${GREEN}✓ Completed successfully${NC}"
        else
            echo -e "${RED}✗ Failed - check log: $LOG_FILE${NC}"
        fi
        echo "Log: $LOG_FILE"

        # Brief pause between runs
        sleep 2
    done
done

# Calculate runtime
END_TIME=$(date +%s)
RUNTIME=$((END_TIME - START_TIME))
HOURS=$((RUNTIME / 3600))
MINUTES=$(((RUNTIME % 3600) / 60))
SECONDS=$((RUNTIME % 60))

echo ""
echo "================================================================================"
echo -e "${GREEN}STAGE 1 TESTING COMPLETE${NC}"
echo "================================================================================"
echo ""
echo "Runtime: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Total runs: $TOTAL_RUNS"
echo ""
echo "Results saved to: $OUTPUT_DIR"
echo "Logs saved to: $LOG_DIR"
echo ""
echo "================================================================================"
echo "NEXT STEPS:"
echo "================================================================================"
echo ""
echo "1. Analyze results to compare hybrid vs pure approaches:"
echo "   - Pure CSS baseline: 98% win rate, 3.79 avg attempts"
echo "   - Pure LLM baseline: 93-100% win rate, 4.03-4.47 avg attempts"
echo ""
echo "2. If any hybrid beats pure CSS (< 3.79 attempts):"
echo "   → Proceed to Stage 2: Full evaluation (100 games) with best strategy"
echo ""
echo "3. If hybrids show mixed results:"
echo "   → Test top 2 strategies with full evaluation"
echo ""
echo "4. If hybrids don't improve over pure approaches:"
echo "   → Document findings, hybrids don't provide benefit"
echo ""
echo "5. Generate summary analysis:"
echo "   cd $SCRIPT_DIR"
echo "   ../../venv/bin/python3 analyze_stage1_results.py"
echo ""
echo "================================================================================"
