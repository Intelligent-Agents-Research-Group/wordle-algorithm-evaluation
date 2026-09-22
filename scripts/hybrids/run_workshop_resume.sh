#!/bin/bash
#
# Resume Workshop Experiments
#
# Runs remaining Group A configs (A3-A7) that were not completed,
# then continues with Groups B, C, D, and sanity.
# Group E and A1/A2 already completed.
#
# Usage:
#   ./run_workshop_resume.sh [num_games]

set -e

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Activate venv if present
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

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

echo "========================================================================"
echo "WORKSHOP EXPERIMENTS - RESUME RUN"
echo "========================================================================"
echo "Games per config: $NUM_GAMES"
echo "Skipping: Group E (done), A1 (done), A2 (done)"
echo "Running: A3-A7, then Groups B, C, D, sanity"
echo "========================================================================"
echo ""

START_TIME=$(date +%s)

MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "llama-3.1-nemotron-nano-8b-v1"
    "mistral-7b-instruct"
    # "mistral-small-3.1"  # Excluded: hangs on API
)

# ============================================================
# Group A remainder: A3-A7
# ============================================================
echo ""
echo "================================================================"
echo "RUNNING GROUP A REMAINDER (A3-A7)"
echo "================================================================"

CONFIGS_A=(
    'A3|L_to_C_alt|{"1":"llm","2":"css","3":"voi","4":"css","5":"voi","6":"css"}'
    'A4|L_to_C_then_V|{"1":"llm","2":"css","3":"css","4":"voi","5":"voi","6":"voi"}'
    'A5|L_to_V_then_C|{"1":"llm","2":"voi","3":"voi","4":"css","5":"css","6":"css"}'
    'A6|C_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'A7|V_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
)

TOTAL_A=$((${#CONFIGS_A[@]} * ${#MODELS[@]}))
CURRENT_A=0
FAILED_A=()

for ENTRY in "${CONFIGS_A[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    BASE_DIR="$PROJECT_DIR/results/workshop/group_a/$CONFIG_NAME/raw_data"
    mkdir -p "$BASE_DIR"

    for MODEL in "${MODELS[@]}"; do
        CURRENT_A=$((CURRENT_A + 1))
        echo ""
        echo "[$CURRENT_A/$TOTAL_A] $LABEL: $CONFIG_NAME | Model: $MODEL"

        if CONFIG_NAME="$CONFIG_NAME" \
           SCHEDULE="$SCHEDULE" \
           NUM_GAMES="$NUM_GAMES" \
           MODEL="$MODEL" \
           PROMPT_TYPE="zero-shot" \
           OUTPUT_DIR="$BASE_DIR" \
           "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py"; then
            echo "SUCCESS: $LABEL $MODEL"
        else
            echo "FAILED: $LABEL $MODEL"
            FAILED_A+=("$LABEL:$MODEL")
        fi

        sleep 2
    done
done

echo ""
echo "Group A remainder done: ${#FAILED_A[@]} failures out of $TOTAL_A"

# ============================================================
# Groups B, C, D, Sanity - delegate to existing scripts
# ============================================================

echo ""
echo "================================================================"
echo "RUNNING GROUP B - K-Handoff Sweeps"
echo "================================================================"
bash "$SCRIPT_DIR/run_workshop_group_b.sh" "$NUM_GAMES"

echo ""
echo "================================================================"
echo "RUNNING GROUP C - Alternation Patterns"
echo "================================================================"
bash "$SCRIPT_DIR/run_workshop_group_c.sh" "$NUM_GAMES"

echo ""
echo "================================================================"
echo "RUNNING GROUP D - Repair Hybrids"
echo "================================================================"
bash "$SCRIPT_DIR/run_workshop_group_d.sh" "$NUM_GAMES"

# Sanity check
echo ""
echo "================================================================"
echo "RUNNING SANITY CHECK"
echo "================================================================"

SANITY_SCHEDULE='{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
SANITY_DIR="$PROJECT_DIR/results/workshop/sanity/raw_data"
mkdir -p "$SANITY_DIR"
SANITY_FAILED=()
SANITY_CURRENT=0
SANITY_TOTAL=${#MODELS[@]}

for MODEL in "${MODELS[@]}"; do
    SANITY_CURRENT=$((SANITY_CURRENT + 1))
    echo ""
    echo "[$SANITY_CURRENT/$SANITY_TOTAL] Sanity: L->CSS CoT | Model: $MODEL"

    if CONFIG_NAME="sanity_L_to_css_cot" \
       SCHEDULE="$SANITY_SCHEDULE" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$MODEL" \
       PROMPT_TYPE="cot" \
       OUTPUT_DIR="$SANITY_DIR" \
       "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py"; then
        echo "SUCCESS: Sanity $MODEL"
    else
        echo "FAILED: Sanity $MODEL"
        SANITY_FAILED+=("$MODEL")
    fi

    sleep 2
done

echo ""
echo "Sanity check: ${#SANITY_FAILED[@]} failures out of $SANITY_TOTAL"

# Summary
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo ""
echo "========================================================================"
echo "RESUME RUN COMPLETE"
echo "========================================================================"
echo "Elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
echo "Results: $PROJECT_DIR/results/workshop/"
echo "========================================================================"
