#!/usr/bin/env bash
# All conditions for llama3.2:3b via Ollama (18 runs)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PROJECT_ROOT}/venv/bin/python3"
export PYTHONUNBUFFERED=1

export MODEL="llama3.2:3b"
SAFE_MODEL="llama3.2_3b"
export NUM_GAMES=100

WORDLE_SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
MM_SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
MM_HARD_SCHEDULE='{"1":"llm","2":"llm","3":"llm","4":"llm","5":"llm"}'

CONDITIONS=("baseline" "voi_informed" "shuffled_ranking")
ALGORITHMS=("css" "voi")

RUN=0
TOTAL=18

# ── Wordle ──
OUTPUT_DIR="${PROJECT_ROOT}/voi_integration/results/wordle"
mkdir -p "$OUTPUT_DIR"
export OUTPUT_DIR
export SCHEDULE="$WORDLE_SCHEDULE"
for COND in "${CONDITIONS[@]}"; do
    for ALGO in "${ALGORITHMS[@]}"; do
        RUN=$((RUN + 1))
        export CONDITION="$COND"
        export ALGORITHM="$ALGO"
        export CONFIG_NAME="${COND}_${ALGO}"
        EXISTING=$(find "$OUTPUT_DIR" -name "${CONFIG_NAME}_${SAFE_MODEL}_*.csv" 2>/dev/null | head -1)
        if [ -n "$EXISTING" ] && [ "$(wc -l < "$EXISTING" | tr -d ' ')" -gt 100 ]; then
            echo "[LLAMA-3B $RUN/$TOTAL] SKIPPING: wordle / $CONFIG_NAME"; continue
        fi
        echo "[LLAMA-3B $RUN/$TOTAL] wordle / $CONFIG_NAME"
        "$PYTHON" "${SCRIPT_DIR}/voi_informed_hybrid.py" \
            2>&1 | tee "${OUTPUT_DIR}/${CONFIG_NAME}_${SAFE_MODEL}.log"
        echo "  Done [LLAMA-3B $RUN/$TOTAL]"
    done
done

# ── MM Extended ──
OUTPUT_DIR="${PROJECT_ROOT}/voi_integration/results/mastermind_extended"
mkdir -p "$OUTPUT_DIR"
export OUTPUT_DIR
export SCHEDULE="$MM_SCHEDULE"
export VARIANT="extended"
for COND in "${CONDITIONS[@]}"; do
    for ALGO in "${ALGORITHMS[@]}"; do
        RUN=$((RUN + 1))
        export CONDITION="$COND"
        export ALGORITHM="$ALGO"
        export CONFIG_NAME="${COND}_${ALGO}"
        EXISTING=$(find "$OUTPUT_DIR" -name "${CONFIG_NAME}_${SAFE_MODEL}_*.csv" 2>/dev/null | head -1)
        if [ -n "$EXISTING" ] && [ "$(wc -l < "$EXISTING" | tr -d ' ')" -gt 100 ]; then
            echo "[LLAMA-3B $RUN/$TOTAL] SKIPPING: mm_extended / $CONFIG_NAME"; continue
        fi
        echo "[LLAMA-3B $RUN/$TOTAL] mm_extended / $CONFIG_NAME"
        "$PYTHON" "${SCRIPT_DIR}/voi_informed_mastermind.py" \
            2>&1 | tee "${OUTPUT_DIR}/${CONFIG_NAME}_${SAFE_MODEL}.log"
        echo "  Done [LLAMA-3B $RUN/$TOTAL]"
    done
done

# ── MM Hard ──
OUTPUT_DIR="${PROJECT_ROOT}/voi_integration/results/mastermind"
mkdir -p "$OUTPUT_DIR"
export OUTPUT_DIR
export SCHEDULE="$MM_HARD_SCHEDULE"
export VARIANT="classic"
for COND in "${CONDITIONS[@]}"; do
    for ALGO in "${ALGORITHMS[@]}"; do
        RUN=$((RUN + 1))
        export CONDITION="$COND"
        export ALGORITHM="$ALGO"
        export CONFIG_NAME="${COND}_${ALGO}"
        EXISTING=$(find "$OUTPUT_DIR" -name "${CONFIG_NAME}_${SAFE_MODEL}_*.csv" 2>/dev/null | head -1)
        if [ -n "$EXISTING" ] && [ "$(wc -l < "$EXISTING" | tr -d ' ')" -gt 100 ]; then
            echo "[LLAMA-3B $RUN/$TOTAL] SKIPPING: mm_hard / $CONFIG_NAME"; continue
        fi
        echo "[LLAMA-3B $RUN/$TOTAL] mm_hard / $CONFIG_NAME"
        "$PYTHON" "${SCRIPT_DIR}/voi_informed_mastermind.py" \
            2>&1 | tee "${OUTPUT_DIR}/${CONFIG_NAME}_${SAFE_MODEL}.log"
        echo "  Done [LLAMA-3B $RUN/$TOTAL]"
    done
done

echo "All $TOTAL runs complete!"
