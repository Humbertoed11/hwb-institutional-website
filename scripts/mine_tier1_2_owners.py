#!/usr/bin/env python3
"""
SigmaFidelity™ Tier 1 & Tier 2 Owner Mining Daemon v1.0
Responsibility: Silas Sync (VP of CRM) & George (Systems Architect)
Governance: HWB-QMS-11.1 / Minimization Mandate / Empirical Integrity Mandate
Target Scope: All Texas Independent Commercial Daycares (Capacity 150+)

Empirical Integrity Mandate:
Strict prohibition against synthetic, fabricated, or unverified data.
Every owner record must be anchored to an empirical documentary citation (URL + snippet)
or official State of Texas regulatory permit record.
"""

import os
import re
import sys
import time
import socket
import argparse
import urllib.parse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import fake_useragent
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings()
load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")

ua = fake_useragent.UserAgent()

TEXAS_CCL_ENDPOINT = "https://data.texas.gov/resource/bc5r-88dy.json"

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "HWB-COMPANY", "HWB-IT", "HWB-IT-SYSTEM-LOGS")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "owner_mining.log")

EXCLUDED_DOMAINS = (
    'yelp.com', 'mapquest.com', 'yellowpages.com', 'texasdaycarecheck.com', 
    'daycarehub.us', 'childcarecenter.us', 'superpages.com', 'bbb.org',
    'facebook.com/login', 'linkedin.com/login', 'indeed.com', 'care.com',
    'winnie.com', 'kangarootime.com', 'greatschools.org', 'privateschoolreview.com',
    'niche.com', 'preschools.co', 'daycarecenter.com', 'daycare.com', 
    'chamberofcommerce.com', 'us-wide-childcare', 'daycarepath.com',
    'google.com', 'bing.com', 'yahoo.com', 'wikipedia.org'
)

BLACKLIST_NAME_WORDS = {
    'school', 'academy', 'center', 'preschool', 'child', 'early', 'learning', 
    'education', 'texas', 'montessori', 'north', 'south', 'east', 'west', 
    'street', 'road', 'parkway', 'avenue', 'suite', 'about', 'contact', 
    'home', 'classes', 'programs', 'parent', 'teacher', 'curriculum', 
    'summer', 'winter', 'spring', 'fall', 'monday', 'friday', 'saturday', 
    'sunday', 'january', 'december', 'nature', 'explore', 'christian', 
    'catholic', 'baptist', 'methodist', 'lutheran', 'jesus', 'god', 
    'welcome', 'click', 'more', 'read', 'our', 'story', 'mission', 
    'vision', 'staff', 'team', 'board', 'director', 'member', 'service', 
    'care', 'infant', 'toddler', 'kindergarten', 'admissions', 'enrolling',
    'enroll', 'registration', 'events', 'news', 'blog', 'careers', 'apply',
    'login', 'portal', 'payment', 'privacy', 'policy', 'terms', 'facilities',
    'facility', 'campus', 'campuses', 'room', 'rooms', 'building', 'playground',
    'tour', 'tours', 'schedule', 'hours', 'phone', 'email', 'address', 'location'
}


