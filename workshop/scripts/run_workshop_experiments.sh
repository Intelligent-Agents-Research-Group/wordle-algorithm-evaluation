#!/bin/bash
#
# Master Workshop Experiments Orchestration Script
#
# Runs all experiment groups (A-E) plus sanity checks.
# Can run individual groups or all at once.
#
# Usage:
#   ./run_workshop_experiments.sh [group] [num_games]
#
# Arguments:
#   group     - Which group to run: all, a, b, c, d, e, sanity (default: all)
#   num_games - Games per configuration (default: 100)
#
# Examples:
#   ./run_workshop_experiments.sh all 100     # Full run
#   ./run_workshop_experiments.sh e 5         # Quick test Group E
#   ./run_workshop_experiments.sh sanity 5    # Sanity check
#   ./run_workshop_experiments.sh a 100       # Just Group A

set -e

GROUP=${1:-all}
NUM_GAMES=${2:-100}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Use venv Python explicitly
PYTHON="$PROJECT_DIR/venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    echo "ERROR: venv Python not found at $PYTHON"
    exit 1
fi

# Load .env
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

echo "========================================================================"
echo "WORKSHOP HYBRID EXPERIMENTS - MASTER ORCHESTRATION"
echo "========================================================================"
echo "Group: $GROUP"
echo "Games per config: $NUM_GAMES"
echo "Results: $PROJECT_DIR/results/workshop/"
echo "========================================================================"
echo ""

# Create top-level results directory
mkdir -p "$PROJECT_DIR/results/workshop"

# Track start time
START_TIME=$(date +%s)

run_group_e() {
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP E - Controls (No LLM)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_e.sh" "$NUM_GAMES"
}

run_group_a() {
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP A - Single Handoff (ZS, 9 models)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_a.sh" "$NUM_GAMES"
}

run_group_b() {
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP B - K-Handoff Sweeps (ZS, 9 models)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_b.sh" "$NUM_GAMES"
}

run_group_c() {
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP C - Alternation Patterns (ZS + CoT, 9 models)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_c.sh" "$NUM_GAMES"
}

run_group_d() {
    echo ""
    echo "================================================================"
    echo "RUNNING GROUP D - Repair Hybrids (ZS + CoT, 9 models)"
    echo "================================================================"
    bash "$SCRIPT_DIR/run_workshop_group_d.sh" "$NUM_GAMES"
}

run_sanity() {
    echo ""
    echo "================================================================"
    echo "RUNNING SANITY CHECK - L->CSS with CoT (k=1)"
    echo "================================================================"

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

    SCHEDULE='{"1":"llm","2":"css","3":"css","4":"css","5":"css","6":"css"}'
    CONFIG_NAME="sanity_L_to_css_cot"
    BASE_DIR="$PROJECT_DIR/results/workshop/sanity/raw_data"
    mkdir -p "$BASE_DIR"

    SANITY_TOTAL=${#MODELS[@]}
    SANITY_CURRENT=0
    SANITY_FAILED=()

    for MODEL in "${MODELS[@]}"; do
        SANITY_CURRENT=$((SANITY_CURRENT + 1))
        echo ""
        echo "[$SANITY_CURRENT/$SANITY_TOTAL] Sanity: L->CSS CoT | Model: $MODEL"

        if CONFIG_NAME="$CONFIG_NAME" \
           SCHEDULE="$SCHEDULE" \
           NUM_GAMES="$NUM_GAMES" \
           MODEL="$MODEL" \
           PROMPT_TYPE="cot" \
           OUTPUT_DIR="$BASE_DIR" \
           "$PYTHON" "$SCRIPT_DIR/flexible_hybrid.py"; then
            echo "SUCCESS: Sanity $MODEL"
        else
            echo "FAILED: Sanity $MODEL"
            SANITY_FAILED+=("$MODEL")
        fi

        sleep 2
    done

    echo ""
    echo "Sanity check complete: ${#SANITY_FAILED[@]} failures out of $SANITY_TOTAL"
}

# Run selected groups
case "$GROUP" in
    all)
        run_group_e
        run_group_a
        run_group_b
        run_group_c
        run_group_d
        run_sanity
        ;;
    e) run_group_e ;;
    a) run_group_a ;;
    b) run_group_b ;;
    c) run_group_c ;;
    d) run_group_d ;;
    sanity) run_sanity ;;
    *)
        echo "ERROR: Unknown group '$GROUP'"
        echo "Valid groups: all, a, b, c, d, e, sanity"
        exit 1
        ;;
esac

# Summary
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

# Generate manifest
MANIFEST="$PROJECT_DIR/results/workshop/manifest.json"
cat > "$MANIFEST" << MANIFEST_EOF
{
  "experiment": "workshop_hybrid_experiments",
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "num_games_per_config": $NUM_GAMES,
  "groups_run": "$GROUP",
  "elapsed_seconds": $ELAPSED,
  "groups": {
    "group_a": {
      "description": "Single handoff (ZS, 9 models)",
      "configs": ["A1_L_to_C", "A2_L_to_V", "A3_L_to_C_alt", "A4_L_to_C_then_V", "A5_L_to_V_then_C", "A6_C_to_L", "A7_V_to_L"],
      "runs": 63
    },
    "group_b": {
      "description": "K-handoff sweeps (ZS, 9 models, k=1,2,3)",
      "configs": ["B8_Lk_to_css", "B9_Lk_to_voi", "B10_cssk_to_L", "B11_voik_to_L"],
      "runs": 108
    },
    "group_c": {
      "description": "Alternation patterns (ZS+CoT, 9 models)",
      "configs": ["C13_alt_css_start", "C15_alt_voi_start"],
      "runs": 36
    },
    "group_d": {
      "description": "Repair hybrids (ZS+CoT, 9 models)",
      "configs": ["D18_constraint_filter_css", "D18b_constraint_filter_voi", "D19_rerank_css", "D19b_rerank_voi"],
      "runs": 72
    },
    "group_e": {
      "description": "Controls (no LLM)",
      "configs": ["E20_random_to_css", "E21_random_to_voi"],
      "runs": 2
    },
    "sanity": {
      "description": "L->CSS with CoT (k=1)",
      "runs": 9
    }
  }
}
MANIFEST_EOF

echo ""
echo "========================================================================"
echo "WORKSHOP EXPERIMENTS COMPLETE"
echo "========================================================================"
echo "Elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
echo "Results: $PROJECT_DIR/results/workshop/"
echo "Manifest: $MANIFEST"
echo "========================================================================"
