#!/bin/bash
#
# Overnight run for CSS experiments with NO algorithm fallback
#
# If LLM fails, the run fails (no fallback to algorithm)
# This ensures we get real LLM data or nothing
#
# Usage:
#   ./run_overnight_no_fallback.sh [num_games]

# Don't use set -e so we can continue after individual run failures
# Use pipefail so | tee returns the actual command's exit code
set -o pipefail

NUM_GAMES=${1:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Output directory
OUTPUT_BASE="$PROJECT_DIR/workshop/results_css"
mkdir -p "$OUTPUT_BASE"

# Log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$OUTPUT_BASE/overnight_no_fallback_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "OVERNIGHT CSS RUN (NO FALLBACK)" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "Games per run: $NUM_GAMES" | tee -a "$LOG_FILE"
echo "Output: $OUTPUT_BASE" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "NO_LLM_FALLBACK: ENABLED" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Use venv python directly (more reliable than source activate)
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

# CRITICAL: Enable no-fallback mode
export NO_LLM_FALLBACK=1

# Working models only (nemotron and GPT models excluded)
MODELS=(
    "llama-3.3-70b-instruct"
    "llama-3.1-70b-instruct"
    "llama-3.1-8b-instruct"
    "codestral-22b"
    "gemma-3-27b-it"
    "granite-3.3-8b-instruct"
    "mistral-7b-instruct"
)

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
}

