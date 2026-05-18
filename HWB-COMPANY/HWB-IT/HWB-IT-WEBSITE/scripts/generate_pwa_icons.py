from PIL import Image, ImageDraw, ImageFont
import os

def create_pwa_icons():
    output_dir = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/icons"
    os.makedirs(output_dir, exist_ok=True)
    
    navy_blue = (0, 74, 173)
    white = (255, 255, 255)
    
    sizes = [192, 512]
    for size in sizes:
        img = Image.new('RGB', (size, size), color=navy_blue)
        draw = ImageDraw.Draw(img)
        
        # Draw a stylized 'HWB' or geometric shape
        padding = size * 0.2
        draw.rectangle([padding, padding, size-padding, size-padding], outline=white, width=int(size*0.05))
        
        # Load a default font for the letter 'H'
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size*0.4))
            # Center the 'H' roughly
            draw.text((size * 0.35, size * 0.25), "H", fill=white, font=font)
        except:
            # Fallback if font missing
            draw.line([(size*0.3, size*0.3), (size*0.3, size*0.7)], fill=white, width=int(size*0.05))
            draw.line([(size*0.7, size*0.3), (size*0.7, size*0.7)], fill=white, width=int(size*0.05))
            draw.line([(size*0.3, size*0.5), (size*0.7, size*0.5)], fill=white, width=int(size*0.05))
        
        img.save(os.path.join(output_dir, f"icon-{size}x{size}.png"))
        print(f"Generated icon-{size}x{size}.png")

if __name__ == "__main__":
    create_pwa_icons()
