#!/usr/bin/env bash
#
# Run the VOI-Informed Integration Experiment for Mastermind
#
# Full experiment: 8 models x 100 games x 3 conditions x 2 algorithms = 48 runs
#
# Usage:
#   ./voi_integration/scripts/run_voi_mastermind_experiment.sh
#
# Required env vars:
#   NAVIGATOR_UF_API_KEY - API key for open-source models on Navigator

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PROJECT_ROOT}/venv/bin/python"
EXPERIMENT_SCRIPT="${SCRIPT_DIR}/voi_informed_mastermind.py"
OUTPUT_DIR="${PROJECT_ROOT}/voi_integration/results/mastermind"

# Load .env
ENV_FILE="${PROJECT_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Check prerequisites
if [ -z "${NAVIGATOR_UF_API_KEY:-}" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY not set"
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: Python venv not found at $PYTHON"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Experiment parameters
MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "llama-3.1-nemotron-nano-8b-v1"
    "mistral-7b-instruct"
    "granite-3.3-8b-instruct"
    "gemma-3-27b-it"
    "codestral-22b"
)
ALGORITHMS=("css" "voi")
CONDITIONS=("baseline" "voi_informed" "shuffled_ranking")
NUM_GAMES=100
VARIANT="classic"

# Schedule: LLM every round (algorithm provides signals in informed/shuffled conditions)
SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'

echo "========================================"
echo "VOI-Informed Integration Experiment (Mastermind)"
echo "========================================"
echo "Models: ${MODELS[*]}"
echo "Algorithms: ${ALGORITHMS[*]}"
echo "Conditions: ${CONDITIONS[*]}"
echo "Games per run: $NUM_GAMES"
echo "Variant: $VARIANT"
echo "Output: $OUTPUT_DIR"
echo "========================================"
echo ""

RUN=0
TOTAL=$(( ${#MODELS[@]} * ${#ALGORITHMS[@]} * ${#CONDITIONS[@]} ))

for MODEL in "${MODELS[@]}"; do
    for ALGO in "${ALGORITHMS[@]}"; do
        # Build schedule with correct algorithm
        RUN_SCHEDULE="${SCHEDULE//ALGO/$ALGO}"

        for COND in "${CONDITIONS[@]}"; do
            RUN=$((RUN + 1))
            CONFIG_NAME="${COND}_${ALGO}"

            # Skip already-completed runs
            EXISTING=$(find "$OUTPUT_DIR" -name "summary_${CONFIG_NAME}_${MODEL}*.json" -newer "$EXPERIMENT_SCRIPT" 2>/dev/null | head -1)
            if [ -n "$EXISTING" ]; then
                # Verify it has real results (win_rate > 0 or it's a valid baseline)
                GAMES=$(python3 -c "import json; print(json.load(open('$EXISTING'))['total_games'])" 2>/dev/null || echo 0)
                WINS=$(python3 -c "import json; print(json.load(open('$EXISTING'))['wins'])" 2>/dev/null || echo -1)
                if [ "$GAMES" -eq "$NUM_GAMES" ] && [ "$WINS" -ge 0 ]; then
                    echo "[$RUN/$TOTAL] SKIPPING (already completed): $CONFIG_NAME / $MODEL"
                    echo "  Found: $EXISTING"
                    echo "----------------------------------------"
                    echo ""
                    continue
                fi
            fi

            echo "[$RUN/$TOTAL] Model=$MODEL  Algo=$ALGO  Condition=$COND"
            echo "  Schedule: $RUN_SCHEDULE"
            echo "  Config: $CONFIG_NAME"

            MODEL="$MODEL" \
            NUM_GAMES="$NUM_GAMES" \
            ALGORITHM="$ALGO" \
            CONDITION="$COND" \
            SCHEDULE="$RUN_SCHEDULE" \
            CONFIG_NAME="$CONFIG_NAME" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            VARIANT="$VARIANT" \
            "$PYTHON" "$EXPERIMENT_SCRIPT" \
                2>&1 | tee "${OUTPUT_DIR}/${CONFIG_NAME}_${MODEL}.log"

            echo ""
            echo "  Completed run $RUN/$TOTAL"
            echo "----------------------------------------"
            echo ""
        done
    done
done

echo "========================================"
echo "All $TOTAL runs complete!"
echo "Results in: $OUTPUT_DIR"
echo "========================================"
