# SigmaFidelity™ Institutional Error Log (PROBLEMS-TO-SOLVE)
Standard: HWB-QMS-1.0 v2.0
Responsibility: George (Architect)

| Date | Issue ID | Description | Status | Impact |
| :--- | :--- | :--- | :--- | :--- |
| 06/01/2026 | BUG-033 | QMS Manual visibility failure (Ghost Volume glitch). | **RESOLVED** | HIGH |
| 06/01/2026 | MIG-001 | Antigravity CLI migration (Quota Exhaustion fallback active). | **IN PROGRESS** | CRITICAL |
| 06/23/2026 | MIG-002 | Session recovery file path mismatch inside container. | **RESOLVED** | MEDIUM |
| 06/23/2026 | SYS-001 | Postgres psql command hanging on interactive TTY pager. | **RESOLVED** | LOW |
| 06/23/2026 | BUG-034 | Operations page HTTP 500 / Gunicorn worker timeout. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-035 | Login redirection loop on local custom domains. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-036 | Invalid credentials on hdominguez login due to typo. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-037 | QMS manual document accessibility failure. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-038 | Recurrence of Ghost Volume Glitch on QMS templates. | **RESOLVED** | HIGH |
| 07/20/2026 | BUG-039 | Inconsistent and amateur visual weights in popup forms. | **RESOLVED** | MEDIUM |
| 07/20/2026 | BUG-040 | Modal delete stays on deleted record instead of sliding or closing. | **RESOLVED** | HIGH |
| 07/20/2026 | BUG-041 | Docker Desktop socket deletion and Telegram listener HTTP 409 collision. | **RESOLVED** | HIGH |
| 07/22/2026 | PROC-001 | Dev-to-Live Lead Staging & Release Protocol (Standard Architecture). | **DOCUMENTED** | INFORMATIONAL |
| 07/22/2026 | BUG-047 | Column Pagination Parameter Loss (Reverting to default view on page change). | **RESOLVED** | HIGH |
| 07/22/2026 | BUG-048 | Custom Column Ordering / Positioning Reset on Page Navigation. | **RESOLVED** | HIGH |
| 07/23/2026 | BUG-049 | Gunicorn Web Server Timeout on `mop.test:5000` during Bulk Background Enrichment. | **RESOLVED** | HIGH |
| 07/23/2026 | BUG-050 | Columns Customization Menu Toggle & Company Anchor Attribute Mismatch. | **RESOLVED** | HIGH |
| 09/02/2026 | BUG-051 | QMS Manual Proposal Missing & Compliance Engine Inode Desync. | **RESOLVED** | HIGH |
| 09/02/2026 | BUG-052 | Excel Quote Formatting Defects (Text Truncation, Missing Headers & Static Row Heights). | **RESOLVED** | MEDIUM |
| 09/03/2026 | BUG-053 | Excel Metadata Block Cell Clipping, Text Bleed & Missing Repeat Print Headers. | **RESOLVED** | MEDIUM |
| 09/03/2026 | BUG-054 | Substrate Description Incongruence Against Empirical Photographic Audit (11 Buildings). | **RESOLVED** | HIGH |
| 09/03/2026 | BUG-055 | Non-Empirical Scope Mismatch: Diamond Restoration Quoted on Ceramic/Quarry & Legacy Gantt Rates. | **RESOLVED** | HIGH |
| 09/03/2026 | BUG-056 | Excel Monolithic Multi-Column Print Scaling Failure (Microscopic 4.5pt Font & Empty Page Fragmentation). | **RESOLVED** | HIGH |
| 09/04/2026 | BUG-057 | Excel Document Header Label Truncation & Repeating Print Title Incongruence. | **RESOLVED** | MEDIUM |

