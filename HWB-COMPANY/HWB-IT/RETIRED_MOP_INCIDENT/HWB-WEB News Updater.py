import json
import time
import os

TEMPLATE_PATH = 'templates/HWB-WEB Resources.html'
QUEUE_PATH = 'HWB-WEB News Queue.json'

def update_page(cycle_data):
    with open(TEMPLATE_PATH, 'r') as f:
        content = f.read()

    # Identify the news section
    news_start_marker = '<div class="news-grid">'
    news_end_marker = '</div>'
    
    start_idx = content.find(news_start_marker) + len(news_start_marker)
    end_idx = content.find(news_end_marker, start_idx)

    # Build new HTML for the 3 articles in this cycle
    new_news_html = ""
    for item in cycle_data['news']:
        tag_class = item['tag'].lower()
        new_news_html += f"""
                    <div class="news-item">
                        <span class="news-tag {tag_class}">{item['tag']} INTEL</span>
                        <h4>{item['title']}</h4>
                        <p>{item['desc']}</p>
                        <a href="{item['url']}" target="_blank">Read Article →</a>
                    </div>"""
    
    updated_content = content[:start_idx] + new_news_html + content[end_idx:]
    
    with open(TEMPLATE_PATH, 'w') as f:
        f.write(updated_content)
    
    print(f"Marketing Assistant: Cycle {cycle_data['cycle']} deployed at {time.strftime('%H:%M:%S')}", flush=True)

def run_sync():
    print(f"Marketing Assistant: Starting sync at {time.strftime('%H:%M:%S')}", flush=True)
    if not os.path.exists(QUEUE_PATH):
        print(f"Error: Queue file not found at {QUEUE_PATH}")
        return
        
    with open(QUEUE_PATH, 'r') as f:
        queue = json.load(f)
    
    for cycle in queue:
        update_page(cycle)
        if cycle['cycle'] < 6:
            time.sleep(600) # Wait 10 minutes

if __name__ == "__main__":
    run_sync()
