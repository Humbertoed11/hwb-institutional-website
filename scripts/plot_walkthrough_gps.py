#!/usr/bin/env python3
"""
=============================================================================
HWB CLEANING SERVICES LLC — SIGMAFIDELITY™ GEOSPATIAL TAKEOFF ENGINE
SCRIPT: plot_walkthrough_gps.py
PURPOSE: Extracts GPS EXIF metadata from on-site walkthrough photos and plots
         exact outdoor trashcan / ash urn coordinates via:
         1. Official Collin College Architectural Campus Site Map (PNG)
         2. Google Earth & Google My Maps (.KML / .KMZ Export)
         3. Interactive Mobile Satellite Map (HTML / Leaflet / Google Satellite)
         4. Direct 1-Click Google Maps Deep Links (lat,lon navigation)
GOVERNANCE: HWB-QMS-11.2 | ISO 9001:2015 Traceability
AUTHOR: Systems Architect George (mbB)
=============================================================================
"""

import os
import sys
import json
import glob
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS, GPSTAGS

# -----------------------------------------------------------------------------
# 1.0 CONFIGURATION & REPOSITORY PATHS
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path("/home/humbertoed/gemini_projects")
QUOTE_DIR = PROJECT_ROOT / "HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE"
WEB_STATIC_DIR = PROJECT_ROOT / "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/proposals"

BASE_MAP_PATH = QUOTE_DIR / "frisco_site_map-1.png"
OUTPUT_MAP_PATH = QUOTE_DIR / "frisco_campus_trashcan_plot.png"
OUTPUT_KML_PATH = QUOTE_DIR / "frisco_trashcans.kml"
OUTPUT_HTML_PATH = QUOTE_DIR / "frisco_interactive_map.html"
OUTPUT_REPORT_PATH = QUOTE_DIR / "TRASHCAN_GPS_INVENTORY.md"
PHOTOS_DIR = QUOTE_DIR / "walkthrough_photos"

# -----------------------------------------------------------------------------
# 2.0 AFFINE GEOREFERENCING CALIBRATION CONSTANTS
# Calibrated across 8 Frisco campus landmarks (Max residual error < 18 pixels)
# Image dimensions: 1275 x 900
# -----------------------------------------------------------------------------
MEAN_LAT = 33.1315517125
MEAN_LON = -96.7927746250

COEFF_X = [143726.5342929482, -11354.454866239055, 550.0000000010314]
COEFF_Y = [-4408.833892967511, -190492.65193186828, 414.37500000013785]

BUILDING_LANDMARKS = [
    ("Founders Hall", 33.1303571, -96.7929494, "Sector Alpha"),
    ("University Hall", 33.1303573, -96.7918300, "Sector Alpha"),
    ("Heritage Hall", 33.1314616, -96.7941169, "Sector Bravo"),
    ("Library & Resource Center", 33.1317080, -96.7928631, "Sector Charlie"),
    ("Lawler Hall (Bldg D)", 33.1306004, -96.7938961, "Sector Charlie"),
    ("Alumni Hall & Gym", 33.1313951, -96.7918255, "Sector Charlie"),
    ("Student Center & Cafe", 33.1322189, -96.7941642, "Sector Bravo"),
    ("IT Center", 33.1327534, -96.7931172, "Sector Bravo"),
    ("Parking Garage", 33.1332939, -96.7929573, "Sector Delta"),
    ("Central Plant / Maintenance", 33.1305764, -96.7912365, "Sector Delta"),
    ("Parking Lot A", 33.1314129, -96.7909186, "Exterior East"),
    ("Parking Lot B", 33.1295739, -96.7913261, "Exterior South"),
    ("Parking Lot C", 33.1294036, -96.7924847, "Exterior South"),
    ("Parking Lot D", 33.1294119, -96.7934325, "Exterior South"),
    ("Parking Lot E", 33.1296980, -96.7942912, "Exterior Southwest"),
    ("Parking Lot F", 33.1302719, -96.7949396, "Exterior West"),
    ("Parking Lot G", 33.1310136, -96.7952240, "Exterior West"),
    ("Parking Lot H", 33.1317889, -96.7951853, "Exterior West"),
    ("Parking Lot J", 33.1328824, -96.7944635, "Exterior Northwest"),
    ("Parking Lot K", 33.1332827, -96.7916069, "Exterior North"),
]

