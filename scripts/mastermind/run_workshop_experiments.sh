#!/bin/bash
#
# Master Mastermind Workshop Experiments Orchestration Script
#
# Runs all experiment groups (A-C) for both Classic and Extended variants.
# Group D (repair hybrids) is excluded per research design.
#
# Usage:
#   ./run_workshop_experiments.sh [group] [variant] [num_games]
#
# Arguments:
#   group     - Which group to run: all, a, b, c, sanity (default: all)
#   variant   - Which variant: classic, extended, both (default: both)
#   num_games - Games per configuration (default: 100)
#
# Examples:
#   ./run_workshop_experiments.sh all both 100    # Full run
#   ./run_workshop_experiments.sh a classic 10    # Quick test Group A
#   ./run_workshop_experiments.sh sanity both 5   # Sanity check

set -e

GROUP=${1:-all}
VARIANT=${2:-both}
NUM_GAMES=${3:-100}

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

echo "========================================================================"
echo "MASTERMIND WORKSHOP HYBRID EXPERIMENTS"
echo "========================================================================"
echo "Group: $GROUP"
echo "Variant: $VARIANT"
echo "Games per config: $NUM_GAMES"
echo "Results: $PROJECT_DIR/results/mastermind/hybrids/"
echo "========================================================================"
echo ""

# Create top-level results directory
mkdir -p "$PROJECT_DIR/results/mastermind/hybrids"

# Track start time
START_TIME=$(date +%s)

# Determine variants to run
if [ "$VARIANT" == "both" ]; then
    VARIANTS=("classic" "extended")
else
    VARIANTS=("$VARIANT")
fi

run_group_a() {
    local var=$1
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP A - Single Handoff ($var)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_a.sh" "$var" "$NUM_GAMES"
}

run_group_b() {
    local var=$1
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP B - K-Handoff Sweeps ($var)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_b.sh" "$var" "$NUM_GAMES"
}

run_group_c() {
    local var=$1
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP C - Alternation Patterns ($var)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_c.sh" "$var" "$NUM_GAMES"
}

run_sanity() {
    local var=$1
    echo ""
    echo "================================================================"
    echo "RUNNING SANITY CHECK - L->CSS with CoT ($var)"
    echo "================================================================"

    MODELS=(
        "llama-3.3-70b-instruct"
        "llama-3.1-70b-instruct"
        "llama-3.1-8b-instruct"
        "codestral-22b"
        "gemma-3-27b-it"
        "granite-3.3-8b-instruct"
        "llama-3.1-nemotron-nano-8B-v1"
        "mistral-7b-instruct"
    )

    # 10 rounds for Mastermind
    SCHEDULE='{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css","7":"css","8":"css","9":"css","10":"css"}'
    CONFIG_NAME="sanity_L_to_css_cot"
    BASE_DIR="$PROJECT_DIR/results/mastermind/hybrids/$var/sanity/raw_data"
    mkdir -p "$BASE_DIR"

    SANITY_TOTAL=${#MODELS[@]}
    SANITY_CURRENT=0
    SANITY_FAILED=()

    for MODEL in "${MODELS[@]}"; do
        SANITY_CURRENT=$((SANITY_CURRENT + 1))
        echo ""
        echo "[$SANITY_CURRENT/$SANITY_TOTAL] Sanity: L->CSS CoT | Model: $MODEL | Variant: $var"

        if CONFIG_NAME="$CONFIG_NAME" \
           SCHEDULE="$SCHEDULE" \
           NUM_GAMES="$NUM_GAMES" \
           MODEL="$MODEL" \
           PROMPT_TYPE="cot" \
           OUTPUT_DIR="$BASE_DIR" \
           "$PROJECT_DIR/venv/bin/python" "$SCRIPT_DIR/flexible_hybrid.py" --variant "$var"; then
            echo "SUCCESS: Sanity $MODEL"
        else
            echo "FAILED: Sanity $MODEL"
            SANITY_FAILED+=("$MODEL")
        fi

        sleep 2
    done

    echo ""
    echo "Sanity check ($var) complete: ${#SANITY_FAILED[@]} failures out of $SANITY_TOTAL"
}

# Run selected groups for each variant
for VAR in "${VARIANTS[@]}"; do
    echo ""
    echo "========================================================================"
    echo "PROCESSING VARIANT: $VAR"
    echo "========================================================================"

    case "$GROUP" in
        all)
            run_group_a "$VAR"
            run_group_b "$VAR"
            run_group_c "$VAR"
            run_sanity "$VAR"
            ;;
        a) run_group_a "$VAR" ;;
        b) run_group_b "$VAR" ;;
        c) run_group_c "$VAR" ;;
        sanity) run_sanity "$VAR" ;;
        *)
            echo "ERROR: Unknown group '$GROUP'"
            echo "Valid groups: all, a, b, c, sanity"
            echo "(Note: Group D repair hybrids are excluded)"
            exit 1
            ;;
    esac
done

# Summary
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

# Generate manifest
MANIFEST="$PROJECT_DIR/results/mastermind/hybrids/manifest.json"
cat > "$MANIFEST" << MANIFEST_EOF
{
  "experiment": "mastermind_workshop_hybrid_experiments",
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "num_games_per_config": $NUM_GAMES,
  "groups_run": "$GROUP",
  "variants_run": "$VARIANT",
  "elapsed_seconds": $ELAPSED,
  "note": "Group D (repair hybrids) excluded per research design",
  "groups": {
    "group_a": {
      "description": "Single handoff (ZS, 8 models)",
      "configs": ["L_to_C", "L_to_V", "L_to_C_alt", "L_to_C_then_V", "L_to_V_then_C", "C_to_L", "V_to_L"],
      "runs_per_variant": 56
    },
    "group_b": {
      "description": "K-handoff sweeps (ZS, 8 models, k=1,2,3)",
      "configs": ["Lk_to_css", "Lk_to_voi", "cssk_to_L", "voik_to_L"],
      "runs_per_variant": 96
    },
    "group_c": {
      "description": "Alternation patterns (ZS+CoT, 8 models)",
      "configs": ["alt_css_start", "alt_voi_start", "alt_llm_start_css", "alt_llm_start_voi"],
      "runs_per_variant": 64
    },
    "sanity": {
      "description": "L->CSS with CoT (k=1)",
      "runs_per_variant": 8
    }
  }
}
MANIFEST_EOF

echo ""
echo "========================================================================"
echo "MASTERMIND WORKSHOP EXPERIMENTS COMPLETE"
echo "========================================================================"
echo "Elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
echo "Results: $PROJECT_DIR/results/mastermind/hybrids/"
echo "Manifest: $MANIFEST"
echo "========================================================================"
