import os
import re

STRATEGY_FILE = 'mop_incident/HWB-WEB Flowchart Marketing Strategy.md'
INDEX_FILE = 'mop_incident/templates/HWB-WEB Index.html'

def test_tagline_alignment():
    print("--- SigmaFidelity: Tagline Alignment Audit ---")
    
    if not os.path.exists(STRATEGY_FILE):
        print(f"ERROR: Strategy file not found: {STRATEGY_FILE}")
        return
    if not os.path.exists(INDEX_FILE):
        print(f"ERROR: Index file not found: {INDEX_FILE}")
        return

    # Extract Primary Hook from Strategy
    with open(STRATEGY_FILE, 'r') as f:
        strategy_content = f.read()
    
    hook_match = re.search(r'\*\*Primary Hook:\*\* "(.*)"', strategy_content)
    if not hook_match:
        print("ERROR: Could not find Primary Hook in Strategy document.")
        return
    
    strategy_tagline = hook_match.group(1)
    print(f"Strategy Tagline: '{strategy_tagline}'")

    # Extract H1 from Index
    with open(INDEX_FILE, 'r') as f:
        index_content = f.read()
    
    h1_match = re.search(r'<h1>(.*)</h1>', index_content)
    if not h1_match:
        print("ERROR: Could not find <h1> tag in Index page.")
        return
    
    index_tagline = h1_match.group(1)
    print(f"Current Index Tagline: '{index_tagline}'")

    if strategy_tagline == index_tagline and "you" not in index_tagline.lower() and "your" not in index_tagline.lower():
        print("SUCCESS: Taglines are aligned in 3rd person.")
    else:
        print("DEFECT: Tagline mismatch or 2nd person detected!")
        print(f"Expected (3rd Person): '{strategy_tagline}'")
        print(f"Actual:                 '{index_tagline}'")

if __name__ == "__main__":
    test_tagline_alignment()
