"""
SigmaFidelity™ Enterprise SEO & AI Multimodal Media Engine
Standard: HWB-QMS-7.2 / GOV-04 Fortune 500 Tier-1 Media Governance
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import hashlib
import os
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape


CITY_GEO_COORDINATES: Dict[str, Dict[str, Any]] = {
    'mckinney': {'lat': 33.1972, 'lng': -96.6397},
    'frisco': {'lat': 33.1507, 'lng': -96.8236},
    'plano': {'lat': 33.0198, 'lng': -96.6989},
    'dallas': {'lat': 32.7767, 'lng': -96.7970},
    'waxahachie': {'lat': 32.3865, 'lng': -96.8483},
    'fort-worth': {'lat': 32.7555, 'lng': -97.3308},
    'irving': {'lat': 32.8140, 'lng': -96.9489},
    'richardson': {'lat': 32.9483, 'lng': -96.7299},
    'allen': {'lat': 33.1032, 'lng': -96.6706},
    'arlington': {'lat': 32.7357, 'lng': -97.1081},
    'addison': {'lat': 32.9618, 'lng': -96.8292},
    'prosper': {'lat': 33.2362, 'lng': -96.8011},
    'celina': {'lat': 33.3246, 'lng': -96.7844},
    'denton': {'lat': 33.2148, 'lng': -97.1331},
    'rockwall': {'lat': 32.9312, 'lng': -96.4597},
    'southlake': {'lat': 32.9412, 'lng': -97.1342},
    'grand-prairie': {'lat': 32.7459, 'lng': -96.9978},
    'mansfield': {'lat': 32.5632, 'lng': -97.1417},
}


FACILITY_VISUAL_METADATA: Dict[str, Dict[str, str]] = {
    'daycare-childcare': {
        'hero_image_title': (
            'Daycare & Preschool Classroom Cleaning in DFW — '
            'Residue-Free Floors & 4-Color Microfiber System'
        ),
        'hero_image_alt': (
            'HWB Cleaning technician in a Dallas-Fort Worth daycare classroom '
            'gliding a blue microfiber flat-mop across a smooth, residue-free '
            'floor next to a caddy with Red, Yellow, Green, and Blue '
            'microfiber cloths'
        ),
        'hero_image_caption': (
            'After-hours daycare and preschool classroom cleaning in '
            'Dallas-Fort Worth using properly diluted neutral floor cleaner '
            '(never sticky) and 4-color microfiber cloth separation.'
        ),
    },
    'schools-education': {
        'hero_image_title': (
            'Private School & K-12 Campus Cleaning in DFW — '
            'Student Desk Wiping & 4-Color Microfiber System'
        ),
        'hero_image_alt': (
            'HWB Cleaning technician in a Dallas-Fort Worth private school '
            'classroom wiping student desks with a blue microfiber cloth '
            'and nitrile gloves beside a 4-color microfiber caddy and '
            'clean hallway floor'
        ),
        'hero_image_caption': (
            'Evening private school and K-12 campus cleaning across '
            'Dallas-Fort Worth featuring student desk detailing, 4-color '
            'microfiber cloth separation, and strict classroom lock-up.'
        ),
    },
    'medical-dental': {
        'hero_image_title': (
            'Medical & Dental Clinic Cleaning in DFW — '
            '4-Color Cloth Separation & Patient Privacy Protection'
        ),
        'hero_image_alt': (
            'HWB Cleaning technician wearing nitrile gloves wiping a '
            'medical exam room counter with a blue microfiber cloth while '
            'the exam chair and computer monitor remain untouched'
        ),
        'hero_image_caption': (
            'Detailed nightly medical and dental office cleaning in '
            'Dallas-Fort Worth with 4-color microfiber separation, '
            'residue-free clinic floors, and strict respect for patient '
            'privacy and clinical equipment.'
        ),
    },
    'corporate-offices': {
        'hero_image_title': (
            'Corporate Office & Class-A Building Cleaning in DFW — '
            'Undisturbed Workstations & Streak-Free Glass'
        ),
        'hero_image_alt': (
            'HWB Cleaning technician flat-mopping a Class-A Dallas-Fort Worth '
            'corporate office corridor alongside a streak-free glass '
            'conference wall while laptops and folders on desks remain '
            'completely undisturbed'
        ),
        'hero_image_caption': (
            'Nightly corporate office and commercial building cleaning in '
            'Dallas-Fort Worth with undisturbed employee workstations, '
            'streak-free conference glass, and residue-free hard floors.'
        ),
    },
    'auto-dealerships': {
        'hero_image_title': (
            'Auto Dealership Showroom & Service Cleaning in DFW — '
            'Mirror-Clear Tile Without Sticky Soap Haze'
        ),
        'hero_image_alt': (
            'HWB Cleaning technician flat-mopping high-gloss porcelain '
            'showroom tile after hours in a Dallas-Fort Worth auto '
            'dealership leaving mirror-clear floors with zero cloudy haze'
        ),
        'hero_image_caption': (
            'After-hours auto dealership showroom cleaning in '
            'Dallas-Fort Worth delivering haze-free high-gloss tile, '
            'streak-free showroom glass, and careful work around vehicles.'
        ),
    },
    'churches-nonprofits': {
        'hero_image_title': (
            'Church Sanctuary & Campus Cleaning in DFW — '
            'Sunday-Ready Seating & Untouched Stage Equipment'
        ),
        'hero_image_alt': (
            'HWB Cleaning technician vacuuming the center carpet aisle '
            'between wooden pews in a Dallas-Fort Worth church sanctuary '
            'while stage instruments and sound gear remain untouched'
        ),
        'hero_image_caption': (
            'Flexible church sanctuary, nursery, and campus cleaning in '
            'Dallas-Fort Worth with Sunday-ready seating, child-safe '
            'nurseries, and untouched worship stage audio equipment.'
        ),
    },
    'warehouses-industrial': {
        'hero_image_title': (
            'Warehouse & 3PL Distribution Floor Scrubbing in DFW — '
            'Debris-Free Concrete Aisles & PPE/PIT Safety'
        ),
        'hero_image_alt': (
            'PPE and PIT-trained HWB Cleaning technician in a hard hat, '
            'safety glasses, high-visibility vest, and steel-toe boots '
            'operating a floor scrubber down a debris-free Dallas-Fort Worth '
            'warehouse concrete aisle'
        ),
        'hero_image_caption': (
            'Industrial warehouse and 3PL distribution center cleaning in '
            'Dallas-Fort Worth keeping concrete aisles free of pallet '
            'splinters and nails to protect forklift tires, backed by '
            'HWB’s in-house Safety Department.'
        ),
    },
    'construction-subdivisions': {
        'hero_image_title': (
            '3-Step Subdivision & 3-Phase Post-Construction Cleanup in DFW — '
            'Clear Transit Lines for City Inspectors & PPE Safety'
        ),
        'hero_image_alt': (
            'HWB Cleaning construction crew in full PPE hard hats, safety '
            'glasses, high-visibility vests, and steel-toe boots sweeping '
            'mud and gravel from a Dallas-Fort Worth subdivision street '
            'curb and protected storm drain for City Inspection'
        ),
        'hero_image_caption': (
            'Division 1 3-Step subdivision transit line and street cleanup '
            'for City Inspectors plus Division 2 3-Phase interior building '
            'final cleans across Dallas-Fort Worth, backed by HWB’s '
            'in-house Safety Department.'
        ),
    },
}


SITEWIDE_IMAGE_METADATA: Dict[str, Dict[str, str]] = {
    'hero_lobby': {
        'title': 'Commercial Building & Lobby Cleaning in Dallas-Fort Worth | HWB Cleaning',
        'alt': 'HWB Cleaning technician maintaining a gleaming Class-A commercial lobby floor in Dallas-Fort Worth, TX',
        'caption': 'Commercial lobby, office, and facility maintenance across Dallas, Plano, Frisco, McKinney, and DFW.',
    },
    'commercial_church_vacuuming': {
        'title': 'Commercial Floor Care, Carpet Extraction & Sanctuary Vacuuming in DFW',
        'alt': 'HWB Cleaning technicians performing commercial carpet care and floor maintenance in a Dallas-Fort Worth facility',
        'caption': 'Commercial floor stripping, waxing, carpet extraction, and deep surface care across North Texas.',
    },
    'commercial_marble_polishing': {
        'title': 'Commercial Hard Floor Polishing, VCT Waxing & Stone Care in DFW',
        'alt': 'HWB Cleaning technician polishing and maintaining commercial hard floors in Dallas-Fort Worth',
        'caption': 'VCT stripping and waxing, natural stone polishing, and residue-free floor maintenance across DFW.',
    },
    'industrial_hero_ppe_aisles': {
        'title': 'Industrial Warehouse Cleaning & PPE/PIT Trained Crews in DFW',
        'alt': 'PPE-trained HWB Cleaning industrial crew maintaining debris-free warehouse concrete aisles in Dallas-Fort Worth',
        'caption': 'Industrial warehouse concrete floor scrubbing and debris removal backed by HWB’s in-house Safety Department.',
    },
    'industrial_m20_scrubber': {
        'title': 'Ride-On Industrial Floor Scrubbing for DFW Warehouses & 3PL Hubs',
        'alt': 'PIT and PPE-trained HWB Cleaning operator scrubbing warehouse concrete floors to remove debris and protect forklift tires',
        'caption': 'Heavy-duty ride-on and walk-behind concrete floor scrubbing for North Texas logistics and manufacturing plants.',
    },
    'construction_rough_clean_ppe': {
        'title': '3-Step Subdivision & 3-Phase Post-Construction Cleanup in DFW',
        'alt': 'PPE-trained HWB Cleaning construction cleanup crew performing interior detail and rough cleaning in Dallas-Fort Worth',
        'caption': '3-Step subdivision transit-line cleanup for City Inspectors and 3-Phase interior building final cleans across DFW.',
    },
    'construction_sweeper_servicing_street': {
        'title': 'Subdivision Street & Transit Line Sweeping for City Inspections in DFW',
        'alt': 'HWB Cleaning street sweeping equipment clearing mud and construction debris from a North Texas subdivision transit line',
        'caption': 'Division 1 subdivision street, curb, and storm-drain transit line cleanup for land developers and builders in DFW.',
    },
    'daycare_busy_active': {
        'title': 'Safe Daycare, School & Commercial Janitorial Services in DFW',
        'alt': 'Clean, child-safe daycare and educational classroom maintained by HWB Cleaning Services LLC in North Texas',
        'caption': 'Nightly janitorial, 4-color microfiber separation, and residue-free floor care for DFW schools, daycares, and offices.',
    },
    'janitorial_breakroom': {
        'title': 'Commercial Breakroom, Restroom & Office Sanitization in DFW',
        'alt': 'Spotless commercial office breakroom and kitchen counters cleaned with green microfiber cloths in Dallas-Fort Worth',
        'caption': 'Daily and nightly office breakroom, restroom, and workstation cleaning across Dallas-Fort Worth.',
    },
    'hwb_core_team_v2': {
        'title': 'HWB Cleaning Services LLC Executive Leadership & Supervision Team in DFW',
        'alt': 'Mirna Rondinella, President, and Humberto Dominguez, CEO of HWB Cleaning Services LLC with North Texas operations team',
        'caption': 'Executive leadership and field supervision team behind HWB Cleaning Services LLC in Dallas-Fort Worth, Texas.',
    },
}


ROUTE_SEO_DEFAULTS: Dict[str, Dict[str, str]] = {
    '/': {
        'name': 'Home',
        'image': '/static/img/hero_lobby.webp',
        'title': 'Commercial Cleaning & Janitorial Services in Dallas, Plano, Frisco & McKinney',
        'alt': 'HWB Cleaning technician maintaining a gleaming Class-A commercial lobby floor in Dallas-Fort Worth, TX',
        'caption': 'Dependable nightly janitorial, floor care, warehouse scrubbing, and post-construction cleanup across Dallas-Fort Worth.',
    },
    '/services/janitorial': {
        'name': 'Daily Office Cleaning & Janitorial',
        'image': '/static/img/hero_facility_corporate.webp',
        'title': 'Daily Office Cleaning & Nightly Janitorial Services in DFW | HWB Cleaning',
        'alt': 'HWB Cleaning technician flat-mopping a Class-A Dallas-Fort Worth corporate office corridor with undisturbed employee desks',
        'caption': 'Nightly office cleaning, day porter staffing, 4-color microfiber separation, and strict lock-up security across DFW.',
    },
    '/services/commercial': {
        'name': 'Commercial Cleaning & Floor Care',
        'image': '/static/img/commercial_church_vacuuming.webp',
        'title': 'Commercial Floor Care, VCT Strip & Wax & Carpet Extraction in DFW',
        'alt': 'HWB Cleaning technicians performing commercial carpet care and floor maintenance in a Dallas-Fort Worth facility',
        'caption': 'VCT floor stripping and waxing, commercial carpet extraction, and streak-free window cleaning in Dallas-Fort Worth.',
    },
    '/services/industrial': {
        'name': 'Industrial & Warehouse Cleaning',
        'image': '/static/img/hero_facility_warehouse.webp',
        'title': 'Industrial & Warehouse Floor Scrubbing in DFW — PPE & PIT Trained Crews',
        'alt': 'PPE and PIT-trained HWB Cleaning technician operating a floor scrubber down a debris-free DFW warehouse concrete aisle',
        'caption': 'Debris-free concrete floor scrubbing that protects forklift tires, shift restroom cleaning, and an in-house Safety Department.',
    },
    '/services/construction': {
        'name': '3-Step Subdivision & 3-Phase Post-Construction Cleanup',
        'image': '/static/img/hero_facility_construction.webp',
        'title': '3-Step Subdivision & 3-Phase Post-Construction Cleanup in DFW',
        'alt': 'HWB Cleaning crew in full PPE sweeping mud and gravel from a Dallas-Fort Worth subdivision street curb for City Inspection',
        'caption': 'Division 1 transit-line cleanup for City Inspectors and Division 2 3-Phase interior building final cleans across DFW.',
    },
    '/about': {
        'name': 'About HWB Cleaning',
        'image': '/static/img/hwb_core_team_v2.webp',
        'title': 'About HWB Cleaning Services LLC — North Texas Commercial Cleaning Leadership',
        'alt': 'Executive leadership and field supervision team of HWB Cleaning Services LLC in Dallas-Fort Worth, Texas',
        'caption': 'Led by President Mirna Rondinella and CEO Humberto Dominguez, maintaining over 656,785 SF across North Texas.',
    },
}


class SEOMediaEngine:
    """
    Singleton engine governing binary EXIF/XMP metadata, multi-resolution
    responsive srcset generation, SHA-256 content-hash cache busting, and
    dynamic XML Image Sitemap and AI Knowledge Manifest synthesis.
    """

    _instance: Optional['SEOMediaEngine'] = None
    _hash_cache: Dict[str, str] = {}

    def __new__(cls) -> 'SEOMediaEngine':
        if cls._instance is None:
            cls._instance = super(SEOMediaEngine, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_file_sha256_short(cls, abs_path: str) -> str:
        """Returns an 8-character SHA-256 digest cached by file mtime."""
        if not abs_path or not os.path.exists(abs_path):
            return '2.4.3'
        try:
            mtime = os.path.getmtime(abs_path)
            cache_key = f"{abs_path}:{mtime}"
            if cache_key in cls._hash_cache:
                return cls._hash_cache[cache_key]
            h = hashlib.sha256()
            with open(abs_path, 'rb') as f_in:
                for chunk in iter(lambda: f_in.read(65536), b''):
                    h.update(chunk)
            digest = h.hexdigest()[:8]
            cls._hash_cache[cache_key] = digest
            return digest
        except Exception:
            return '2.4.3'

    @classmethod
    def build_responsive_urls(
        cls,
        base_rel_path: str,
        static_folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds versioned 640w, 1024w, 1376w URLs and srcset string."""
        clean_rel = str(base_rel_path or '/static/img/hero_lobby.webp').split('?')[0]
        stem = clean_rel[:-5] if clean_rel.endswith('.webp') else clean_rel
        rel_640 = f"{stem}-640w.webp"
        rel_1024 = f"{stem}-1024w.webp"
        rel_1376 = f"{stem}.webp"

        ver = '2.4.3'
        has_640 = False
        has_1024 = False
        if static_folder:
            abs_1376 = os.path.join(
                static_folder, rel_1376.replace('/static/', '', 1)
            )
            abs_1024 = os.path.join(
                static_folder, rel_1024.replace('/static/', '', 1)
            )
            abs_640 = os.path.join(
                static_folder, rel_640.replace('/static/', '', 1)
            )
            ver = cls.get_file_sha256_short(abs_1376)
            has_640 = os.path.exists(abs_640)
            has_1024 = os.path.exists(abs_1024)

        url_1376 = f"{rel_1376}?v={ver}"
        url_1024 = f"{rel_1024}?v={ver}" if has_1024 else url_1376
        url_640 = f"{rel_640}?v={ver}" if has_640 else url_1376
        if has_640 and has_1024:
            srcset = f"{url_640} 640w, {url_1024} 1024w, {url_1376} 1376w"
        else:
            srcset = f"{url_1376} 1376w"

        return {
            'raw': rel_1376,
            'url': url_1376,
            'url_1024': url_1024,
            'url_640': url_640,
            'srcset': srcset,
            'canonical_url': f"https://www.hwbcleaning.com{rel_1376}",
            'sha256': ver,
            'width': 1376,
            'height': 768,
        }

    @classmethod
    def enrich_facility_media(
        cls,
        facility_dict: Dict[str, Any],
        static_folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enriches a facility dictionary with responsive srcset and SEO metadata."""
        enriched = dict(facility_dict)
        slug = str(enriched.get('slug') or '').strip()
        meta = FACILITY_VISUAL_METADATA.get(slug, {})
        resp = cls.build_responsive_urls(
            enriched.get('hero_image') or '/static/img/hero_lobby.webp',
            static_folder,
        )

        enriched['hero_image_raw'] = resp['raw']
        enriched['hero_image'] = resp['url']
        enriched['hero_image_640'] = resp['url_640']
        enriched['hero_image_1024'] = resp['url_1024']
        enriched['hero_image_srcset'] = resp['srcset']
        enriched['hero_image_width'] = resp['width']
        enriched['hero_image_height'] = resp['height']
        enriched['hero_image_sha256'] = resp['sha256']
        enriched['hero_image_canonical_url'] = resp['canonical_url']
        enriched['hero_image_title'] = (
            enriched.get('hero_image_title')
            or meta.get('hero_image_title')
            or enriched.get('h1')
            or 'HWB Commercial Cleaning in Dallas-Fort Worth'
        )
        enriched['hero_image_alt'] = (
            enriched.get('hero_image_alt')
            or meta.get('hero_image_alt')
            or enriched.get('meta_desc')
            or 'HWB Commercial Cleaning in Dallas-Fort Worth, TX'
        )
        enriched['hero_image_caption'] = (
            enriched.get('hero_image_caption')
            or meta.get('hero_image_caption')
            or enriched.get('desc')
            or ''
        )
        enriched['hero_image_geo'] = 'Dallas-Fort Worth, TX, USA'
        return enriched

    @classmethod
    def enrich_location_media(
        cls,
        city_slug: str,
        location_dict: Dict[str, Any],
        static_folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enriches a city location dictionary with GeoCoordinates and hero ImageObject data."""
        enriched = dict(location_dict)
        slug_clean = str(city_slug or '').lower().strip()
        city_name = enriched.get('name') or slug_clean.replace('-', ' ').title()
        coords = CITY_GEO_COORDINATES.get(
            slug_clean, {'lat': 32.8998, 'lng': -97.0403}
        )
        resp = cls.build_responsive_urls(
            '/static/img/hero_lobby.webp', static_folder
        )
        enriched['slug'] = slug_clean
        enriched['geo_lat'] = coords['lat']
        enriched['geo_lng'] = coords['lng']
        enriched['hero_image_raw'] = resp['raw']
        enriched['hero_image'] = resp['url']
        enriched['hero_image_srcset'] = resp['srcset']
        enriched['hero_image_width'] = resp['width']
        enriched['hero_image_height'] = resp['height']
        enriched['hero_image_canonical_url'] = resp['canonical_url']
        enriched['hero_image_title'] = (
            f"Commercial Cleaning & Janitorial Services in {city_name}, TX | HWB Cleaning"
        )
        enriched['hero_image_alt'] = (
            f"HWB Cleaning technician maintaining a commercial building lobby in {city_name}, Texas"
        )
        enriched['hero_image_caption'] = (
            enriched.get('desc')
            or f"Nightly office janitorial, floor care, warehouse scrubbing, and post-construction cleanup in {city_name}, TX."
        )
        enriched['hero_image_geo'] = f"{city_name}, TX, USA"
        return enriched

    @staticmethod
    def build_xmp_packet(
        title: str,
        description: str,
        alt_text: str,
    ) -> bytes:
        """Builds an Adobe XMP Dublin Core / IPTC Rights XML packet."""
        t_esc = xml_escape(title)
        d_esc = xml_escape(description)
        a_esc = xml_escape(alt_text)
        xmp = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"
    xmlns:Iptc4xmpCore="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"
    photoshop:Credit="HWB Cleaning Services LLC"
    photoshop:City="Dallas-Fort Worth"
    photoshop:State="TX"
    photoshop:Country="United States"
    xmpRights:Marked="True"
    xmpRights:WebStatement="https://www.hwbcleaning.com/get-quote"
    Iptc4xmpCore:AltTextAccessibility="{a_esc}">
   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{t_esc}</rdf:li></rdf:Alt></dc:title>
   <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{d_esc}</rdf:li></rdf:Alt></dc:description>
   <dc:creator><rdf:Seq><rdf:li>HWB Cleaning Services LLC</rdf:li></rdf:Seq></dc:creator>
   <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">Copyright 2026 HWB Cleaning Services LLC. All Rights Reserved.</rdf:li></rdf:Alt></dc:rights>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
        return xmp.encode('utf-8')

    @classmethod
    def generate_dynamic_sitemap_xml(
        cls,
        facilities_data: Dict[str, Dict[str, Any]],
        locations_data: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        Generates a Google-compliant XML Sitemap with Image Sitemap 1.1
        extensions (<image:image>) across Home, Services, Facilities,
        Locations, and About pages.
        """
        lines: List[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
            '  <!-- Core Conversion & Home Surface -->',
            '  <url>',
            '    <loc>https://www.hwbcleaning.com/</loc>',
            '    <lastmod>2026-11-10</lastmod>',
            '    <priority>1.0</priority>',
            '    <image:image>',
            '      <image:loc>https://www.hwbcleaning.com/static/img/hero_lobby.webp</image:loc>',
            '      <image:title>Commercial Cleaning &amp; Janitorial Services in Dallas, Plano, Frisco &amp; McKinney | HWB Cleaning</image:title>',
            '      <image:caption>Dependable nightly janitorial, specialty floor care, warehouse scrubbing, and post-construction cleanup across Dallas-Fort Worth.</image:caption>',
            '      <image:geo_location>Dallas-Fort Worth, TX, USA</image:geo_location>',
            '      <image:license>https://www.hwbcleaning.com/terms</image:license>',
            '    </image:image>',
            '  </url>',
            '  <url><loc>https://www.hwbcleaning.com/get-quote</loc><lastmod>2026-11-10</lastmod><priority>0.95</priority></url>',
            '',
            '  <!-- Specialized Commercial Cleaning Service Lines -->',
        ]

        service_paths = [
            '/services/janitorial',
            '/services/commercial',
            '/services/industrial',
            '/services/construction',
        ]
        for sp in service_paths:
            s_meta = ROUTE_SEO_DEFAULTS[sp]
            lines.extend([
                '  <url>',
                f'    <loc>https://www.hwbcleaning.com{sp}</loc>',
                '    <lastmod>2026-11-10</lastmod>',
                '    <priority>0.90</priority>',
                '    <image:image>',
                f'      <image:loc>https://www.hwbcleaning.com{xml_escape(s_meta["image"])}</image:loc>',
                f'      <image:title>{xml_escape(s_meta["title"])}</image:title>',
                f'      <image:caption>{xml_escape(s_meta["caption"])}</image:caption>',
                '      <image:geo_location>Dallas-Fort Worth, TX, USA</image:geo_location>',
                '      <image:license>https://www.hwbcleaning.com/terms</image:license>',
                '    </image:image>',
                '  </url>',
            ])

        lines.append('')
        lines.append(
            '  <!-- Dedicated Facility Vertical Hubs (8 Specialized Hubs with Image Sitemap 1.1) -->'
        )
        for slug, raw_fac in facilities_data.items():
            fac = cls.enrich_facility_media(raw_fac)
            loc_url = f"https://www.hwbcleaning.com/facilities/{xml_escape(slug)}"
            img_url = xml_escape(fac['hero_image_canonical_url'])
            img_title = xml_escape(fac['hero_image_title'])
            img_caption = xml_escape(fac['hero_image_caption'])
            lines.extend([
                '  <url>',
                f'    <loc>{loc_url}</loc>',
                '    <lastmod>2026-11-10</lastmod>',
                '    <priority>0.92</priority>',
                '    <image:image>',
                f'      <image:loc>{img_url}</image:loc>',
                f'      <image:title>{img_title}</image:title>',
                f'      <image:caption>{img_caption}</image:caption>',
                '      <image:geo_location>Dallas-Fort Worth, TX, USA</image:geo_location>',
                '      <image:license>https://www.hwbcleaning.com/terms</image:license>',
                '    </image:image>',
                '  </url>',
            ])

        lines.append('')
        lines.append('  <!-- Regional North Texas Metropolitan Corridors (18 Cities) -->')
        primary_cities = {'mckinney', 'frisco', 'plano', 'dallas'}
        growth_cities = {'prosper', 'celina'}
        for city_slug, raw_loc in locations_data.items():
            loc_info = cls.enrich_location_media(city_slug, raw_loc)
            prio = (
                '0.90'
                if city_slug in primary_cities
                else ('0.88' if city_slug in growth_cities else '0.85')
            )
            c_esc = xml_escape(city_slug)
            lines.extend([
                '  <url>',
                f'    <loc>https://www.hwbcleaning.com/locations/{c_esc}</loc>',
                '    <lastmod>2026-11-10</lastmod>',
                f'    <priority>{prio}</priority>',
                '    <image:image>',
                f'      <image:loc>{xml_escape(loc_info["hero_image_canonical_url"])}</image:loc>',
                f'      <image:title>{xml_escape(loc_info["hero_image_title"])}</image:title>',
                f'      <image:caption>{xml_escape(loc_info["hero_image_caption"])}</image:caption>',
                f'      <image:geo_location>{xml_escape(loc_info["hero_image_geo"])}</image:geo_location>',
                '      <image:license>https://www.hwbcleaning.com/terms</image:license>',
                '    </image:image>',
                '  </url>',
            ])

        lines.extend([
            '',
            '  <!-- Commercial Trust, B2B Procurement & Prequalification -->',
            '  <url>',
            '    <loc>https://www.hwbcleaning.com/about</loc>',
            '    <lastmod>2026-11-10</lastmod>',
            '    <priority>0.80</priority>',
            '    <image:image>',
            '      <image:loc>https://www.hwbcleaning.com/static/img/hwb_core_team_v2.webp</image:loc>',
            '      <image:title>About HWB Cleaning Services LLC — North Texas Commercial Cleaning Leadership</image:title>',
            '      <image:caption>Led by President Mirna Rondinella and CEO Humberto Dominguez, maintaining over 656,785 SF across North Texas.</image:caption>',
            '      <image:geo_location>Dallas-Fort Worth, TX, USA</image:geo_location>',
            '      <image:license>https://www.hwbcleaning.com/terms</image:license>',
            '    </image:image>',
            '  </url>',
            '  <url><loc>https://www.hwbcleaning.com/trust-center</loc><lastmod>2026-11-10</lastmod><priority>0.80</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/capability-statement</loc><lastmod>2026-11-10</lastmod><priority>0.80</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/prequal</loc><lastmod>2026-11-10</lastmod><priority>0.80</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/academy</loc><lastmod>2026-11-10</lastmod><priority>0.75</priority></url>',
            '',
            '  <!-- Workforce Recruitment & Operational Methodology -->',
            '  <url><loc>https://www.hwbcleaning.com/work-with-us</loc><lastmod>2026-11-10</lastmod><priority>0.70</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/compliance</loc><lastmod>2026-11-10</lastmod><priority>0.70</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/ehsq</loc><lastmod>2026-11-10</lastmod><priority>0.70</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/methodology</loc><lastmod>2026-11-10</lastmod><priority>0.70</priority></url>',
            '',
            '  <!-- AI Knowledge Manifests -->',
            '  <url><loc>https://www.hwbcleaning.com/llms.txt</loc><lastmod>2026-11-10</lastmod><priority>0.85</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/llms-full.txt</loc><lastmod>2026-11-10</lastmod><priority>0.85</priority></url>',
            '',
            '  <!-- Legal & Institutional Standards -->',
            '  <url><loc>https://www.hwbcleaning.com/privacy-policy</loc><lastmod>2026-11-10</lastmod><priority>0.50</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/terms</loc><lastmod>2026-11-10</lastmod><priority>0.50</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/accessibility</loc><lastmod>2026-11-10</lastmod><priority>0.50</priority></url>',
            '  <url><loc>https://www.hwbcleaning.com/fcra-disclosure</loc><lastmod>2026-11-10</lastmod><priority>0.50</priority></url>',
            '</urlset>',
        ])
        return '\n'.join(lines) + '\n'
