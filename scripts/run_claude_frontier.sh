#!/bin/bash
#
# Run claude-4-sonnet frontier experiments (all configs) via Navigator API
# Can run concurrently with gpt-5 (which uses direct OpenAI API)
#
# Usage:
#   nohup ./scripts/run_claude_frontier.sh 50 >> claude_frontier.log 2>&1 &

set -e

NUM_GAMES=${1:-50}

MODEL="claude-4-sonnet"

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

if [ -z "$NAVIGATOR_UF_GPT_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_GPT_API_KEY not set"
    exit 1
fi

# --- Skip logic ---
run_exists() {
    local output_dir="$1"
    local config_name="$2"
    local count
    count=$(find "$output_dir" -name "${config_name}_${MODEL}_*.csv" 2>/dev/null | wc -l)
    [ "$count" -gt 0 ]
}

FAILED=()
SKIP_COUNT=0
RUN_COUNT=0

run_single() {
    local config_name="$1"
    local schedule="$2"
    local output_dir="$3"
    local prompt_type="${4:-zero-shot}"
    local script="$5"
    local variant_flag="$6"

    mkdir -p "$output_dir"

    if run_exists "$output_dir" "$config_name"; then
        echo "[SKIP] $config_name ($MODEL) - already exists"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        return 0
    fi

    RUN_COUNT=$((RUN_COUNT + 1))
    echo ""
    echo "========================================"
    echo "[RUN $RUN_COUNT] $config_name | $MODEL | $prompt_type $variant_flag"
    echo "========================================"

    if CONFIG_NAME="$config_name" \
       SCHEDULE="$schedule" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$MODEL" \
       PROMPT_TYPE="$prompt_type" \
       OUTPUT_DIR="$output_dir" \
       "$PYTHON" "$script" $variant_flag; then
        echo "SUCCESS: $config_name $MODEL"
    else
        echo "FAILED: $config_name $MODEL"
        FAILED+=("$config_name:$MODEL")
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
echo "CLAUDE-4-SONNET FRONTIER EXPERIMENTS"
echo "========================================"
echo "Model: $MODEL (via Navigator API)"
echo "Games per run: $NUM_GAMES"
echo "Configs: 48 (16 x 3 testbeds)"
echo "========================================"

# ============================================================
# WORDLE
# ============================================================
echo ""
echo "===== WORDLE ====="
W_BASE="$PROJECT_DIR/results/workshop"

for ENTRY in "${W_GROUP_A[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$W_BASE/group_a/$CONFIG_NAME/raw_data" "zero-shot" "$WORDLE_SCRIPT"
done
for ENTRY in "${W_GROUP_B[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$W_BASE/group_b/$CONFIG_NAME/raw_data" "zero-shot" "$WORDLE_SCRIPT"
done

# ============================================================
# MASTERMIND CLASSIC
# ============================================================
echo ""
echo "===== MASTERMIND CLASSIC ====="
MC_BASE="$PROJECT_DIR/results/mastermind/hybrids/classic"

for ENTRY in "${W_GROUP_A[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$MC_BASE/group_a/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant classic"
done
for ENTRY in "${W_GROUP_B[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$MC_BASE/group_b/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant classic"
done

# ============================================================
# MASTERMIND EXTENDED
# ============================================================
echo ""
echo "===== MASTERMIND EXTENDED ====="
ME_BASE="$PROJECT_DIR/results/mastermind/hybrids/extended"

for ENTRY in "${ME_GROUP_A[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$ME_BASE/group_a/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant extended"
done
for ENTRY in "${ME_GROUP_B[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$ME_BASE/group_b/$CONFIG_NAME/raw_data" "zero-shot" "$MASTERMIND_SCRIPT" "--variant extended"
done

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "========================================"
echo "CLAUDE-4-SONNET EXPERIMENTS COMPLETE"
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