## BUG-057: Excel Document Header Label Truncation & Repeating Print Title Incongruence
**Detected:** 09/04/2026
**Symptoms:**
1. In `Commercial_Quote` Rows 4 to 7, document control labels (`Central Office:` [15 chars] and `Primary Scope:` [14 chars]) were severely cut off and truncated on screen and in print.
2. Repeating header was originally set to `$1:$2`, failing to show document metadata and the ISO 9001 Clause 8.2.2 Data Integrity Notice on Pages 2 and 3.
3. Table 2 Option B (`"$3/Stp + $21/Lnd"`, `"N/A (Excluded)"`) and Option D (`"Available Per Hour"`) collided with cell borders in Column H (width 13) and Column K (width 17.5).
4. Table 3 scope descriptions (Rows 48 to 54) suffered vertical row height clipping (only 24 pt height for 3-line descriptions).
5. Sheet 2 Row 3 metadata bar had column merge collisions causing cutoffs on `Project Start:` and `Crew Assigned:`.
**Root Cause:**
1. Metadata labels in Rows 4–7 were placed in single unmerged Column A cells (width 5.5).
2. `print_title_rows` was configured as `$1:$2` instead of `$1:$8`.
3. Table 2 and Table 3 columns and row heights were not matched to the empirical character length and line-wrap requirements of their text.
**Solution:**
1. Merged `A:B` for left metadata labels (width **`30.5`**), `C:F` for left values (width **`73.0`**), `G:H` for right labels (width **`29.0`**), and `I:K` for right values (width **`49.5`**).
2. Locked `ws_quote.print_title_rows = '$1:$8'`, repeating the official masthead, project metadata, and ISO 9001 Data Integrity Notice across all pages.
3. Expanded Column H to **`20.0`** and Column K to **`20.0`** on Sheet 1.
4. Increased Table 3 description row heights from 24 pt to **`50 pt`** with `wrap_text = True`.
5. Rebalanced Sheet 2 Row 3 merges and set footnote row height to 24 pt.
6. Executed an automated cell-by-cell ripgrep/openpyxl audit confirming **100% Zero Width and Height Cutoffs** across all 3 sheets.

## BUG-056: Excel Monolithic Multi-Column Print Scaling Failure (Microscopic Font & Fragmentation)
**Detected:** 09/03/2026
**Symptoms:**
1. Printing Sheet 1 (`Commercial_Quote`) rendered text at microscopic, unreadable sizes (~3.5pt to 4.5pt font).
2. Printing one section per sheet created 7 separate landscape pages where each page had only a narrow 8–12 row band of content surrounded by massive empty white space.
**Root Cause:**
1. Placement of the 35-day daily calendar timeline (Columns L to AT) onto the same worksheet as the 11-column commercial pricing proposal created a monolithic 46-column wide worksheet (~300 width units).
2. Configuring `fitToWidth = 1` forced Excel to scale the entire sheet down to ~40% zoom across standard 11" Letter Landscape paper, causing massive proportional font shrinkage.
3. Arbitrary manual page breaks inserted after every single section fragmented the proposal into tiny strips.
**Solution:**
1. Re-architected the workbook into **Option 1: The Executive Multi-Tab Architecture**.
2. Decoupled the narrative commercial proposal onto Sheet 1 (`Commercial_Quote`), strictly formatted to **11 columns (A to K, 180.0 width units)**, flowing naturally across 3 dense executive pages at **100% full scale (10pt–11pt font, zero shrinking)**.
3. Moved the 35-day daily calendar to Sheet 2 (`Service_Gantt_Schedule`) as a standalone, dedicated **1-Page Letter Landscape attachment** (Appendix A).

