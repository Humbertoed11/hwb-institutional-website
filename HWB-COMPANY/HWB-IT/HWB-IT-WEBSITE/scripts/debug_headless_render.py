import asyncio
import os
from playwright.async_api import async_playwright

async def debug_render():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("--- Initiating Headless Render Debug ---")
        
        # 1. Login
        await page.goto("http://localhost:8000/debug/aesthetic-audit")
        await page.wait_for_timeout(1000)
        
        # 2. Access Operations
        print("Accessing Dashboard...")
        response = await page.goto("http://localhost:8000/admin/operations?view=accounts")
        print(f"HTTP Status: {response.status}")
        
        # 3. Capture Content
        content = await page.content()
        print(f"Content Length: {len(content)} bytes")
        
        # Look for the button in the raw content
        has_btn = "#btn-add-main" in content
        print(f"Has 'btn-add-main' in source: {has_btn}")
        
        with open("diag_headless_render.html", "w") as f:
            f.write(content)
            
        await page.screenshot(path="static/gen_ai_staging/diag_headless_render.png")
        await browser.close()
        print("--- Debug Complete ---")

if __name__ == "__main__":
    asyncio.run(debug_render())
