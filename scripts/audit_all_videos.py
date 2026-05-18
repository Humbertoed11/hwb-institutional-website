import os
import pickle
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv()

TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

def audit_all_videos():
    print("--- SigmaFidelity: Comprehensive Video Metadata Audit ---")
    
    with open(TOKEN_PICKLE_FILE, 'rb') as token:
        creds = pickle.load(token)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    
    # 1. Get 'Uploads' playlist ID
    channels_res = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_id = channels_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # 2. Retrieve all video IDs from the uploads playlist
    videos = []
    next_page_token = None
    
    while True:
        playlist_res = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        videos.extend(playlist_res['items'])
        next_page_token = playlist_res.get('nextPageToken')
        if not next_page_token:
            break

    print(f"Total Videos Found: {len(videos)}")
    
    # 3. Analyze each video for SEO gaps
    for v in videos:
        snippet = v['snippet']
        v_id = snippet['resourceId']['videoId']
        title = snippet['title']
        desc = snippet['description']
        
        print(f"\n--- AUDITING VIDEO: {title} ({v_id}) ---")
        
        gaps = []
        if len(desc) < 100: gaps.append("Description too short.")
        if "hwbcleaning.com" not in desc: gaps.append("Missing corporate link.")
        if "Fidelity" not in desc: gaps.append("Missing SigmaFidelity branding.")
        if "#" not in desc: gaps.append("No hashtags detected.")
        
        if gaps:
            print(f"SEO DEFICIENCIES: {', '.join(gaps)}")
        else:
            print("STATUS: SEO Compliant.")

if __name__ == "__main__":
    audit_all_videos()
