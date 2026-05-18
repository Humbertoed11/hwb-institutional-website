import os
import pickle
import googleapiclient.discovery
import googleapiclient.http
from dotenv import load_dotenv

load_dotenv()

TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"
BANNER_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-corporate-intranet-banner.png"

# High-Fidelity Meta Profile
NEW_DESCRIPTION = (
    "HWB Cleaning Services LLC is the premier institutional sanitation provider in Dallas Fort Worth. "
    "Driven by the SigmaFidelity™ standard and ISO 9001:2015 certified quality, we specialize in the "
    "high-stakes environments of Daycares, Warehouses, and Construction sites. We believe leadership "
    "deserves better than burnout and children deserve the science of safety. Explore our systems at "
    "www.hwbcleaning.com and our startup SOPs at www.babysop.com. Fidelity. Safety. Respect."
)

NEW_KEYWORDS = (
    '"Commercial cleaning" "Daycare Sanitation" "SOP" "SigmaFidelity" "ISO 9001" '
    '"Plano TX" "Dallas Fort Worth" "Facility Management" "BabySOP" "Childcare Safety" "Business Systems"'
)

def update_channel_branding():
    print("--- SigmaFidelity: Executing YouTube Channel Overhaul ---")
    
    with open(TOKEN_PICKLE_FILE, 'rb') as token:
        creds = pickle.load(token)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    # 1. Fetch current channel info to get the ID
    channels_res = youtube.channels().list(part="id,brandingSettings", mine=True).execute()
    channel_id = channels_res['items'][0]['id']
    
    # 2. Upload the Banner (Requires 2 steps: Insert then Update)
    print("Step 1: Uploading New Institutional Banner...")
    try:
        banner_insert_res = youtube.channelBanners().insert(
            media_body=googleapiclient.http.MediaFileUpload(BANNER_PATH, mimetype='image/png')
        ).execute()
        banner_url = banner_insert_res['url']
        print(f"SUCCESS: Banner uploaded. Resource URL: {banner_url}")
    except Exception as e:
        print(f"WARNING: Banner upload failed: {str(e)}")
        banner_url = None

    # 3. Update Channel Metadata (Description, Keywords, Banner)
    print("Step 2: Injecting SEO-Optimized Metadata...")
    
    # Prepare the update body
    branding_body = {
        "id": channel_id,
        "brandingSettings": {
            "channel": {
                "description": NEW_DESCRIPTION,
                "keywords": NEW_KEYWORDS,
                "country": "US"
            }
        }
    }
    
    if banner_url:
        branding_body["brandingSettings"]["image"] = {"bannerExternalUrl": banner_url}

    update_res = youtube.channels().update(
        part="brandingSettings",
        body=branding_body
    ).execute()
    
    print(f"SUCCESS: Channel '{update_res['brandingSettings']['channel']['title']}' branding is now SigmaFidelity™ Compliant.")
    print("--- Overhaul Complete ---")

if __name__ == "__main__":
    update_channel_branding()
