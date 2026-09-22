#!/bin/bash
#
# Re-run the 20 failed experiments WITH algorithm fallback enabled
# This will produce complete data even if LLM fails on some guesses
#
# Usage:
#   ./rerun_failed_with_fallback.sh [num_games]

# Don't use set -e so we can continue after individual run failures
set -o pipefail

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Output directory (same as main css experiments)
OUTPUT_BASE="$PROJECT_DIR/workshop/results_css"
mkdir -p "$OUTPUT_BASE"

# Log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$OUTPUT_BASE/rerun_failed_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "RE-RUNNING 20 FAILED EXPERIMENTS" | tee -a "$LOG_FILE"
echo "NO ALGORITHM FALLBACK (maintaining experiment integrity)" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "Games per run: $NUM_GAMES" | tee -a "$LOG_FILE"
echo "Output: $OUTPUT_BASE" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Use venv python directly
if [ -f "$PROJECT_DIR/venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/venv/bin/python"
else
    PYTHON="python3"
fi
echo "Using Python: $PYTHON" | tee -a "$LOG_FILE"

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE" | tee -a "$LOG_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo "ERROR: NAVIGATOR_UF_API_KEY not set" | tee -a "$LOG_FILE"
    exit 1
fi

# IMPORTANT: Keep NO_LLM_FALLBACK enabled to maintain experiment integrity
export NO_LLM_FALLBACK=1

CURRENT=0
FAILED=()
SUCCEEDED=0

# Helper function to run flexible_hybrid.py
run_flexible() {
    local config_name=$1
    local schedule=$2
    local output_dir=$3
    local model=$4
    local prompt_type=${5:-"zero-shot"}

    mkdir -p "$output_dir"

    CONFIG_NAME="$config_name" \
    SCHEDULE="$schedule" \
    NUM_GAMES="$NUM_GAMES" \
    MODEL="$model" \
    PROMPT_TYPE="$prompt_type" \
    OUTPUT_DIR="$output_dir" \
    $PYTHON "$SCRIPT_DIR/flexible_hybrid.py"
    return $?
}

# Helper function to run alternating_hybrid.py
run_alternating() {
    local model=$1
    local algorithm=$2
    local start_with=$3
    local prompt_type=$4
    local output_dir=$5

    mkdir -p "$output_dir"

    MODEL="$model" \
    NUM_GAMES="$NUM_GAMES" \
    START_WITH="$start_with" \
    PROMPT_TYPE="$prompt_type" \
    ALGORITHM="$algorithm" \
    OUTPUT_DIR="$output_dir" \
    $PYTHON "$SCRIPT_DIR/alternating_hybrid.py"
    return $?
}

# Helper to generate schedule JSON
make_schedule() {
    local k=$1
    local strat_a=$2
    local strat_b=$3
    local sched="{"
    for r in 1 2 3 4 5 6; do
        if [ $r -le $k ]; then
            sched+="\"$r\":\"$strat_a\""
        else
            sched+="\"$r\":\"$strat_b\""
        fi
        if [ $r -lt 6 ]; then
            sched+=","
        fi
    done
    sched+="}"
    echo "$sched"
}

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP A FAILURES (4 runs)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# A3_true granite-3.3-8b-instruct
CURRENT=$((CURRENT + 1))
echo "[$CURRENT/20] A3_true | granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
SCHEDULE='{"1":"llm","2":"css","3":"voi","4":"css","5":"voi","6":"css"}'
BASE_DIR="$OUTPUT_BASE/group_a/L_to_C_alt_true/raw_data"
if run_flexible "L_to_C_alt_true" "$SCHEDULE" "$BASE_DIR" "granite-3.3-8b-instruct" 2>&1 | tee -a "$LOG_FILE"; then
    echo "SUCCESS: A3_true granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    SUCCEEDED=$((SUCCEEDED + 1))
else
    echo "FAILED: A3_true granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    FAILED+=("A3_true:granite-3.3-8b-instruct")
fi
sleep 2

# A4_true granite-3.3-8b-instruct
CURRENT=$((CURRENT + 1))
echo "[$CURRENT/20] A4_true | granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
SCHEDULE='{"1":"llm","2":"css","3":"css","4":"voi","5":"voi","6":"voi"}'
BASE_DIR="$OUTPUT_BASE/group_a/L_to_C_then_V_true/raw_data"
if run_flexible "L_to_C_then_V_true" "$SCHEDULE" "$BASE_DIR" "granite-3.3-8b-instruct" 2>&1 | tee -a "$LOG_FILE"; then
    echo "SUCCESS: A4_true granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    SUCCEEDED=$((SUCCEEDED + 1))
else
    echo "FAILED: A4_true granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    FAILED+=("A4_true:granite-3.3-8b-instruct")
fi
sleep 2

# A5_true granite-3.3-8b-instruct
CURRENT=$((CURRENT + 1))
echo "[$CURRENT/20] A5_true | granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
SCHEDULE='{"1":"llm","2":"voi","3":"voi","4":"css","5":"css","6":"css"}'
BASE_DIR="$OUTPUT_BASE/group_a/L_to_V_then_C_true/raw_data"
if run_flexible "L_to_V_then_C_true" "$SCHEDULE" "$BASE_DIR" "granite-3.3-8b-instruct" 2>&1 | tee -a "$LOG_FILE"; then
    echo "SUCCESS: A5_true granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    SUCCEEDED=$((SUCCEEDED + 1))
else
    echo "FAILED: A5_true granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    FAILED+=("A5_true:granite-3.3-8b-instruct")
fi
sleep 2

# A6_true - ALL 3 small models failed
SCHEDULE='{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
BASE_DIR="$OUTPUT_BASE/group_a/C_to_L_true/raw_data"

for MODEL in "llama-3.1-8b-instruct" "granite-3.3-8b-instruct" "mistral-7b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] A6_true | $MODEL" | tee -a "$LOG_FILE"
    if run_flexible "C_to_L_true" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: A6_true $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: A6_true $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("A6_true:$MODEL")
    fi
    sleep 2
done

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP B FAILURES (12 runs)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# L1_to_css granite
CURRENT=$((CURRENT + 1))
echo "[$CURRENT/20] L1_to_css | granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
SCHEDULE=$(make_schedule 1 llm css)
BASE_DIR="$OUTPUT_BASE/group_b/L1_to_css/raw_data"
if run_flexible "L1_to_css" "$SCHEDULE" "$BASE_DIR" "granite-3.3-8b-instruct" 2>&1 | tee -a "$LOG_FILE"; then
    echo "SUCCESS: L1_to_css granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    SUCCEEDED=$((SUCCEEDED + 1))
else
    echo "FAILED: L1_to_css granite-3.3-8b-instruct" | tee -a "$LOG_FILE"
    FAILED+=("L1_to_css:granite-3.3-8b-instruct")
fi
sleep 2

# css1_to_L - all 3 models
SCHEDULE=$(make_schedule 1 css llm)
BASE_DIR="$OUTPUT_BASE/group_b/css1_to_L/raw_data"
for MODEL in "llama-3.1-8b-instruct" "granite-3.3-8b-instruct" "mistral-7b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] css1_to_L | $MODEL" | tee -a "$LOG_FILE"
    if run_flexible "css1_to_L" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: css1_to_L $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: css1_to_L $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("css1_to_L:$MODEL")
    fi
    sleep 2
done

# L2_to_css granite, mistral
SCHEDULE=$(make_schedule 2 llm css)
BASE_DIR="$OUTPUT_BASE/group_b/L2_to_css/raw_data"
for MODEL in "granite-3.3-8b-instruct" "mistral-7b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] L2_to_css | $MODEL" | tee -a "$LOG_FILE"
    if run_flexible "L2_to_css" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: L2_to_css $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: L2_to_css $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("L2_to_css:$MODEL")
    fi
    sleep 2
done

# css2_to_L llama, granite
SCHEDULE=$(make_schedule 2 css llm)
BASE_DIR="$OUTPUT_BASE/group_b/css2_to_L/raw_data"
for MODEL in "llama-3.1-8b-instruct" "granite-3.3-8b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] css2_to_L | $MODEL" | tee -a "$LOG_FILE"
    if run_flexible "css2_to_L" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: css2_to_L $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: css2_to_L $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("css2_to_L:$MODEL")
    fi
    sleep 2
done

# L3_to_css llama, granite
SCHEDULE=$(make_schedule 3 llm css)
BASE_DIR="$OUTPUT_BASE/group_b/L3_to_css/raw_data"
for MODEL in "llama-3.1-8b-instruct" "granite-3.3-8b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] L3_to_css | $MODEL" | tee -a "$LOG_FILE"
    if run_flexible "L3_to_css" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: L3_to_css $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: L3_to_css $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("L3_to_css:$MODEL")
    fi
    sleep 2
done

# css3_to_L llama, mistral
SCHEDULE=$(make_schedule 3 css llm)
BASE_DIR="$OUTPUT_BASE/group_b/css3_to_L/raw_data"
for MODEL in "llama-3.1-8b-instruct" "mistral-7b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] css3_to_L | $MODEL" | tee -a "$LOG_FILE"
    if run_flexible "css3_to_L" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: css3_to_L $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: css3_to_L $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("css3_to_L:$MODEL")
    fi
    sleep 2
done

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP C FAILURES (2 runs)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# alt_css zero-shot - granite, mistral
BASE_DIR="$OUTPUT_BASE/group_c/alt_css_start_zs/raw_data"
for MODEL in "granite-3.3-8b-instruct" "mistral-7b-instruct"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/20] alt_css (zero-shot) | $MODEL" | tee -a "$LOG_FILE"
    if run_alternating "$MODEL" "css" "algorithm" "zero-shot" "$BASE_DIR" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: alt_css (zero-shot) $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: alt_css (zero-shot) $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("alt_css:zero-shot:$MODEL")
    fi
    sleep 2
done

# ============================================
# SUMMARY
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "RE-RUN COMPLETE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Finished: $(date)" | tee -a "$LOG_FILE"
echo "Total runs attempted: $CURRENT" | tee -a "$LOG_FILE"
echo "Successful: $SUCCEEDED" | tee -a "$LOG_FILE"
echo "Failed: ${#FAILED[@]}" | tee -a "$LOG_FILE"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "Failed runs:" | tee -a "$LOG_FILE"
    for F in "${FAILED[@]}"; do
        echo "  - $F" | tee -a "$LOG_FILE"
    done
fi
echo "========================================" | tee -a "$LOG_FILE"
echo "Results saved to: $OUTPUT_BASE" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
