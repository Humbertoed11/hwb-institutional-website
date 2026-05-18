#!/bin/bash

# This script renames Markdown files (.md) to follow a naming convention:
# - Removes hyphens and underscores
# - Capitalizes the first letter of each word (simple Title Case)
# - Asks for confirmation before renaming each file.

echo "Starting note renaming process..."
echo "This script will suggest new names for your .md files based on the convention:"
echo "  - No hyphens or underscores"
echo "  - First letter of each word capitalized (simple Title Case)"
echo ""

# Find all Markdown files, excluding those in .git and .obsidian directories
find . -type f -name "*.md" -not -path "./.git/*" -not -path "./.obsidian/*" | while read -r old_path; do
  # Extract just the filename (without path or extension)
  filename=$(basename -- "$old_path")
  extension="${filename##*.}"
  filename_no_ext="${filename%.*}"

  # Remove hyphens and underscores, replacing them with spaces
  new_filename_no_ext=$(echo "$filename_no_ext" | sed 's/[-_]/ /g')

  # Capitalize the first letter of each word (simple Title Case)
  # This sed command capitalizes the first letter of each word boundary.
  new_filename_no_ext=$(echo "$new_filename_no_ext" | sed -r 's/\b(.)/\U\1/g')

  # Construct the new full path
  dir_path=$(dirname -- "$old_path")
  new_path="$dir_path/$new_filename_no_ext.$extension"

  # Skip if the new name is the same as the old name
  if [[ "$old_path" == "$new_path" ]]; then
    continue
  fi

  echo "--------------------------------------------------"
  echo "Current file: $old_path"
  echo "Proposed new: $new_path"
  read -p "Rename this file? (y/N): " confirm
  if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
    mv "$old_path" "$new_path"
    echo "Renamed: $old_path -> $new_path"
  else
    echo "Skipped: $old_path"
  fi
done

echo "--------------------------------------------------"
echo "Note renaming process complete."
echo "Please remember to update any internal links in Obsidian that might have broken due to renaming."