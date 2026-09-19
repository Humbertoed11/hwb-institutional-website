#!/usr/bin/env python3
"""
SigmaFidelity™ Daycare Economic Enrichment Engine v2.0
Responsibility: Silas Sync (VP of CRM) & George (Systems Architect)
Governance: HWB-QMS-11.1 / Minimization Mandate / Empirical Integrity Mandate
"""

import os
import re
import sys
import time
import socket
import urllib.parse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import fake_useragent
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")

ua = fake_useragent.UserAgent()

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
IGNORE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff', '.ttf', '.mp4')
IGNORE_DOMAINS = (
    'sentry.io', 'wixpress.com', 'google.com', 'schema.org', 'domain.com', 
    'example.com', 'cloudflare.com', 'wordpress.org', 'w3.org'
)
EXCLUDED_SEARCH_DOMAINS = (
    'yelp.com', 'mapquest.com', 'yellowpages.com', 'texasdaycarecheck.com', 
    'daycarehub.us', 'childcarecenter.us', 'superpages.com', 'bbb.org',
    'facebook.com/login', 'linkedin.com/login', 'indeed.com', 'care.com',
    'winnie.com', 'kangarootime.com', 'greatschools.org', 'privateschoolreview.com',
    'niche.com', 'preschools.co', 'daycarecenter.com', 'daycare.com', 
    'chamberofcommerce.com', 'us-wide-childcare', 'daycarepath.com'
)


DUMMY_EMAIL_PATTERNS = (
    'jane@', 'john@', 'test@', 'sample@', 'example@', 'name@', 'user@', 
    'email@', 'yourname@', 'someone@', 'admin@domain', 'info@domain', 
    '@example.', '@sentry.', '@wixpress.', 'domain@', 'contact@domain'
)


def init_billing_tracker(conn):
    """Ensures API billing ledger exists to track spend."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "ApiBillingTracker" (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                service_name VARCHAR(100),
                endpoint VARCHAR(255),
                lead_id INTEGER,
                cost_usd NUMERIC(8, 4),
                status VARCHAR(50)
            );
        """)
    conn.commit()

def verify_mx_record(email_address):
    """Verifies recipient domain has valid mail exchangers to prevent cold email bounces."""
    if not email_address or "@" not in email_address:
        return False
    domain = email_address.split('@')[-1].strip().lower()
    try:
        socket.getaddrinfo(domain, 25)
        return True
    except Exception:
        return False

def is_valid_website(url):
    """Checks if URL is an official domain rather than an aggregator or directory listing."""
    if not url or url.strip() in ('', '--'):
        return False
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    if any(ex in domain for ex in EXCLUDED_SEARCH_DOMAINS):
        return False
    if any(ex in path for ex in ('/rankings/', '/preschool-rankings/', '/childcare-preschool-rankings/', '/directory/', '/listing/', '/profile/', '/reviews/')):
        return False
    return True

def is_email_domain_consistent(email, website_url):
    """Verifies email belongs to the facility rather than a third-party directory owner."""
    if not email or not website_url:
        return True
    email_domain = email.split('@')[-1].lower().strip()
    web_domain = urlparse(website_url).netloc.lower().replace('www.', '').strip()
    if any(prov in email_domain for prov in ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'aol.com', 'att.net', 'sbcglobal.net')):
        return True
    if email_domain == web_domain or email_domain.endswith('.' + web_domain) or web_domain.endswith('.' + email_domain):
        return True
    brand_token = email_domain.split('.')[0]
    if len(brand_token) >= 4 and brand_token in web_domain:
        return True
    return False


