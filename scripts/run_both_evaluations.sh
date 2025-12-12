#!/bin/bash
# Run both CoT and Zero-Shot evaluations sequentially

echo "=========================================="
echo "Starting Full Evaluation Pipeline"
echo "=========================================="
echo ""

# Run CoT evaluation
echo "PHASE 1: Chain-of-Thought Evaluation"
echo "Starting at: $(date)"
echo ""
./run_all_models_cot.sh

echo ""
echo "=========================================="
echo "CoT evaluation complete!"
echo "Completed at: $(date)"
echo "=========================================="
echo ""

# Run Zero-Shot evaluation
echo "PHASE 2: Zero-Shot Evaluation"
echo "Starting at: $(date)"
echo ""
./run_all_models_zero_shot.sh

echo ""
echo "=========================================="
echo "All evaluations complete!"
echo "CoT results: ./test_results/*_chain-of-thought_*"
echo "Zero-Shot results: ./test_results/*_zero-shot_*"
echo "Logs: ./evaluation_logs/"
echo "Completed at: $(date)"
echo "=========================================="
