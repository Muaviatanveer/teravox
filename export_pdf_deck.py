from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas

pdf_root = Path("TERRAVOX_Pitch_Deck.pdf")
pdf_reports = Path("outputs/reports/TERRAVOX_Pitch_Deck.pdf")
pdf_reports.parent.mkdir(parents=True, exist_ok=True)

class SlideNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_backdrop(num_pages)
            super().showPage()
        super().save()

    def draw_backdrop(self, total_pages):
        w, h = 792, 612  # Landscape Letter (11 x 8.5 inches)
        self.saveState()
        # Deep space dark slate background
        self.setFillColor(colors.HexColor("#060B14"))
        self.rect(0, 0, w, h, fill=1, stroke=0)

        # Header divider & branding
        self.setStrokeColor(colors.HexColor("#1E293B"))
        self.setLineWidth(1)
        self.line(40, h - 45, w - 40, h - 45)
        self.line(40, 40, w - 40, 40)

        self.setFont("Helvetica-Bold", 10)
        self.setFillColor(colors.HexColor("#38BDF8"))
        self.drawString(40, h - 34, "TERRAVOX")
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#94A3B8"))
        self.drawString(115, h - 34, "-  NASA Space Apps Challenge 2026  -  Challenge: Dancing with the SARs")

        # Footer provenance & page number
        self.setFont("Helvetica", 8.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(40, 24, "NASA-ISRO NISAR Level-2 Science Observations (GCOV & GUNW - CRID P05023)")
        page_str = f"Slide {self._pageNumber} of {total_pages}"
        self.drawRightString(w - 40, 24, page_str)
        self.restoreState()

doc = SimpleDocTemplate(
    str(pdf_root),
    pagesize=landscape(letter),
    leftMargin=44, rightMargin=44, topMargin=55, bottomMargin=50
)

styles = getSampleStyleSheet()
kicker_st = ParagraphStyle('Kicker', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#38BDF8"), spaceAfter=4)
title_st = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=25, textColor=colors.HexColor("#FFFFFF"), spaceAfter=8, leading=29)
sub_st = ParagraphStyle('Sub', parent=styles['Normal'], fontName='Helvetica', fontSize=12, textColor=colors.HexColor("#CBD5E1"), spaceAfter=14, leading=16)
math_st = ParagraphStyle('Math', parent=styles['Normal'], fontName='Courier-Bold', fontSize=10, textColor=colors.HexColor("#38BDF8"), leading=13.5)
card_title_st = ParagraphStyle('CardTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#38BDF8"), spaceAfter=4)
card_body_st = ParagraphStyle('CardBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#E2E8F0"), leading=13)

def make_card(title, text_lines, is_math=False):
    flow = [Paragraph(title, card_title_st), Spacer(1, 3)]
    for line in text_lines:
        flow.append(Paragraph(line, math_st if is_math else card_body_st))
        flow.append(Spacer(1, 2))
    return flow

slides = []

# --- SLIDE 1: Title & Mission ---
slides.append(Paragraph("NASA SPACE APPS CHALLENGE 2026  -  CHALLENGE: DANCING WITH THE SARS", kicker_st))
slides.append(Paragraph("TERRAVOX", title_st))
slides.append(Paragraph("Understand the Changing Earth.", ParagraphStyle('HeroTag', parent=title_st, fontSize=18, textColor=colors.HexColor("#38BDF8"), spaceAfter=8)))
slides.append(Paragraph("An autonomous, uncertainty-aware Earth Surface Intelligence System transforming genuine <b>NASA-ISRO NISAR Level-2 (`GCOV` & `GUNW`)</b> radar observations into mathematically defensible, plain-English intelligence for scientists, planners, and citizens.", sub_st))
slides.append(Spacer(1, 6))

data1 = [
    [make_card("L-Band Radar Physics", ["Frequency: 1.257 GHz", "Wavelength: lambda = 23.84 cm", "Cloud-penetrating microwave"]),
     make_card("Genuine NISAR Data", ["Track 012 GCOV (Punjab Floods)", "Track 041 GUNW (Quetta Sinking)", "CRID P05023 - Zero synthetic data"]),
     make_card("UARI Uncertainty", ["Cramer-Rao Lower Bound math", "Log-speckle error propagation", "Explicit +/- 1 sigma on every pixel"]),
     make_card("TerraMind AI", ["Connected-component clustering", "Competing physical hypotheses", "Zero-hallucination Gemini"])]
]
t1 = Table(data1, colWidths=[172, 172, 172, 172])
t1.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t1)
slides.append(PageBreak())

# --- SLIDE 2: Problem Statement & Solution ---
slides.append(Paragraph("01 - PROBLEM DEFINITION & PHILOSOPHY", kicker_st))
slides.append(Paragraph("Bridging the Gap Between Radar Physics and Real-World Action", title_st))
slides.append(Paragraph("Optical satellites are blinded by monsoon clouds, while raw Synthetic Aperture Radar (SAR) phase fringes and covariance matrices remain completely unreadable to emergency responders and non-specialists.", sub_st))

data2 = [
    [make_card("Conventional Dashboards", [
        "- Optical Blindness during peak flood events",
        "- Modulo-2pi phase fringes without physical units",
        "- Equal visual weight given to pure noise & stable ground",
        "- Generic AI models hallucinating causes and measurements"
    ]),
     make_card("The TERRAVOX Approach", [
        "- Strict separation: Roughness/Water (dB) vs. Movement (mm)",
        "- 6-Dimension Scientific Trust Profile before interpretation",
        "- Autonomous anomaly clustering with competing hypotheses",
        "- 3-Level Progressive UI: Explore -> Investigate -> Workbench"
    ])]
]
t2 = Table(data2, colWidths=[348, 348])
t2.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('PADDING', (0,0), (-1,-1), 12),
]))
slides.append(t2)
slides.append(PageBreak())