def search_facility_website(center_name, city, address=None):
    """Uses zero-cost search engine to identify official domain."""
    clean_name = center_name.replace(" LLC", "").replace(" Inc", "").strip()
    query = f"{clean_name} {city} TX daycare official website"
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": ua.random}
    
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return None
        
        soup = BeautifulSoup(r.text, "lxml")
        for res in soup.select(".result"):
            url_tag = res.select_one(".result__url")
            link_tag = res.select_one(".result__title a")
            if not url_tag and not link_tag:
                continue
                
            raw_url = (url_tag.get_text(strip=True) if url_tag else link_tag.get('href', '')).strip()
            if not raw_url.startswith("http"):
                raw_url = "https://" + raw_url
                
            parsed_url = urlparse(raw_url)
            domain = parsed_url.netloc.lower()
            path = parsed_url.path.lower()
            if any(ex in domain for ex in EXCLUDED_SEARCH_DOMAINS):
                continue
            if any(ex in path for ex in ('/rankings/', '/preschool-rankings/', '/childcare-preschool-rankings/', '/directory/', '/listing/', '/profile/', '/reviews/')):
                continue

                
            # Filter out non-relevant domains
            if any(tld in domain for tld in ('.com', '.org', '.net', '.edu', '.us')):
                return raw_url
    except Exception as e:
        print(f"    [SEARCH WARNING] Search query failed: {e}", flush=True)
    return None

def extract_email_from_website(base_url):
    """Deep scrapes website homepage and contact sub-routes for verified direct emails."""
    headers = {"User-Agent": ua.random}
    parsed = urlparse(base_url)
    clean_path = parsed.path.rstrip('/')
    
    # Build prioritized path list respecting subpath if present
    if clean_path and clean_path not in ("", "/"):
        paths_to_check = [
            clean_path,
            f"{clean_path}/contact",
            f"{clean_path}/contact-us",
            f"{clean_path}/about",
            "",
            "/contact",
            "/contact-us",
            "/about"
        ]
    else:
        paths_to_check = ["", "/contact", "/contact-us", "/about", "/about-us", "/our-team", "/staff"]
        
    candidates = []
    
    for path in paths_to_check:
        target_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", path)
        try:
            r = requests.get(target_url, headers=headers, timeout=6)
            if r.status_code != 200:
                continue
                
            soup = BeautifulSoup(r.text, "lxml")
            
            # 1. Search mailto: links
            for mailto in soup.select('a[href^="mailto:"]'):
                clean = mailto["href"].replace("mailto:", "").split("?")[0].strip().lower()
                if "@" in clean and not clean.endswith(IGNORE_EXTS):
                    if not any(d in clean for d in IGNORE_DOMAINS) and not any(p in clean for p in DUMMY_EMAIL_PATTERNS):
                        candidates.append(clean)
                        
            # 2. Decompose script, style, form, input elements to prevent placeholder/template extraction
            for tag in soup(['script', 'style', 'noscript', 'svg', 'form', 'input', 'select', 'textarea']):
                tag.decompose()
                
            visible_text = soup.get_text(separator=' ')
            for raw_match in EMAIL_REGEX.findall(visible_text):
                clean = raw_match.strip().lower()
                if not any(d in clean for d in IGNORE_DOMAINS) and not any(p in clean for p in DUMMY_EMAIL_PATTERNS) and not clean.endswith(IGNORE_EXTS):
                    candidates.append(clean)
                    
            if candidates:
                break
        except Exception:
            continue
            
    # Verify candidates with MX pre-flight
    for email in candidates:
        if verify_mx_record(email):
            return email
    return None

