#!/usr/bin/env bash
#
# Run signal integration experiments for gpt-5 and gemini-2.5-pro
#
# Runs baseline + voi_informed conditions for CSS and VOI algorithms
# across Wordle, Mastermind Extended, and Mastermind Extended Hard.
#
# Total: 2 models x 2 algos x 2 conditions x 3 domains = 24 runs (100 games each)
#
# Usage:
#   nohup ./voi_integration/scripts/run_frontier_signal_integration.sh >> frontier_signal.log 2>&1 &

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PROJECT_ROOT}/venv/bin/python3"
WORDLE_SCRIPT="${SCRIPT_DIR}/voi_informed_hybrid.py"
MM_SCRIPT="${SCRIPT_DIR}/voi_informed_mastermind.py"

# Load .env
ENV_FILE="${PROJECT_ROOT}/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "${NAVIGATOR_UF_API_KEY3:-}" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY3 not set"
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: Python not found at $PYTHON"
    exit 1
fi

MODELS=("gpt-5" "gemini-2.5-pro")
ALGORITHMS=("css" "voi")
CONDITIONS=("baseline" "voi_informed")
NUM_GAMES=100

WORDLE_SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
MM_SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
MM_HARD_SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm"}'

echo "========================================"
echo "Frontier Signal Integration (gpt-5 + gemini-2.5-pro)"
echo "========================================"
echo "Models: ${MODELS[*]}"
echo "Algorithms: ${ALGORITHMS[*]}"
echo "Conditions: ${CONDITIONS[*]}"
echo "Games per run: $NUM_GAMES"
echo "Domains: wordle, mastermind_extended, mastermind_extended_hard"
echo "========================================"
echo ""

RUN=0
TOTAL=24  # 2 models x 2 algos x 2 conditions x 3 domains

for MODEL in "${MODELS[@]}"; do

    # ── Wordle ──────────────────────────────────────────────────────────────
    WORDLE_OUTPUT="${PROJECT_ROOT}/voi_integration/results/wordle"
    mkdir -p "$WORDLE_OUTPUT"

    for ALGO in "${ALGORITHMS[@]}"; do
        for COND in "${CONDITIONS[@]}"; do
            RUN=$((RUN + 1))
            CONFIG_NAME="${COND}_${ALGO}"

            EXISTING=$(find "$WORDLE_OUTPUT" -name "${CONFIG_NAME}_${MODEL}_*.csv" 2>/dev/null | head -1)
            if [ -n "$EXISTING" ]; then
                LINES=$(wc -l < "$EXISTING" | tr -d ' ')
                if [ "$LINES" -gt 100 ]; then
                    echo "[$RUN/$TOTAL] SKIPPING (already completed): Wordle / $CONFIG_NAME / $MODEL"
                    continue
                fi
            fi

            echo "[$RUN/$TOTAL] Wordle / $CONFIG_NAME / $MODEL"
            MODEL="$MODEL" \
            NUM_GAMES="$NUM_GAMES" \
            ALGORITHM="$ALGO" \
            CONDITION="$COND" \
            SCHEDULE="$WORDLE_SCHEDULE" \
            CONFIG_NAME="$CONFIG_NAME" \
            OUTPUT_DIR="$WORDLE_OUTPUT" \
            "$PYTHON" "$WORDLE_SCRIPT" \
                2>&1 | tee "${WORDLE_OUTPUT}/${CONFIG_NAME}_${MODEL}.log"
            echo "  Done [$RUN/$TOTAL]"
            echo ""
        done
    done

    # ── Mastermind Extended ─────────────────────────────────────────────────
    MM_EXT_OUTPUT="${PROJECT_ROOT}/voi_integration/results/mastermind_extended"
    mkdir -p "$MM_EXT_OUTPUT"

    for ALGO in "${ALGORITHMS[@]}"; do
        for COND in "${CONDITIONS[@]}"; do
            RUN=$((RUN + 1))
            CONFIG_NAME="${COND}_${ALGO}"

            EXISTING=$(find "$MM_EXT_OUTPUT" -name "${CONFIG_NAME}_${MODEL}_*.csv" 2>/dev/null | head -1)
            if [ -n "$EXISTING" ]; then
                LINES=$(wc -l < "$EXISTING" | tr -d ' ')
                if [ "$LINES" -gt 100 ]; then
                    echo "[$RUN/$TOTAL] SKIPPING (already completed): MM Extended / $CONFIG_NAME / $MODEL"
                    continue
                fi
            fi

            echo "[$RUN/$TOTAL] MM Extended / $CONFIG_NAME / $MODEL"
            MODEL="$MODEL" \
            NUM_GAMES="$NUM_GAMES" \
            ALGORITHM="$ALGO" \
            CONDITION="$COND" \
            SCHEDULE="$MM_SCHEDULE" \
            CONFIG_NAME="$CONFIG_NAME" \
            OUTPUT_DIR="$MM_EXT_OUTPUT" \
            VARIANT="extended" \
            "$PYTHON" "$MM_SCRIPT" \
                2>&1 | tee "${MM_EXT_OUTPUT}/${CONFIG_NAME}_${MODEL}.log"
            echo "  Done [$RUN/$TOTAL]"
            echo ""
        done
    done

    # ── Mastermind Extended Hard ────────────────────────────────────────────
    MM_HARD_OUTPUT="${PROJECT_ROOT}/voi_integration/results/mastermind_extended_hard"
    mkdir -p "$MM_HARD_OUTPUT"

    for ALGO in "${ALGORITHMS[@]}"; do
        for COND in "${CONDITIONS[@]}"; do
            RUN=$((RUN + 1))
            CONFIG_NAME="${COND}_${ALGO}"

            EXISTING=$(find "$MM_HARD_OUTPUT" -name "${CONFIG_NAME}_${MODEL}_*.csv" 2>/dev/null | head -1)
            if [ -n "$EXISTING" ]; then
                LINES=$(wc -l < "$EXISTING" | tr -d ' ')
                if [ "$LINES" -gt 100 ]; then
                    echo "[$RUN/$TOTAL] SKIPPING (already completed): MM Hard / $CONFIG_NAME / $MODEL"
                    continue
                fi
            fi

            echo "[$RUN/$TOTAL] MM Hard / $CONFIG_NAME / $MODEL"
            MODEL="$MODEL" \
            NUM_GAMES="$NUM_GAMES" \
            ALGORITHM="$ALGO" \
            CONDITION="$COND" \
            SCHEDULE="$MM_HARD_SCHEDULE" \
            CONFIG_NAME="$CONFIG_NAME" \
            OUTPUT_DIR="$MM_HARD_OUTPUT" \
            VARIANT="extended" \
            "$PYTHON" "$MM_SCRIPT" \
                2>&1 | tee "${MM_HARD_OUTPUT}/${CONFIG_NAME}_${MODEL}.log"
            echo "  Done [$RUN/$TOTAL]"
            echo ""
        done
    done

done

echo "========================================"
echo "All $TOTAL runs complete!"
echo "========================================"
echo ""
echo "Next step: re-run analysis scripts:"
echo "  venv/bin/python3 voi_integration/scripts/alignment_model_comparison.py"
echo "  venv/bin/python3 voi_integration/scripts/cross_domain_regime_transfer.py"
echo "  venv/bin/python3 voi_integration/scripts/performance_conditioned_analysis.py"
