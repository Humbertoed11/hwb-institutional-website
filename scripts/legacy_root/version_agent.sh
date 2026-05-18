#!/bin/bash

# Navigate to your Obsidian vault
cd "/run/user/1000/gvfs/onedrive:host=47df85a1-cc91-46b2-bd1c-9fdecdc801ab/OneDrive/gemini_projects"

# Add all new and modified files to the staging area
git add .

# Commit the changes with a timestamp as the message
COMMIT_MESSAGE="Snapshot at $(date +'%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MESSAGE"

echo "New version created: $COMMIT_MESSAGE"
