#!/bin/bash
#
# Run Missing Experiments
#
# Wordle L_to_C: llama-3.3-70b-instruct, llama-3.1-70b-instruct, llama-3.1-8b-instruct
# Mastermind L_to_C: llama-3.3-70b-instruct, llama-3.1-70b-instruct, llama-3.1-8b-instruct
# Mastermind css3_to_L: mistral-7b-instruct
#
# Usage: ./run_missing_experiments.sh [num_games]

set -e

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Use venv python directly
PYTHON="$PROJECT_DIR/venv/bin/python3"

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY not set"
    exit 1
fi

echo "========================================"
echo "RUNNING MISSING EXPERIMENTS"
echo "========================================"
echo "Games per run: $NUM_GAMES"
echo ""

FAILED=()
TOTAL=7
CURRENT=0

# --- WORDLE L_to_C ---
WORDLE_L_TO_C_MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
)

SCHEDULE_L_TO_C='{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
WORDLE_OUTPUT_DIR="$PROJECT_DIR/results/workshop/group_a/L_to_C/raw_data"
mkdir -p "$WORDLE_OUTPUT_DIR"

for MODEL in "${WORDLE_L_TO_C_MODELS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "========================================"
    echo "[$CURRENT/$TOTAL] WORDLE L_to_C | $MODEL"
    echo "========================================"

    if CONFIG_NAME="L_to_C" \
       SCHEDULE="$SCHEDULE_L_TO_C" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$MODEL" \
       PROMPT_TYPE="zero-shot" \
       OUTPUT_DIR="$WORDLE_OUTPUT_DIR" \
       $PYTHON "$SCRIPT_DIR/flexible_hybrid.py"; then
        echo "SUCCESS: WORDLE L_to_C $MODEL"
    else
        echo "FAILED: WORDLE L_to_C $MODEL"
        FAILED+=("WORDLE L_to_C:$MODEL")
    fi
    sleep 2
done

# --- MASTERMIND L_to_C ---
MM_L_TO_C_MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
)

MM_OUTPUT_DIR_L_TO_C="$PROJECT_DIR/results/mastermind/hybrids/classic/group_a/L_to_C/raw_data"
mkdir -p "$MM_OUTPUT_DIR_L_TO_C"

for MODEL in "${MM_L_TO_C_MODELS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "========================================"
    echo "[$CURRENT/$TOTAL] MASTERMIND L_to_C | $MODEL"
    echo "========================================"

    if CONFIG_NAME="L_to_C" \
       SCHEDULE="$SCHEDULE_L_TO_C" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$MODEL" \
       PROMPT_TYPE="zero-shot" \
       OUTPUT_DIR="$MM_OUTPUT_DIR_L_TO_C" \
       $PYTHON "$PROJECT_DIR/scripts/mastermind/flexible_hybrid.py"; then
        echo "SUCCESS: MASTERMIND L_to_C $MODEL"
    else
        echo "FAILED: MASTERMIND L_to_C $MODEL"
        FAILED+=("MASTERMIND L_to_C:$MODEL")
    fi
    sleep 2
done

# --- MASTERMIND css3_to_L ---
SCHEDULE_CSS3_TO_L='{"1":"css","2":"css","3":"css","4":"llm","5":"llm","6":"llm"}'
MM_OUTPUT_DIR_CSS3="$PROJECT_DIR/results/mastermind/hybrids/classic/group_b/css3_to_L/raw_data"
mkdir -p "$MM_OUTPUT_DIR_CSS3"

CURRENT=$((CURRENT + 1))
echo ""
echo "========================================"
echo "[$CURRENT/$TOTAL] MASTERMIND css3_to_L | mistral-7b-instruct"
echo "========================================"

if CONFIG_NAME="css3_to_L" \
   SCHEDULE="$SCHEDULE_CSS3_TO_L" \
   NUM_GAMES="$NUM_GAMES" \
   MODEL="mistral-7b-instruct" \
   PROMPT_TYPE="zero-shot" \
   OUTPUT_DIR="$MM_OUTPUT_DIR_CSS3" \
   $PYTHON "$PROJECT_DIR/scripts/mastermind/flexible_hybrid.py"; then
    echo "SUCCESS: MASTERMIND css3_to_L mistral-7b-instruct"
else
    echo "FAILED: MASTERMIND css3_to_L mistral-7b-instruct"
    FAILED+=("MASTERMIND css3_to_L:mistral-7b-instruct")
fi

# --- SUMMARY ---
echo ""
echo "========================================"
echo "MISSING EXPERIMENTS COMPLETE"
echo "========================================"
echo "Total runs: $TOTAL"
echo "Successful: $((TOTAL - ${#FAILED[@]}))"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo ""
    echo "Failed runs:"
    for F in "${FAILED[@]}"; do
        echo "  - $F"
    done
fi
echo "========================================"