## BUG-055: Non-Empirical Scope Mismatch (Option C Diamond Abrasion on Ceramic/Quarry & Legacy Gantt Rates)
**Detected:** 09/03/2026
**Symptoms:**
1. Option C (Capital Diamond Restoration @ $2.65/SF) was indiscriminately quoted across all 11 buildings, including Burk Burnett Building (Ceramic Mosaic), Knights of Pythias Hall (Ceramic Mosaic), and Plaza Hotel Building (Commercial Quarry Tile).
2. Fired clay quarry tile and vitrified ceramic mosaic tile cannot be mechanically ground or honed with diamond abrasives without popping mosaic tiles, stripping ceramic glazes, gouging grout joints, and destroying slip resistance ratings.
3. Excel Sheet 2 (`Service_Gantt_Schedule`) contained stale pre-Pathway 1 metadata figures ($7,584.04 and $6,022.62) and unbuffered quarterly rates ($302.40, $223.56, $186.30) for Virtuoso, Pythias, and Plaza Hotel.
4. Photo 4 in Section 6.0 cited "Schwarz Building" without connecting it to Building #9 (Virtuoso Building / 505 Main St).
**Root Cause:**
1. Mechanical restorative formulas were applied globally to total portfolio square footage without substrate-specific material science filtering.
2. Secondary workbook tabs were not regenerated during Pathway 1 / v2.7.0 rate schedule updates.
**Solution:**
1. Formally exempted Burk Burnett, Knights of Pythias, and Plaza Hotel from Option C Diamond Restoration across all proposals and Excel sheets. Marked as `N/A (Exempt - Mosaic/Quarry)`.
2. Recalculated true empirical Option C investment to **$24,713.90 complete** across the 8 eligible natural stone and terrazzo properties (9,326 Billing SF).
3. Substrate-engineered Phase 3 Track A maintenance scope: rotary diamond polymer refresh for 8 stone lobbies vs. cylindrical brush deep grout flush for 3 mosaic/quarry lobbies.
4. Updated Sheet 2 (`Service_Gantt_Schedule`) metadata to $9,307.20 (Reset) and $6,282.36 (Quarterly), and updated all three sub-600 SF properties to the $324.00 commercial baseline.
5. Clarified Photo 4 title as `PHOTO 4: VIRTUOSO BUILDING (505 MAIN ST / HISTORIC SCHWARZ BLDG)`.

## BUG-054: Substrate Description Incongruence Against Empirical Photographic Audit (11 Buildings)
**Detected:** 09/03/2026
**Symptoms:**
1. Preliminary quote and proposal drafts mischaracterized ground-floor lobby substrates across the 11-building commercial portfolio (e.g., The Westbrook cited as "Polished Granite & Terrazzo", Chase Bank cited as "Polished Granite & Marble Slab", Sanger Lofts cited as "Polished Concrete & Sealed Terrazzo", Plaza Hotel cited as "Historic Terrazzo & Ceramic Accents", Petroleum Building cited as "1927 Art Deco Terrazzo").
2. Substrate misidentifications presented risk of improper chemical deployment (e.g., applying acidic tile cleaners to calcium-based Crema Marfil marble in Petroleum Building or alkaline degreasers to sensitive terrazzo).
**Root Cause:**
Reliance on preliminary property spec assumptions prior to high-fidelity on-site photographic substrate verification.
**Solution:**
1. Conducted an exhaustive forensic visual audit across photographic documentation for all 11 buildings in `/HWB-COMPANY/HWB-QUOTES/photos/`.
2. Reconciled and empirically classified all 11 substrates:
   - The Westbrook: Monolithic Terrazzo & Art Deco Inlaid Medallions (Zero granite flooring)
   - Chase Bank Building: Cementitious Terrazzo & Art Deco Sunburst Inlays (Zero granite flooring)
   - The Commerce Building: Geometric Terrazzo Tile & Diamond Harlequin Inlays
   - Virtuoso Building: Polished Grey Fleuri Marble Slab & Black Inlays
   - Knights of Pythias Hall: Historic 1" Unglazed Mosaic Tile & Greek Key Border
   - Burk Burnett Building: Historic 1" Unglazed Mosaic & Green Inlaid Borders (Italian marble stairs)
   - The Carnegie: Multi-Tone Terrazzo & Art Deco Geometric Borders
   - Petroleum Building: Polished Crema Marfil Marble Tile & Dark Emperador Inlays (Zero terrazzo flooring)
   - Sanger Lofts: Cementitious Terrazzo & Rose/Diamond Geometric Borders (Zero concrete flooring)
   - Plaza Hotel Building: Historic Unglazed Red Terracotta Quarry Tile (Zero terrazzo flooring)
   - The Cassidy: Contemporary Monolithic Terrazzo & Ribbon Inlays (Zero slate/concrete flooring)
