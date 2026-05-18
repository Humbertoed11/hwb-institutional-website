import requests
from bs4 import BeautifulSoup
import os
import urllib.parse

def harvest_photos(urls, output_dir):
    print(f"--- SigmaFidelity: Initiating Deep Photo Harvest ---")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    img_urls = set()

    for url in urls:
        print(f"Scanning: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    img_urls.add(urllib.parse.urljoin(url, src))
        except Exception as e:
            print(f"Scan Error on {url}: {e}")

    count = 0
    for img_url in img_urls:
        if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            try:
                filename = os.path.basename(urllib.parse.urlparse(img_url).path)
                # Avoid generic filenames or empty extensions
                if not filename or '.' not in filename:
                    filename = f"hwb_asset_{count}.jpg"
                
                with open(os.path.join(output_dir, filename), 'wb') as f:
                    f.write(requests.get(img_url, headers=headers).content)
                print(f"Captured: {filename}")
                count += 1
            except:
                pass

    print(f"--- Deep Harvest Complete: {count} assets captured ---")

if __name__ == "__main__":
    target_urls = [
        "https://www.hwbcleaning.com",
        "https://www.hwbcleaning.com/our-services",
        "https://www.hwbcleaning.com/facility-services",
        "https://www.hwbcleaning.com/industries"
    ]
    harvest_photos(target_urls, "static/photos")
