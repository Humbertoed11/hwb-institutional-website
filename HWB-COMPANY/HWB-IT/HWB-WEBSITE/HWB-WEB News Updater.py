import json
import time
import os
import sys

TEMPLATE_PATH = 'templates/HWB-WEB Resources.html'
QUEUE_PATH = 'HWB-WEB News Queue.json'

def update_page(cycle_data):
    with open(TEMPLATE_PATH, 'r') as f:
        content = f.read()

    # Identify the news section using markers
    news_start_marker = '<!-- START_NEWS -->'
    news_end_marker = '<!-- END_NEWS -->'
    
    start_idx = content.find(news_start_marker) + len(news_start_marker)
    end_idx = content.find(news_end_marker)

    if start_idx == -1 or end_idx == -1:
        print("Error: Could not find news markers in template.")
        return

    # Build new Carousel HTML
    new_news_html = ""
    for item in cycle_data['news']:
        tag_class = item['tag'].lower()
        new_news_html += f"""
                <div class="news-slide">
                    <span class="slide-tag {tag_class}">{item['tag']} INTEL</span>
                    <h3>{item['title']}</h3>
                    <p>{item['desc']}</p>
                    <a href="{item['url']}" target="_blank" class="btn-read">Read Empirical Source →</a>
                </div>"""
    
    updated_content = content[:start_idx] + new_news_html + "\n                " + content[end_idx:]
    
    with open(TEMPLATE_PATH, 'w') as f:
        f.write(updated_content)
    
    # Re-initialize the carousel via script if possible, but the JS in template handles dynamic count
    print(f"Marketing Assistant: Cycle {cycle_data['cycle']} deployed at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

def run_sync():
    print(f"Marketing Assistant: Starting autonomous sync loop at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    if not os.path.exists(QUEUE_PATH):
        print(f"Error: Queue file not found at {QUEUE_PATH}")
        return
        
    with open(QUEUE_PATH, 'r') as f:
        queue = json.load(f)
    
    while True:
        for cycle_data in queue:
            update_page(cycle_data)
            # Wait 10 minutes between news cycle updates
            time.sleep(600)

if __name__ == "__main__":
    run_sync()