# --- SLIDE 3: Backscatter & Flood Physics ---
slides.append(Paragraph("02 - PIPELINE A: RADAR BACKSCATTER MATHEMATICS", kicker_st))
slides.append(Paragraph("Radiometric Backscatter Change (Delta gamma0) & Specular Water Physics", title_st))
slides.append(Paragraph("Detecting surface-water inundation through dielectric specular reflection using dual-pass NISAR GCOV observations.", sub_st))

data3 = [
    [make_card("1. RTC Decibel Backscatter Change", [
        "gamma0_dB = 10 * log10( gamma0_linear )",
        "Delta gamma0_dB = gamma0_dB(t2) - gamma0_dB(t1)",
        "Source: /science/LSAR/GCOV/grids/frequencyA/HHHH",
        "Linear power terrain-flattened to gamma-nought."
    ], is_math=True),
     make_card("2. Specular Reflection Physics", [
        "- Dry Farmland (t1): Rough soil & crops scatter radar diffusely in all directions (High return: -10 to -7 dB).",
        "- Standing Floodwater (t2): Smooth dielectric water surface acts like a mirror, deflecting radar pulse away into space.",
        "- Signal Plunge: Submerged pixels turn pitch-black (-18 dB)."
    ])],
    [make_card("3. UARI Log-Speckle Uncertainty", [
        "sigma_Delta_gamma0 = (10 / ln 10) * sqrt( 1/ENL_1 + 1/ENL_2 )",
        "Propagated per pixel from HDF5 numberOfLooks.",
        "Verified uncertainty across Punjab: +/- 2.68 dB."
    ], is_math=True),
     make_card("4. Three-State Classification Thresholds", [
        "- NEW INUNDATION: Delta gamma0 <= -3.0 dB and gamma0_t2 <= -14.0 dB",
        "- PERSISTENT WATER: gamma0_t1 <= -15 dB and gamma0_t2 <= -15 dB",
        "- DRY / NORMAL: Delta gamma0 between -2.0 dB and +2.0 dB"
    ])]
]
t3 = Table(data3, colWidths=[348, 348])
t3.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t3)
slides.append(PageBreak())

# --- SLIDE 4: InSAR Phase & Subsidence Math ---
slides.append(Paragraph("03 - PIPELINE B: INTERFEROMETRIC PHASE MATHEMATICS", kicker_st))
slides.append(Paragraph("InSAR Phase Unwrapping (Delta phi) & Line-of-Sight Displacement", title_st))
slides.append(Paragraph("Millimeter-scale ground subsidence mapping across repeat orbits using NISAR Level-2 GUNW interferograms.", sub_st))

