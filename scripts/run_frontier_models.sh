#!/bin/bash
#
# Run frontier model experiments across all 3 testbeds
# Models: gpt-oss-120b, gpt-5, claude-4-sonnet
#
# Per model: 16 configs x 3 testbeds = 48 runs x 100 games = 4,800 games
# Total: 3 models x 48 = 144 runs = 14,400 games
#
# Usage:
#   ./scripts/run_frontier_models.sh [num_games]
#   nohup ./scripts/run_frontier_models.sh 100 >> frontier_experiments.log 2>&1 &

set -e

NUM_GAMES=${1:-100}

# Models that run ALL configs (Group A + B)
FULL_MODELS=(
    "gpt-5"
    "claude-4-sonnet"
)

# Models that run ONLY Group A (direction effect): expensive reasoning models
GROUP_A_ONLY_MODELS=(
)

# Combine for display
FRONTIER_MODELS=("${GROUP_A_ONLY_MODELS[@]}" "${FULL_MODELS[@]}")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORDLE_SCRIPT="$SCRIPT_DIR/hybrids/flexible_hybrid.py"
MASTERMIND_SCRIPT="$SCRIPT_DIR/mastermind/flexible_hybrid.py"
PYTHON="$PROJECT_DIR/venv/bin/python3"

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Force gpt-5 through Navigator (direct OpenAI quota exhausted)
unset GPT_API_KEY
echo "Routing gpt-5 through Navigator API (GPT_API_KEY unset)"

if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY not set"
    exit 1
