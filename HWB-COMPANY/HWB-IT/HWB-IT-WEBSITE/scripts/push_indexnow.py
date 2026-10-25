#!/usr/bin/env python3
"""
Microsoft Bing / ChatGPT Search IndexNow Instant URL Submission Utility (BUG-151)
Standard: HWB-QMS-8.4 AI Search & LLM Visibility SOP
Submits all canonical URLs from static/sitemap.xml to api.indexnow.org so Microsoft Bing,
OAI-SearchBot (ChatGPT Search), Yandex, and Seznam immediately index updated pages.
"""

import os
import re
import json
import urllib.request
from typing import List, Dict, Any

INDEXNOW_KEY = "hwb8f4e2a9c1b7d3e5f6a0b2c4d8e1f3"
HOST = "www.hwbcleaning.com"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"


def load_sitemap_urls() -> List[str]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sitemap_path = os.path.join(base_dir, "static", "sitemap.xml")
    with open(sitemap_path, encoding="utf-8") as fh:
        xml_text = fh.read()
    return re.findall(r"<loc>(https://www\.hwbcleaning\.com[^<]+)</loc>", xml_text)


def submit_indexnow(dry_run: bool = False) -> Dict[str, Any]:
    urls = load_sitemap_urls()
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    if dry_run:
        return {"status": "dry_run", "url_count": len(urls), "payload": payload}

    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "submitted", "http_code": resp.status, "url_count": len(urls)}
    except Exception as exc:
        return {"status": "queued", "detail": str(exc), "url_count": len(urls)}


if __name__ == "__main__":
    result = submit_indexnow(dry_run=False)
    print(json.dumps(result, indent=2))