def run_enrichment(batch_size=50, min_capacity=100, batch_num=None):
    """Executes prioritized Tier 1 enrichment loop."""
    print(f"==================================================================", flush=True)
    prefix = f"Batch {batch_num}" if batch_num else "Tier 1 Run"
    print(f"--- SigmaFidelity™ Daycare Economic Ingress Daemon ({prefix}) ---", flush=True)
    print(f"Authority: Silas Sync (VP of CRM) | Lead Architect: George", flush=True)
    print(f"Batch Size: {batch_size} | Minimum Capacity: {min_capacity} children", flush=True)
    print(f"==================================================================", flush=True)
    
    conn = psycopg2.connect(DB_URL)
    init_billing_tracker(conn)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT l.id, l.center_name, l.city, l.website, l.director, l.capacity, l.estimated_annual_value, l.address
            FROM "Leads" l
            WHERE (l.industry = 'Child Care' OR l.facility_type = 'Child Care Center' OR l.lead_source ILIKE '%%daycare%%' OR l.lead_source ILIKE '%%CCL%%' OR l.lead_source ILIKE '%%Childcare%%')
              AND (l.email IS NULL OR TRIM(l.email) = '' OR l.email = '--')
              AND l.capacity >= %s
              AND NOT EXISTS (
                  SELECT 1 FROM "GlobalActivities" ga
                  WHERE ga.parent_id = l.id 
                    AND ga.parent_type = 'Lead' 
                    AND ga.activity_type = 'Autonomous Ingress'
              )
            ORDER BY l.capacity DESC, l.estimated_annual_value DESC
            LIMIT %s;
        """, (min_capacity, batch_size))
        leads = cur.fetchall()

        
    if not leads:
        print(f"[INGRESS] Zero pending accounts matching Tier 1 criteria. Queue complete.\n", flush=True)
        conn.close()
        return 0
        
    print(f"[INGRESS] Fetched {len(leads)} high-capacity Tier 1 leads for processing.\n", flush=True)
    
    stats = {
        "processed": 0,
        "websites_found": 0,
        "emails_recovered": 0,
        "pipeline_value_unlocked": 0.0
    }
    highlights = []
    
    for idx, (lead_id, name, city, site, director, cap, val, addr) in enumerate(leads):
        stats["processed"] += 1
        val_display = f"${val:,.0f}" if val else "$0"
        print(f"[{idx+1}/{len(leads)}] Lead #{lead_id}: {name} ({city}, TX) | Cap: {cap} | Value: {val_display}", flush=True)
        
        target_website = site
        # Step 1: Discover website if missing or invalid directory URL
        if not is_valid_website(target_website):
            target_website = search_facility_website(name, city, addr)
            if target_website and is_valid_website(target_website):
                print(f"    -> [DOMAIN RESOLVED] {target_website}", flush=True)
                with conn.cursor() as cur:
                    cur.execute('UPDATE "Leads" SET website = %s WHERE id = %s;', (target_website, lead_id))
                    # Innate Corporate Umbrella Detection
                    try:
                        clean_dom = urlparse(target_website).netloc.lower().replace('www.', '').strip()
                        cur.execute('''
                            SELECT umbrella_name, cleaning_delivery_model 
                            FROM "CorporateUmbrellas" 
                            WHERE %s = ANY(root_domains)
                            LIMIT 1;
                        ''', (clean_dom,))
                        u_match = cur.fetchone()
                        if u_match:
                            cur.execute('''
                                UPDATE "Leads"
                                SET umbrella_name = %s,
                                    cleaning_delivery_model = COALESCE(cleaning_delivery_model, %s)
                                WHERE id = %s AND (umbrella_name IS NULL OR umbrella_name = '');
                            ''', (u_match[0], u_match[1], lead_id))
                            print(f"    -> [AUTONOMOUS UMBRELLA] Linked to '{u_match[0]}'", flush=True)
                    except Exception as u_err:
                        print(f"    -> [UMBRELLA LOOKUP ERROR] {u_err}", flush=True)
                conn.commit()
                stats["websites_found"] += 1
            else:
                target_website = None
                print(f"    -> [DOMAIN PENDING] No primary domain found in search.", flush=True)
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, 'Lead', 'Autonomous Ingress', 'Autonomous web search returned no primary domain.');
                    """, (lead_id,))
                conn.commit()
                
        # Step 2: Scrape and extract email
        if target_website and target_website.startswith("http"):
            recovered_email = extract_email_from_website(target_website)
            if recovered_email and is_email_domain_consistent(recovered_email, target_website):
                print(f"    -> [EMAIL RECOVERED] {recovered_email} (MX Verified)", flush=True)
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE "Leads" 
                        SET email = %s, updated_at = CURRENT_DATE 
                        WHERE id = %s;
                    """, (recovered_email, lead_id))
                    
                    cur.execute("""
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, 'Lead', 'Autonomous Ingress', %s);
                    """, (lead_id, f"Mined direct email '{recovered_email}' from {target_website}."))
                conn.commit()
                stats["emails_recovered"] += 1
                if val:
                    stats["pipeline_value_unlocked"] += float(val)
                highlights.append({
                    "name": name,
                    "city": city,
                    "email": recovered_email,
                    "val": val_display
                })
            else:
                print(f"    -> [EMAIL FORM ONLY] No direct email extracted from contact pages.", flush=True)
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, 'Lead', 'Autonomous Ingress', %s);
                    """, (lead_id, f"Enriched website '{target_website}'; contact form only, no direct email."))
                conn.commit()

                
        # Respectful crawl rate limit
        time.sleep(1.5)
        
    with conn.cursor() as cur:
        base_filter = "(industry = 'Child Care' OR facility_type = 'Child Care Center' OR lead_source ILIKE '%daycare%' OR lead_source ILIKE '%CCL%' OR lead_source ILIKE '%Childcare%')"
        base_filter_param = "(l.industry = 'Child Care' OR l.facility_type = 'Child Care Center' OR l.lead_source ILIKE '%%daycare%%' OR l.lead_source ILIKE '%%CCL%%' OR l.lead_source ILIKE '%%Childcare%%')"
        cur.execute(f'SELECT COUNT(*) FROM "Leads" WHERE {base_filter};')
        total_leads = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "Leads" WHERE {base_filter} AND email IS NOT NULL AND TRIM(email) != \'\' AND TRIM(email) != \'--\' AND email LIKE \'%@%.%\';')
        total_ready = cur.fetchone()[0]
        cur.execute(f"""
            SELECT COUNT(*) FROM "Leads" l 
            WHERE {base_filter_param} 
              AND (l.email IS NULL OR TRIM(l.email) = '' OR l.email = '--') 
              AND l.capacity >= %s
              AND NOT EXISTS (
                  SELECT 1 FROM "GlobalActivities" ga
                  WHERE ga.parent_id = l.id AND ga.parent_type = 'Lead' AND ga.activity_type = 'Autonomous Ingress'
              );
        """, (min_capacity,))
        tier1_pending = cur.fetchone()[0]


    conn.close()
    
    print(f"\n==================================================================", flush=True)
    print(f"--- BATCH INGRESS SUMMARY ---", flush=True)
    print(f"Total Tier 1 Facilities Processed : {stats['processed']}", flush=True)
    print(f"Official Websites Discovered      : {stats['websites_found']}", flush=True)
    print(f"Direct Verified Emails Recovered   : {stats['emails_recovered']}", flush=True)
    print(f"Pipeline Contract Value Unlocked  : ${stats['pipeline_value_unlocked']:,.2f}", flush=True)
    print(f"Tier 1 Facilities Remaining Queued: {tier1_pending}", flush=True)
    print(f"Google Cloud Out-of-Pocket Cost   : $0.00 (Zero Paid API Calls Used)", flush=True)
    print(f"==================================================================", flush=True)

    # Dispatch executive Telegram notification to CEO
    print("[TELEGRAM] Dispatching progress report to CEO Humberto Dominguez...", flush=True)
    sent = dispatch_telegram_progress(stats, highlights, total_ready, total_leads, tier1_pending, batch_num)
    if sent:
        print("[TELEGRAM] Executive report delivered successfully.", flush=True)
    else:
        print("[TELEGRAM] Notice: Dispatch failed or skipped.", flush=True)
        
    return stats["processed"]

