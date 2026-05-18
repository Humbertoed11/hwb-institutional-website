import os
from moviepy import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips

OUTPUT_DIR = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/gen_ai_staging"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "HWB-BABYSOP-Lemonade.mp4")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_scene(text, color, duration=3.0, font_size=60):
    bg = ColorClip(size=(1280, 720), color=color, duration=duration)
    txt = TextClip(
        font=FONT,
        text=text,
        font_size=font_size,
        color="white",
        duration=duration
    ).with_position("center")
    return CompositeVideoClip([bg, txt])

scenes = [
    create_scene("A small boy asks his dad:\n'How does business work?'", (0, 74, 173), 3.0),
    create_scene("Dad gets lemons, sugar, water,\nand builds a wooden stand.", (218, 165, 32), 3.0), 
    create_scene("The first customer arrives!\nBut wait...", (200, 50, 50), 3.0), 
    create_scene("They can't close the sale.\nDad forgot the float cash!", (200, 50, 50), 3.0),
    create_scene("The Hero steps in with a $20 bill...", (46, 204, 113), 3.0), 
    create_scene("And explains the 'Baby SOP':", (0, 74, 173), 2.5),
    create_scene("BABY SOP - LEMONADE STAND\n\n1. Prep Supplies\n2. Set Up Float Cash\n3. Make the Sale", (0, 74, 173), 5.0, 50)
]

final_video = concatenate_videoclips(scenes)
final_video.write_videofile(OUTPUT_PATH, fps=24, codec="libx264")
print(f"Video saved to {OUTPUT_PATH}")
