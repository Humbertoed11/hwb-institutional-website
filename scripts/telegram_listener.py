import os
import re
import time
import tempfile
import requests
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

# SigmaFidelity™ Telegram Ingest Listener Daemon
# Responsibility: George (Systems Architect)

# Load secrets
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

# Verify configuration
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("[TELEGRAM] CRITICAL: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing from .env", flush=True)
    exit(1)

# Ensure numeric ID matching
try:
    ALLOWED_CHAT_ID = int(TELEGRAM_CHAT_ID)
except ValueError:
    ALLOWED_CHAT_ID = TELEGRAM_CHAT_ID

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM] Error sending message: {e}", flush=True)

def clean_html_content(html_text):
    # Remove script and style tags completely
    html_text = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)</\1>', '', html_text, flags=re.IGNORECASE)
    # Remove HTML comments
    html_text = re.sub(r'<!--[\s\S]*?-->', '', html_text)
    # Strip remaining HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    # Normalize whitespaces
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def ingest_url(url, chat_id):
    print(f"[TELEGRAM] Initiating scraping for URL: {url}", flush=True)
    send_telegram_message(chat_id, f"George: Fetching and analyzing content from {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            send_telegram_message(chat_id, f"George: Failed to access {url} (HTTP Status {response.status_code}).")
            return
            
        raw_html = response.text
        clean_text = clean_html_content(raw_html)
        
        if not clean_text or len(clean_text) < 50:
            send_telegram_message(chat_id, f"George: Scraped content from {url} is too short or empty.")
            return
            
        # Create a unique doc_id
        safe_slug = re.sub(r'[^a-zA-Z0-9]', '-', url)
        # Trim slug length
        safe_slug = safe_slug[-60:] if len(safe_slug) > 60 else safe_slug
        doc_id = f"telegram-ingest-{safe_slug}"
        
        metadata = {
            "source": "Telegram Ingest",
            "url": url,
            "chat_id": chat_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Write to PostgreSQL db
        conn = None
        try:
            conn = psycopg2.connect(DB_URL)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sigma_kb (doc_id, content, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
                """, (doc_id, clean_text, Json(metadata)))
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        print(f"[TELEGRAM] Successfully ingested {url} under {doc_id}", flush=True)
        send_telegram_message(chat_id, f"George: Website successfully stored in brain. Doc ID: {doc_id}")
        
    except Exception as e:
        print(f"[TELEGRAM] Scraping failure: {e}", flush=True)
        send_telegram_message(chat_id, f"George: Ingestion error for {url}. Details: {str(e)}")

def ingest_pdf(file_id, file_name, chat_id):
    print(f"[TELEGRAM] Initiating PDF download for: {file_name}", flush=True)
    send_telegram_message(chat_id, f"George: Downloading and parsing PDF document '{file_name}'...")
    
    # 1. Get file path from Telegram API
    get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    try:
        res = requests.get(get_file_url, params={"file_id": file_id}, timeout=15)
        if res.status_code != 200:
            send_telegram_message(chat_id, f"George: Failed to retrieve file path from Telegram (HTTP {res.status_code}).")
            return
        
        file_path = res.json().get("result", {}).get("file_path")
        if not file_path:
            send_telegram_message(chat_id, "George: Telegram did not return a valid file path.")
            return
            
        # 2. Download the file from Telegram servers
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        file_res = requests.get(download_url, timeout=30)
        if file_res.status_code != 200:
            send_telegram_message(chat_id, f"George: Failed to download PDF from Telegram servers (HTTP {file_res.status_code}).")
            return
            
        # 3. Save temporarily and parse via pypdf
        import pypdf
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file_name)
        
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file_res.content)
            
        # Parse PDF
        text = ""
        reader = pypdf.PdfReader(temp_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
                
        # Clean up local temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        text = text.strip()
        if not text or len(text) < 20:
            send_telegram_message(chat_id, f"George: Extracted PDF content from '{file_name}' is too short or empty.")
            return
            
        # 4. Store in database
        safe_slug = re.sub(r'[^a-zA-Z0-9]', '-', file_name)
        safe_slug = safe_slug[-60:] if len(safe_slug) > 60 else safe_slug
        doc_id = f"telegram-pdf-{safe_slug}"
        
        metadata = {
            "source": "Telegram Ingest (PDF)",
            "filename": file_name,
            "chat_id": chat_id,
            "timestamp": datetime.now().isoformat()
        }
        
        conn = None
        try:
            conn = psycopg2.connect(DB_URL)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sigma_kb (doc_id, content, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
                """, (doc_id, text, Json(metadata)))
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        print(f"[TELEGRAM] Successfully ingested PDF {file_name} under {doc_id}", flush=True)
        send_telegram_message(chat_id, f"George: PDF document '{file_name}' successfully stored in brain. Doc ID: {doc_id}")
        
    except Exception as e:
        print(f"[TELEGRAM] PDF Ingestion failure: {e}", flush=True)
        send_telegram_message(chat_id, f"George: Ingestion error for PDF '{file_name}'. Details: {str(e)}")

def process_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    
    # Security checkpoint: Only accept from verified chat ID
    if chat_id != ALLOWED_CHAT_ID:
        print(f"[TELEGRAM] Unauthorized command from chat_id {chat_id} blocked.", flush=True)
        return
        
    # Check for text
    text = message.get("text", "")
    if text:
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            for url in urls:
                ingest_url(url, chat_id)
        else:
            # Handle plain text note ingestion
            print(f"[TELEGRAM] Ingesting plain text note: {text[:30]}...", flush=True)
            send_telegram_message(chat_id, "George: Storing text note in brain...")
            
            timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
            doc_id = f"telegram-note-{timestamp_str}"
            
            metadata = {
                "source": "Telegram Ingest (Text Note)",
                "chat_id": chat_id,
                "timestamp": datetime.now().isoformat()
            }
            
            conn = None
            try:
                conn = psycopg2.connect(DB_URL)
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO sigma_kb (doc_id, content, metadata)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
                    """, (doc_id, text, Json(metadata)))
                conn.commit()
                send_telegram_message(chat_id, f"George: Text note successfully stored in brain. Doc ID: {doc_id}")
            except Exception as e:
                print(f"[TELEGRAM] Text Ingestion failure: {e}", flush=True)
                send_telegram_message(chat_id, f"George: Ingestion error for text note. Details: {str(e)}")
            finally:
                if conn:
                    conn.close()
                
    # Check for document (PDFs)
    document = message.get("document")
    if document:
        file_name = document.get("file_name", "")
        file_id = document.get("file_id")
        mime_type = document.get("mime_type", "")
        
        if file_id and (file_name.lower().endswith(".pdf") or "pdf" in mime_type.lower()):
            ingest_pdf(file_id, file_name, chat_id)
        else:
            send_telegram_message(chat_id, f"George: Attachment '{file_name}' ignored. Currently, only PDF documents are supported.")

def poll_updates():
    offset = None
    print("[TELEGRAM] Starting long-poll listener with PDF support...", flush=True)
    
    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
            
        try:
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    results = data.get("result", [])
                    for update in results:
                        update_id = update.get("update_id")
                        offset = update_id + 1
                        
                        message = update.get("message")
                        if message:
                            process_message(message)
            else:
                print(f"[TELEGRAM] getUpdates error: HTTP {response.status_code}", flush=True)
        except Exception as e:
            print(f"[TELEGRAM] Connection error: {e}", flush=True)
            
        time.sleep(2)

if __name__ == "__main__":
    poll_updates()