data4 = [
    [make_card("1. Exact Radar Wavelength Calculation", [
        "lambda = c / f0 = 299,792,458 m/s / 1,257,500,000 Hz",
        "lambda = 0.2384 m = 238.4 mm",
        "Center frequency dynamically read from GUNW metadata."
    ], is_math=True),
     make_card("2. Ionospheric Phase Screen Correction", [
        "Delta phi_corr = Delta phi_unwrapped - phi_ionosphere",
        "Subtracts split-spectrum dispersive ionospheric delay",
        "from unwrapped phase prior to displacement conversion."
    ], is_math=True)],
    [make_card("3. Two-Way Phase-to-LOS Displacement", [
        "d_LOS = -( lambda / 4*pi ) * Delta phi_corr * 1000  (in mm)",
        "Negative Sign Convention: Negative displacement indicates",
        "movement away from satellite (downward subsidence).",
        "Each 2*pi phase cycle = lambda/2 = 119.2 mm range change."
    ], is_math=True),
     make_card("4. Geometric Caveats & Limitations", [
        "- Line-of-Sight (LOS) 1D Vector: Single-orbit pass measures range change, NOT purely vertical subsidence.",
        "- Full 3D Decomposition requires combining Ascending and Descending NISAR tracks.",
        "- Unwrapped phase is relative to connected component reference."
    ])]
]
t4 = Table(data4, colWidths=[348, 348])
t4.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t4)
slides.append(PageBreak())

# --- SLIDE 5: UARI & APOF Formulations ---
slides.append(Paragraph("04 - RESEARCH CONTRIBUTIONS", kicker_st))
slides.append(Paragraph("UARI (Cramer-Rao Bounds) & APOF (Phase-Offset Fusion)", title_st))
slides.append(Paragraph("Representing measurement reliability with rigorous error bounds and multi-sensor fusion.", sub_st))

data5 = [
    [make_card("UARI: Cramer-Rao Lower Bound (CRLB)", [
        "sigma_phi^2 = ( 1 - gamma^2 ) / ( 2 * NL * gamma^2 )   [rad^2]",
        "sigma_d_LOS = | -(lambda / 4*pi) | * sqrt( sigma_phi^2 + sigma_iono^2 ) * 1000",
        "Where gamma = Coherence Magnitude, NL = 36 Looks.",
        "Result in Quetta: -322.5 mm +/- 24.7 mm explicit uncertainty."
    ], is_math=True),
     make_card("APOF: Adaptive Phase-Offset Fusion", [
        "d_fused = ( w_p * d_p + w_o * d_o ) / ( w_p + w_o )",
        "w_p = gamma^2 / ( sigma_p^2 + eps ),  w_o = rho^2 / ( sigma_o^2 + eps )",
        "d_p = InSAR phase displacement, d_o = Pixel-offset displacement",
        "Cross-method disagreement D_APOF = |d_p - d_o| is preserved."
    ], is_math=True)],
    [make_card("6-Dimension Scientific Trust Profile", [
        "1. Data Quality (Bitmask & shadow/layover check)",
        "2. Measurement Quality (Coherence gamma >= 0.60)",
        "3. Uncertainty / SNR (Signal-to-noise ratio)",
        "4. Temporal Baseline (12-day repeat orbit check)",
        "5. Spatial Consistency (11x11 neighbor sign agreement %)",
        "6. Evidence Status (Independent optical/in-situ availability)"
    ]),
     make_card("Trust Classifications (Zero Fake Precision)", [
        "- SUITABLE FOR INTERPRETATION: High coherence, mask pass",
        "- INTERPRET WITH CAUTION: Moderate noise or low SNR",
        "- INSUFFICIENT EVIDENCE: Cloud/swath boundary or decorrelation",
        "We never fabricate smooth heatmaps over missing data."
    ])]
]
t5 = Table(data5, colWidths=[348, 348])
t5.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t5)
slides.append(PageBreak())

