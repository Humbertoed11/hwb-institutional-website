
import os
from moviepy import ColorClip, ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips

# Branding Configuration
PRIMARY_BLUE = (0, 74, 173) # #004aad
SECONDARY_GOLD = "#ffbd59"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LOGO_PATH = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/HWB-WEB Hwb Logo.png"
OUTPUT_DIR = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/gen_ai_staging"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "HWB-WEB-Marketing-4s.mp4")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_scene(text, logo_path, duration=1.0):
    # Background
    bg = ColorClip(size=(1280, 720), color=PRIMARY_BLUE, duration=duration)
    
    # Logo
    logo = ImageClip(logo_path).with_duration(duration).resized(height=200).with_position(("center", 150))
    
    # Text
    txt = TextClip(
        font=FONT,
        text=text,
        font_size=70,
        color=SECONDARY_GOLD,
        duration=duration
    ).with_position(("center", 450))
    
    return CompositeVideoClip([bg, logo, txt])

# Create 4 scenes
scenes = [
    create_scene("Shine Bright", LOGO_PATH),
    create_scene("Respect. Safety. Fidelity.", LOGO_PATH),
    create_scene("Professional Janitorial", LOGO_PATH),
    create_scene("GET A FREE QUOTE\n214-586-0257", LOGO_PATH)
]

# Concatenate
final_video = concatenate_videoclips(scenes)

# Write to file
# We use libx264 for MP4 compatibility
final_video.write_videofile(OUTPUT_PATH, fps=24, codec="libx264")

print(f"Video successfully created at {OUTPUT_PATH}")
