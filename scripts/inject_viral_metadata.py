import os
import pickle
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv()

TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"
VIDEO_ID = "Sw5jpgdRI9Q"

# High-Fidelity Profile (HWB-MKT-BSOP-MET-001)
TITLE = "It is what it is"
DESCRIPTION = """Yesterday I had an appointment at a daycare to discuss cleaning services. The director greeted me at the lobby. She was cleaning the floors and on the edge of a meltdown.

Her regional director had scheduled a surprise visit. The pressure was intense. The previous inspections had not gone as expected. 

On the surface, everything looked normal—babies cooing, toddlers napping, kids playing.

But the details told a different story.

The observation windows were layered with weeks of smudges. The staff wore those “happy-tired” smiles you see on professionals being stretched to their limit. In the toddler rooms—where children crawl all day—the rugs were soiled and the floors had that sticky pull under your shoes that comes from mopping with dirty water.

I asked to see the janitorial closet.

This is where the true health of a facility is revealed. 

To maintain a 13,000 sq ft. daycare with 195 children, takes professional grade equipment. It's janitorial grade work. 

The director walked me through her equipment: 
- One household mop head
- A rusty mop bucket missing a wheel
- A small home vacuum
- One gallon of Fabuloso
- And cloth rags for wiping and dusting

The director told me something I've heard before.
"When I accepted the job, my regional director made one thing clear:
We do our own cleaning in-house.
I was instructed to “work it into the schedule” and divide the cleaning responsibilities among my staff.
I couldn’t bring myself to ask the staff—after an 8-hour shift of caring for children—to scrub 12 little bathrooms.
So I get the job done. Night after night. Sometimes staying until 9:00 PM just to get us ready for the next day."

Then she said with a very decisive voice:
“I want to pay for a deep clean out of my own pocket. I can’t afford to lose my job over failing inspections or the mandate to keep lowering operational expenses.”

I offered to deep clean the facility at no charge.
The next day she called back.
She thanked me, but said she couldn’t accept it. She knew the labor and cost involved, and it didn’t feel right. She told me corporate would not extend a cleaning contract anyway. 

Then she said something everyone who leads a team should hear:
“It is what it is. I’m going to meet with my district manager and resign. My family deserves to see me after work.”

Moments like that remind me of something simple:
Behind every “cost-saving mandate” is usually a professional quietly absorbing the pressure.
And sometimes… they break.

---
At HWB Cleaning Services LLC, we believe leadership deserves better. We believe children deserve better.

Standardizing safety and excellence through SigmaFidelity™:
- Corporate Site: www.hwbcleaning.com
- Startup Systems: www.babysop.com

#DaycareManagement #LeadershipBurnout #CleaningServices #SigmaFidelity #HWBcleaning #BabySOP #FacilityManagement #BusinessEthics #StartupGrowth #PlanoTX
"""

TAGS = ["Daycare", "Childcare Safety", "Janitorial Services", "Burnout", "Leadership", "SOP", "ISO 9001", "Business Management", "Plano TX", "HWB Cleaning"]

def inject_metadata():
    print(f"--- SigmaFidelity: Metadata Injection for Video {VIDEO_ID} ---")
    
    with open(TOKEN_PICKLE_FILE, 'rb') as token:
        creds = pickle.load(token)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    
    # 1. Update snippet (Title, Description, Tags, Category)
    request = youtube.videos().update(
        part="snippet,status",
        body={
            "id": VIDEO_ID,
            "snippet": {
                "title": TITLE,
                "description": DESCRIPTION,
                "tags": TAGS,
                "categoryId": "27" # Education
            },
            "status": {
                "selfDeclaredMadeForKids": False # This is about management/burnout, not for kids
            }
        }
    )
    
    response = request.execute()
    print(f"SUCCESS: Viral Metadata injected into video '{response['snippet']['title']}'.")
    print(f"URL: https://youtu.be/{VIDEO_ID}")

if __name__ == "__main__":
    inject_metadata()