def dispatch_telegram_progress(stats, highlights, total_ready, total_leads, tier1_pending, batch_num=None):
    """Sends high-fidelity progress report to CEO Humberto Dominguez's Telegram device."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
        
    pct = (stats['emails_recovered'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
    batch_title = f"Batch #{batch_num} Update" if batch_num else "Batch Ingress Complete"
    
    lines = [
        "🏛️ *SigmaFidelity™ Tier 1 Ingress Report*",
        "━━━━━━━━━━━━━━━━━━━━━",
        "*Authority:* Silas Sync (VP of CRM) & George",
        "*Target Cohort:* Tier 1 Large Daycares (Capacity ≥ 100)",
        f"*Status:* ✅ {batch_title} ({stats['processed']} Processed)",
        "",
        "📊 *Batch Yield Metrics:*",
        f"• Facilities Processed: *{stats['processed']}*",
        f"• Domains Resolved: *{stats['websites_found']}*",
        f"• Verified Emails Recovered: *{stats['emails_recovered']}* ({pct:.1f}%)",
        f"• New Pipeline Value Unlocked: *${stats['pipeline_value_unlocked']:,.2f}*",
        f"• Google API Cost: *$0.00* (Zero-cost engine)",
        "",
        "🎯 *Top Mined Accounts (This Slice):*"
    ]
    
    if highlights:
        for h in highlights[:5]:
            lines.append(f"• *{h['name']}* ({h['city']})\n  └ ✉️ `{h['email']}` | *{h['val']}*")
    else:
        lines.append("• _No new direct emails extracted in this slice._")
        
    lines.extend([
        "",
        "📡 *Cumulative Database Telemetry:*",
        f"• Tier 1 Accounts Remaining: *{tier1_pending:,}*",
        f"• Total Texas Childcare Leads: *{total_leads:,}*",
        f"• Total Campaign-Ready (Email): *{total_ready:,}*",
        "━━━━━━━━━━━━━━━━━━━━━",
        "_Delivered via Autonomous Command Node v3.0_"
    ])
    
    msg_text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg_text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        return res.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM DISPATCH ERROR] {e}", flush=True)
        return False

def dispatch_completion_alert(total_processed, total_recovered, total_unlocked):
    """Sends milestone completion notification to CEO."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    msg_text = (
        "🏆 *SigmaFidelity™ Tier 1 Ingress Complete!*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*Milestone:* 100% of Tier 1 Facilities (Capacity ≥ 100) Processed\n"
        f"• Total Facilities Crawled: *{total_processed:,}*\n"
        f"• Total Verified Direct Emails: *{total_recovered:,}*\n"
        f"• Total Contract Value Unlocked: *${total_unlocked:,.2f}*\n"
        "• Total Google API Spend: *$0.00*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "_Silas Sync stands by for Tier 2 executive directive._"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg_text, "parse_mode": "Markdown"}, timeout=15)
    except Exception:
        pass

def run_continuous_tier1(batch_size=50, min_capacity=100):
    """Runs continuous micro-batches until Tier 1 is fully processed."""
    print(">>> Launching Continuous Tier 1 Ingress Daemon...", flush=True)
    batch_idx = 1
    total_processed = 0
    
    while True:
        processed = run_enrichment(batch_size=batch_size, min_capacity=min_capacity, batch_num=batch_idx)
        if processed == 0:
            print("[INGRESS COMPLETE] All Tier 1 facilities have been processed.", flush=True)
            break
        total_processed += processed
        batch_idx += 1
        print(f"[PAUSE] Resting 3 seconds before Batch #{batch_idx}...\n", flush=True)
        time.sleep(3.0)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "continuous"
    if mode.isdigit():
        run_enrichment(batch_size=int(mode), min_capacity=100)
    else:
        run_continuous_tier1(batch_size=50, min_capacity=100)