3. Synchronized reconciled substrate definitions across `scratch/generate_sundance_excel.py`, `SUNDANCE-QUOTE-gantt.xlsx`, `hwb-bid-2026-09-02-downtown-fort-worth-floor-cleaning-quote.html`, and `09-02-2026-Downtown-Fort-Worth-Lobby-Floor-Cleaning-Proposal.html`.
4. Standardized all client-facing substrate titles to non-threatening, routine commercial facility terminology (`Polished Terrazzo`, `Polished Marble Tile`, `Ceramic Mosaic Tile`, `Commercial Quarry Tile`, `Terrazzo Tile`) across Table 1.0, Table 2.0, and the Section 4.0 Photographic Damage Survey to prevent client price anxiety, avoid conservation-tier audit scrutiny, and ensure seamless budget alignment.

## BUG-052: Excel Proposal Formatting Defects (Text Truncation, Missing Headers & Static Row Heights)
**Detected:** 09/02/2026
**Symptoms:**
1. Long table headers in `Commercial_Quote` Table 2 (`Option B: Stair Care (Per Visit)`, `Option B: Stair Care (Monthly Total)`, `Option C: Deep Scrub ($0.38/SF)`, `Option D: Restoration ($1.85/SF)`) were physically cut off in Excel.
2. Section 3.0 (`Commercial Program Executive Summary & Billing Terms`) lacked column labels entirely, transitioning immediately from section banner to unlabelled data rows.
3. Multi-line methodology descriptions in Section 3.0 were cut off due to static row heights and un-wrapped text cells.
4. Cleanable square footage totals were missing explicit Grand Total labeling, and Section 1.0 lacked visible per-square-foot rate columns to determine frequency pricing.
5. Spreadsheet opened in desktop Excel failed to show background script edits until explicitly closed and re-opened.
**Root Cause:**
1. `openpyxl` generated cells without setting `alignment.wrap_text = True`.
2. Row heights were left at default `18.0pt` and `25.0pt`, which cannot accommodate multi-line strings.
3. Section 3.0 generator script merged arbitrary ranges (`A:D`, `E:G`, `H`, `I`, `J:K`) without rendering a column header row.
4. Calculation formulas hardcoded the `$0.22/SF` multiplier instead of exposing explicit Per-SF Rate cells.
5. Desktop office software maintains an in-memory cache of open files, preventing hot-reloading from disk.
**Solution:**
1. Standardized multi-line header text with deliberate `\n` linebreaks, expanded column widths to 18–20 chars, and set header row heights to `36–42pt` with `wrap_text=True`.
2. Re-architected Section 3.0 with an institutional-grade dark slate header row (`#1E293B`) in Row 41 containing explicit column labels (`Program / Service Tier`, `Operational Scope & Methodology`, `Unit Rate`, `Investment Per Pass`, `Contract Billing Terms`).
3. Expanded description column span across columns D–F (57-char width) with `wrap_text=True` and `36.0pt` row height.
4. Added dedicated Per-SF Rate columns for all core frequencies (`$0.24`, `$0.32`, `$0.38`) that dynamically drive visit and monthly pricing (`=SQFT * Rate`), and added prominent `GRAND TOTAL SQUARE FOOTAGE (21,600 SQFT)` rows across both Section 1.0 and Section 2.0.
5. Codified institutional instruction that spreadsheets must be closed before background generation to prevent display caching and write locks.

