import os
import pickle
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# Institutional Paths
TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

def test_youtube_connectivity():
    print("--- SigmaFidelity: YouTube Connectivity Diagnostic ---")
    
    # 1. Load Token
    if not os.path.exists(TOKEN_PICKLE_FILE):
        print(f"FAILURE: Token file not found at {TOKEN_PICKLE_FILE}")
        print("ACTION: Run '.venv_new/bin/python3 scripts/authenticate_youtube.py' first.")
        return

    with open(TOKEN_PICKLE_FILE, 'rb') as token:
        creds = pickle.load(token)

    # 2. Verify/Refresh
    if creds.expired and creds.refresh_token:
        print("Refreshing institutional token...")
        creds.refresh(Request())
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)

    # 3. Build Service
    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        
        # 4. Execute Test Call (Get My Channel Info)
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        response = request.execute()
        
        if "items" in response:
            channel = response['items'][0]
            print(f"SUCCESS: Connected to YouTube as '{channel['snippet']['title']}'")
            print(f"Channel ID: {channel['id']}")
            print(f"Total Views: {channel['statistics']['viewCount']}")
            print(f"Subscriber Count: {channel['statistics']['subscriberCount']}")
        else:
            print("FAILURE: No channel found for this account.")
            
    except googleapiclient.errors.HttpError as e:
        print(f"CRITICAL API ERROR: {e.resp.status} - {e.content}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {str(e)}")

if __name__ == "__main__":
    test_youtube_connectivity()