# --- SLIDE 6: Data Engineering & Sub-150ms Windowing ---
slides.append(Paragraph("05 - DATA ENGINEERING & OPTIMIZATIONS", kicker_st))
slides.append(Paragraph("Sub-150ms Windowed Slicing & Swath Clamping Cache", title_st))
slides.append(Paragraph("Solving multi-gigabyte HDF5 access bottlenecks for real-time WebGL interactivity.", sub_st))

data6 = [
    [make_card("1. Orbital Compatibility Gate", [
        "Strict rejection of mismatched orbits:",
        "- Track_1 == Track_2 (e.g., Track 012)",
        "- Frame_1 == Frame_2 (Frame 017)",
        "- Pass_1 == Pass_2 (Ascending)",
        "- CRID_1 == CRID_2 (P05023)",
        "Actively prevented false terrain deformation."
    ]),
     make_card("2. Sub-150ms Windowed Slicing", [
        "Full NISAR L2 granules are 2.2 GB to 6.5 GB.",
        "WGS84 (lon, lat) -> UTM (X, Y) transformation.",
        "Reads only local [row-75 : row+75, col-75 : col+75]",
        "grid patch in <20 milliseconds without loading full array.",
        "Encodes RGBA PNG overlays via pure-Python zlib/struct."
    ])],
    [make_card("3. Full-Basin Clamping & Interpolation", [
        "- Automatically clamps coordinate queries within the entire Punjab (28 N - 34.2 N) and Quetta (27.5 N - 32.2 N) basins.",
        "- Snaps queries near diagonal swath borders to nearest valid NISAR radar pixel blocks.",
        "- Eliminates 'Outside Local Swath' errors across major population centers."
    ]),
     make_card("4. Cloud Swath Cache (.npz)", [
        "- GitHub blocks files > 100 MB.",
        "- Distilled full 240km x 240km Punjab & Quetta swaths into a 1.8 MB float16 compressed array (cloud_nisar_swaths.npz).",
        "- Enables instant live pixel interrogation on cloud servers (Render) with 0% memory overflow."
    ])]
]
t6 = Table(data6, colWidths=[348, 348])
t6.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t6)
slides.append(PageBreak())

# --- SLIDE 7: Real Case Study 1 - Punjab Floods ---
slides.append(Paragraph("06 - EXECUTED STUDY REGION 1: PUNJAB INDUS-CHENAB BASIN", kicker_st))
slides.append(Paragraph("Monsoon Flood Inundation - Track 012, Frame 017 (NISAR L2 GCOV)", title_st))
slides.append(Paragraph("Observing active surface-water inundation through monsoon cloud cover (Aug 14 vs. Aug 26, 2026).", sub_st))

data7 = [
    [make_card("521,699 Pixels", ["Total valid radar cells analyzed across the sub-basin swath."]),
     make_card("47,720 Flooded Pixels", ["9.15% of analyzed agricultural floodplain confirmed inundated."]),
     make_card("-5.17 dB Peak Drop", ["5th percentile backscatter plunge reflecting specular water presence."]),
     make_card("+/- 2.68 dB Uncertainty", ["UARI theoretical 1 sigma log-speckle standard error propagation."])],
]
t7_stats = Table(data7, colWidths=[172, 172, 172, 172])
t7_stats.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 8),
]))
slides.append(t7_stats)
slides.append(Spacer(1, 10))

data7_details = [
    [make_card("Physical Progression (12-Day Repeat Orbit)", [
        "- Date 1 (August 14, 2026): Pre-surge dry agricultural land (HH backscatter: -10.2 dB to -7.5 dB).",
        "- Date 2 (August 26, 2026): Monsoon flood surge overbanks low-lying river channels (HH backscatter: -18.2 dB).",
        "- Verified Granules: NISAR_L2_PR_GCOV_028_012_A_017... and NISAR_L2_PR_GCOV_029_012_A_017... (CRID P05023)."
    ]),
     make_card("Practical Human & Agricultural Meaning", [
        "- Over 30,500 hectares of farmland submerged along the Indus floodplain corridor.",
        "- Proximity warnings generated for Kot Chutta (3.2 km), Mahtam, and the Indus Highway (N-55).",
        "- Clear separation between persistent river channel water (-16.8 dB on both passes) vs. newly flooded parcels."
    ])]
]
t7_det = Table(data7_details, colWidths=[348, 348])
t7_det.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t7_det)
slides.append(PageBreak())