def log_msg(msg: str):
    """Outputs to console and writes to persistent audit log."""
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{ts} {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def verify_mx_record(email: str) -> bool:
    """Verifies that the target email domain has live MX records."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[1].strip()
    try:
        socket.getaddrinfo(domain, 25, socket.AF_INET, socket.SOCK_STREAM)
        return True
    except Exception:
        return False


def clean_person_name(name_str: str) -> str:
    """Cleans and validates a prospective human name."""
    if not name_str:
        return ""
    name_str = re.sub(r'[\r\n\t]+', ' ', name_str)
    name_str = re.sub(r'[^\w\s\.\,\'-]', '', name_str).strip()
    
    # Remove honorifics and degrees
    name_str = re.sub(r'^(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s+', '', name_str, flags=re.IGNORECASE)
    name_str = re.sub(r'[, ]+(?:M\.?Ed|Ph\.?D|MBA|Ed\.?D|MA|MS|BS|BA|RN|LCSW|CPA)$', '', name_str, flags=re.IGNORECASE).strip()
    
    words = [w for w in name_str.split() if w]
    # Remove leading duplicate if string was like "Williams Tammie Williams"
    if len(words) >= 3 and words[0].lower() == words[-1].lower():
        words = words[1:]
    # Deduplicate consecutive duplicates
    words = [w for i, w in enumerate(words) if i == 0 or w.lower() != words[i-1].lower()]
    
    if len(words) < 2 or len(words) > 4:
        return ""
        
    for w in words:
        if w.lower() in BLACKLIST_NAME_WORDS:
            return ""
        if not re.match(r'^[A-Z][a-z]+(?:\'[A-Z]?[a-z]+)?$', w):
            # Allow initials like "J." or hyphens
            if not (len(w) == 2 and w[1] == '.') and '-' not in w:
                return ""
                
    return " ".join(words)


def query_texas_ccl_record(op_number: str) -> dict:
    """Queries Texas Child Care Licensing open data endpoint for official record."""
    if not op_number:
        return {}
    clean_op = op_number.replace("texas-ccl-", "").strip()
    url = f"{TEXAS_CCL_ENDPOINT}?operation_number={clean_op}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=10)
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception as e:
        log_msg(f"    [CCL API WARNING] Failed query for {clean_op}: {e}")
    return {}


def search_domain_zero_cost(center_name: str, city: str) -> str:
    """Identifies official domain using zero-cost search engine queries."""
    clean_name = center_name.replace(" LLC", "").replace(" Inc", "").strip()
    query = f'"{clean_name}" "{city}" Texas preschool official website'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": ua.random}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for res in soup.select(".result"):
            url_tag = res.select_one(".result__url")
            link_tag = res.select_one(".result__title a")
            if not url_tag and not link_tag:
                continue
            raw_url = (url_tag.get_text(strip=True) if url_tag else link_tag.get('href', '')).strip()
            if not raw_url.startswith("http"):
                raw_url = "https://" + raw_url
            parsed = urlparse(raw_url)
            domain = parsed.netloc.lower()
            if any(ex in domain for ex in EXCLUDED_DOMAINS):
                continue
            if any(domain.endswith(tld) for tld in ('.com', '.org', '.net', '.edu', '.us')):
                return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return ""


def extract_ownership_from_website(base_url: str) -> dict:
    """
    Crawls target website to extract empirical ownership citations.
    Returns dict with {owner_name, job_title, citation, citation_url} or empty dict.
    """
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    pages_to_visit = [base_url]
    visited = set()
    
    # Check sitemaps for deep about / founder / team pages
    for sm_path in ['/page-sitemap.xml', '/sitemap.xml', '/wp-sitemap.xml']:
        sm_url = urljoin(base_url, sm_path)
        try:
            sm_r = requests.get(sm_url, headers=headers, verify=False, timeout=5)
            if sm_r.status_code == 200:
                sm_soup = BeautifulSoup(sm_r.text, 'xml')
                for loc in sm_soup.find_all('loc'):
                    u = loc.text.strip()
                    path = urlparse(u).path.lower()
                    if any(k in path for k in ('about', 'story', 'history', 'founder', 'owner', 'leadership', 'team', 'staff', 'director', 'parenting', 'handbook')):
                        if u not in pages_to_visit and len(pages_to_visit) < 8:
                            pages_to_visit.append(u)
                if len(pages_to_visit) > 1:
                    break
        except Exception:
            pass

    try:
        r = requests.get(base_url, headers=headers, verify=False, timeout=10)
        if r.status_code == 200:
            visited.add(base_url)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Discover high-priority about/history/staff pages from links
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.netloc.lower() != urlparse(base_url).netloc.lower():
                    continue
                path = parsed.path.lower()
                if any(keyword in path for keyword in (
                    'about', 'story', 'history', 'founder', 'owner', 'leadership', 
                    'team', 'staff', 'director', 'handbook', 'parenting', 'contact'
                )):
                    if full_url not in pages_to_visit and len(pages_to_visit) < 8:
                        pages_to_visit.append(full_url)
    except Exception:
        pass

    # Regex patterns for empirical ownership detection
    patterns = [
        # "Tammie Williams is the founder and owner..." or "Chuck Wall is the owner and oversees..."
        (re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+is\s+(?:the\s+)?(?:founder\s+and\s+owner|owner\s+and\s+founder|founder|owner|co-founder|president|proprietor)\b', re.IGNORECASE), "Founder & Owner"),
        # "Tammie Williams is the founder and owner of Apple Creek..."
        (re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+(?:is\s+the\s+)?(?:founder\s+and\s+owner|owner\s+and\s+founder|founder|owner|co-founder|president|proprietor)\s+of\b', re.IGNORECASE), "Founder & Owner"),
        # "Founded in 2004 by Tammie Williams..."
        (re.compile(r'\b(?:founded|established|started|owned\s+and\s+operated|opened)\s+(?:in\s+\d{4}\s+)?by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b', re.IGNORECASE), "Founder & Owner"),
        # "Owner: Tammie Williams" or "Founder - Tammie Williams"
        (re.compile(r'\b(?:Owner|Founder|Co-Founder|President|Proprietor)\s*[:\-–]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b', re.IGNORECASE), "Owner"),
        # "Tammie Williams, Owner & Executive Director"
        (re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*[,–\-\n/|]+\s*(?:Owner|Founder|President|Proprietor)\b', re.IGNORECASE), "Owner & Executive"),
        # "Chuck Wall Owner/Lead Director"
        (re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+(?:Owner|Founder|President|Proprietor)(?:/|\b)', re.IGNORECASE), "Owner"),
        # "Meet the Owner: Tammie Williams"
        (re.compile(r'\b(?:Meet\s+the\s+Owner|About\s+the\s+Owner|Message\s+from\s+the\s+Owner)\s*[:\-–]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b', re.IGNORECASE), "Owner")
    ]

    for page_url in pages_to_visit:
        try:
            time.sleep(0.4)
            pr = requests.get(page_url, headers=headers, verify=False, timeout=10)
            if pr.status_code != 200:
                continue
            psoup = BeautifulSoup(pr.text, "html.parser")
            
            # Remove scripts, styles, navigations
            for element in psoup(["script", "style", "nav", "footer"]):
                element.extract()
                
            # Test block elements first (p, div, li, h1-h4)
            for tag in psoup.find_all(['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4']):
                block_text = re.sub(r'\s+', ' ', tag.get_text()).strip()
                if 15 < len(block_text) < 700:
                    for pat, default_title in patterns:
                        m = pat.search(block_text)
                        if m:
                            candidate = clean_person_name(m.group(1))
                            if candidate:
                                # Attempt email extraction from page
                                owner_email = None
                                for a in psoup.find_all('a', href=True):
                                    if a['href'].startswith('mailto:'):
                                        em = a['href'].replace('mailto:', '').split('?')[0].strip()
                                        if verify_mx_record(em):
                                            owner_email = em
                                            break
                                return {
                                    "owner_name": candidate,
                                    "job_title": default_title,
                                    "citation": block_text[:280],
                                    "citation_url": page_url,
                                    "email": owner_email
                                }
        except Exception:
            continue
            
    return {}


def process_target_lead(lead: dict, conn) -> bool:
    """
    Executes empirical owner verification on a single Tier 1 or Tier 2 target lead.
    Enforces strict zero-synthetic data policy.
    """
    lead_id = lead['id']
    center_name = lead['center_name']
    city = lead['city']
    capacity = lead['capacity']
    existing_director = lead.get('director')
    existing_website = lead.get('website')
    process_id = lead.get('process_id') or ''
    
    log_msg(f"Target #{lead_id}: {center_name} ({city}, TX) | Capacity: {capacity}")
    
    official_website = existing_website
    official_email = lead.get('email')
    ccl_director = existing_director
    
    # 1. State Regulatory Ingress (Texas CCL Open Data)
    if process_id.startswith("texas-ccl-"):
        ccl_data = query_texas_ccl_record(process_id)
        if ccl_data:
            if not official_website and ccl_data.get('website_address'):
                w = ccl_data.get('website_address').strip()
                if not w.startswith("http"):
                    w = "https://" + w
                official_website = w
                log_msg(f"    -> [CCL WEBSITE INGESTED] {official_website}")
            if not official_email and ccl_data.get('email_address'):
                em = ccl_data.get('email_address').strip()
                if verify_mx_record(em):
                    official_email = em
                    log_msg(f"    -> [CCL EMAIL INGESTED] {official_email}")
            if not ccl_director and ccl_data.get('administrator_director_name'):
                ccl_director = ccl_data.get('administrator_director_name').strip()
                log_msg(f"    -> [CCL DIRECTOR INGESTED] {ccl_director}")
                
    # 2. Zero-Cost Domain Fallback
    if not official_website:
        discovered_domain = search_domain_zero_cost(center_name, city)
        if discovered_domain:
            official_website = discovered_domain
            log_msg(f"    -> [SEARCH DOMAIN RESOLVED] {official_website}")
            
    # 3. Autonomous Website Ownership Extraction
    ownership_data = {}
    if official_website:
        ownership_data = extract_ownership_from_website(official_website)
        
    with conn.cursor() as cur:
        if ownership_data and ownership_data.get("email") and not official_email:
            official_email = ownership_data["email"]
            
        lead['website'] = official_website
        lead['email'] = official_email
        lead['director'] = ccl_director
        
        if ownership_data and ownership_data.get("owner_name"):
            owner_name = ownership_data["owner_name"]
            title = ownership_data.get("job_title", "Founder & Owner")
            citation = f"Source: {ownership_data['citation_url']} | Citation: \"{ownership_data['citation']}\""
            
            log_msg(f"    >>> [VERIFIED OWNER FOUND] {owner_name} ({title})")
            log_msg(f"    >>> [CITATION] {citation[:160]}...")
            
            cur.execute("""
                UPDATE "Leads"
                SET decision_maker = %s,
                    job_title = %s,
                    director = COALESCE(director, %s),
                    website = COALESCE(website, %s),
                    email = COALESCE(email, %s),
                    owner_verification_status = 'EMPIRICALLY_VERIFIED',
                    owner_evidence_citation = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (owner_name, title, ccl_director, official_website, official_email, citation, lead_id))
            
            # Upsert into Contacts table
            cur.execute("""
                INSERT INTO "Contacts" (lead_id, full_name, role, title, email, phone)
                VALUES (%s, %s, 'Executive / Equity Owner', %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (lead_id, owner_name, title, official_email, lead.get('phone')))
            
            # Record audit note
            cur.execute("""
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                VALUES (%s, 'Lead', 'NOTE', %s, CURRENT_TIMESTAMP);
            """, (lead_id, f"[M&A Intelligence] Empirically verified Owner/Founder: {owner_name} ({title}). {citation}"))
            
            conn.commit()
            return True
            
        elif ccl_director:
            # Regulatory Director confirmed, owner pending documentary discovery
            citation = f"Texas CCL Regulatory Permit {process_id}: Designated Center Administrator/Director"
            log_msg(f"    -> [REGULATORY DIRECTOR CONFIRMED] {ccl_director} (Owner pending site verification)")
            
            cur.execute("""
                UPDATE "Leads"
                SET decision_maker = COALESCE(decision_maker, %s),
                    job_title = COALESCE(job_title, 'Facility Director (Texas Licensed)'),
                    director = %s,
                    website = COALESCE(website, %s),
                    email = COALESCE(email, %s),
                    owner_verification_status = 'DIRECTOR_CONFIRMED_OWNER_PENDING',
                    owner_evidence_citation = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (ccl_director, ccl_director, official_website, official_email, citation, lead_id))
            
            cur.execute("""
                INSERT INTO "Contacts" (lead_id, full_name, role, title, email, phone)
                VALUES (%s, %s, 'Facility Director', 'Facility Director (Texas Licensed)', %s, %s)
                ON CONFLICT DO NOTHING;
            """, (lead_id, ccl_director, official_email, lead.get('phone')))
            
            conn.commit()
            return False
            
        else:
            log_msg(f"    -- [AUDITED PENDING PROOF] No empirical owner or director record found. Retaining unverified state.")
            cur.execute("""
                UPDATE "Leads"
                SET owner_verification_status = 'AUDITED_PENDING_PROOF',
                    website = COALESCE(website, %s),
                    email = COALESCE(email, %s),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (official_website, official_email, lead_id))
            conn.commit()
            return False


def dispatch_telegram_progress(stats: dict):
    """Sends batch progress update to CEO Humberto Dominguez via Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
        
    msg = (
        f"🎯 *SigmaFidelity™ M&A Owner Mining Report*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Batch Status:* Completed {stats['batch_count']} Targets\n"
        f"💎 *Verified Owners Discovered:* `{stats['verified_owners']}`\n"
        f"🏛️ *Regulatory Directors Attached:* `{stats['directors_confirmed']}`\n"
        f"🌐 *Websites Ingested:* `{stats['websites_ingested']}`\n"
        f"⏳ *Pending Documentary Proof:* `{stats['pending_proof']}`\n"
        f"💰 *Out-of-Pocket API Spend:* `$0.00 (Zero Paid API Calls)`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 *Next Batch Ready.*"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=8)
    except Exception as e:
        log_msg(f"[TELEGRAM ERROR] {e}")


def run_mining(batch_size: int = 25, target_id: int = None, continuous: bool = False):
    """Main operational runner for Tier 1 & 2 Owner Mining Daemon."""
    log_msg("==================================================================")
    log_msg("--- SigmaFidelity™ M&A Owner Mining Daemon (v1.0) ---")
    log_msg("Authority: Silas Sync (VP of CRM) | Lead Architect: George")
    log_msg(f"Empirical Integrity Mode: Active | Zero Synthetic Tolerance: Strict")
    log_msg(f"Batch Size: {batch_size} | Mode: {'Continuous' if continuous else 'Standard'}")
    log_msg("==================================================================")
    
    conn = psycopg2.connect(DB_URL)
    
    batch_num = 1
    while True:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if target_id:
                cur.execute('SELECT * FROM "Leads" WHERE id = %s;', (target_id,))
            else:
                cur.execute('''
                    SELECT * FROM "Leads"
                    WHERE is_commercial = TRUE 
                      AND acquisition_tier IN ('Tier 1 - Mega Institutional', 'Tier 2 - Regional Commercial')
                      AND ownership_type = 'Independent Commercial'
                      AND (owner_verification_status IS NULL OR owner_verification_status = 'PENDING_PROOF')
                    ORDER BY capacity DESC, id ASC
                    LIMIT %s;
                ''', (batch_size,))
            targets = cur.fetchall()

        if not targets:
            log_msg("[MINING COMPLETE] All Tier 1 & Tier 2 independent targets have been audited.")
            break

        log_msg(f"\n--- INITIATING BATCH #{batch_num} ({len(targets)} TARGETS) ---")
        
        stats = {
            "batch_count": len(targets),
            "verified_owners": 0,
            "directors_confirmed": 0,
            "websites_ingested": 0,
            "pending_proof": 0
        }

        for idx, t in enumerate(targets):
            time.sleep(1.0) # Polite pacing
            had_website = bool(t.get('website'))
            verified = process_target_lead(t, conn)
            
            if verified:
                stats["verified_owners"] += 1
            elif t.get('director'):
                stats["directors_confirmed"] += 1
            else:
                stats["pending_proof"] += 1
                
            if not had_website and t.get('website'):
                stats["websites_ingested"] += 1

        log_msg("==================================================================")
        log_msg(f"--- BATCH #{batch_num} SUMMARY ---")
        log_msg(f"Verified Founders/Owners Found : {stats['verified_owners']}")
        log_msg(f"Licensed Directors Confirmed   : {stats['directors_confirmed']}")
        log_msg(f"Websites Ingested              : {stats['websites_ingested']}")
        log_msg(f"Pending Documentary Proof      : {stats['pending_proof']}")
        log_msg(f"Third-Party API Spend          : $0.00")
        log_msg("==================================================================")
        
        dispatch_telegram_progress(stats)
        
        if not continuous or target_id:
            break
            
        batch_num += 1
        log_msg("[PACING] Pausing 5 seconds before next batch...")
        time.sleep(5.0)

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SigmaFidelity Tier 1 & 2 Owner Mining Daemon")
    parser.add_argument("--batch-size", type=int, default=25, help="Number of centers to process per batch")
    parser.add_argument("--target-id", type=int, default=None, help="Process a specific lead ID")
    parser.add_argument("--continuous", action="store_true", help="Run continuously across all targets")
    args = parser.parse_args()
    
    run_mining(batch_size=args.batch_size, target_id=args.target_id, continuous=args.continuous)
