import os
import re
import json
import requests
from dotenv import load_dotenv

# Load HWB Institutional Secrets
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")

def convert_html_to_nodes(html_content):
    """
    SigmaFidelity™ Light HTML-to-Telegraph Node Converter.
    Parses common structural HTML tags (<p>, <h2>, <h3>, <li>) into Telegraph's JSON node format.
    """
    nodes = []
    # Strip carriage returns and leading/trailing whitespace
    html_content = html_content.replace("\r", "").strip()
    
    # Simple regex block-tag matcher
    pattern = re.compile(r'<(\w+)[^>]*>(.*?)</\1>', re.DOTALL)
    matches = pattern.findall(html_content)
    
    for tag, content in matches:
        # Strip all nested HTML tags for standard child text nodes
        clean_text = re.sub(r'<[^>]+>', '', content).strip()
        if clean_text:
            nodes.append({
                "tag": tag,
                "children": [clean_text]
            })
            
    if not nodes:
        # Fallback to plain text in a paragraph node if no structural tags found
        clean_text = re.sub(r'<[^>]+>', '', html_content).strip()
        nodes.append({
            "tag": "p",
            "children": [clean_text]
        })
        
    return nodes

def create_telegraph_account(short_name="HWB-Systems", author_name="George"):
    """
    Register an anonymous Telegraph account dynamically and return the access token.
    """
    url = "https://api.telegra.ph/createAccount"
    params = {
        "short_name": short_name,
        "author_name": author_name
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                token = data.get("result", {}).get("access_token")
                print(f"[TELEGRAPH] Successfully created account. Access Token: {token}")
                return token
        print(f"[TELEGRAPH] Failed to create account: {res.text}")
    except Exception as e:
        print(f"[TELEGRAPH] Exception creating account: {e}")
    return None

def publish_to_telegraph(title, html_content, author_name="George", access_token=None):
    """
    Publish content to Telegra.ph and return the URL of the published page.
    """
    if not access_token:
        # Generate a dynamic anonymous token if none provided
        access_token = create_telegraph_account()
        if not access_token:
            return None
            
    nodes = convert_html_to_nodes(html_content)
    url = "https://api.telegra.ph/createPage"
    
    payload = {
        "access_token": access_token,
        "title": title,
        "author_name": author_name,
        "content": json.dumps(nodes),
        "return_content": False
    }
    
    try:
        res = requests.post(url, data=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                page_url = data.get("result", {}).get("url")
                print(f"[TELEGRAPH] Page published successfully: {page_url}")
                return page_url
            else:
                print(f"[TELEGRAPH] API returned error: {data.get('error')}")
        else:
            print(f"[TELEGRAPH] HTTP status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[TELEGRAPH] Exception publishing page: {e}")
    return None

def send_telegram_notification(message):
    """
    Dispatch a notification to the executive Telegram Chat via the Bot API.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured in .env.")
        print("[TELEGRAM] Setup Guide:")
        print("  1. Create a bot using BotFather on Telegram to get your Bot Token.")
        print("  2. Start a chat with your bot and fetch the Chat ID using: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("  3. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                print("[TELEGRAM] Notification dispatched successfully.")
                return True
            else:
                print(f"[TELEGRAM] API error: {data.get('description')}")
        else:
            print(f"[TELEGRAM] HTTP status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[TELEGRAM] Exception sending notification: {e}")
    return False

def broadcast_walkthrough(walkthrough_html_path, title="HWB Walkthrough Report"):
    """
    Primary interface: Reads a local HTML walkthrough report, publishes to Telegra.ph,
    and sends the link to the Telegram group chat.
    """
    if not os.path.exists(walkthrough_html_path):
        print(f"[ERROR] Walkthrough file not found: {walkthrough_html_path}")
        return False
        
    with open(walkthrough_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    print(f"Publishing walkthrough '{title}' to Telegra.ph...")
    page_url = publish_to_telegraph(title, html_content, access_token=TELEGRAPH_ACCESS_TOKEN)
    
    if page_url:
        notification_text = f"<b>🔔 HWB Systems Update</b>\n\nWalkthrough Report published:\n<a href='{page_url}'>{title}</a>"
        send_telegram_notification(notification_text)
        return True
        
    return False

if __name__ == "__main__":
    # Test publishing a simple greeting page
    test_html = "<h2>System Handshake Successful</h2><p>George has established communication channels via the Telegraph publishing engine.</p>"
    page = publish_to_telegraph("Telegraph Handshake Test", test_html, access_token=TELEGRAPH_ACCESS_TOKEN)
    if page:
        send_telegram_notification(f"<b>🔔 Systems Handshake</b>\n\nTelegraph publishing protocol active:\n{page}")
