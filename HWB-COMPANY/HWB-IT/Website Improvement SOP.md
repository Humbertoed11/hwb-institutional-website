# SOP: Website Content and SEO Improvement

**Purpose:** To provide a standardized process for adding new content and optimizing pages on `hwbcleaning.com` to improve search engine ranking and user engagement.

**Scope:** This SOP applies to all new and existing pages, service pages, and blog posts.

**Frequency:** This process should be followed for every new page created and should be used to review existing key pages at least once per quarter.

---

## Procedure

Follow these steps to ensure all new and updated content is optimized to attract local customers and communicate effectively with search engines.

### Step 1: Keyword & Topic Planning

Before writing, identify the main topic and keywords for the page.

1.  **Identify the Primary Target:** Determine the single most important service or topic for the page.
    *   *Example:* For a new page about cleaning carpets, the primary target is "commercial carpet cleaning."

2.  **Identify the Location:** For local services, the target location is critical.
    *   *Example:* "Plano, TX"

3.  **Combine for Primary Keyword:** Combine the service and location.
    *   *Example:* "commercial carpet cleaning in Plano, TX"

4.  **Identify Secondary Keywords:** Think of related terms or questions.
    *   *Example:* "office carpet cleaning Plano," "business rug cleaning," "stain removal for commercial carpet."

### Step 2: Content Creation

1.  **Write for Humans:** Create detailed, high-quality content (aim for at least 400-500 words) that is genuinely helpful to a potential customer. Fully explain the service, its benefits, and your process.

2.  **Use Keywords Naturally:** Include your primary and secondary keywords where they make sense. Do not force them in unnaturally. They should appear in headings and paragraphs.

3.  **Structure with Headings:** Use a clear structure with headings and subheadings (H1, H2, H3).
    *   There should only be **one H1 heading** on the page, which should be the main title and include the primary keyword.
    *   Use H2s and H3s for sub-topics.

4.  **Add a Call to Action (CTA):** End the page with a clear instruction for the reader.
    *   *Example:* "Contact HWB Cleaning today for a free, no-obligation quote on our carpet cleaning services!"

### Step 3: On-Page SEO Optimization (SigmaFidelity™ Hardening)

Once the content is written, optimize the page's technical elements.

1.  **Canonical URL (MANDATORY):** Every page MUST have a canonical link pointing to the primary domain (`www.hwbcleaning.com`) to prevent authority dilution and ranking fragmentation.
    *   **Format:** `<link rel="canonical" href="https://www.hwbcleaning.com/page-slug">`
    *   **Mandate:** Never use staging or Azure-specific URLs in production canonical tags.

2.  **Social Visibility (OG Tags):** Include Open Graph tags in the `<head>` to ensure high-fidelity previews on professional networks like LinkedIn.
    *   **Required Tags:** `og:title`, `og:description`, `og:image`, `og:url`.

3.  **Page Title (`<title>`):** This is the most important SEO element.
    *   **Format:** `Primary Keyword | Brand Name`
    *   **Example:** `Commercial Carpet Cleaning in Plano, TX | HWB Cleaning`
    *   **Length:** Keep it under 60 characters.

2.  **Meta Description (`<meta name="description">`):** This is the short text that appears under your title in Google search results.
    *   **Content:** Write an enticing summary of the page. It must include your primary keyword and a call to action.
    *   **Example:** `HWB Cleaning offers professional carpet cleaning for offices and businesses in Plano, TX. We handle tough stains and high-traffic areas. Get a free quote today!`
    *   **Length:** Keep it under 160 characters.

3.  **URL (Slug):**
    *   **Format:** Use a short, descriptive URL that contains the primary keyword without the location.
    *   **Example:** `www.hwbcleaning.com/commercial-carpet-cleaning`

4.  **Image Optimization:**
    *   **Filename:** Before uploading, name image files with descriptive keywords (e.g., `plano-tx-office-carpet-cleaning.jpg`).
    *   **Alt Text:** Add descriptive "alt text" to every image. This helps search engines understand the image content.
    *   **Example Alt Text:** `Technician from HWB Cleaning steam cleaning a commercial office carpet in Plano, TX.`

