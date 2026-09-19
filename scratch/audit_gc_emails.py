import os, requests, msal
from dotenv import load_dotenv
from collections import defaultdict
import re

load_dotenv('.env')

cid = os.getenv('GRAPH_API_PROD_APPLICATION_ID')
secret = os.getenv('GRAPH_API_PROD_SECRET_VALUE')
tid = os.getenv('GRAPH_API_PROD_TENANT_ID')
user_email = 'humbertoed@hwbcleaning.com'

authority = f'https://login.microsoftonline.com/{tid}'
app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
token = result['access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

start_date = '2026-03-01T00:00:00Z'
url = f'https://graph.microsoft.com/v1.0/users/{user_email}/messages'
params = {
    '$filter': f'receivedDateTime ge {start_date}',
    '$select': 'id,subject,from,receivedDateTime,isRead,hasAttachments,bodyPreview',
    '$top': '100',
    '$orderby': 'receivedDateTime desc'
}

all_messages = []
next_url = url

print("--- SigmaFidelity: Fetching 6-Month Inbound Bidding Stream ---")
page_count = 0

while next_url and page_count < 15: # up to 1,500 messages
    if page_count == 0:
        res = requests.get(next_url, headers=headers, params=params)
    else:
        res = requests.get(next_url, headers=headers)
        
    if res.status_code != 200:
        print(f"Error fetching page {page_count}: {res.status_code}")
        break
        
    data = res.json()
    batch = data.get('value', [])
    all_messages.extend(batch)
    page_count += 1
    print(f"Page {page_count}: Fetched {len(batch)} messages (Total: {len(all_messages)})")
    
    next_url = data.get('@odata.nextLink')

print(f"\nTotal messages in 6-month window: {len(all_messages)}")

# Filter Construction & Final Clean Bid Invites
gc_keywords = [
    'buildingconnected', 'reproconnect', 'planroom', 'planhub', 'procore', 'isqft', 'smartbid',
    'final clean', 'rough clean', 'construction clean', 'invitation to bid', 'itb', 'subcontractor',
    'bid due', 'addendum', 'cad files', 'estimating@', 'builders', 'construction', 'contractors'
]

gc_bids = []
gc_companies = defaultdict(list)
monthly_volume = defaultdict(int)

for m in all_messages:
    subj = m.get('subject') or ''
    body = m.get('bodyPreview') or ''
    sender_obj = m.get('from', {}).get('emailAddress', {})
    s_name = sender_obj.get('name') or ''
    s_addr = sender_obj.get('address') or ''
    dt = m.get('receivedDateTime', '')[:10]
    month = dt[:7] # YYYY-MM
    
    # Exclude routine security/payment digests unless they contain GC bids
    if 'cloud-protect.net' in s_addr or 'intuit.com' in s_addr or 'paypal.com' in s_addr:
        continue
        
    combined_text = f"{subj} {body} {s_name} {s_addr}".lower()
    
    is_gc = any(k in combined_text for k in gc_keywords)
    if is_gc:
        # Try to identify the GC company name
        company = "Unknown GC"
        # Match pattern like "Person (Company Name)"
        match_paren = re.search(r'\((.*?)\)', s_name)
        if match_paren:
            company = match_paren.group(1).strip()
        elif "builders" in s_name.lower() or "construction" in s_name.lower() or "contractors" in s_name.lower():
            company = s_name.strip()
        elif "novel builders" in combined_text:
            company = "Novel Builders"
        elif "weekes construction" in combined_text:
            company = "Weekes Construction"
        elif "mycon" in combined_text:
            company = "MYCON General Contractors"
        elif "source building group" in combined_text:
            company = "Source Building Group"
        elif "dfw planroom" in combined_text:
            company = "DFW Planroom"
        elif "ldi plan room" in combined_text:
            company = "LDI Plan Room"
        else:
            company = s_name or s_addr
            
        monthly_volume[month] += 1
        gc_companies[company].append({
            'date': dt,
            'subject': subj,
            'sender': f"{s_name} <{s_addr}>",
            'preview': body[:120]
        })
        gc_bids.append({
            'company': company,
            'date': dt,
            'subject': subj,
            'sender': s_addr
        })

print(f"\nIdentified {len(gc_bids)} Construction & Final Cleaning Bid Messages!")

print("\n=== MONTHLY BID INVITATION VOLUME ===")
for mth in sorted(monthly_volume.keys()):
    print(f"  {mth}: {monthly_volume[mth]} bids / invitations")

print(f"\n=== TOP GENERAL CONTRACTORS & BID PLATFORMS ({len(gc_companies)} Total) ===")
sorted_companies = sorted(gc_companies.items(), key=lambda x: len(x[1]), reverse=True)
for comp, bids in sorted_companies[:15]:
    latest = bids[0]['date']
    print(f"  • {comp:35s} | {len(bids):3d} invitations | Latest: {latest}")

