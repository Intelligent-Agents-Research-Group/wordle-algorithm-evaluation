#!/bin/bash
# Run all 11 models with chain-of-thought prompting (100 games each)

export NUM_TEST_GAMES=100

MODELS=(
  "llama-3.3-70b-instruct"
  "llama-3.1-70b-instruct"
  "gpt-oss-120b"
  "gemma-3-27b-it"
  "codestral-22b"
  "gpt-oss-20b"
  "llama-3.1-8b-instruct"
  "llama-3.1-nemotron-nano-8B-v1"
  "mistral-7b-instruct"
  "granite-3.3-8b-instruct"
  "mistral-small-3.1"
)

LOG_DIR="./evaluation_logs"
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Running CoT evaluation for all 11 models"
echo "100 games per model, ~20 min each"
echo "Total estimated time: ~3-4 hours"
echo "=========================================="
echo ""

for i in "${!MODELS[@]}"; do
  MODEL="${MODELS[$i]}"
  MODEL_NUM=$((i + 1))
  LOG_FILE="$LOG_DIR/${MODEL//-/_}_cot.log"

  echo "[$MODEL_NUM/11] Starting: $MODEL"
  echo "  Log: $LOG_FILE"
  echo "  Started at: $(date)"

  ./test_single_model.sh "$MODEL" chain-of-thought 100 > "$LOG_FILE" 2>&1
  EXIT_CODE=$?

  if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ Completed successfully"
  else
    echo "  ❌ Failed with exit code $EXIT_CODE (check log)"
  fi

  echo "  Finished at: $(date)"
  echo ""
done

echo "=========================================="
echo "All evaluations complete!"
echo "Results in: ./test_results/"
echo "Logs in: $LOG_DIR/"
echo "=========================================="