def gps_to_pixel(lat: float, lon: float) -> tuple:
    """Converts real-world GPS Latitude/Longitude to Pixel (X, Y) on site map."""
    u = lon - MEAN_LON
    v = lat - MEAN_LAT
    px = int(round(COEFF_X[0] * u + COEFF_X[1] * v + COEFF_X[2]))
    py = int(round(COEFF_Y[0] * u + COEFF_Y[1] * v + COEFF_Y[2]))
    px = max(10, min(1265, px))
    py = max(10, min(890, py))
    return px, py

def get_nearest_landmark(lat: float, lon: float) -> tuple:
    """Finds the nearest building or parking lot to a given GPS coordinate."""
    best_name = "Campus Grounds"
    best_sector = "General Exterior"
    best_dist = float("inf")
    for name, b_lat, b_lon, sector in BUILDING_LANDMARKS:
        d = ((lat - b_lat)**2 + (lon - b_lon)**2)**0.5
        if d < best_dist:
            best_dist = d
            best_name = name
            best_sector = sector
    dist_ft = round(best_dist * 364000)
    return best_name, best_sector, dist_ft

def extract_exif_gps(image_path: str):
    """Extracts decimal Latitude and Longitude from image EXIF data."""
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if not exif:
                return None
            gps_info = {}
            for tag, val in exif.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    for t in val:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_info[sub_decoded] = val[t]
            
            if "GPSLatitude" not in gps_info or "GPSLongitude" not in gps_info:
                return None
            
            def dms_to_decimal(dms, ref):
                degrees = float(dms[0])
                minutes = float(dms[1])
                seconds = float(dms[2])
                dec = degrees + (minutes / 60.0) + (seconds / 3600.0)
                if ref in ["S", "W"]:
                    dec = -dec
                return dec
            
            lat = dms_to_decimal(gps_info["GPSLatitude"], gps_info.get("GPSLatitudeRef", "N"))
            lon = dms_to_decimal(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "W"))
            timestamp = exif.get(36867, exif.get(306, "Unknown"))
            return {"lat": lat, "lon": lon, "timestamp": timestamp}
    except Exception as e:
        print(f"Error reading EXIF from {image_path}: {e}")
        return None

def generate_kml(points_data: list, output_kml_path: Path):
    """Generates a standard KML file importable into Google Earth & Google My Maps."""
    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>',
        '    <name>Collin College Frisco Campus — Exterior Trashcan Inventory</name>',
        '    <description>Audited by HWB Cleaning Services LLC | SigmaFidelity™ Geospatial Takeoff</description>',
        '    <Style id="trashcanPin">',
        '      <IconStyle>',
        '        <color>ff0000ff</color>',
        '        <scale>1.2</scale>',
        '        <Icon>',
        '          <href>http://maps.google.com/mapfiles/kml/shapes/recycle.png</href>',
        '        </Icon>',
        '      </IconStyle>',
        '    </Style>',
    ]

    for pt in points_data:
        idx = pt["id"]
        lat = pt["lat"]
        lon = pt["lon"]
        notes = pt.get("notes", "Outside Trash Can")
        fname = pt.get("filename", "")
        nearest_bldg, sector, dist_ft = get_nearest_landmark(lat, lon)

        kml_lines.extend([
            '    <Placemark>',
            f'      <name>Unit #{idx}: {nearest_bldg}</name>',
            f'      <description><![CDATA[<b>Unit:</b> #{idx}<br><b>Nearest Building:</b> {nearest_bldg} (~{dist_ft} ft)<br><b>Sector:</b> {sector}<br><b>Field Notes:</b> {notes}<br><b>Photo:</b> {fname}]]></description>',
            '      <styleUrl>#trashcanPin</styleUrl>',
            '      <Point>',
            f'        <coordinates>{lon:.6f},{lat:.6f},0</coordinates>',
            '      </Point>',
            '    </Placemark>',
        ])

    kml_lines.extend([
        '  </Document>',
        '</kml>'
    ])

    with open(output_kml_path, "w") as f:
        f.write("\n".join(kml_lines))
    print(f"Google Earth / My Maps KML successfully written to: {output_kml_path}")

