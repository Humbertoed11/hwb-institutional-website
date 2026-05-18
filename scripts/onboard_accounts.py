import asyncio
import os
from playwright.async_api import async_playwright

async def onboard_accounts():
    accounts = [
        {
            "company": "North Texas Logistics Hub",
            "contact": "Sarah Miller",
            "phone": "12145550101",
            "email": "smiller@ntlogistics.com",
            "address": "4500 Logistics Way",
            "city": "Plano",
            "zip": "75024",
            "sqf": "25000",
            "quote": "Q-2026-001",
            "revenue": "45000.00",
            "frequency": "5x Week"
        },
        {
            "company": "Preston Road Medical Plaza",
            "contact": "Dr. Robert Chen",
            "phone": "19725550202",
            "email": "admin@prestonmedical.com",
            "address": "8200 Preston Rd",
            "city": "Frisco",
            "zip": "75034",
            "sqf": "12000",
            "quote": "Q-2026-002",
            "revenue": "28000.00",
            "frequency": "3x Week"
        },
        {
            "company": "Silicon Prairie Tech Center",
            "contact": "Mark Thompson",
            "phone": "18175550303",
            "email": "facilities@siliconprairie.com",
            "address": "1500 Innovation Dr",
            "city": "Richardson",
            "zip": "75080",
            "sqf": "50000",
            "quote": "Q-2026-003",
            "revenue": "85000.00",
            "frequency": "Daily"
        }
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a single context for persistent session
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()

        print("--- Initiating SigmaFidelity™ Standard Onboarding Sequence ---")
        
        # 1. Login via Form (Ensures cookie persistence)
        print("Step 1: Authenticating via Secure Vault...")
        await page.goto("http://localhost:8000/login")
        await page.fill("input[name='username']", "admin")
        await page.fill("input[name='password']", "hwbpassword2026")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/admin/operations**")
        print("  Session Established.")
        
        for idx, acc in enumerate(accounts, 1):
            print(f"Onboarding Account {idx}/3: {acc['company']}...")
            
            # 2. Access Accounts View
            await page.goto("http://localhost:8000/admin/operations?view=accounts")
            # Wait for data table to load
            await page.wait_for_selector(".accounts-row, #btn-add-main", timeout=10000)
            
            # 3. Trigger Modal
            await page.click("#btn-add-main")
            await page.wait_for_selector("#add-menu", state="visible")
            await page.click("button:has-text('New Account')")
            await page.wait_for_selector("#modal-add-account", state="visible")
            
            # 4. Fill Data
            await page.fill("#modal-add-account input[name='company_name']", acc['company'])
            await page.fill("#modal-add-account input[name='contact_person_name']", acc['contact'])
            await page.fill("#modal-add-account input[name='phone']", acc['phone'])
            await page.fill("#modal-add-account input[name='email']", acc['email'])
            await page.fill("#modal-add-account input[name='company_address']", acc['address'])
            await page.fill("#modal-add-account input[name='city']", acc['city'])
            await page.fill("#modal-add-account input[name='zip']", acc['zip'])
            await page.fill("#modal-add-account input[name='sqf']", acc['sqf'])
            await page.fill("#modal-add-account input[name='quote_number']", acc['quote'])
            await page.select_option("#modal-add-account select[name='frequency']", acc['frequency'])
            await page.fill("#modal-add-account input[name='annual_revenue']", acc['revenue'])
            
            # 5. Submit
            await page.click("#modal-add-account button:has-text('Activate Account')")
            await page.wait_for_url("**/admin/operations?view=accounts")
            print(f"  SUCCESS: {acc['company']} onboarded.")
            await page.wait_for_timeout(1000)

        # Final Capture
        print("Finalizing Portfolio Audit...")
        await page.screenshot(path="static/gen_ai_staging/onboarding_final_success.png", full_page=True)
        await browser.close()
        print("--- Standard Onboarding Complete ---")

if __name__ == "__main__":
    asyncio.run(onboard_accounts())
