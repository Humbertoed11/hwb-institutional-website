from PIL import Image, ImageDraw, ImageFont
import os

def create_youtube_banner():
    # YouTube Standard Dimensions
    width = 2560
    height = 1440
    
    # Safe Area for Desktop/Mobile (1546 x 423)
    safe_width = 1546
    safe_height = 423
    
    navy_blue = (0, 74, 173)
    white = (255, 255, 255)
    
    # Create Base
    banner = Image.new('RGB', (width, height), color=navy_blue)
    draw = ImageDraw.Draw(banner)
    
    # Add Subtle Background Pattern
    for i in range(0, width, 200):
        draw.line([(i, 0), (i + 400, height)], fill=(10, 84, 183), width=3)

    # Central Safe Area Design (This is what shows on most devices)
    safe_top = (height - safe_height) // 2
    safe_left = (width - safe_width) // 2
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw Corporate Identity in Safe Area
    draw.text((safe_left + 100, safe_top + 100), "HWB CLEANING", fill=white, font=font_large)
    draw.text((safe_left + 100, safe_top + 250), "SIGMAFIDELITY™ INSTITUTIONAL STANDARDS", fill=white, font=font_small)
    draw.text((safe_left + 100, safe_top + 320), "FIDELITY. SAFETY. RESPECT.", fill=(200, 200, 200), font=font_small)

    # Save Asset
    output_path = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/static/youtube_assets/hwb-cleaning-services-llc-youtube-banner-plano-tx.png"
    banner.save(output_path)
    print(f"SUCCESS: Corrected 2560x1440 YouTube Banner generated at {output_path}")

if __name__ == "__main__":
    create_youtube_banner()
