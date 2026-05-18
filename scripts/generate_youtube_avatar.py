from PIL import Image
import os

# Institutional Paths
SOURCE_LOGO = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-cleaning-services-llc-logo-plano-tx.png"
OUTPUT_DIR = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/static/youtube_assets"
# SEO-Optimized Filename for YouTube Crawlers
OUTPUT_FILENAME = "hwb-cleaning-services-llc-youtube-logo-plano-tx.png"

def generate_youtube_logo():
    if not os.path.exists(SOURCE_LOGO):
        print(f"FAILURE: Source logo not found at {SOURCE_LOGO}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # Load and verify image
        with Image.open(SOURCE_LOGO) as img:
            # YouTube recommendation is 800x800 for high-fidelity rendering
            # but user requested at least 100x100. We will use 800x800 for 100% quality.
            target_size = (800, 800)
            
            # Create a white background square
            canvas = Image.new("RGBA", target_size, (255, 255, 255, 255))
            
            # Resize source while maintaining aspect ratio
            img.thumbnail((700, 700), Image.Resampling.LANCZOS)
            
            # Center the logo on the canvas
            offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
            canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
            
            # Save final asset
            output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
            canvas.save(output_path, "PNG")
            
            print(f"SUCCESS: YouTube Logo generated at {output_path}")
            print(f"Fidelity: 800x800 (SEO Optimized Filename)")
            
    except Exception as e:
        print(f"FAILURE: Logo generation failed. {str(e)}")

if __name__ == "__main__":
    generate_youtube_logo()
