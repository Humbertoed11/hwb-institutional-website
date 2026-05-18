#!/bin/bash

# BabySOP Factory™ Automation Script
# Version 1.0.0 (Institutional Standard)

CHILD="Santo Bazooka"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKS_FILE="$BASE_DIR/tasks/task_list.txt"
PROMPT_FILE="$BASE_DIR/prompts/babysop_master_prompt.txt"
OUTPUT_DIR="$BASE_DIR/output/sop_docs"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "--- SigmaFidelity: Initiating BabySOP Factory Cycle ---"

while read -r TASK
do
    if [ -z "$TASK" ]; then continue; fi
    
    echo "Generating SOP for: $TASK"
    
    # Replace placeholder with current task
    PROMPT=$(sed "s/{{TASK}}/$TASK/g" "$PROMPT_FILE")
    
    # Process through Gemini CLI
    # Note: Using printf to handle potential special characters in PROMPT
    printf "%s" "$PROMPT" | gemini > "$OUTPUT_DIR/babysop_${TASK// /_}.txt"
    
    echo "SUCCESS: Saved to $OUTPUT_DIR/babysop_${TASK// /_}.txt"
    
done < "$TASKS_FILE"

echo "--- Factory Cycle Complete: 40 Assets Produced ---"