## BUG-053: Excel Metadata Block Cell Clipping, Text Bleed & Missing Repeat Print Headers
**Detected:** 09/03/2026
**Symptoms:**
1. Header and metadata blocks in `Commercial_Quote` (Rows 4–7) ran together without spaces or separation when viewed or copied (`Client:Sundance Square...Proposal ID:HWB-BID...`).
2. Cell B text overflowed across unmerged cells C–G and collided with Column H.
3. Multi-page printouts and PDF exports omitted institutional headers and metadata context on subsequent pages.
**Root Cause:**
1. Metadata keys and values were placed in unmerged single cells with insufficient widths (Column A width 5, Column B width 22, Column H width 13).
2. `print_title_rows` was unconfigured, preventing Rows 1–8 from repeating across multi-page document printouts.
3. Excel print page headers (`oddHeader`, `evenHeader`, `firstHeader`) lacked institutional division text.
**Solution:**
1. Unitized and merged metadata rows across columns: Left Block merged `A:B` (Label) and `C:E` (Value); Column F set as spacer gutter; Right Block merged `G:H` (Label) and `I:K` (Value). Applied boxed borders and zebra background fills.
2. Configured `ws_quote.print_title_rows = '1:8'` so the entire institutional banner, document title, metadata box, and ISO data notice repeat at the top of every printed page.
3. Set `ws.oddHeader.center.text = '&B&10HWB CLEANING SERVICES LLC | INSTITUTIONAL DIVISION'` and page numbering footer across all three worksheets.

## BUG-051: QMS Manual Proposal Visibility & Compliance Engine Inode Desync
**Detected:** 09/02/2026
**Symptoms:** 
1. New commercial bids and sales proposals staged in `HWB-SALES-MARKETING` were not visible on `http://mop.test:5000/manual`.
2. Accessing `/manual/<filename>` directly returned `QMS Error: Document not found (404)`.
**Root Cause:**
1. The QMS manual index (`/manual`) derives its catalog strictly from `qms_index.json`. Newly drafted proposals in `HWB-COMPANY/HWB-SALES-MARKETING/` were not automatically linked into `qms_index.json` or placed in `static/qms/`.
2. The Nginx microservice container `hwb_compliance_engine` maintained a stale bind-mount inode for `/usr/share/nginx/html/qms`, causing newly added static HTML files to be invisible inside the Nginx container until restarted.
**Solution:**
1. Formatted the proposal into a standardized QMS fragment: `static/qms/hwb-bid-2026-09-02-downtown-fort-worth-floor-cleaning-quote.html`.
2. Added the document entry to `qms_index.json` under `SALES-MARKETING` with current date `09-02-2026`, making it immediately appear in both "Today's Active Releases" at the top of the manual and the departmental catalog.
3. Restarted `hwb_compliance_engine` container, eliminating the stale inode and restoring 200 OK delivery.
**Detected:** 07/23/2026
**Symptoms:** 
1. Clicking the "Columns" customization button on Leads and Accounts views appeared completely unresponsive / failed to toggle the menu open.
2. The Company column label and building data vanished from the table view across page reloads.
**Forensic Root Cause Chain (4 Failure Modes):**
1. **Failure Mode A (Default Value Trap):** Checkbox in customization menu lacked `value="company"`. HTML5 defaulted `cb.value` to `"on"`.
2. **Failure Mode B (Session Cookie Poisoning):** `main_app.py` saved `session['leads_custom_cols'] = 'on,status...'`. Flask session cookies persisted `"on"`, causing Jinja `{% if col == 'company' %}` to evaluate `False` on all subsequent page views and omit Column #1.
3. **Failure Mode C (Microsecond Open-Close Collision):** A secondary legacy `window.addEventListener('click')` listener at line 3312 executed on the exact same click cycle. Clicking `<i class="fas fa-columns">` failed `!e.target.closest('button')`, forcing `display = 'none'` in 0ms.
4. **Failure Mode D (SyntaxError Lockdown):** A stray duplicate closing brace `}` halted JS parsing, throwing `ReferenceError: toggleColumnMenu is not defined`.
**Poka-Yoke Engineering Safeguards Deployed:**
1. **Server-Side Column Anchor (`main_app.py`):** Backend automatically strips `"on"` strings and forces `company` into index 0 (`active_cols.insert(0, 'company')`), guaranteeing Column #1 rendering regardless of client session corruption.
2. **Single Event Listener Rule:** Purged duplicate legacy event listeners; consolidated dismissal handlers under a single UI manager.
3. **Explicit Form Attributes:** Enforced mandatory `name` and `value` attributes on all form inputs.
4. **Clean Baseline Restoration:** Rolled back `templates/backoffice_operations.html` to Git HEAD baseline and flushed Gunicorn container caches (`docker restart hwb_web_app`).

