#!/bin/bash
#
# Overnight runner: Waits for current css experiments to finish,
# then automatically runs additional models (gpt-oss-120b, gpt-oss-20b)
#
# Usage:
#   nohup ./run_overnight.sh &
#
# This script will:
# 1. Monitor the current run_all_css.sh process
# 2. When it finishes, automatically start run_additional_models.sh
# 3. Log everything to a single overnight log file

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
OUTPUT_BASE="$PROJECT_DIR/workshop/results_css"

LOG_FILE="$OUTPUT_BASE/overnight_run_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG_FILE"
echo "OVERNIGHT AUTOMATION STARTED" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Function to check if main experiments are still running
check_main_running() {
    pgrep -f "run_all_css.sh" > /dev/null 2>&1
    return $?
}

# Wait for main experiments to finish
echo "" | tee -a "$LOG_FILE"
echo "Monitoring run_all_css.sh..." | tee -a "$LOG_FILE"
echo "Will start additional models when complete." | tee -a "$LOG_FILE"

while check_main_running; do
    # Count completed runs
    COMPLETED=$(find "$OUTPUT_BASE" -name "*.csv" 2>/dev/null | wc -l | tr -d ' ')
    echo "[$(date '+%H:%M:%S')] Main experiments running... ($COMPLETED CSV files completed)" | tee -a "$LOG_FILE"
    sleep 300  # Check every 5 minutes
done

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Main experiments FINISHED at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Count final results
FINAL_COUNT=$(find "$OUTPUT_BASE" -name "*.csv" 2>/dev/null | wc -l | tr -d ' ')
echo "Total CSV files from main run: $FINAL_COUNT" | tee -a "$LOG_FILE"

# Small delay before starting additional models
echo "" | tee -a "$LOG_FILE"
echo "Starting additional models in 30 seconds..." | tee -a "$LOG_FILE"
sleep 30

# Start additional models
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "STARTING ADDITIONAL MODELS (gpt-oss-120b, gpt-oss-20b)" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Run additional models script
cd "$PROJECT_DIR"
source venv/bin/activate 2>/dev/null || true
source .env 2>/dev/null || true

"$SCRIPT_DIR/run_additional_models.sh" 100 2>&1 | tee -a "$LOG_FILE"

# Final summary
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "OVERNIGHT RUN COMPLETE" | tee -a "$LOG_FILE"
echo "Finished: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

TOTAL_CSV=$(find "$OUTPUT_BASE" -name "*.csv" 2>/dev/null | wc -l | tr -d ' ')
echo "Total CSV files: $TOTAL_CSV" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