# Helper function to run repair_hybrid.py
run_repair() {
    local model=$1
    local repair_mode=$2
    local algorithm=$3
    local prompt_type=$4
    local config_name=$5
    local output_dir=$6

    mkdir -p "$output_dir"

    MODEL="$model" \
    NUM_GAMES="$NUM_GAMES" \
    PROMPT_TYPE="$prompt_type" \
    REPAIR_MODE="$repair_mode" \
    ALGORITHM="$algorithm" \
    CONFIG_NAME="$config_name" \
    TOP_K="5" \
    OUTPUT_DIR="$output_dir" \
    $PYTHON "$SCRIPT_DIR/repair_hybrid.py"
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

# ============================================
# GROUP A - SINGLE HANDOFF (css versions)
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP A - SINGLE HANDOFF (CSS)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

GROUP_A_CONFIGS=(
    'A1_true|L_to_C_true|{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
    'A3_true|L_to_C_alt_true|{"1":"llm","2":"css","3":"voi","4":"css","5":"voi","6":"css"}'
    'A4_true|L_to_C_then_V_true|{"1":"llm","2":"css","3":"css","4":"voi","5":"voi","6":"voi"}'
    'A5_true|L_to_V_then_C_true|{"1":"llm","2":"voi","3":"voi","4":"css","5":"css","6":"css"}'
    'A6_true|C_to_L_true|{"1":"css","2":"llm","3":"llm","4":"llm","5":"llm","6":"llm"}'
)

for ENTRY in "${GROUP_A_CONFIGS[@]}"; do
    IFS='|' read -r LABEL CONFIG_NAME SCHEDULE <<< "$ENTRY"
    BASE_DIR="$OUTPUT_BASE/group_a/$CONFIG_NAME/raw_data"

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo "" | tee -a "$LOG_FILE"
        echo "[$CURRENT] $LABEL | Model: $MODEL" | tee -a "$LOG_FILE"

        if run_flexible "$CONFIG_NAME" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
            echo "SUCCESS: $LABEL $MODEL" | tee -a "$LOG_FILE"
            SUCCEEDED=$((SUCCEEDED + 1))
        else
            echo "FAILED: $LABEL $MODEL" | tee -a "$LOG_FILE"
            FAILED+=("$LABEL:$MODEL")
        fi
        sleep 2
    done
done

# ============================================
# GROUP B - K-HANDOFF SWEEPS (css versions)
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP B - K-HANDOFF SWEEPS (CSS)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

for K in 1 2 3; do
    # L×k -> CSS
    CONFIG_NAME="L${K}_to_css"
    SCHEDULE=$(make_schedule $K llm css)
    BASE_DIR="$OUTPUT_BASE/group_b/$CONFIG_NAME/raw_data"

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo "" | tee -a "$LOG_FILE"
        echo "[$CURRENT] B8_k${K}_true | Model: $MODEL" | tee -a "$LOG_FILE"

        if run_flexible "$CONFIG_NAME" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
            echo "SUCCESS: L${K}_to_css $MODEL" | tee -a "$LOG_FILE"
            SUCCEEDED=$((SUCCEEDED + 1))
        else
            echo "FAILED: L${K}_to_css $MODEL" | tee -a "$LOG_FILE"
            FAILED+=("L${K}_to_css:$MODEL")
        fi
        sleep 2
    done

    # CSS×k -> L
    CONFIG_NAME="css${K}_to_L"
    SCHEDULE=$(make_schedule $K css llm)
    BASE_DIR="$OUTPUT_BASE/group_b/$CONFIG_NAME/raw_data"

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo "" | tee -a "$LOG_FILE"
        echo "[$CURRENT] B10_k${K}_true | Model: $MODEL" | tee -a "$LOG_FILE"

        if run_flexible "$CONFIG_NAME" "$SCHEDULE" "$BASE_DIR" "$MODEL" 2>&1 | tee -a "$LOG_FILE"; then
            echo "SUCCESS: css${K}_to_L $MODEL" | tee -a "$LOG_FILE"
            SUCCEEDED=$((SUCCEEDED + 1))
        else
            echo "FAILED: css${K}_to_L $MODEL" | tee -a "$LOG_FILE"
            FAILED+=("css${K}_to_L:$MODEL")
        fi
        sleep 2
    done
done

# ============================================
# GROUP C - ALTERNATION (css versions)
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP C - ALTERNATION (CSS)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

for PROMPT_TYPE in "zero-shot" "cot"; do
    if [ "$PROMPT_TYPE" == "cot" ]; then
        DIR_SUFFIX="alt_css_start_cot"
    else
        DIR_SUFFIX="alt_css_start_zs"
    fi
    BASE_DIR="$OUTPUT_BASE/group_c/$DIR_SUFFIX/raw_data"

    for MODEL in "${MODELS[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo "" | tee -a "$LOG_FILE"
        echo "[$CURRENT] C13_true ($PROMPT_TYPE) | Model: $MODEL" | tee -a "$LOG_FILE"

        if run_alternating "$MODEL" "css" "algorithm" "$PROMPT_TYPE" "$BASE_DIR" 2>&1 | tee -a "$LOG_FILE"; then
            echo "SUCCESS: alt_css ($PROMPT_TYPE) $MODEL" | tee -a "$LOG_FILE"
            SUCCEEDED=$((SUCCEEDED + 1))
        else
            echo "FAILED: alt_css ($PROMPT_TYPE) $MODEL" | tee -a "$LOG_FILE"
            FAILED+=("alt_css:$PROMPT_TYPE:$MODEL")
        fi
        sleep 2
    done
done

# ============================================
# GROUP D - REPAIR HYBRIDS (css versions)
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "GROUP D - REPAIR HYBRIDS (CSS)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

REPAIR_CONFIGS=(
    "constraint_filter|css|constraint_filter_css"
    "rerank_llm_first|css|rerank_llm_first_css"
    "rerank|css|rerank_css"
)

for CONFIG_ENTRY in "${REPAIR_CONFIGS[@]}"; do
    IFS='|' read -r REPAIR_MODE ALGORITHM DIR_BASE <<< "$CONFIG_ENTRY"

    for PROMPT_TYPE in "zero-shot" "cot"; do
        if [ "$PROMPT_TYPE" == "cot" ]; then
            DIR_SUFFIX="${DIR_BASE}_cot"
            CONFIG_NAME="${DIR_BASE}_cot"
        else
            DIR_SUFFIX="${DIR_BASE}"
            CONFIG_NAME="${DIR_BASE}"
        fi
        BASE_DIR="$OUTPUT_BASE/group_d/$DIR_SUFFIX/raw_data"

        for MODEL in "${MODELS[@]}"; do
            CURRENT=$((CURRENT + 1))
            echo "" | tee -a "$LOG_FILE"
            echo "[$CURRENT] D_${DIR_BASE} ($PROMPT_TYPE) | Model: $MODEL" | tee -a "$LOG_FILE"

            if run_repair "$MODEL" "$REPAIR_MODE" "$ALGORITHM" "$PROMPT_TYPE" "$CONFIG_NAME" "$BASE_DIR" 2>&1 | tee -a "$LOG_FILE"; then
                echo "SUCCESS: $DIR_BASE ($PROMPT_TYPE) $MODEL" | tee -a "$LOG_FILE"
                SUCCEEDED=$((SUCCEEDED + 1))
            else
                echo "FAILED: $DIR_BASE ($PROMPT_TYPE) $MODEL" | tee -a "$LOG_FILE"
                FAILED+=("$DIR_BASE:$PROMPT_TYPE:$MODEL")
            fi
            sleep 2
        done
    done
done

# ============================================
# SANITY CHECK (css version)
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "SANITY CHECK (CSS)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

SANITY_SCHEDULE='{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
BASE_DIR="$OUTPUT_BASE/sanity/raw_data"

for MODEL in "${MODELS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo "" | tee -a "$LOG_FILE"
    echo "[$CURRENT] SANITY_true | Model: $MODEL" | tee -a "$LOG_FILE"

    if run_flexible "sanity_css" "$SANITY_SCHEDULE" "$BASE_DIR" "$MODEL" "cot" 2>&1 | tee -a "$LOG_FILE"; then
        echo "SUCCESS: sanity_css $MODEL" | tee -a "$LOG_FILE"
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "FAILED: sanity_css $MODEL" | tee -a "$LOG_FILE"
        FAILED+=("sanity_css:$MODEL")
    fi
    sleep 2
done

# ============================================
# SUMMARY
# ============================================
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "OVERNIGHT RUN COMPLETE" | tee -a "$LOG_FILE"
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
