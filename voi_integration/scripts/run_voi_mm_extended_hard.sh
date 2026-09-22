#!/usr/bin/env bash
#
# Run Signal Integration Experiment — Mastermind Extended HARD MODE
#
# Extended Mastermind (8 colors, 5 pegs, 32768 codes) with only 5 rounds.
# This forces LLMs to fail in baseline, revealing signal integration's true impact.
#
# 7 models x 100 games x 3 conditions x 2 algorithms = 42 runs
#
# Usage:
#   nohup ./voi_integration/scripts/run_voi_mm_extended_hard.sh >> voi_mm_hard.log 2>&1 &

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PROJECT_ROOT}/venv/bin/python"
EXPERIMENT_SCRIPT="${SCRIPT_DIR}/voi_informed_mastermind.py"
OUTPUT_DIR="${PROJECT_ROOT}/voi_integration/results/mastermind_extended_hard"

# Load .env
ENV_FILE="${PROJECT_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "${NAVIGATOR_UF_API_KEY:-}" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY not set"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "mistral-7b-instruct"
    "granite-3.3-8b-instruct"
    "gemma-3-27b-it"
    "codestral-22b"
)
ALGORITHMS=("css" "voi")
CONDITIONS=("baseline" "voi_informed" "shuffled_ranking")
NUM_GAMES=100
VARIANT="extended"
MAX_ATTEMPTS=5

# Schedule: LLM every round, only 5 rounds
SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm"}'

echo "========================================"
echo "Signal Integration — Mastermind Extended HARD MODE"
echo "========================================"
echo "Models: ${MODELS[*]}"
echo "Algorithms: ${ALGORITHMS[*]}"
echo "Conditions: ${CONDITIONS[*]}"
echo "Games per run: $NUM_GAMES"
echo "Variant: $VARIANT"
echo "Max attempts: $MAX_ATTEMPTS"
echo "Output: $OUTPUT_DIR"
echo "========================================"
echo ""

RUN=0
TOTAL=$(( ${#MODELS[@]} * ${#ALGORITHMS[@]} * ${#CONDITIONS[@]} ))

for MODEL in "${MODELS[@]}"; do
    for ALGO in "${ALGORITHMS[@]}"; do
        RUN_SCHEDULE="$SCHEDULE"

        for COND in "${CONDITIONS[@]}"; do
            RUN=$((RUN + 1))
            CONFIG_NAME="${COND}_${ALGO}"

            # Skip already-completed runs
            EXISTING=$(find "$OUTPUT_DIR" -name "summary_${CONFIG_NAME}_${MODEL}*.json" 2>/dev/null | head -1)
            if [ -n "$EXISTING" ]; then
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
            MAX_ATTEMPTS="$MAX_ATTEMPTS" \
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
