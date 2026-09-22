#!/bin/bash
#
# Re-run claude-4-sonnet Mastermind experiments (Classic + Extended)
# Uses direct Anthropic API via CLAUDE_API_KEY
# All previous claude-4-sonnet MM data was invalidated by the NEED parsing bug
#
# Total: 32 configs (16 per domain) x 50 games = 1,600 games
#
# Usage:
#   nohup ./scripts/run_claude_mm_rerun.sh >> claude_mm_rerun.log 2>&1 &

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MASTERMIND_SCRIPT="$SCRIPT_DIR/mastermind/flexible_hybrid.py"
PYTHON="$PROJECT_DIR/venv/bin/python3"
NUM_GAMES=50

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "$CLAUDE_API_KEY" ]; then
    echo "ERROR: CLAUDE_API_KEY not set"
    exit 1
fi

echo "Using direct Anthropic API (CLAUDE_API_KEY)"

MODEL="claude-4-sonnet"

# --- Mastermind Classic configs (6 rounds) ---
MC_GROUP_A=(
    'L_to_C|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
    'L_to_V|{"1":"llm","2":"voi","3":"voi","4":"voi","5":"voi","6":"voi"}'
    'C_to_L|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
    'V_to_L|{"1":"voi","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
)
MC_GROUP_B=(
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

FAILED=()
RUN=0
TOTAL=32

# --- Skip logic ---
run_exists() {
    local output_dir="$1"
    local config_name="$2"
    # Only skip if a VALID run exists (check for non-zero wins or it's an LLM-first config)
    local csv_file
    csv_file=$(find "$output_dir" -name "${config_name}_${MODEL}_*.csv" -not -name "summary_*" 2>/dev/null | sort | tail -1)
    if [ -z "$csv_file" ]; then
        return 1
    fi
    # Check it has no INVALID entries (i.e., the NEED bug is fixed)
    local inv_count
    inv_count=$(grep -c "INVALID" "$csv_file" 2>/dev/null || echo 0)
    if [ "$inv_count" -gt 0 ]; then
        echo "  (Removing old NEED-bugged run: $(basename $csv_file))"
        rm -f "$csv_file"
        rm -f "${csv_file%.csv}.json"
        local summary=$(echo "$csv_file" | sed 's|/\([^/]*\)\.csv|/summary_\1.json|')
        rm -f "$summary"
        return 1
    fi
    return 0
}

run_single() {
    local config_name="$1"
    local schedule="$2"
    local output_dir="$3"
    local variant_flag="$4"

    mkdir -p "$output_dir"

    if run_exists "$output_dir" "$config_name"; then
        echo "[SKIP] $config_name - already has valid data"
        return 0
    fi

    RUN=$((RUN + 1))
    echo ""
    echo "========================================"
    echo "[RUN $RUN/$TOTAL] $config_name | $MODEL | $variant_flag"
    echo "========================================"

    if CONFIG_NAME="$config_name" \
       SCHEDULE="$schedule" \
       NUM_GAMES="$NUM_GAMES" \
       MODEL="$MODEL" \
       PROMPT_TYPE="zero-shot" \
       OUTPUT_DIR="$output_dir" \
       "$PYTHON" "$MASTERMIND_SCRIPT" $variant_flag; then
        echo "SUCCESS: $config_name"
    else
        echo "FAILED: $config_name"
        FAILED+=("$config_name")
    fi

    sleep 2
}

echo "========================================"
echo "CLAUDE-4-SONNET MASTERMIND RE-RUN"
echo "========================================"
echo "Model: $MODEL (direct Anthropic API)"
echo "Games per run: $NUM_GAMES"
echo "Total configs: $TOTAL"
echo "========================================"

# --- Mastermind Classic ---
echo ""
echo "===== MASTERMIND CLASSIC ====="
MC_BASE="$PROJECT_DIR/results/mastermind/hybrids/classic"

for ENTRY in "${MC_GROUP_A[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$MC_BASE/group_a/$CONFIG_NAME/raw_data" "--variant classic"
done
for ENTRY in "${MC_GROUP_B[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$MC_BASE/group_b/$CONFIG_NAME/raw_data" "--variant classic"
done

# --- Mastermind Extended ---
echo ""
echo "===== MASTERMIND EXTENDED ====="
ME_BASE="$PROJECT_DIR/results/mastermind/hybrids/extended"

for ENTRY in "${ME_GROUP_A[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$ME_BASE/group_a/$CONFIG_NAME/raw_data" "--variant extended"
done
for ENTRY in "${ME_GROUP_B[@]}"; do
    IFS='|' read -r CONFIG_NAME SCHEDULE <<< "$ENTRY"
    run_single "$CONFIG_NAME" "$SCHEDULE" "$ME_BASE/group_b/$CONFIG_NAME/raw_data" "--variant extended"
done

echo ""
echo "========================================"
echo "COMPLETE"
echo "========================================"
echo "Ran: $RUN"
echo "Failed: ${#FAILED[@]}"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed runs:"
    for F in "${FAILED[@]}"; do
        echo "  - $F"
    done
fi
echo "========================================"
