#!/bin/bash

# This script modifies the main title (H1) inside Markdown files (.md)
# to follow a naming convention:
# - Removes hyphens and underscores
# - Capitalizes the first letter of each word (simple Title Case)
# - Asks for confirmation before modifying each file.

echo "Starting note retitling process..."
echo "This script will suggest new titles for your .md files based on the convention:"
echo "  - No hyphens or underscores in the title"
echo "  - First letter of each word capitalized (simple Title Case)"
echo ""

# Find all Markdown files, excluding those in .git and .obsidian directories
find . -type f -name "*.md" -not -path "./.git/*" -not -path "./.obsidian/*" | while read -r file_path; do
  # Read the first line of the file
  first_line=$(head -n 1 "$file_path")

  # Check if the first line is a level 1 heading
  if [[ "$first_line" == "# "* ]]; then
    # Extract the title text (remove the '# ' prefix)
    title_text=${first_line:2}

    # Remove hyphens and underscores, replacing them with spaces
    new_title_text=$(echo "$title_text" | sed 's/[-_]/ /g')

    # Capitalize the first letter of each word (simple Title Case)
    new_title_text=$(echo "$new_title_text" | sed -r 's/\b(.)/\U\1/g')

    # Construct the new full heading line
    new_heading="# $new_title_text"

    # Skip if the new heading is the same as the old one
    if [[ "$first_line" == "$new_heading" ]]; then
      continue
    fi

    echo "--------------------------------------------------"
    echo "File: $file_path"
    echo "Current title: $first_line"
    echo "Proposed new:  $new_heading"
    read -p "Update this title? (y/N): " confirm
    if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
      # Use sed to replace only the first line of the file
      sed -i "1s/.*/$new_heading/" "$file_path"
      echo "Updated title in: $file_path"
    else
      echo "Skipped: $file_path"
    fi
  fi
done

echo "--------------------------------------------------"
echo "Note retitling process complete."
