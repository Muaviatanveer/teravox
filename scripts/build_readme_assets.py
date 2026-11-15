"""
TERRAVOX — NASA Mission README Asset Generator
Generates high-definition cinematic visuals, animations, and composites for the GitHub README.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ASSETS_DIR = Path("assets/readme")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
RASTERS_DIR = Path("outputs/rasters")

# Colors
COLOR_BG = (5, 7, 13)
COLOR_NAVY = (11, 20, 37)
COLOR_NASA_BLUE = (11, 61, 145)
COLOR_ELECTRIC_BLUE = (56, 189, 248)
COLOR_WHITE = (248, 250, 252)
COLOR_MUTED = (148, 163, 184)
COLOR_GOLD = (234, 179, 8)
COLOR_RED = (252, 61, 33)


def get_font(size: int = 14, bold: bool = False):
    """Fallback font loader using macOS system fonts."""
    candidates = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/System/Library/Fonts/Geneva.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def generate_mission_patch():
    """Generates a circular NASA-style TERRAVOX Mission Patch."""
    size = 600
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r_outer = 280
    r_inner = 250

    # Outer border gold ring
    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=(11, 20, 37, 255), outline=(234, 179, 8, 255), width=6)
    draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=(5, 10, 24, 255), outline=(56, 189, 248, 255), width=3)

    # Starfield inside patch
    np.random.seed(42)
    for _ in range(80):
        sx = int(cx + (np.random.rand() - 0.5) * 2 * (r_inner - 20))
        sy = int(cy + (np.random.rand() - 0.5) * 2 * (r_inner - 20))
        if math.hypot(sx - cx, sy - cy) < r_inner - 15:
            brightness = np.random.randint(140, 255)
            rad = np.random.choice([1, 1, 1, 2])
            draw.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=(brightness, brightness, 255, 220))

    # Stylized Earth in center
    r_earth = 110
    draw.ellipse([cx - r_earth - 6, cy - r_earth - 6, cx + r_earth + 6, cy + r_earth + 6], fill=(56, 189, 248, 40))
    draw.ellipse([cx - r_earth, cy - r_earth, cx + r_earth, cy + r_earth], fill=(11, 61, 145, 255), outline=(56, 189, 248, 220), width=3)

    # Stylized continent continents inside Earth
    draw.polygon([(cx - 70, cy - 30), (cx - 20, cy - 60), (cx + 30, cy - 40), (cx - 10, cy + 10)], fill=(20, 110, 75, 220))
    draw.polygon([(cx - 30, cy + 20), (cx + 40, cy + 10), (cx + 60, cy + 60), (cx + 10, cy + 70)], fill=(20, 110, 75, 220))
    draw.polygon([(cx + 20, cy - 20), (cx + 70, cy - 50), (cx + 80, cy - 10), (cx + 50, cy + 10)], fill=(20, 110, 75, 220))

    # Radar wavefront arcs
    for arc_r in range(70, 160, 25):
        draw.arc([cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r], start=-60, end=40, fill=(56, 189, 248, 160), width=2)

    # Orbital vector ellipse
    orbit_box = [cx - 230, cy - 90, cx + 230, cy + 90]
    draw.arc(orbit_box, start=160, end=380, fill=(252, 61, 33, 230), width=4)

    # NISAR Satellite icon on orbit
    sat_x = cx + 180
    sat_y = cy - 45
    draw.rectangle([sat_x - 12, sat_y - 8, sat_x + 12, sat_y + 8], fill=(234, 179, 8, 255), outline=(255, 255, 255, 255), width=1)
    draw.rectangle([sat_x - 30, sat_y - 4, sat_x - 14, sat_y + 4], fill=(56, 189, 248, 220))
    draw.rectangle([sat_x + 14, sat_y - 4, sat_x + 30, sat_y + 4], fill=(56, 189, 248, 220))

    # Mission patch typography
    f_title = get_font(38, bold=True)
    f_sub = get_font(15, bold=True)
    f_ring = get_font(13, bold=True)

    # Center banner
    banner_w = 340
    banner_h = 56
    draw.rectangle([cx - banner_w // 2, cy + 75, cx + banner_w // 2, cy + 75 + banner_h], fill=(11, 20, 37, 240), outline=(56, 189, 248, 255), width=2)
    draw.text((cx, cy + 95), "TERRAVOX", fill=(255, 255, 255, 255), font=f_title, anchor="mm")
    draw.text((cx, cy + 145), "UNDERSTAND THE CHANGING EARTH", fill=(56, 189, 248, 255), font=f_sub, anchor="mm")

    # Top ring text
    draw.text((cx, cy - 262), "★ NASA SPACE APPS CHALLENGE 2026 ★", fill=(234, 179, 8, 255), font=f_ring, anchor="mm")
    draw.text((cx, cy + 262), "• NISAR L2 RADAR OBSERVATION SYSTEM •", fill=(148, 163, 184, 255), font=f_ring, anchor="mm")

    out_png = ASSETS_DIR / "terravox_mission_patch.png"
    img.save(out_png, "PNG")
    print(f"Saved: {out_png}")


def generate_hero_banner():
    """Generates a high-quality 24-frame looping animated GIF hero banner."""
    w, h = 1100, 420
    frames = []
    num_frames = 24

    # Background starfield
    np.random.seed(101)
    stars = []
    for _ in range(120):
        sx = np.random.randint(0, w)
        sy = np.random.randint(0, h)
        rad = np.random.choice([1, 1, 1, 2])
        base_bright = np.random.randint(120, 240)
        phase = np.random.rand() * 2 * math.pi
        stars.append((sx, sy, rad, base_bright, phase))

    for frame_idx in range(num_frames):
        img = Image.new("RGB", (w, h), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Draw deep space radial glow on left (Sun) and right (Earth)
        # Twinkling stars
        for sx, sy, rad, base_b, phase in stars:
            b = int(base_b + 35 * math.sin(phase + (frame_idx / num_frames) * 2 * math.pi))
            b = max(60, min(255, b))
            draw.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=(b, b, min(255, b + 25)))

        # Sun on Left
        sun_x, sun_y = 120, h // 2
        for glow_r in range(110, 45, -10):
            alpha = int(45 * (1 - (glow_r - 45) / 65))
            draw.ellipse([sun_x - glow_r, sun_y - glow_r, sun_x + glow_r, sun_y + glow_r], fill=(234, 179, 8))
        draw.ellipse([sun_x - 45, sun_y - 45, sun_x + 45, sun_y + 45], fill=(255, 230, 130), outline=(255, 255, 255), width=2)

        # Planetary orbital arcs crossing toward Earth
        for r_orbit in [220, 340, 480, 640]:
            draw.arc([sun_x - r_orbit, sun_y - r_orbit * 0.45, sun_x + r_orbit, sun_y + r_orbit * 0.45], start=-55, end=55, fill=(40, 60, 95), width=1)

        # Earth on Right
        earth_x, earth_y = w - 190, h // 2 + 10
        r_earth = 75

        # Atmospheric halo
        for a_r in range(r_earth + 22, r_earth, -3):
            draw.ellipse([earth_x - a_r, earth_y - a_r, earth_x + a_r, earth_y + a_r], outline=(56, 189, 248), width=1)

        # Earth globe
        draw.ellipse([earth_x - r_earth, earth_y - r_earth, earth_x + r_earth, earth_y + r_earth], fill=(15, 65, 140), outline=(56, 189, 248), width=2)

        # Rotating cloud / continent features
        rot_offset = (frame_idx / num_frames) * 50
        draw.ellipse([earth_x - 50 + rot_offset - 25, earth_y - 35, earth_x + 10 + rot_offset - 25, earth_y + 10], fill=(30, 120, 80))
        draw.ellipse([earth_x - 10 + rot_offset - 25, earth_y - 10, earth_x + 45 + rot_offset - 25, earth_y + 40], fill=(30, 120, 80))

        # Moon orbiting Earth
        moon_angle = (frame_idx / num_frames) * 2 * math.pi
        moon_dist_x = 135
        moon_dist_y = 55
        moon_x = int(earth_x + moon_dist_x * math.cos(moon_angle))
        moon_y = int(earth_y + moon_dist_y * math.sin(moon_angle))
        draw.ellipse([moon_x - 7, moon_y - 7, moon_x + 7, moon_y + 7], fill=(210, 215, 225), outline=(255, 255, 255), width=1)

        # NISAR Satellite in Orbit pulsing radar beam
        sat_angle = (frame_idx / num_frames) * 2 * math.pi + 1.2
        sat_x = int(earth_x + 95 * math.cos(sat_angle))
        sat_y = int(earth_y + 95 * math.sin(sat_angle))
        draw.ellipse([sat_x - 5, sat_y - 5, sat_x + 5, sat_y + 5], fill=(234, 179, 8))
        # Radar pulse to Earth
        pulse_alpha = int(180 + 70 * math.sin(frame_idx * 0.8))
        draw.line([sat_x, sat_y, earth_x, earth_y], fill=(56, 189, 248), width=1)

        # Mission Title & Telemetry Overlay (Center-Left)
        f_badge = get_font(12, bold=True)
        f_main = get_font(46, bold=True)
        f_sub = get_font(16, bold=True)
        f_desc = get_font(13, bold=False)

        # Pill badge
        draw.rounded_rectangle([250, 48, 640, 78], radius=8, fill=(11, 20, 37), outline=(56, 189, 248), width=1)
        draw.text((445, 63), "🛰️ NASA SPACE APPS CHALLENGE 2026", fill=(56, 189, 248), font=f_badge, anchor="mm")

        # Main Title
        draw.text((250, 95), "TERRAVOX", fill=(248, 250, 252), font=f_main)

        # Subtitle
        draw.text((252, 160), "Understand the Changing Earth", fill=(56, 189, 248), font=f_sub)

        # Description lines
        draw.text((252, 200), "Autonomous Earth Surface Intelligence System", fill=(255, 255, 255), font=get_font(14, bold=True))
        draw.text((252, 226), "Dancing with the SARs · NASA–ISRO NISAR Mission", fill=(148, 163, 184), font=f_desc)
        draw.text((252, 250), "L-Band Level-2 (GCOV & GUNW) Radar Ingestion & UARI Trust Engine", fill=(148, 163, 184), font=f_desc)

        # Telemetry metrics row at bottom
        metrics_y = 330
        draw.rectangle([250, metrics_y, 880, metrics_y + 55], fill=(11, 20, 37), outline=(40, 60, 95), width=1)
        draw.text((270, metrics_y + 16), "PUNJAB FLOOD BASIN", fill=(56, 189, 248), font=get_font(11, bold=True))
        draw.text((270, metrics_y + 34), "17,669 Ha Inundated · GCOV Track 12", fill=(248, 250, 252), font=get_font(11))

        draw.text((500, metrics_y + 16), "QUETTA VALLEY SUBSIDENCE", fill=(252, 61, 33), font=get_font(11, bold=True))
        draw.text((500, metrics_y + 34), "-32.2 cm InSAR Sink · GUNW Track 41", fill=(248, 250, 252), font=get_font(11))

        draw.text((750, metrics_y + 16), "SCIENTIFIC UARI TRUST", fill=(34, 197, 94), font=get_font(11, bold=True))
        draw.text((750, metrics_y + 34), "CRLB & Log-Speckle Evaluated", fill=(248, 250, 252), font=get_font(11))

        frames.append(img)

    out_gif = ASSETS_DIR / "hero_banner.gif"
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    print(f"Saved: {out_gif}")


def generate_solar_system_gif():
    """Generates an animated solar system visual showing Sun, 8 planets, and Earth target reticle."""
    w, h = 880, 440
    frames = []
    num_frames = 24
    cx, cy = w // 2, h // 2

    planets = [
        ("Mercury", 55, 0.42, 3, (160, 160, 165), 0.08),
        ("Venus", 90, 0.42, 5, (225, 190, 140), 0.05),
        ("Earth", 135, 0.42, 6, (56, 189, 248), 0.035),
        ("Mars", 175, 0.42, 4, (230, 95, 60), 0.025),
        ("Jupiter", 230, 0.42, 12, (210, 165, 120), 0.015),
        ("Saturn", 285, 0.42, 9, (230, 205, 150), 0.010),
        ("Uranus", 340, 0.42, 7, (130, 215, 230), 0.007),
        ("Neptune", 390, 0.42, 7, (70, 120, 240), 0.005),
    ]

    for frame_idx in range(num_frames):
        img = Image.new("RGB", (w, h), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Background stars
        np.random.seed(77)
        for _ in range(80):
            sx = np.random.randint(0, w)
            sy = np.random.randint(0, h)
            draw.point((sx, sy), fill=(160, 175, 200))

        # Sun at center
        for r in range(45, 15, -6):
            draw.ellipse([cx - r, cy - r * 0.42, cx + r, cy + r * 0.42], fill=(234, 179, 8))
        draw.ellipse([cx - 16, cy - 16 * 0.42, cx + 16, cy + 16 * 0.42], fill=(255, 240, 180))

        # Draw orbital ellipses and planets
        for name, a, b_factor, p_size, color, speed in planets:
            b = int(a * b_factor)
            # Ellipse orbit line
            draw.ellipse([cx - a, cy - b, cx + a, cy + b], outline=(30, 45, 70), width=1)

            # Planet position
            theta = (frame_idx * speed * 2 * math.pi) + (hash(name) % 10)
            px = int(cx + a * math.cos(theta))
            py = int(cy + b * math.sin(theta))

            # Planet circle
            draw.ellipse([px - p_size, py - p_size, px + p_size, py + p_size], fill=color)

            # Highlight Earth
            if name == "Earth":
                reticle_r = 16
                draw.arc([px - reticle_r, py - reticle_r, px + reticle_r, py + reticle_r], start=0, end=360, fill=(56, 189, 248), width=1)
                draw.line([px - reticle_r - 4, py, px - reticle_r + 2, py], fill=(56, 189, 248), width=2)
                draw.line([px + reticle_r - 2, py, px + reticle_r + 4, py], fill=(56, 189, 248), width=2)
                draw.text((px + 18, py - 9), "EARTH [NISAR MISSION TARGET]", fill=(56, 189, 248), font=get_font(10, bold=True))

        # Top banner label
        draw.text((cx, 25), "SOLAR SYSTEM OBSERVATION CONTEXT · HELIOCENTRIC ORBITAL PLANE", fill=(148, 163, 184), font=get_font(12, bold=True), anchor="mm")
        draw.text((cx, h - 22), "8 Planetary Orbits · Sun Center · Target Planet Earth in NISAR Polar L-Band Orbit", fill=(56, 189, 248), font=get_font(11), anchor="mm")

        frames.append(img)

    out_gif = ASSETS_DIR / "solar_system_orbits.gif"
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    print(f"Saved: {out_gif}")


def generate_punjab_comparison_panel():
    """Builds a high-resolution 3-panel scientific comparison for Punjab Flood Plains."""
    f_before = RASTERS_DIR / "punjab_before_sar.png"
    f_after = RASTERS_DIR / "punjab_after_sar.png"
    f_change = RASTERS_DIR / "punjab_flood_overlay.png"

    if not (f_before.exists() and f_after.exists() and f_change.exists()):
        print("Skipping Punjab panel: raster pngs missing.")
        return

    im_b = Image.open(f_before).convert("RGB").resize((380, 380))
    im_a = Image.open(f_after).convert("RGB").resize((380, 380))
    im_c = Image.open(f_change).convert("RGB").resize((380, 380))

    canvas_w = 380 * 3 + 40
    canvas_h = 380 + 130
    panel = Image.new("RGB", (canvas_w, canvas_h), COLOR_NAVY)
    draw = ImageDraw.Draw(panel)

    # Title header
    f_h = get_font(15, bold=True)
    f_sub = get_font(12)
    draw.text((20, 16), "PUNJAB FLOOD PLAINS (INDUS–CHENAB CORRIDOR) · NISAR LEVEL-2 GCOV OBSERVED", fill=COLOR_WHITE, font=f_h)
    draw.text((20, 38), "12-Day Orbital Repeat Pass · Track 012 · Frame 017 · 70.60°E–71.60°E, 29.60°N–30.60°N", fill=COLOR_ELECTRIC_BLUE, font=f_sub)

    # Paste 3 images
    y_img = 62
    panel.paste(im_b, (15, y_img))
    panel.paste(im_a, (15 + 380 + 10, y_img))
    panel.paste(im_c, (15 + (380 + 10) * 2, y_img))

    # Panel captions
    f_cap = get_font(12, bold=True)
    draw.text((15 + 190, y_img + 395), "PRE-EVENT: Aug 14, 2026 (HH)", fill=COLOR_WHITE, font=f_cap, anchor="mm")
    draw.text((15 + 380 + 10 + 190, y_img + 395), "POST-EVENT: Aug 26, 2026 (HH)", fill=COLOR_WHITE, font=f_cap, anchor="mm")
    draw.text((15 + (380 + 10) * 2 + 190, y_img + 395), "EXTRACTED INUNDATION (CYAN)", fill=COLOR_ELECTRIC_BLUE, font=f_cap, anchor="mm")

    # Bottom metric bar
    y_bar = y_img + 412
    draw.rectangle([15, y_bar, canvas_w - 15, y_bar + 25], fill=(5, 10, 24))
    draw.text((30, y_bar + 6), "MEASUREMENT: Δγ⁰ = -5.2 dB to -18.2 dB", fill=(56, 189, 248), font=f_sub)
    draw.text((450, y_bar + 6), "SURFACE IMPACT: 17,669.1 Hectares Inundated", fill=COLOR_WHITE, font=f_sub)
    draw.text((860, y_bar + 6), "UARI TRUST: ±2.68 dB (1σ Log-Speckle)", fill=(34, 197, 94), font=f_sub)

    out_p = ASSETS_DIR / "punjab_sar_comparison.png"
    panel.save(out_p, "PNG")
    print(f"Saved: {out_p}")


def generate_quetta_comparison_panel():
    """Builds a high-resolution 3-panel scientific comparison for Quetta–Mastung Valley."""
    f_before = RASTERS_DIR / "quetta_before_sar.png"
    f_after = RASTERS_DIR / "quetta_after_sar.png"
    f_change = RASTERS_DIR / "quetta_deformation_overlay.png"

    if not (f_before.exists() and f_after.exists() and f_change.exists()):
        print("Skipping Quetta panel: raster pngs missing.")
        return

    im_b = Image.open(f_before).convert("RGB").resize((380, 380))
    im_a = Image.open(f_after).convert("RGB").resize((380, 380))
    im_c = Image.open(f_change).convert("RGB").resize((380, 380))

    canvas_w = 380 * 3 + 40
    canvas_h = 380 + 130
    panel = Image.new("RGB", (canvas_w, canvas_h), COLOR_NAVY)
    draw = ImageDraw.Draw(panel)

    # Title header
    f_h = get_font(15, bold=True)
    f_sub = get_font(12)
    draw.text((20, 16), "QUETTA–MASTUNG VALLEY · NISAR LEVEL-2 GUNW INTERFEROMETRIC DISPLACEMENT", fill=COLOR_WHITE, font=f_h)
    draw.text((20, 38), "12-Day Interferometric Pair · Track 041 · Frame 017 · 66.45°E–67.35°E, 29.65°N–30.45°N", fill=(252, 61, 33), font=f_sub)

    # Paste 3 images
    y_img = 62
    panel.paste(im_b, (15, y_img))
    panel.paste(im_a, (15 + 380 + 10, y_img))
    panel.paste(im_c, (15 + (380 + 10) * 2, y_img))

    # Panel captions
    f_cap = get_font(12, bold=True)
    draw.text((15 + 190, y_img + 395), "COHERENCE MAP (γ = 0.68)", fill=COLOR_WHITE, font=f_cap, anchor="mm")
    draw.text((15 + 380 + 10 + 190, y_img + 395), "WRAPPED INTERFEROGRAM FRINGES", fill=COLOR_WHITE, font=f_cap, anchor="mm")
    draw.text((15 + (380 + 10) * 2 + 190, y_img + 395), "UNWRAPPED SUBSIDENCE BOWL (RED)", fill=(252, 61, 33), font=f_cap, anchor="mm")

    # Bottom metric bar
    y_bar = y_img + 412
    draw.rectangle([15, y_bar, canvas_w - 15, y_bar + 25], fill=(5, 10, 24))
    draw.text((30, y_bar + 6), "PEAK DEFORMATION: -322.5 mm (-32.2 cm LOS)", fill=(252, 61, 33), font=f_sub)
    draw.text((450, y_bar + 6), "COHERENT COVERAGE: 88.1% Valid (ConnComp > 0)", fill=COLOR_WHITE, font=f_sub)
    draw.text((860, y_bar + 6), "UARI TRUST: ±24.7 mm (Cramér-Rao Bound)", fill=(34, 197, 94), font=f_sub)

    out_p = ASSETS_DIR / "quetta_sar_comparison.png"
    panel.save(out_p, "PNG")
    print(f"Saved: {out_p}")


def generate_architecture_diagram():
    """Generates an aerospace-styled scientific architecture flow diagram."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 520" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020408" />
      <stop offset="100%" stop-color="#0B1425" />
    </linearGradient>
    <linearGradient id="blueGlow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0B3D91" />
      <stop offset="100%" stop-color="#38BDF8" />
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#0B1322" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect width="1100" height="520" fill="url(#bgGrad)" rx="14" stroke="#1E293B" stroke-width="2"/>

  <!-- Telemetry Header -->
  <text x="35" y="42" fill="#38BDF8" font-family="'SF Pro Display', -apple-system, sans-serif" font-size="12" font-weight="800" letter-spacing="2">TERRAVOX SCIENTIFIC PIPELINE &amp; SYSTEM ARCHITECTURE</text>
  <text x="35" y="66" fill="#F8FAFC" font-family="'SF Pro Display', -apple-system, sans-serif" font-size="22" font-weight="900">End-to-End NISAR Level-2 Radar Ingestion to 3D Earth Intelligence</text>

  <!-- Flow Arrows (Connecting paths) -->
  <path d="M 220 180 L 260 180" stroke="#38BDF8" stroke-width="3" marker-end="url(#arrow)" filter="url(#glow)"/>
  <path d="M 470 180 L 510 180" stroke="#38BDF8" stroke-width="3" filter="url(#glow)"/>
  <path d="M 720 180 L 760 180" stroke="#38BDF8" stroke-width="3" filter="url(#glow)"/>
  <path d="M 970 180 L 1010 180" stroke="#38BDF8" stroke-width="3" filter="url(#glow)"/>

  <!-- Stage 1: Space Segment -->
  <g transform="translate(35, 100)">
    <rect width="190" height="370" fill="url(#cardGrad)" rx="10" stroke="#38BDF8" stroke-width="1.5"/>
    <rect x="0" y="0" width="190" height="34" fill="#0B3D91" rx="10"/>
    <text x="95" y="22" fill="#FFFFFF" font-family="sans-serif" font-size="11" font-weight="800" text-anchor="middle">1. SPACE SEGMENT</text>
    <text x="95" y="70" fill="#38BDF8" font-family="sans-serif" font-size="34" text-anchor="middle">🛰️</text>
    <text x="95" y="105" fill="#F8FAFC" font-family="sans-serif" font-size="14" font-weight="800" text-anchor="middle">NASA-ISRO NISAR</text>
    <text x="95" y="125" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="middle">L-Band (1.25 GHz SAR)</text>

    <line x1="20" y1="145" x2="170" y2="145" stroke="#1E293B"/>

    <text x="20" y="170" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• 12-Day Exact Repeat</text>
    <text x="20" y="195" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Level-2 GCOV (RTC)</text>
    <text x="20" y="215" fill="#94A3B8" font-family="sans-serif" font-size="10">  Normalized Backscatter</text>
    <text x="20" y="245" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Level-2 GUNW</text>
    <text x="20" y="265" fill="#94A3B8" font-family="sans-serif" font-size="10">  Unwrapped InSAR Phase</text>
    <text x="20" y="295" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• 24 cm L-Band Radar</text>
    <text x="20" y="315" fill="#94A3B8" font-family="sans-serif" font-size="10">  Cloud/Smoke Penetrating</text>
    <text x="95" y="350" fill="#38BDF8" font-family="sans-serif" font-size="10" font-weight="800" text-anchor="middle">[747 km Sun-Synch Orbit]</text>
  </g>

  <!-- Stage 2: Ingestion & Subsetting -->
  <g transform="translate(250, 100)">
    <rect width="210" height="370" fill="url(#cardGrad)" rx="10" stroke="#1E293B" stroke-width="1.5"/>
    <rect x="0" y="0" width="210" height="34" fill="#1E293B" rx="10"/>
    <text x="105" y="22" fill="#38BDF8" font-family="sans-serif" font-size="11" font-weight="800" text-anchor="middle">2. INGESTION GATEWAY</text>
    <text x="105" y="70" fill="#38BDF8" font-family="sans-serif" font-size="34" text-anchor="middle">⚡</text>
    <text x="105" y="105" fill="#F8FAFC" font-family="sans-serif" font-size="14" font-weight="800" text-anchor="middle">NASA Earthdata Cloud</text>
    <text x="105" y="125" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="middle">ASF DAAC API + CMR</text>

    <line x1="20" y1="145" x2="190" y2="145" stroke="#1E293B"/>

    <text x="20" y="170" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Study Area Gate Verifier</text>
    <text x="20" y="190" fill="#94A3B8" font-family="sans-serif" font-size="10">  Track/Frame Compatibility</text>
    <text x="20" y="220" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• CachedRangeReader</text>
    <text x="20" y="240" fill="#94A3B8" font-family="sans-serif" font-size="10">  HTTP Range Byte Subsetting</text>
    <text x="20" y="270" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Stream 15–35 MB Chunks</text>
    <text x="20" y="290" fill="#94A3B8" font-family="sans-serif" font-size="10">  Bypasses 4 GB Full Download</text>
    <text x="20" y="320" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Filename Regex Parser</text>
    <text x="105" y="350" fill="#22C55E" font-family="sans-serif" font-size="10" font-weight="800" text-anchor="middle">[Authentic NASA URS Session]</text>
  </g>

  <!-- Stage 3: Science Engine -->
  <g transform="translate(485, 100)">
    <rect width="220" height="370" fill="url(#cardGrad)" rx="10" stroke="#38BDF8" stroke-width="2"/>
    <rect x="0" y="0" width="220" height="34" fill="#0B3D91" rx="10"/>
    <text x="110" y="22" fill="#FFFFFF" font-family="sans-serif" font-size="11" font-weight="800" text-anchor="middle">3. SCIENCE ENGINE &amp; UARI</text>
    <text x="110" y="70" fill="#38BDF8" font-family="sans-serif" font-size="34" text-anchor="middle">🔬</text>
    <text x="110" y="105" fill="#F8FAFC" font-family="sans-serif" font-size="14" font-weight="800" text-anchor="middle">Physics &amp; Uncertainty</text>
    <text x="110" y="125" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="middle">NumPy · SciPy · Rasterio</text>

    <line x1="20" y1="145" x2="200" y2="145" stroke="#1E293B"/>

    <text x="20" y="170" fill="#38BDF8" font-family="sans-serif" font-size="11" font-weight="700">• Pipeline A: GCOV</text>
    <text x="20" y="190" fill="#94A3B8" font-family="sans-serif" font-size="10">  Δγ⁰ = 10·log₁₀(γ₂/γ₁) dB</text>
    <text x="20" y="220" fill="#EF4444" font-family="sans-serif" font-size="11" font-weight="700">• Pipeline B: GUNW</text>
    <text x="20" y="240" fill="#94A3B8" font-family="sans-serif" font-size="10">  d_LOS = -(λ/4π)·Δφ mm</text>
    <text x="20" y="270" fill="#22C55E" font-family="sans-serif" font-size="11" font-weight="700">• UARI Trust Framework</text>
    <text x="20" y="290" fill="#94A3B8" font-family="sans-serif" font-size="10">  Cramér-Rao Lower Bound</text>
    <text x="20" y="320" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• APOF Multi-Res Fusion</text>
    <text x="110" y="350" fill="#38BDF8" font-family="sans-serif" font-size="10" font-weight="800" text-anchor="middle">[Strict Scientific Provenance]</text>
  </g>

  <!-- Stage 4: TerraMind Intelligence -->
  <g transform="translate(730, 100)">
    <rect width="210" height="370" fill="url(#cardGrad)" rx="10" stroke="#1E293B" stroke-width="1.5"/>
    <rect x="0" y="0" width="210" height="34" fill="#1E293B" rx="10"/>
    <text x="105" y="22" fill="#38BDF8" font-family="sans-serif" font-size="11" font-weight="800" text-anchor="middle">4. TERRAMIND AI</text>
    <text x="105" y="70" fill="#38BDF8" font-family="sans-serif" font-size="34" text-anchor="middle">🧠</text>
    <text x="105" y="105" fill="#F8FAFC" font-family="sans-serif" font-size="14" font-weight="800" text-anchor="middle">Spatial Anomalies &amp; MECA</text>
    <text x="105" y="125" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="middle">Gemini 3.8 Flash Cloud</text>

    <line x1="20" y1="145" x2="190" y2="145" stroke="#1E293B"/>

    <text x="20" y="170" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Connected-Components</text>
    <text x="20" y="190" fill="#94A3B8" font-family="sans-serif" font-size="10">  Cluster Area in Hectares</text>
    <text x="20" y="220" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Competing Hypotheses</text>
    <text x="20" y="240" fill="#94A3B8" font-family="sans-serif" font-size="10">  Multiple Physical Causes</text>
    <text x="20" y="270" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• 4-Part Earth Story</text>
    <text x="20" y="290" fill="#94A3B8" font-family="sans-serif" font-size="10">  Observations to Plain Prose</text>
    <text x="20" y="320" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="700">• Temporal Earth Memory</text>
    <text x="105" y="350" fill="#EAB308" font-family="sans-serif" font-size="10" font-weight="800" text-anchor="middle">[Never Hallucinates Radar]</text>
  </g>

  <!-- Stage 5: Mission Control Interface -->
  <g transform="translate(960, 100)">
    <rect width="115" height="370" fill="url(#cardGrad)" rx="10" stroke="#38BDF8" stroke-width="1.5"/>
    <rect x="0" y="0" width="115" height="34" fill="#0B3D91" rx="10"/>
    <text x="57" y="22" fill="#FFFFFF" font-family="sans-serif" font-size="10" font-weight="800" text-anchor="middle">5. WORKSTATION</text>
    <text x="57" y="70" fill="#38BDF8" font-family="sans-serif" font-size="28" text-anchor="middle">🖥️</text>
    <text x="57" y="105" fill="#F8FAFC" font-family="sans-serif" font-size="11" font-weight="800" text-anchor="middle">3D Earth</text>
    <text x="57" y="125" fill="#94A3B8" font-family="sans-serif" font-size="9" text-anchor="middle">Three.js</text>

    <line x1="10" y1="145" x2="105" y2="145" stroke="#1E293B"/>

    <text x="12" y="170" fill="#E2E8F0" font-family="sans-serif" font-size="9" font-weight="700">• 3D Solar</text>
    <text x="12" y="195" fill="#E2E8F0" font-family="sans-serif" font-size="9" font-weight="700">• MapLibre</text>
    <text x="12" y="220" fill="#E2E8F0" font-family="sans-serif" font-size="9" font-weight="700">• Microscope</text>
    <text x="12" y="245" fill="#E2E8F0" font-family="sans-serif" font-size="9" font-weight="700">• Trust HUD</text>
    <text x="12" y="270" fill="#E2E8F0" font-family="sans-serif" font-size="9" font-weight="700">• Split Swipe</text>
    <text x="12" y="295" fill="#E2E8F0" font-family="sans-serif" font-size="9" font-weight="700">• PDF Export</text>
    <text x="57" y="350" fill="#38BDF8" font-family="sans-serif" font-size="9" font-weight="800" text-anchor="middle">[60 FPS GL]</text>
  </g>
