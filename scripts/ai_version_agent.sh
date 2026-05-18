#!/bin/bash
# SigmaFidelity™ AI Version Agent v1.0
# Standard: HWB-QMS-9.1 (Git Troubleshooting)
# Responsibility: George (System Architect)

# 1. Stage changes
git add .

# 2. Get the diff summary for AI context
DIFF_SUMMARY=$(git diff --cached --stat | head -n 20)

# 3. Use Gemini to generate a high-fidelity commit message
# We use the existing Gemini Client script
PYTHON_EXEC=".venv_agent/bin/python"
GEMINI_CLIENT="scripts/HWB-WEB Gemini Client.py"

PROMPT="Generate a professional, high-authority Git commit message for the following changes. 
Focus on SigmaFidelity™ institutional hardening and 3rd person perspective.
Use this format: 'Persona: Description of impact.'
Diff Summary:
$DIFF_SUMMARY"

# Fallback message in case AI fails
COMMIT_MESSAGE="George: Institutional Infrastructure Update $(date +'%m-%d-%Y')"

if [ -f "$PYTHON_EXEC" ]; then
    AI_MSG=$($PYTHON_EXEC -c "
import sys
import os
sys.path.append('scripts')
from HWB_WEB_Gemini_Client import GeminiClient
try:
    client = GeminiClient()
    print(client.generate_content(\"\"\"$PROMPT\"\"\"))
except Exception as e:
    print('FAIL')
")
    
    if [[ "$AI_MSG" != "FAIL" && -n "$AI_MSG" ]]; then
        COMMIT_MESSAGE=$(echo "$AI_MSG" | head -n 1)
    fi
fi

# 4. Commit
git commit -m "$COMMIT_MESSAGE"

echo "--- SigmaFidelity: AI Version Control Success ---"
echo "Message: $COMMIT_MESSAGE"