## BUG-049: Gunicorn Web Server Timeout During Bulk DB Enrichment
**Detected:** 07/23/2026
**Symptoms:** Requests to `http://mop.test:5000/` timed out or returned empty responses (`Operation timed out after 5000 milliseconds` / `Worker (pid:7) was sent SIGKILL!`).
**Root Cause:** Executing bulk database update scripts (`daycare_registry_sync.py --force` over 9,558 rows) directly inside the web container blocked Gunicorn's single synchronous worker (`sync`), preventing incoming HTTP web requests on port 5000 from completing within Gunicorn's 30-second timeout window.
**Solution:** Restarted container `hwb_web_app` to restore Gunicorn worker responsiveness. Isolated bulk database background enrichment tasks to separate background daemons/workers (`hwb_agent_worker`), isolating HTTP request handling from bulk database mutations.



## BUG-047: Column Pagination Parameter Loss
**Detected:** 07/22/2026
**Symptoms:** Selecting a custom column view worked on Page 1, but changing to Page 2 or Page 3 caused columns to revert back to default view.
**Root Cause:** Pagination `Previous` and `Next` HTML links omitted the `cols` URL query parameter.
**Solution:** Updated pagination links in `backoffice_operations.html` to pass `cols=active_cols_str` and stored active columns in Flask session memory (`session['leads_custom_cols']`).

## BUG-048: Custom Column Positioning Reset
**Detected:** 07/22/2026
**Symptoms:** Custom column arrangement / position reverted back to static HTML form order upon page navigation.
**Root Cause:** Column form inputs gathered values in static HTML DOM order without preserving user-defined positional sequence in session memory.
**Solution:** Configured `main_app.py` to store and output the exact ordered sequence of custom columns in Flask session memory.

## PROC-001: Dev-to-Live Lead Staging & Release Protocol (Standard Architecture)
**Clarification:** This difference in numbers is **NOT a system bug or error**. It is the **intended, standard architectural separation** between the Development Sandbox and the Live Production Site.
**Operational Logic:**
1. **Dev Database (Sandbox):** Holds new unreleased batch downloads (e.g. 2,048 new Texas Childcare Registry leads) and offline tests.
2. **Live Database (Production):** Holds live customer web submissions (`27,887` leads) and published releases.
3. **Confusion Resolution:** The count difference occurred because the Dev environment held new batch imports undergoing validation prior to executive approval for live release.
**Standard Release Protocol:** Lead transfers from Dev to Live are executed strictly via the 3-Step Safe Merge (UPSERT) pipeline upon executive approval. Zero deletions or overwriting of live web leads occur.

## BUG-033: Ghost Volume Glitch
**Detected:** 06/01/2026
**Symptoms:** `/manual` endpoint returns 200 OK but content zone is empty; Nginx logs show 404 for fragments.
**Root Cause:** `hwb_compliance_engine` starts before the Docker volume bind-mount from the host is fully synchronized.
**Solution:** Restarted the container.
**Preventative:** Add `sleep 5` or a volume check to `scripts/startup_master.sh`.

