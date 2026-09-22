#!/bin/bash
#
# Run True CSS Hybrid Evaluation
# Tests alternating LLM + True CSS (minimax regret) strategy on all models
#
# Usage:
#   ./run_true_css_hybrid_evaluation.sh [num_games] [prompt_type]
#
# Examples:
#   ./run_true_css_hybrid_evaluation.sh 100 zero-shot   # Full evaluation, zero-shot
#   ./run_true_css_hybrid_evaluation.sh 10 zero-shot    # Quick test
#   ./run_true_css_hybrid_evaluation.sh 100 cot         # Full evaluation, CoT
#

set -e

# Configuration
NUM_GAMES=${1:-100}
PROMPT_TYPE=${2:-zero-shot}
ALGORITHM="css_true"
START_WITH="llm"

# Models to evaluate (same as original CSS hybrid tests)
MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "llama-3.1-nemotron-nano-8B-v1"
    "mistral-7b-instruct"
    "mistral-small-3.1"
)

# Get directories first
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load .env file if it exists
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Check for API key
if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY environment variable not set"
    echo "Please set it with: export NAVIGATOR_UF_API_KEY='your-api-key'"
    echo "Or create a .env file in the project root"
    exit 1
fi

# Create results directory

if [ "$PROMPT_TYPE" == "cot" ]; then
    RESULTS_DIR="$PROJECT_DIR/results/hybrids/stage3_true_css_cot/raw data"
else
    RESULTS_DIR="$PROJECT_DIR/results/hybrids/stage3_true_css/raw data"
fi

mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "TRUE CSS HYBRID EVALUATION"
echo "========================================"
echo "Algorithm: $ALGORITHM (Minimax Regret + Witness Targeting)"
echo "Start with: $START_WITH"
echo "Prompt type: $PROMPT_TYPE"
echo "Games per model: $NUM_GAMES"
echo "Results directory: $RESULTS_DIR"
echo "Models to test: ${#MODELS[@]}"
echo "========================================"
echo ""

# Track progress
TOTAL=${#MODELS[@]}
CURRENT=0
FAILED=()

for MODEL in "${MODELS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "========================================"
    echo "[$CURRENT/$TOTAL] Testing model: $MODEL"
    echo "========================================"

    # Run the evaluation
    if MODEL="$MODEL" \
       NUM_GAMES="$NUM_GAMES" \
       START_WITH="$START_WITH" \
       PROMPT_TYPE="$PROMPT_TYPE" \
       ALGORITHM="$ALGORITHM" \
       OUTPUT_DIR="$RESULTS_DIR" \
       python "$SCRIPT_DIR/alternating_hybrid.py"; then
        echo "SUCCESS: $MODEL completed"
    else
        echo "FAILED: $MODEL"
        FAILED+=("$MODEL")
    fi

    # Small delay between models to avoid rate limiting
    sleep 2
done

echo ""
echo "========================================"
echo "EVALUATION COMPLETE"
echo "========================================"
echo "Total models: $TOTAL"
echo "Successful: $((TOTAL - ${#FAILED[@]}))"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo ""
    echo "Failed models:"
    for MODEL in "${FAILED[@]}"; do
        echo "  - $MODEL"
    done
fi

echo ""
echo "Results saved to: $RESULTS_DIR"
echo "========================================"