### Step 4: Linking

1.  **Internal Linking:**
    *   From your new page, add at least 1-2 links to other relevant pages on your site (like the `/contact` or `/facility-services` page).
    *   From an existing, relevant page (like `/facility-services`), add a link *to* your new page. This helps search engines discover it and understand its importance.

### Step 5: Post-Publishing

1.  **Request Indexing:** After publishing the page, use the Google Search Console "URL Inspection" tool to submit the new URL. This asks Google to crawl and index your new page faster.

2.  **Promote on Google Business Profile:** Create a "Post" on your Google Business Profile with a summary of the new service and a link back to the new page on your website. This is a powerful signal for local SEO.

---

## Appendix: Initial SEO Analysis (Example)

The following is a real-world example of a "brutal" SEO analysis conducted on `hwbcleaning.com`. It identifies the most critical issues and provides a prioritized action plan. This serves as a practical illustration of the concepts discussed in this SOP.

---

### The Ugly: Critical Issues to Fix Immediately

This is the #1 constraint holding you back. If you do nothing else, do this.

*   **Your website is invisible to local customers.** There is no mention of your service area (e.g., Plano, TX, DFW) in your page title or the content summary. For a local business, this is an SEO death sentence. Google has no idea where you operate, so it will not show your site to people searching for "office cleaning in Plano."
*   **Your page title is weak.** The title tag (<title>) is the most important on-page SEO factor. Yours is just "HWB Cleaning Services LLC.". It tells Google your name, but not what you do or where you do it.
*   **You are likely ignoring Google Business Profile.** I cannot see this, but for a local service business, an optimized Google Business Profile (GBP) is more important than your website. It's what appears in the Google Maps listings (the "snack pack"), which is where the majority of local service clicks come from.

**Action Plan (Fix these first):**

1.  **Optimize Your Title Tag:** Change your homepage title to be keyword- and location-focused. Do this now.
    *   From: HWB Cleaning Services LLC.
    *   To: Professional Janitorial & Office Cleaning Services in Plano, TX | HWB Cleaning Services LLC
2.  **Create and Optimize a Google Business Profile:** Go to google.com/business and either claim or create your profile. Fill out every single section: services, service area, hours, photos, business description. Get reviews from your customers. This is non-negotiable.

---

### The Bad: Major Issues to Address Next

These issues are seriously hindering your ability to compete.

*   **Content is likely too thin.** A single page with "core beliefs" is not enough. Google rewards expertise. You need to prove you are an authority on cleaning services.
*   **No clear Call to Action (CTA).** What is the single most important thing you want a visitor to do? "Get a Free Quote"? "Call Us Now"? This should be front and center.
*   **Missing Meta Description.** This is the text that appears under your title in Google search results. It's your ad copy. If it's missing, Google will just pull random text from your page, which looks unprofessional and reduces clicks.

**Action Plan:**

1.  **Write a Compelling Meta Description:** Add a meta description to your homepage that is around 155 characters. It should describe your services, include your location, and have a call to action.
    *   Example: "HWB Cleaning offers reliable and affordable janitorial services for offices and commercial properties in Plano, TX. Contact us today for a free, no-obligation quote!"
2.  **Build Out Service Pages:** Create separate pages for each of your core services (e.g., "Office Cleaning," "Commercial Janitorial Services," "Post-Construction Cleaning"). Each page should have at least 300-500 words of unique content describing that service.

---

### The Good: What You Can Build On

*   You have a website that is online and functional.
*   Your business name is clear.
*   You mention "janitorial cleaning services," which is a good starting keyword.

### Conclusion:

Your website is currently a digital business card, but it is not an asset that will generate leads. The primary constraint is its complete lack of local SEO signals.

Focus 80% of your effort on optimizing your Google Business Profile and fixing your homepage title tag. These two actions will have the biggest impact on your visibility in local search results.