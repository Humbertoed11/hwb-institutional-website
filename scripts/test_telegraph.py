import os
import re
import sys
from telegraph_client import publish_to_telegraph, TELEGRAPH_ACCESS_TOKEN

def md_to_html(md_text):
    """
    SigmaFidelity™ Ultra-Lightweight Markdown-to-HTML Converter.
    Translates basic markdown structures into clean, block-level HTML tags for Telegraph.
    """
    html_lines = []
    lines = md_text.split("\n")
    
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                in_list = False
            continue
            
        # 1. Headings
        if line.startswith("# "):
            if in_list: in_list = False
            html_lines.append(f"<h2>{line[2:].strip()}</h2>")
        elif line.startswith("## "):
            if in_list: in_list = False
            html_lines.append(f"<h3>{line[3:].strip()}</h3>")
        elif line.startswith("### "):
            if in_list: in_list = False
            html_lines.append(f"<h3>{line[4:].strip()}</h3>")
        # 2. List Items
        elif line.startswith("* ") or line.startswith("- "):
            in_list = True
            # Clean list markers
            item_text = line[2:].strip()
            # Clean checkmark markdown if present ([x], [ ], [/])
            item_text = re.sub(r'^\[[xX ]\]\s*', '', item_text)
            item_text = re.sub(r'^\[\/\]\s*', '', item_text)
            html_lines.append(f"<li>{item_text}</li>")
        # 3. Horizontal Rules
        elif line == "---":
            if in_list: in_list = False
            html_lines.append("<p>—</p>")
        # 4. Standard Paragraphs
        else:
            if in_list: in_list = False
            # Clean links markdown [text](url) to plain text
            line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
            # Clean bold/italic indicators
            line = line.replace("**", "").replace("*", "")
            html_lines.append(f"<p>{line}</p>")
            
    return "\n".join(html_lines)

def run_test():
    print("--- SigmaFidelity: Initiating Telegraph Walkthrough Publisher Test ---")
    
    # Locate the active session walkthrough
    latest_dir = "/home/humbertoed/.gemini/antigravity-cli/brain/2cb93ce6-bded-4b6c-bd12-b445e32492ba"
    walkthrough_path = os.path.join(latest_dir, "walkthrough.md")
    
    if not os.path.exists(walkthrough_path):
        print(f"[ERROR] Walkthrough file not found: {walkthrough_path}")
        sys.exit(1)
        
    print(f"Reading walkthrough from: {walkthrough_path}")
    with open(walkthrough_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
    print("Converting Markdown to HTML...")
    html_content = md_to_html(md_content)
    
    title = "HWB Institutional Website Walkthrough Report"
    print(f"Publishing page '{title}' to Telegra.ph...")
    
    page_url = publish_to_telegraph(title, html_content, access_token=TELEGRAPH_ACCESS_TOKEN)
    
    if page_url:
        print(f"\nSUCCESS: Walkthrough report successfully published via Telegraph!")
        print(f"URL: {page_url}")
    else:
        print("\nFAILED: Publishing process failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