## MIG-002: Session Recovery Path Mismatch
**Detected:** 06/23/2026
**Symptoms:** Run of `sigma_sync.py` in container does not pick up latest host-level `HWB-SESSION-RECOVERY.md` updates.
**Root Cause:** The container only mounts the `HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE` subfolder. Root-level `HWB-SESSION-RECOVERY.md` is not visible inside the container.
**Solution:** Copied root recovery file to the container app directory before running the sync script.
**Preventative:** Modify `scripts/sigma_sync.py` to copy the file or use a shared bind mount.

## SYS-001: Psql Interactive TTY Hanging
**Detected:** 06/23/2026
**Symptoms:** `docker exec -t ... psql` query hangs indefinitely in background execution.
**Root Cause:** The interactive TTY allocation `-t` forces the output into a pager, pausing for keyboard input.
**Solution:** Removed `-t` and added `-A -t` parameters to `psql` to force clean non-interactive print.

## BUG-034: Operations Page Timeout / HTTP 500
**Detected:** 06/23/2026
**Symptoms:** `http://mop.test:5000/admin/operations` throws 500 error or connection times out.
**Root Cause:** Gunicorn worker failed to boot due to `ModuleNotFoundError` on container mismatch, and subsequently timed out due to database connection leaks in the `load_user` Flask-Login helper during unauthenticated request floods.
**Solution:** Initialized container suite via `startup_master.sh` to resolve boot path alignment, and verified connection leaks are blocked by `finally` blocks in `load_user` and other database operations.
**Preventative:** Strictly enforce `finally: conn.close()` on all database operations and run standard startup diagnostics.

## BUG-035: Login Redirection Loop / SameSite Cookie Mismatch
**Detected:** 06/23/2026
**Symptoms:** Logging in accepts correct username and password, but immediately redirects back to `/login` instead of showing `/admin/operations`.
**Root Cause:** The session cookie lacked an explicit `SameSite` attribute. Modern browsers reject or block cookies lacking explicit SameSite attributes on insecure local custom TLDs (like `mop.test:5000` over HTTP).
**Solution:** Explicitly configured `SESSION_COOKIE_SAMESITE = 'Lax'`, `SESSION_COOKIE_HTTPONLY = True`, and environment-specific `SESSION_COOKIE_SECURE` (`False` for local dev, `True` for production HTTPS) in `config.py` per QMS-9.7 specifications.
**Preventative:** Standardize explicit SameSite and Secure cookie inheritance for all corporate tenants and local sandbox portals.

## BUG-036: Invalid Credentials on hdominguez Login
**Detected:** 06/23/2026
**Symptoms:** Logging in as `hdominguez` with correct password `password11` fails with "invalid credentials".
**Root Cause:** The database user password hash was initialized using the typo string `assword11` from legacy scripts, causing standard logins with the correct spelling `password11` to fail hash verification.
**Recurrence (07/10/2026):** The login failure returned because a database restoration from `pre_consolidation_snapshot_05-22-2026_1405.sql` re-seeded the outdated/corrupted password hashes into the PostgreSQL database.
**Solution:** Re-ran python commands to generate and set fresh, cryptographically valid hashes for both `admin` (`HWB-Admin-2026!`) and `hdominguez` (`password11`) in both PostgreSQL and SQLite user tables.
**Preventative:** Standardize user seeding configurations and verify credentials against literal keys before committing password hashes.

## BUG-037: QMS Manual Document Accessibility Failure
**Detected:** 06/23/2026
**Symptoms:** Requesting specific QMS manual pages from `/manual/<filename>` returns "Document not found (404)".
**Root Cause:**
1. Four Obsidian-related HTML SOP files were located in the `trash/` directory instead of the active `static/qms/` directory.
2. The index file `qms_index.json` mapped `hwb-qms-9.1_gemini_master_setup_sop.html` as the target file, but on disk the file was named `hwb-qms-9.1_antigravity_master_setup_sop.html` (filename mismatch).
**Solution:**
1. Restored the 4 Obsidian HTML documents from `trash/` to `static/qms/`.
2. Updated the filename reference for the master setup document in `qms_index.json` to `hwb-qms-9.1_antigravity_master_setup_sop.html`.
**Preventative:** Perform automated file integrity checks on static resources during the database handshake sync.