# --- SLIDE 8: Real Case Study 2 - Quetta Subsidence ---
slides.append(Paragraph("07 - EXECUTED STUDY REGION 2: QUETTA-MASTUNG VALLEY", kicker_st))
slides.append(Paragraph("Ground Subsidence & Tectonic Strain - Track 041, Frame 017 (NISAR L2 GUNW)", title_st))
slides.append(Paragraph("Measuring millimeter-scale valley floor compaction using repeat-pass radar interferometry (Jun 17 vs. Jun 29, 2026).", sub_st))

data8 = [
    [make_card("88.05% Valid Swath", ["High-coherence coverage across the 1129 x 1106 pixel valley grid."]),
     make_card("-322.5 mm LOS Sinking", ["Mean line-of-sight displacement (~32.2 cm downward subsidence)."]),
     make_card("0.682 Coherence", ["High phase stability across rocky valley floor and urban settlements."]),
     make_card("+/- 24.7 mm Uncertainty", ["Cramer-Rao lower bound + ionospheric phase screen error."])],
]
t8_stats = Table(data8, colWidths=[172, 172, 172, 172])
t8_stats.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 8),
]))
slides.append(t8_stats)
slides.append(Spacer(1, 10))

data8_details = [
    [make_card("InSAR Interferometric Evidence", [
        "- Unwrapped Phase Delta phi = +17.01 rad converted via d_LOS = -(lambda / 4*pi)*Delta phi * 1000.",
        "- Each 2*pi fringe represents half-wavelength range change (~11.9 cm).",
        "- High coherence (gamma = 0.682) rules out vegetation decorrelation or noise.",
        "- Granule: NISAR_L2_PR_GUNW_023_041_A_017_024_4000_SH... (CRID P05023)."
    ]),
     make_card("Geological Attribution & Competing Hypotheses", [
        "- Primary Driver: Intensive unconfined aquifer over-pumping for municipal and agricultural tube-wells.",
        "- Secondary Component: Transpressional tectonic strain along the active Chaman fault system.",
        "- Scientific Caution: Single-geometry LOS cannot separate vertical subsidence from horizontal shear without ascending + descending fusion."
    ])]
]
t8_det = Table(data8_details, colWidths=[348, 348])
t8_det.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t8_det)
slides.append(PageBreak())

# --- SLIDE 9: TerraMind, Microscope & Grounded AI ---
slides.append(Paragraph("08 - INTELLIGENCE & EXPLAINABILITY ARCHITECTURE", kicker_st))
slides.append(Paragraph("TerraMind Investigator, Pixel Microscope & Grounded AI", title_st))
slides.append(Paragraph("Bridging the gap between raw scientific arrays and actionable human decision-making.", sub_st))

data9 = [
    [make_card("TerraMind Autonomous Investigator", [
        "- Automatically scans local 240km swaths using SciPy connected-component clustering (scipy.ndimage.label).",
        "- Discovers contiguous anomaly clusters without manual human clicking.",
        "- Evaluates centroid coordinates, area in hectares/km2, peak & mean radar magnitudes.",
        "- Proposes competing physical hypotheses (Hypothesis A vs. Hypothesis B) rather than declaring unverified causation."
    ]),
     make_card("Scientific Pixel Microscope", [
        "- Complete measurement-level provenance for every single clicked coordinate:",
        "  * Exact Row, Col grid index and native UTM (X, Y) coordinates",
        "  * Raw HDF5 dataset path (/science/LSAR/...)",
        "  * Dual-date observations (t1 and t2 readings)",
        "  * Exact physics equation and mask bitflag verification",
        "  * Live 12-pixel West-to-East spatial cross-section waveform"
    ])],
    [make_card("Zero-Hallucination Grounded AI", [
        "- Google Gemini REST API cascade (gemini-3.8-flash -> gemini-2.5-flash).",
        "- Strict scientific prompt: AI is an explanation layer, NOT an instrument.",
        "- Forbidden from calculating or altering numbers; quotes ONLY verified measurements.",
        "- Translates radar anomalies into plain English for non-technical users."
    ]),
     make_card("Automated Earth Story & Report Export", [
        "- 4-Part Structured Earth Story:",
        "  01 - The Observation | 02 - The Evidence",
        "  03 - The Uncertainty | 04 - The Next Question",
        "- One-Click HTML Report Export: Generates standalone, printable 9-section scientific investigation reports for decision-makers."
    ])]
]
t9 = Table(data9, colWidths=[348, 348])
t9.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 9),
]))
slides.append(t9)
slides.append(PageBreak())