</svg>"""
    out_svg = ASSETS_DIR / "system_architecture.svg"
    out_svg.write_text(svg)
    print(f"Saved: {out_svg}")


def generate_earth_return_footer():
    """Generates the cinematic 'Return to Earth' closing visual banner."""
    w, h = 1100, 300
    img = Image.new("RGB", (w, h), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Stars
    np.random.seed(999)
    for _ in range(140):
        sx = np.random.randint(0, w)
        sy = np.random.randint(0, h)
        b = np.random.randint(100, 255)
        draw.point((sx, sy), fill=(b, b, min(255, b + 30)))

    # Earth limb curve rising from bottom
    earth_cx = w // 2
    earth_cy = h + 800
    earth_r = 920

    # Atmospheric glow layers
    for glow in range(25, 0, -3):
        r_g = earth_r + glow
        draw.ellipse([earth_cx - r_g, earth_cy - r_g, earth_cx + r_g, earth_cy + r_g], outline=(56, 189, 248), width=2)

    # Earth disc
    draw.ellipse([earth_cx - earth_r, earth_cy - earth_r, earth_cx + earth_r, earth_cy + earth_r], fill=(11, 45, 105), outline=(56, 189, 248), width=3)

    # Subtle cloud arcs
    draw.arc([earth_cx - 700, earth_cy - 900, earth_cx + 700, earth_cy - 700], start=210, end=330, fill=(200, 220, 245), width=4)
    draw.arc([earth_cx - 500, earth_cy - 880, earth_cx + 500, earth_cy - 720], start=230, end=310, fill=(180, 210, 240), width=6)

    # Mission closing text
    draw.text((w // 2, 60), "TERRAVOX", fill=COLOR_WHITE, font=get_font(34, bold=True), anchor="mm")
    draw.text((w // 2, 98), "Understand the Changing Earth.", fill=(56, 189, 248), font=get_font(18, bold=True), anchor="mm")
    draw.text((w // 2, 135), "NASA Space Apps Challenge 2026 · Challenge: Dancing with the SARs", fill=(203, 213, 225), font=get_font(13), anchor="mm")
    draw.text((w // 2, 160), "NASA–ISRO Synthetic Aperture Radar (NISAR) Mission", fill=(148, 163, 184), font=get_font(12), anchor="mm")

    out_p = ASSETS_DIR / "earth_return_footer.png"
    img.save(out_p, "PNG")
    print(f"Saved: {out_p}")


if __name__ == "__main__":
    print("Building TERRAVOX README visuals...")
    generate_mission_patch()
    generate_hero_banner()
    generate_solar_system_gif()
    generate_punjab_comparison_panel()
    generate_quetta_comparison_panel()
    generate_architecture_diagram()
    generate_earth_return_footer()
    print("All README visuals generated successfully!")