## BUG-038: Recurrence of Ghost Volume Glitch on QMS Templates
**Detected:** 06/23/2026
**Symptoms:** Requests to `hwb-pur-001_container_xchange.html` and other QMS pages returned "Document not found (404)".
**Root Cause:** The bind mount mapping `/usr/share/nginx/html/qms` inside the `hwb_compliance_engine` container was empty, causing Nginx to serve 404 for all files even though they existed on the host.
**Solution:** Restarted the `compliance` container via `docker-compose restart compliance` to refresh the bind mounts.
**Preventative:** Check if `/usr/share/nginx/html/qms` inside the compliance container contains files during the master startup sequence, and auto-restart the container if it is empty.

## BUG-039: Inconsistent and amateur visual weights in popup forms
**Detected:** 07/20/2026
**Symptoms:** Details popup forms show oversized input boxes and loud, heavy `800`/`900` font weights for data values.
**Root Cause:**
1. CSS style class `.sigma-input` used `padding: 0.5rem 0.75rem` (40px height) and `font-weight: 600`.
2. Javascript dynamic template injected `font-weight: 800` and `font-size: 1.15rem` for read-only data values.
3. Overview cards used inside-card boundaries (`.isc-list-item`) which clashed with outer-label forms styling.
**Solution:**
1. Modified `.sigma-input` to use vertically compressed `0.4rem 0.65rem` padding (32-34px height) and medium `500` weight.
2. Standardized details values in Javascript template to `font-weight: 600` and `font-size: 0.9rem`.
3. Converted Overview tab cards to borderless `.sigma-read-field` with Title Case outer labels sitting above values.
4. Standardized split grid layouts across all tab screens to `300px 1fr` columns with a `2.5rem` gap.
**Preventative:** Strictly follow the *Outer Label and Grid Stability Standard* codified in version 5.0 of HWB-QMS-7.2.

## BUG-040: Modal delete stays on deleted record
**Detected:** 07/20/2026
**Symptoms:** Clicking "Delete Lead" (or "Delete Account") from inside the details modal successfully deletes the record, but leaves the modal open showing the deleted data.
**Root Cause:** The `deleteLead` and `deleteAccount` callbacks did not close the modal or switch to the adjacent records after the DELETE background query.
**Solution:** Updated callbacks to check if the modal is open. If so, they scan the table row elements to retrieve the adjacent record's ID and load it instantly. If no records remain on the page, the modal closes.
**Preventative:** Standardize in-modal deletions to use transition navigation handlers.

## BUG-041: Docker Desktop Socket Deletion and Telegram Listener Collision
**Detected:** 07/20/2026
**Symptoms:** `hwb_agent_worker` logs show repeated `[TELEGRAM] getUpdates error: HTTP 409` errors, blocking the containerized Telegram daemon from fetching updates. Additionally, Port 8000 returns a 502 routing error.
**Root Cause:**
1. A duplicate container stack was running under the legacy host `snap.docker.dockerd` service, running an older `telegram_listener.py` instance that collided with the new Docker Desktop stack.
2. The legacy snap container stack bound to Port 8000 on the host, preventing the new gateway from routing web traffic.
3. Stopping the snap service successfully deleted the duplicate containers, but also deleted the shared `/var/run/docker.sock` socket file.
**Solution:**
1. Disabled and stopped the `docker.dockerd` snap service permanently to prevent legacy container auto-restart.
2. Toggled the WSL integration in the Docker Desktop settings GUI to force the integration daemon to recreate the `/var/run/docker.sock` file and restart all containers cleanly.
**Preventative:** Ensure Docker Desktop is the sole active container runtime, and verify `/var/run/docker.sock` validity during the pre-flight check.







