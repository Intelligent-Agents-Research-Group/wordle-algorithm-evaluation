#!/usr/bin/env bash
#
# Run CoT Reasoning Trace Experiments
#
# 3 models x 2 domains x 2 algorithms = 12 runs, 30 games each
# Total: 360 games with full reasoning traces
#
# Usage:
#   ./voi_integration/scripts/run_cot_traces.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PROJECT_ROOT}/venv/bin/python"
EXPERIMENT_SCRIPT="${SCRIPT_DIR}/cot_trace_experiment.py"
OUTPUT_DIR="${PROJECT_ROOT}/voi_integration/results/cot_traces"

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
    "granite-3.3-8b-instruct"
    "codestral-22b"
    "llama-3.3-70b-instruct"
    "gpt-oss-120b"
    "claude-4-sonnet"
)
DOMAINS=("wordle" "mastermind")
ALGORITHMS=("css" "voi")
NUM_GAMES=30

echo "========================================"
echo "CoT Reasoning Trace Experiment"
echo "========================================"
echo "Models: ${MODELS[*]}"
echo "Domains: ${DOMAINS[*]}"
echo "Algorithms: ${ALGORITHMS[*]}"
echo "Games per run: $NUM_GAMES"
echo "Output: $OUTPUT_DIR"
echo "========================================"
echo ""

RUN=0
TOTAL=$(( ${#MODELS[@]} * ${#DOMAINS[@]} * ${#ALGORITHMS[@]} ))

for DOMAIN in "${DOMAINS[@]}"; do
    for ALGO in "${ALGORITHMS[@]}"; do
        for MODEL in "${MODELS[@]}"; do
            RUN=$((RUN + 1))

            # Skip if already completed
            EXISTING=$(find "$OUTPUT_DIR" -name "cot_traces_${DOMAIN}_${ALGO}_${MODEL}*.json" 2>/dev/null | head -1)
            if [ -n "$EXISTING" ]; then
                GAMES=$(python3 -c "import json; print(json.load(open('$EXISTING'))['num_games'])" 2>/dev/null || echo 0)
                if [ "$GAMES" -eq "$NUM_GAMES" ]; then
                    echo "[$RUN/$TOTAL] SKIPPING (already completed): $DOMAIN / $ALGO / $MODEL"
                    continue
                fi
            fi

            echo "[$RUN/$TOTAL] Domain=$DOMAIN  Algo=$ALGO  Model=$MODEL"

            DOMAIN="$DOMAIN" \
            ALGORITHM="$ALGO" \
            MODEL="$MODEL" \
            NUM_GAMES="$NUM_GAMES" \
            OUTPUT_DIR="$OUTPUT_DIR" \
            "$PYTHON" "$EXPERIMENT_SCRIPT" \
                2>&1 | tee "${OUTPUT_DIR}/cot_${DOMAIN}_${ALGO}_${MODEL}.log"

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
