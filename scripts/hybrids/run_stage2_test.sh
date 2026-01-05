#!/bin/bash

################################################################################
# Stage 2 Hybrid Strategy Validation
#
# Full evaluation (100 games) of the most promising strategies from Stage 1.
#
# Test Configuration:
# - 2 best models from Stage 1
# - 2 best strategies from Stage 1
# - 100 games per combination (full canonical test set)
# - Total: 400 games with LLM calls
# - Estimated runtime: 1-2 hours
#
# Models tested:
# 1. llama-3.3-70b-instruct (best in Stage 1: 3.60 avg)
# 2. mistral-7b-instruct (second best: 3.67 avg)
#
# Strategies tested:
# 1. llm_then_css (Stage 1 winner: 3.60 avg with llama)
# 2. alternating_hybrid (Stage 1 runner-up: 3.67 avg with mistral-7b)
#
# Output: results/hybrids/stage2/
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
echo "STAGE 2: HYBRID STRATEGY FULL EVALUATION"
echo "================================================================================"
echo ""
echo "This test runs full 100-game evaluation on the best performing strategies"
echo "from Stage 1 to validate performance with larger sample size."
echo ""
echo "Models: llama-3.3-70b-instruct, mistral-7b-instruct"
echo "Strategies: llm_then_css, alternating_hybrid"
echo "Games per run: 100"
echo "Total games: 400"
echo "Estimated time: 1-2 hours"
echo ""
echo "Stage 1 Results to Beat:"
echo "  - llm_then_css + llama-3.3-70b: 3.60 avg (100% win rate)"
echo "  - alternating + mistral-7b: 3.67 avg (90% win rate)"
echo "  - Pure CSS baseline: 3.79 avg (98% win rate)"
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

# Models to test (best performers from Stage 1)
MODELS=(
    "llama-3.3-70b-instruct"
    "mistral-7b-instruct"
)

# Strategies to test (best performers from Stage 1)
STRATEGIES=(
    "llm_then_css"
    "alternating_hybrid"
)

# Create output directory structure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$SCRIPT_DIR/../../results/hybrids/stage2"
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
        echo -e "${GREEN}[$CURRENT_RUN/$TOTAL_RUNS] Running: $STRATEGY with $MODEL (100 games)${NC}"
        echo "-----------------------------------------------------------"

        # Set model
        export MODEL="$MODEL"

        # Log file
        LOG_FILE="$LOG_DIR/${STRATEGY}_${MODEL}_${TIMESTAMP}.log"

        # Run strategy
        echo "Started: $(date)"
        if "$SCRIPT_DIR/../../venv/bin/python3" "$SCRIPT_DIR/${STRATEGY}.py" > "$LOG_FILE" 2>&1; then
            echo -e "${GREEN}✓ Completed successfully${NC}"

            # Show quick summary from the log
            echo -e "${YELLOW}Quick Summary:${NC}"
            tail -8 "$LOG_FILE" | grep -E "Win Rate|Average Attempts" || echo "  (see log for details)"
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
echo -e "${GREEN}STAGE 2 TESTING COMPLETE${NC}"
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
echo "NEXT STEPS:"
echo "================================================================================"
echo ""
echo "1. Analyze Stage 2 results in summary stats directory"
echo ""
echo "2. Compare to baselines:"
echo "   - Stage 1: llm_then_css + llama: 3.60 avg (10 games)"
echo "   - Pure CSS: 3.79 avg (100 games)"
echo "   - Pure LLM best: 4.03 avg (100 games)"
echo ""
echo "3. If Stage 2 confirms < 3.79 avg:"
echo "   → Proceed to Stage 3: Test with all 11 models"
echo ""
echo "4. If Stage 2 shows ~3.79 or higher:"
echo "   → Document that hybrids match but don't beat CSS"
echo ""
echo "5. Create summary document:"
echo "   cd $SCRIPT_DIR"
echo "   # Analyze results and create docs/hybrids_stage2_results.md"
echo ""
echo "================================================================================"
