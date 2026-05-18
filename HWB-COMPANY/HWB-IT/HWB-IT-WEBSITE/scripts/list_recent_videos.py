import os
import pickle
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv()

TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

def list_recent_videos():
    print("--- SigmaFidelity: Fetching Recent Uploads ---")
    
    if not os.path.exists(TOKEN_PICKLE_FILE):
        print("FAILURE: Token missing.")
        return

    with open(TOKEN_PICKLE_FILE, 'rb') as token:
        creds = pickle.load(token)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    
    # 1. Get the 'Uploads' playlist ID
    channels_res = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_id = channels_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # 2. List videos from the uploads playlist
    playlist_res = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_id,
        maxResults=5
    ).execute()
    
    for item in playlist_res['items']:
        print(f"- Title: {item['snippet']['title']} | ID: {item['snippet']['resourceId']['videoId']}")

if __name__ == "__main__":
    list_recent_videos()
