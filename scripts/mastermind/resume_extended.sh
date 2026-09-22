#!/bin/bash
#
# Resume Extended Mastermind experiments
# Skips runs that already have results on disk
#
# Usage:
#   ./resume_extended.sh [num_games]
#   nohup ./resume_extended.sh 100 >> mastermind_extended_experiments.log 2>&1 &

set -e

VARIANT="extended"
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

# 7 canonical models (nemotron excluded)
MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "mistral-7b-instruct"
)

# --- Group A ---
GROUP_A_CONFIGS=(
    'A1|L_to_C|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'A2|L_to_V|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'A3|L_to_C_alt|{"1":"llm","2":"css","3":"voi","4":"css","5":"voi","6":"css","7":"voi","8":"css","9":"voi","10":"css"}'
    'A4|L_to_C_then_V|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'A5|L_to_V_then_C|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'A6|C_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'A7|V_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
)

# --- Group B ---
GROUP_B_CONFIGS=(
    'B1|css1_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B2|css2_to_L|{"1":"css","2":"css","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B3|css3_to_L|{"1":"css","2":"css","3":"css","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B4|voi1_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B5|voi2_to_L|{"1":"voi","2":"voi","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B6|voi3_to_L|{"1":"voi","2":"voi","3":"voi","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'B7|L1_to_css|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'B8|L2_to_css|{"1":"llm","2":"llm","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'B9|L3_to_css|{"1":"llm","2":"llm","3":"llm","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'B10|L1_to_voi|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'B11|L2_to_voi|{"1":"llm","2":"llm","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'B12|L3_to_voi|{"1":"llm","2":"llm","3":"llm","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
)

# --- Group C ---
GROUP_C_CONFIGS=(
    'C1_zs|alt_css_start_zs|{"1":"css","2":"llm","3":"css","4":"llm","5":"css","6":"llm","7":"css","8":"llm","9":"css","10":"llm"}'
    'C1_cot|alt_css_start_cot|{"1":"css","2":"llm","3":"css","4":"llm","5":"css","6":"llm","7":"css","8":"llm","9":"css","10":"llm"}'
    'C2_zs|alt_voi_start_zs|{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm","7":"voi","8":"llm","9":"voi","10":"llm"}'
    'C2_cot|alt_voi_start_cot|{"1":"voi","2":"llm","3":"voi","4":"llm","5":"voi","6":"llm","7":"voi","8":"llm","9":"voi","10":"llm"}'
)

# Function to check if a run already exists
run_exists() {
    local group="$1"
    local config_name="$2"
    local model="$3"
    local dir="$PROJECT_DIR/results/mastermind/hybrids/$VARIANT/${group}/${config_name}/raw_data"
    local count
    count=$(find "$dir" -name "${config_name}_${model}_*.csv" 2>/dev/null | wc -l)
    [ "$count" -gt 0 ]
}

# Function to run a group
run_group() {
    local group_name="$1"
    local group_dir="$2"
    shift 2
    local configs=("$@")

    echo ""
    echo "========================================"
    echo "  $group_name - $VARIANT (resume mode)"
    echo "========================================"

    for ENTRY in "${configs[@]}"; do
        IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"

        # Determine prompt type from label
        PROMPT_TYPE="zero-shot"
        if [[ "$LABEL" == *"_cot"* ]]; then
            PROMPT_TYPE="cot"
        fi

        BASE_DIR="$PROJECT_DIR/results/mastermind/hybrids/$VARIANT/${group_dir}/${CONFIG_NAME}/raw_data"
        mkdir -p "$BASE_DIR"

        for MODEL in "${MODELS[@]}"; do
            if run_exists "$group_dir" "$CONFIG_NAME" "$MODEL"; then
                echo "[SKIP] $LABEL: $CONFIG_NAME | $MODEL (already exists)"
                continue
            fi

            echo ""
            echo "========================================"
            echo "[RUN] $LABEL: $CONFIG_NAME | Model: $MODEL | Prompt: $PROMPT_TYPE"
            echo "========================================"

            if CONFIG_NAME="$CONFIG_NAME" \
               SCHEDULE="$SCHEDULE" \
               NUM_GAMES="$NUM_GAMES" \
               MODEL="$MODEL" \
               PROMPT_TYPE="$PROMPT_TYPE" \
               OUTPUT_DIR="$BASE_DIR" \
               "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py" --variant "$VARIANT"; then
                echo "SUCCESS: $LABEL $MODEL"
            else
                echo "FAILED: $LABEL $MODEL"
                FAILED+=("$LABEL:$MODEL")
            fi

            sleep 2
        done
    done
}

FAILED=()

# Count what needs to run
SKIP_COUNT=0
RUN_COUNT=0
for ENTRY in "${GROUP_A_CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    for MODEL in "${MODELS[@]}"; do
        if run_exists "group_a" "$CONFIG_NAME" "$MODEL"; then
            SKIP_COUNT=$((SKIP_COUNT + 1))
        else
            RUN_COUNT=$((RUN_COUNT + 1))
        fi
    done
done
for ENTRY in "${GROUP_B_CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    for MODEL in "${MODELS[@]}"; do
        if run_exists "group_b" "$CONFIG_NAME" "$MODEL"; then
            SKIP_COUNT=$((SKIP_COUNT + 1))
        else
            RUN_COUNT=$((RUN_COUNT + 1))
        fi
    done
done
for ENTRY in "${GROUP_C_CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    for MODEL in "${MODELS[@]}"; do
        if run_exists "group_c" "$CONFIG_NAME" "$MODEL"; then
            SKIP_COUNT=$((SKIP_COUNT + 1))
        else
            RUN_COUNT=$((RUN_COUNT + 1))
        fi
    done
done

echo "========================================"
echo "RESUME EXTENDED MASTERMIND EXPERIMENTS"
echo "========================================"
echo "Already completed: $SKIP_COUNT runs"
echo "Remaining: $RUN_COUNT runs"
echo "Games per run: $NUM_GAMES"
echo "========================================"

run_group "GROUP A" "group_a" "${GROUP_A_CONFIGS[@]}"
run_group "GROUP B" "group_b" "${GROUP_B_CONFIGS[@]}"
run_group "GROUP C" "group_c" "${GROUP_C_CONFIGS[@]}"

echo ""
echo "========================================"
echo "ALL GROUPS COMPLETE ($VARIANT)"
echo "========================================"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed runs:"
    for F in "${FAILED[@]}"; do
        echo "  - $F"
    done
fi
echo "========================================"