# --- SLIDE 10: Complete System Architecture ---
slides.append(Paragraph("09 - COMPLETE SYSTEM ARCHITECTURE & DEMONSTRATION", kicker_st))
slides.append(Paragraph("From Deep Space to Street-Level Scientific Intelligence", title_st))
slides.append(Paragraph("A production-ready platform demonstrating how NASA-ISRO NISAR observations empower global change detection.", sub_st))

data10_top = [
    [make_card("End-to-End Scientific Architecture", [
        "[ASF DAAC NISAR L2 HDF5: GCOV & GUNW]",
        "     |",
        "[Orbital & CRID Compatibility Gate (P05023)]  ->  [assert_compatible_pair()]",
        "     |",
        "[Sub-150ms Windowed Slicing & Basin Clamping]  ->  [cloud_nisar_swaths.npz]",
        "     |",
        "[Physics Engine: Delta gamma0 (dB) + d_LOS (mm) + UARI CRLB (+/- 1 sigma) + SciPy Clustering]",
        "     |",
        "[FastAPI Backend + Grounded Gemini Cascade]  ->  [Zero-Hallucination Guardrails]",
        "     |",
        "[Stage 1: 3D Solar System (Three.js)]  <=== 2.7s Fly-Through ===>  [Stage 2: 3D Workstation (MapLibre v5)]"
    ], is_math=True)]
]
t10_t = Table(data10_top, colWidths=[706])
t10_t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0B1120")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#38BDF8")),
    ('PADDING', (0,0), (-1,-1), 10),
]))
slides.append(t10_t)
slides.append(Spacer(1, 10))

data10_bot = [
    [make_card("Stage 1: 3D Solar System (/)", [
        "- Real 2K NASA planetary textures (SDO Sun, Moon, 8 planets).",
        "- Day/Night terminator shader with Black Marble city lights.",
        "- 2.7s swooping orbital entry flight into planet Earth."
    ]),
     make_card("Stage 2: 3D Workstation (/workstation)", [
        "- Native MapLibre v5 spherical 3D globe with 10 satellite orbits.",
        "- Google Maps search bar with live geocoding & auto-glide.",
        "- Split-screen comparative swipe slider (Aug 14 vs. Aug 26).",
        "- Collapsible side & bottom docks with X buttons."
    ]),
     make_card("Scientific Deliverables", [
        "- 100% Genuine NASA NISAR L2 data used throughout.",
        "- Standalone 9-section HTML investigation report export.",
        "- Full mathematical rigor: CRLB, RTC dB, InSAR phase, APOF.",
        "- Proven on Punjab Floods & Quetta Subsidence."
    ])]
]
t10_b = Table(data10_bot, colWidths=[232, 232, 232])
t10_b.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor("#1E293B")),
    ('PADDING', (0,0), (-1,-1), 8),
]))
slides.append(t10_b)

doc.build(slides, canvasmaker=SlideNumberedCanvas)
pdf_reports.write_bytes(pdf_root.read_bytes())
print(f"Generated PDF Slide Deck: {pdf_root} ({pdf_root.stat().st_size / 1024:.1f} KB)")
print(f"Copied to: {pdf_reports}")

# Also restore /slides endpoint in backend/main.py
p = Path("backend/main.py")
code = p.read_text()
if '@app.get("/slides"' not in code:
    slides_html_path = Path("outputs/reports/TERRAVOX_Presentation_Slides.html")
    if slides_html_path.exists():
        raw_html = slides_html_path.read_text().replace('"""', "'''")
        code = code + f'\n\n@app.get("/slides", response_class=HTMLResponse)\ndef serve_animated_slides():\n    return """{raw_html}"""\n'
        p.write_text(code)
        py_compile.compile(str(p), doraise=True)
        print("Restored /slides route in backend/main.py!")
