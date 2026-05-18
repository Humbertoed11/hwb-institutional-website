from PIL import Image, ImageDraw, ImageFont
import os

def create_corporate_banner():
    # Dimensions for SharePoint Hub Header
    width = 1920
    height = 480
    
    # Institutional Navy Blue
    navy_blue = (0, 74, 173) 
    white = (255, 255, 255)
    
    # Create Base Image
    banner = Image.new('RGB', (width, height), color=navy_blue)
    draw = ImageDraw.Draw(banner)
    
    # Add High-Fidelity Geometric Patterns (Subtle)
    for i in range(0, width, 100):
        draw.line([(i, 0), (i + 200, height)], fill=(10, 84, 183), width=2)
    
    # Load Font (Fallback to default if specific fonts missing)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    # Draw Text
    draw.text((100, 150), "HWB CLEANING SERVICES LLC", fill=white, font=font_large)
    draw.text((100, 250), "SIGMAFIDELITY™ INSTITUTIONAL DIVISION", fill=white, font=font_small)
    draw.text((100, 300), "FIDELITY. SAFETY. RESPECT.", fill=(200, 200, 200), font=font_small)
    
    # Add a white border accent at the bottom
    draw.rectangle([0, height-10, width, height], fill=white)

    # Save to Static Directory
    target_path = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-corporate-intranet-banner.png"
    banner.save(target_path)
    print(f"SUCCESS: Corporate banner generated at {target_path}")

if __name__ == "__main__":
    create_corporate_banner()
