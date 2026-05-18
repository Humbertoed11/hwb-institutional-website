import os
import pickle
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv()

TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

# Accurate High-Fidelity Template
GLOBAL_FOOTER = """
---
Experience the SigmaFidelity™ difference in industrial sanitation. HWB Cleaning Services LLC specializes in high-stakes floor care, construction cleaning, and warehouse maintenance across the DFW Metroplex. 

We are currently in the active phase of preparing for ISO 9001:2015 Certification to further standardize our commitment to operational excellence.

Explore our systems: www.hwbcleaning.com
Startup Solutions: www.babysop.com

#HWBcleaning #SigmaFidelity #WarehouseCleaning #ConstructionClean #FloorCare #Tennant #PlanoTX #DFWBusiness #ISO9001
"""

def batch_optimize_videos():
    print("--- SigmaFidelity: Batch Metadata Optimization (Fixed) ---")
    
    with open(TOKEN_PICKLE_FILE, 'rb') as token:
        creds = pickle.load(token)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    
    # 1. Fetch Uploads
    channels_res = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_id = channels_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    playlist_res = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_id,
        maxResults=50
    ).execute()
    
    for item in playlist_res['items']:
        v_id = item['snippet']['resourceId']['videoId']
        title = item['snippet']['title']
        
        # Explicitly get the full video object to acquire the correct categoryId
        v_res = youtube.videos().list(part="snippet", id=v_id).execute()
        v_snippet = v_res['items'][0]['snippet']
        current_desc = v_snippet['description']
        
        # Avoid double-updating
        if "hwbcleaning.com" in current_desc and "ISO 9001" in current_desc:
            print(f"SKIPPING: {title} is already optimized.")
            continue

        print(f"OPTIMIZING: {title}...")
        
        # Prepare New Snippet
        v_snippet['description'] = current_desc + "\n" + GLOBAL_FOOTER
        
        try:
            youtube.videos().update(
                part="snippet",
                body={
                    "id": v_id,
                    "snippet": v_snippet
                }
            ).execute()
            print(f"SUCCESS: Metadata injected into {title}.")
        except Exception as e:
            print(f"WARNING: Could not update {title}. {str(e)}")

if __name__ == "__main__":
    batch_optimize_videos()