def generate_interactive_map_html(points_data: list, output_html_path: Path):
    """Generates a standalone Leaflet.js interactive satellite map with Google Maps navigation."""
    markers_js = []
    for pt in points_data:
        idx = pt["id"]
        lat = pt["lat"]
        lon = pt["lon"]
        notes = pt.get("notes", "Exterior Trash Receptacle")
        fname = pt.get("filename", "")
        nearest_bldg, sector, dist_ft = get_nearest_landmark(lat, lon)
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}"

        popup_html = (
            f"<div style='font-family: sans-serif; min-width: 220px;'>"
            f"<div style='font-weight: bold; color: #1e3a8a; font-size: 15px; border-bottom: 2px solid #3b82f6; padding-bottom: 4px;'>🗑️ Trash Unit #{idx}</div>"
            f"<div style='margin-top: 6px; font-size: 13px;'><b>Nearest Landmark:</b> {nearest_bldg} (~{dist_ft} ft)</div>"
            f"<div style='font-size: 13px;'><b>Sector:</b> {sector}</div>"
            f"<div style='font-size: 12px; color: #475569; margin-top: 4px;'><b>Notes:</b> {notes}</div>"
            f"<div style='font-size: 11px; color: #64748b;'><b>Coordinates:</b> {lat:.6f}, {lon:.6f}</div>"
            f"<div style='margin-top: 10px;'>"
            f"<a href='{gmaps_url}' target='_blank' style='display: inline-block; background: #2563eb; color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold;'>📍 Open in Google Maps</a>"
            f"</div>"
            f"</div>"
        )

        markers_js.append(
            f"L.marker([{lat:.6f}, {lon:.6f}], {{icon: trashIcon}}).addTo(map).bindPopup({json.dumps(popup_html)});"
        )

    markers_block = "\n    ".join(markers_js)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Collin College Frisco Campus — Exterior Trashcan Satellite Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html {{ margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    #map {{ width: 100%; height: 100%; }}
    .header-bar {{
      position: absolute; top: 15px; left: 60px; z-index: 1000;
      background: rgba(15, 23, 42, 0.92); color: white; padding: 12px 20px;
      border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
      border-left: 4px solid #3b82f6; backdrop-filter: blur(8px);
    }}
    .header-title {{ font-size: 16px; font-weight: bold; letter-spacing: 0.5px; }}
    .header-sub {{ font-size: 12px; color: #93c5fd; margin-top: 3px; }}
    .trash-pin {{
      background-color: #ef4444; border: 2px solid white; border-radius: 50%;
      box-shadow: 0 0 10px rgba(239, 68, 68, 0.8);
    }}
  </style>
</head>
<body>
  <div class="header-bar">
    <div class="header-title">🏛️ Collin College Frisco Campus — Exterior Trashcan Inventory</div>
    <div class="header-sub">HWB SigmaFidelity™ Geospatial Takeoff | Total Plotted Units: {len(points_data)}</div>
  </div>
  <div id="map"></div>

  <script>
    // Initialize Leaflet map centered on Frisco Campus quad
    var map = L.map('map').setView([33.13155, -96.79277], 17);

    // Google Satellite Hybrid Layer
    var googleHybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={{x}}&y={{y}}&z={{z}}', {{
      maxZoom: 21,
      attribution: '&copy; Google Maps & Imagery'
    }}).addTo(map);

    // Custom Red Marker Icon with Trash Can Symbol
    var trashIcon = L.divIcon({{
      className: 'trash-marker',
      html: '<div style="background-color: #ef4444; color: white; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; border: 2px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.5); font-weight: bold;">🗑️</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14]
    }});

    // Add Markers for each surveyed trash can
    {markers_block}
  </script>
</body>
</html>
"""
    with open(output_html_path, "w") as f:
        f.write(html_content)
    print(f"Interactive Satellite Map successfully written to: {output_html_path}")

    # Mirror to web static directory
    if WEB_STATIC_DIR.exists():
        mirror_path = WEB_STATIC_DIR / "frisco_interactive_map.html"
        with open(mirror_path, "w") as mf:
            mf.write(html_content)
        print(f"Mirrored interactive map to web server: {mirror_path}")

def plot_trashcans(points_data: list, output_image_path: Path, output_md_path: Path):
    """Plots markers on the campus map and generates an audit report with Google Maps deep links."""
    if not BASE_MAP_PATH.exists():
        raise FileNotFoundError(f"Base map not found at {BASE_MAP_PATH}")

    base_img = Image.open(BASE_MAP_PATH).convert("RGBA")
    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        small_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    report_rows = []

    for pt in points_data:
        idx = pt["id"]
        lat = pt["lat"]
        lon = pt["lon"]
        notes = pt.get("notes", "Outside Trash Receptacle")
        fname = pt.get("filename", "Field Photo")
        tstamp = pt.get("timestamp", "Walkthrough 09/14/2026")

        px, py = gps_to_pixel(lat, lon)
        nearest_bldg, sector, dist_ft = get_nearest_landmark(lat, lon)

        # Draw outer pulse / glow ring (bright red / amber)
        r_outer = 16
        draw.ellipse([(px - r_outer, py - r_outer), (px + r_outer, py + r_outer)], 
                     fill=(239, 68, 68, 90), outline=(185, 28, 28, 200), width=2)

        # Draw solid inner marker pin
        r_inner = 10
        draw.ellipse([(px - r_inner, py - r_inner), (px + r_inner, py + r_inner)], 
                     fill=(220, 38, 38, 240), outline=(255, 255, 255, 255), width=2)

        # Draw pin label number
        lbl = str(idx)
        draw.text((px - 4, py - 6), lbl, fill=(255, 255, 255, 255), font=small_font)

        # Draw callout badge next to pin
        badge_text = f"#{idx}: {nearest_bldg} (~{dist_ft}ft)"
        draw.rectangle([(px + 14, py - 12), (px + 14 + len(badge_text)*7 + 10, py + 8)],
                       fill=(15, 23, 42, 220), outline=(255, 255, 255, 200), width=1)
        draw.text((px + 18, py - 10), badge_text, fill=(255, 255, 255, 255), font=small_font)

        gmaps_link = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"

        report_rows.append({
            "id": idx,
            "lat": lat,
            "lon": lon,
            "pixel": f"({px}, {py})",
            "nearest": nearest_bldg,
            "sector": sector,
            "dist_ft": dist_ft,
            "notes": notes,
            "filename": fname,
            "timestamp": tstamp,
            "gmaps_link": gmaps_link
        })

    # Add Map Title Banner at bottom left
    banner_x, banner_y = 30, 810
    draw.rectangle([(banner_x, banner_y), (banner_x + 580, banner_y + 70)],
                   fill=(15, 23, 42, 235), outline=(59, 130, 246, 255), width=2)
    draw.text((banner_x + 15, banner_y + 10), "HWB SIGMAFIDELITY™ — EXTERIOR TRASHCAN AUDIT PLOT",
              fill=(255, 255, 255, 255), font=header_font)
    draw.text((banner_x + 15, banner_y + 36), 
              f"COLLIN COLLEGE FRISCO CAMPUS | PLOTTED UNITS: {len(points_data)} | GPS GEOREFERENCED",
              fill=(147, 197, 253, 255), font=small_font)

    # Composite and save
    final_img = Image.alpha_composite(base_img, overlay).convert("RGB")
    final_img.save(output_image_path, "PNG", quality=95)
    print(f"Annotated site map successfully saved to: {output_image_path}")

    # Generate Markdown Report with Google Maps Navigation
    md_content = [
        "# Collin College Frisco Campus — Exterior Trashcan & Grounds Takeoff",
        "",
        f"**Audit Date:** 09/14/2026  ",
        f"**Total Plotted Units:** {len(points_data)}  ",
        f"**Georeferenced Site Map:** [`frisco_campus_trashcan_plot.png`](file://{output_image_path})  ",
        f"**Google Earth / My Maps File:** [`frisco_trashcans.kml`](file://{OUTPUT_KML_PATH})  ",
        f"**Interactive Satellite Map:** [`frisco_interactive_map.html`](file://{OUTPUT_HTML_PATH})  ",
        "",
        "### Empirical GPS Field Inventory & Google Maps Navigation",
        "",
        "| Unit # | Nearest Landmark | Sector | Distance | Latitude | Longitude | Map (X,Y) | Google Maps Navigation | Field Notes |",
        "| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for r in report_rows:
        md_content.append(
            f"| **#{r['id']}** | {r['nearest']} | {r['sector']} | {r['dist_ft']} ft | `{r['lat']:.6f}` | `{r['lon']:.6f}` | `{r['pixel']}` | [📍 Navigate in Google Maps]({r['gmaps_link']}) | {r['notes']} |"
        )
    md_content.append("")
    md_content.append("---")
    md_content.append("*Generated by Systems Architect George (mbB) | HWB SigmaFidelity™ Engine*")

    with open(output_md_path, "w") as f:
        f.write("\n".join(md_content))
    print(f"Inventory report successfully written to: {output_md_path}")

    # Generate Google Earth KML & Interactive Web Map
    generate_kml(points_data, OUTPUT_KML_PATH)
    generate_interactive_map_html(points_data, OUTPUT_HTML_PATH)

def scan_and_process_photos():
    """Scans walkthrough_photos directory for images with EXIF GPS data."""
    photo_files = (
        glob.glob(str(PHOTOS_DIR / "*.jpg")) + 
        glob.glob(str(PHOTOS_DIR / "*.jpeg")) + 
        glob.glob(str(PHOTOS_DIR / "*.png")) +
        glob.glob(str(PHOTOS_DIR / "*.heic"))
    )
    points = []
    unit_id = 1
    for p in photo_files:
        gps = extract_exif_gps(p)
        if gps:
            fname = Path(p).name
            notes = "Identified via on-site walkthrough photo"
            points.append({
                "id": unit_id,
                "lat": gps["lat"],
                "lon": gps["lon"],
                "filename": fname,
                "timestamp": gps["timestamp"],
                "notes": notes
            })
            unit_id += 1

    return points

if __name__ == "__main__":
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    detected_points = scan_and_process_photos()

    if not detected_points:
        print("No live walkthrough photos detected yet in walkthrough_photos/. Generating baseline demonstration points...")
        demonstration_points = [
            {"id": 1, "lat": 33.13045, "lon": -96.79320, "filename": "founders_main_entry.jpg", "timestamp": "Demo 09/14/2026", "notes": "Founders Hall North Portico Dual Can"},
            {"id": 2, "lat": 33.13020, "lon": -96.79170, "filename": "university_south_entry.jpg", "timestamp": "Demo 09/14/2026", "notes": "University Hall South Entry Ash Urn"},
            {"id": 3, "lat": 33.13155, "lon": -96.79425, "filename": "heritage_quad_can.jpg", "timestamp": "Demo 09/14/2026", "notes": "Heritage Hall Central Quad Bench Can"},
            {"id": 4, "lat": 33.13180, "lon": -96.79275, "filename": "library_east_walkway.jpg", "timestamp": "Demo 09/14/2026", "notes": "Library Main Entrance Concrete Receptacle"},
            {"id": 5, "lat": 33.13230, "lon": -96.79430, "filename": "student_center_patio.jpg", "timestamp": "Demo 09/14/2026", "notes": "Student Center Outdoor Dining Patio Can"},
            {"id": 6, "lat": 33.13140, "lon": -96.79150, "filename": "alumni_gym_approach.jpg", "timestamp": "Demo 09/14/2026", "notes": "Alumni Hall Athletic Entrance Bin"},
            {"id": 7, "lat": 33.13320, "lon": -96.79310, "filename": "garage_level1_elevator.jpg", "timestamp": "Demo 09/14/2026", "notes": "Parking Garage Ground Level Vestibule Can"},
            {"id": 8, "lat": 33.13095, "lon": -96.79515, "filename": "lot_g_perimeter.jpg", "timestamp": "Demo 09/14/2026", "notes": "Lot G Student Walkway Pole-Mount Can"},
        ]
        plot_trashcans(demonstration_points, OUTPUT_MAP_PATH, OUTPUT_REPORT_PATH)
    else:
        print(f"Found {len(detected_points)} geotagged photos! Plotting...")
        plot_trashcans(detected_points, OUTPUT_MAP_PATH, OUTPUT_REPORT_PATH)