fi
if [ -z "$NAVIGATOR_UF_GPT_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_GPT_API_KEY not set (needed for gpt-5, claude-4-sonnet)"
    exit 1
fi

# --- Skip logic ---
run_exists() {
    local output_dir="$1"
    local config_name="$2"
    local model="$3"
    local count
    count=$(find "$output_dir" -name "${config_name}_${model}_*.csv" 2>/dev/null | wc -l)
    [ "$count" -gt 0 ]
}

FAILED=()
SKIP_COUNT=0
RUN_COUNT=0

run_single() {
    local model="$1"
    local config_name="$2"
    local schedule="$3"
    local output_dir="$4"
    local prompt_type="${5:-zero-shot}"
    local script="$6"
    local variant_flag="$7"

    mkdir -p "$output_dir"

    if run_exists "$output_dir" "$config_name" "$model"; then
        echo "[SKIP] $config_name ($model) - already exists"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        return 0
    fi

    RUN_COUNT=$((RUN_COUNT + 1))
    echo ""
    echo "========================================"
    echo "[RUN $RUN_COUNT] $config_name | $model | $prompt_type $variant_flag"
    echo "========================================"

    if CONFIG_NAME="$config_name" \
       SCHEDULE="$schedule" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$model" \
       PROMPT_TYPE="$prompt_type" \
       OUTPUT_DIR="$output_dir" \
       "$PYTHON" "$script" $variant_flag; then
        echo "SUCCESS: $config_name $model"
    else
        echo "FAILED: $config_name $model"
        FAILED+=("$config_name:$model")
    fi

    sleep 2
}

# --- Wordle configs (6 rounds) ---
W_GROUP_A=(
    'L_to_C|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
    'L_to_V|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi"}'
    'C_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'V_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
)
W_GROUP_B=(
    'css1_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'css2_to_L|{"1":"css","2":"css","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'css3_to_L|{"1":"css","2":"css","3":"css","4":"llm","5":"llm","6":"llm"}'
    'voi1_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'voi2_to_L|{"1":"voi","2":"voi","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'voi3_to_L|{"1":"voi","2":"voi","3":"voi","4":"llm","5":"llm","6":"llm"}'
    'L1_to_css|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
    'L2_to_css|{"1":"llm","2":"llm","3":"css","4":"css","5":"css","6":"css"}'
    'L3_to_css|{"1":"llm","2":"llm","3":"llm","4":"css","5":"css","6":"css"}'
    'L1_to_voi|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi"}'
    'L2_to_voi|{"1":"llm","2":"llm","3":"voi","4":"voi","5":"voi","6":"voi"}'
    'L3_to_voi|{"1":"llm","2":"llm","3":"llm","4":"voi","5":"voi","6":"voi"}'
)

# --- Mastermind Classic configs (6 rounds, same schedules) ---
# Uses same schedules as Wordle

# --- Mastermind Extended configs (10 rounds) ---
ME_GROUP_A=(
    'L_to_C|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'L_to_V|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'C_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'V_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
)
ME_GROUP_B=(
    'css1_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'css2_to_L|{"1":"css","2":"css","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'css3_to_L|{"1":"css","2":"css","3":"css","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'voi1_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'voi2_to_L|{"1":"voi","2":"voi","3":"llm","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'voi3_to_L|{"1":"voi","2":"voi","3":"voi","4":"llm","5":"llm","6":"llm","7":"llm","8":"llm","9":"llm","10":"llm"}'
    'L1_to_css|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'L2_to_css|{"1":"llm","2":"llm","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'L3_to_css|{"1":"llm","2":"llm","3":"llm","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    'L1_to_voi|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'L2_to_voi|{"1":"llm","2":"llm","3":"voi","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
    'L3_to_voi|{"1":"llm","2":"llm","3":"llm","4":"voi","5":"voi","6":"voi","7":"voi","8":"voi","9":"voi","10":"voi"}'
)

echo "========================================"
echo "FRONTIER MODEL EXPERIMENTS"
echo "========================================"
echo "Models: ${FRONTIER_MODELS[*]}"
echo "Games per run: $NUM_GAMES"
echo "Configs per model: 48 (16 x 3 testbeds)"
echo "Total runs: $((${#FRONTIER_MODELS[@]} * 48))"
echo "Total games: $((${#FRONTIER_MODELS[@]} * 48 * NUM_GAMES))"
echo "========================================"

# Helper: check if model is Group A only
is_group_a_only() {
    local model="$1"
    for m in "${GROUP_A_ONLY_MODELS[@]}"; do
        [[ "$m" == "$model" ]] && return 0
    done
    return 1
}

for MODEL in "${FRONTIER_MODELS[@]}"; do
    echo ""
    echo "############################################################"
    echo "  MODEL: $MODEL"
    if is_group_a_only "$MODEL"; then
        echo "  (Group A only — direction effect configs)"
    else
        echo "  (Full — Group A + B)"
    fi
    echo "############################################################"

    # ============================================================
    # WORDLE
    # ============================================================
    echo ""
    echo "===== WORDLE ($MODEL) ====="
    W_BASE="$PROJECT_DIR/results/workshop"

    for ENTRY in "${W_GROUP_A[@]}"; do
        IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
        run_single "$MODEL" "$CONFIG_NAME" "$SCHEDULE" "$W_BASE/group_a/$CONFIG_NAME/raw_data" "zero-shot" "$WORDLE_SCRIPT"
    done
    if ! is_group_a_only "$MODEL"; then
        for ENTRY in "${W_GROUP_B[@]}"; do
            IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
            run_single "$MODEL" "$CONFIG_NAME" "$SCHEDULE" "$W_BASE/group_b/$CONFIG_NAME/raw_data" "zero-shot" "$WORDLE_SCRIPT"
        done
    fi

    # ============================================================
    # MASTERMIND CLASSIC
    # ============================================================
    echo ""
    echo "===== MASTERMIND CLASSIC ($MODEL) ====="
    MC_BASE="$PROJECT_DIR/results/mastermind/hybrids/classic"

    for ENTRY in "${W_GROUP_A[@]}"; do
        IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
        run_single "$MODEL" "$CONFIG_NAME" "$SCHEDULE" "$MC_BASE/group_a/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant classic"
    done
    if ! is_group_a_only "$MODEL"; then
        for ENTRY in "${W_GROUP_B[@]}"; do
            IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
            run_single "$MODEL" "$CONFIG_NAME" "$SCHEDULE" "$MC_BASE/group_b/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant classic"
        done
    fi

    # ============================================================
    # MASTERMIND EXTENDED
    # ============================================================
    echo ""
    echo "===== MASTERMIND EXTENDED ($MODEL) ====="
    ME_BASE="$PROJECT_DIR/results/mastermind/hybrids/extended"

    for ENTRY in "${ME_GROUP_A[@]}"; do
        IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
        run_single "$MODEL" "$CONFIG_NAME" "$SCHEDULE" "$ME_BASE/group_a/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant extended"
    done
    if ! is_group_a_only "$MODEL"; then
        for ENTRY in "${ME_GROUP_B[@]}"; do
            IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
            run_single "$MODEL" "$CONFIG_NAME" "$SCHEDULE" "$ME_BASE/group_b/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant extended"
        done
    fi
done

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "========================================"
echo "FRONTIER MODEL EXPERIMENTS COMPLETE"
echo "========================================"
echo "Skipped (already done): $SKIP_COUNT"
echo "Ran: $RUN_COUNT"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed runs:"
    for F in "${FAILED[@]}"; do
        echo "  - $F"
    done
fi
echo "========================================"
