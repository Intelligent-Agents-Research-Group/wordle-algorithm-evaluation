#!/bin/bash

# Test script to run a small evaluation locally

export MODEL="${1:-llama-3.3-70b-instruct}"
export PROMPT_TYPE="${2:-zero-shot}"
export NUM_TEST_GAMES="${3:-3}"
export OUT_DIR="./test_results"
export DEBUG_RESPONSES="1"  # Enable debug mode to save raw responses

echo "Testing with:"
echo "  MODEL: $MODEL"
echo "  PROMPT_TYPE: $PROMPT_TYPE"
echo "  NUM_TEST_GAMES: $NUM_TEST_GAMES"
echo "  DEBUG_RESPONSES: $DEBUG_RESPONSES"
echo ""

# Check if API key is set
if [ -z "$NAVIGATOR_UF_API_KEY" ]; then
    echo "⚠️  NAVIGATOR_UF_API_KEY not set. Loading from .env if available..."
    if [ -f .env ]; then
        export $(cat .env | xargs)
    fi
fi

mkdir -p "$OUT_DIR"

python llm_evaluation.py

echo ""
echo "=== Test Complete ==="
if [ -d "$OUT_DIR/debug_responses" ]; then
    echo "Debug responses saved to:"
    ls -la "$OUT_DIR/debug_responses"
fi
