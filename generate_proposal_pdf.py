import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
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
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#334155"))
        
        # Header (pages after cover page)
        if self._pageNumber > 1:
            self.drawString(40, 11 * inch - 28, "AQUACHECK: PORTABLE MULTI-PARAMETER WATER QUALITY MONITORING DEVICE")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawRightString(8.5 * inch - 40, 11 * inch - 28, "PROJECT PROPOSAL & ENGINEERING PLAN")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(40, 11 * inch - 32, 8.5 * inch - 40, 11 * inch - 32)
        
        # Footer (all pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 40, 24, page_str)
        self.drawString(40, 24, "Embedded Systems Engineering Mini-Project — Technical Proposal Dossier")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 34, 8.5 * inch - 40, 34)
        
        self.restoreState()

def create_pdf(filename="AquaCheck_Project_Proposal.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=42,
        bottomMargin=42
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#0F2942")    # Deep Navy
    c_secondary = colors.HexColor("#1E5F8A")  # Technical Blue
    c_accent = colors.HexColor("#0D9488")     # Aqua/Teal Accent
    c_dark = colors.HexColor("#1E293B")       # High-contrast Slate Body Text
    c_light = colors.HexColor("#F8FAFC")      # Light BG
    c_border = colors.HexColor("#CBD5E1")
    
    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=23,
        textColor=c_primary,
        spaceAfter=3
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=c_secondary,
        spaceAfter=8
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14.5,
        textColor=c_primary,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=c_secondary,
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.6,
        leading=11.8,
        textColor=c_dark,
        spaceAfter=4
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )
    
    code_block_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.4,
        leading=9.8,
        textColor=colors.HexColor("#0F172A")
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10,
        textColor=c_dark
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=c_primary
    )
    
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10,
        textColor=colors.white
    )

    story = []
    
    # ---------------------------------------------------------
    # COVER / HEADER BANNER
    # ---------------------------------------------------------
    story.append(Paragraph("AQUACHECK", title_style))
    story.append(Paragraph("Portable Multi-Parameter Water Quality Monitoring & Assessment Device", subtitle_style))
    
    meta_data = [
        [
            Paragraph("<b>Project Title:</b> AquaCheck Handheld Water Analyzer", table_cell),
            Paragraph("<b>Target Platform:</b> ESP32 Dual-Core (Xtensa 240MHz)", table_cell)
        ],
        [
            Paragraph("<b>Academic Scope:</b> Embedded Systems Mini-Project", table_cell),
            Paragraph("<b>Target Domain:</b> Environmental & Public Health Sensing", table_cell)
        ],
        [
            Paragraph("<b>Estimated Budget:</b> LKR 14,480 (~$47.50 USD)", table_cell),
            Paragraph("<b>Output Interfaces:</b> 0.96\" OLED, MicroSD Logger, Piezo Alert", table_cell)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[266, 266])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_light),
        ('BOX', (0,0), (-1,-1), 1, c_secondary),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 4))
    
    # ---------------------------------------------------------
    # 1. EXECUTIVE SUMMARY & PROBLEM STATEMENT
    # ---------------------------------------------------------
    story.append(Paragraph("1. Executive Summary & Problem Statement", h1_style))
    story.append(Paragraph(
        "Access to verified clean drinking water is a critical humanitarian priority across developing nations and specifically "
        "in Sri Lanka's dry zones, where agrochemical runoff and elevated fluoride/mineral concentrations are strongly linked to chronic "
        "health crises such as CKDu (Chronic Kidney Disease of unknown etiology). Conventional water testing depends on centralized "
        "laboratories. While accurate, laboratory analysis incurs 24–72 hour delays, prohibitive operational costs, and complex sample handling, "
        "preventing rapid, on-site diagnostics by field health officers, rural community well owners, and agriculturalists.",
        body_style
    ))
    story.append(Paragraph(
        "<b>AquaCheck</b> resolves this bottleneck by integrating a complete analytical instrument into an ultra-portable, battery-operated "
        "handheld device. It synchronously measures four primary physicochemical water quality parameters: <b>pH</b> (acidity/alkalinity), "
        "<b>Turbidity</b> (optical clarity/suspended solids), <b>Total Dissolved Solids (TDS/EC)</b> (dissolved ionic species), and "
        "<b>Water Temperature</b>. Powered by an ESP32 microcontroller, AquaCheck executes real-time temperature compensation, automatically "
        "classifies water safety against WHO and Sri Lanka Standards (SLS 614:2013), writes continuous logs to an onboard MicroSD card, "
        "and triggers immediate audio-visual danger alerts.",
        body_style
    ))
    
    # ---------------------------------------------------------
    # 2. PROJECT OBJECTIVES & KEY NOVELTY
    # ---------------------------------------------------------
    story.append(Paragraph("2. Project Objectives & Engineering Novelty", h1_style))
    story.append(Paragraph("• <b>Synchronous Multi-Sensor Co-Location:</b> Acquire stable readings from 4 distinct physical probes submerged in a common liquid sample within 5 seconds.", bullet_style))
    story.append(Paragraph("• <b>Real-Time Embedded Compensation:</b> Execute onboard mathematical temperature compensation for both pH (Nernst equation) and electrical conductivity (EC/TDS at 25°C) to eliminate thermal drift.", bullet_style))
    story.append(Paragraph("• <b>Full Field Autonomy:</b> Deliver 8+ hours continuous runtime via an internal 18650 Li-ion cell with integrated USB-C charging and step-up power management.", bullet_style))
    story.append(Paragraph("• <b>Edge Health Classification:</b> Automatically benchmark sample measurements against SLS 614:2013 standards, outputting immediate 'Safe', 'Permissible', or 'Hazardous' status.", bullet_style))
    story.append(Paragraph(
        "<b>Engineering Novelty:</b> Unlike generic IoT projects that push unverified analog readings to the cloud, AquaCheck resolves "
        "critical hardware challenges: (1) <i>Inter-probe electrical interference</i> where active TDS AC pulses corrupt high-impedance pH "
        "glass probes; (2) <i>Non-linear optical dispersion</i> in low-cost turbidity sensors; and (3) <i>Autonomous offline logging</i> with zero cloud dependency.",
        body_style
    ))
    
    # ---------------------------------------------------------
    # 3. TECHNICAL SPECIFICATIONS & PIN INTERFACING
    # ---------------------------------------------------------
    story.append(Paragraph("3. Technical Hardware Architecture & Interfacing Table", h1_style))
    
    pin_headers = [Paragraph("<b>Subsystem / Module</b>", table_header), Paragraph("<b>Component Model</b>", table_header), Paragraph("<b>ESP32 Pin</b>", table_header), Paragraph("<b>Signal Type / Protocol</b>", table_header), Paragraph("<b>Operating Voltage</b>", table_header)]
    pin_data = [
        pin_headers,
        [Paragraph("pH Measurement", table_cell_bold), Paragraph("Analog pH V1.1 (BNC Probe)", table_cell), Paragraph("GPIO 32 (ADC1_CH4)", table_cell), Paragraph("Analog (0.0V – 3.3V mapped)", table_cell), Paragraph("5.0V / 3.3V Logic", table_cell)],
        [Paragraph("Turbidity / Clarity", table_cell_bold), Paragraph("TS-300B Optical Turbidity", table_cell), Paragraph("GPIO 33 (ADC1_CH5)", table_cell), Paragraph("Analog (0.5V – 4.0V mapped)", table_cell), Paragraph("5.0V VCC", table_cell)],
        [Paragraph("TDS / Conductivity", table_cell_bold), Paragraph("Gravity Analog TDS Sensor", table_cell), Paragraph("GPIO 34 (ADC1_CH6)", table_cell), Paragraph("Analog AC Excitation (0–2.3V)", table_cell), Paragraph("3.3V – 5.0V", table_cell)],
        [Paragraph("Water Temperature", table_cell_bold), Paragraph("DS18B20 Stainless Probe", table_cell), Paragraph("GPIO 4 (4.7kΩ Pull-up)", table_cell), Paragraph("Maxim 1-Wire Digital Bus", table_cell), Paragraph("3.3V VCC", table_cell)],
        [Paragraph("Display Output", table_cell_bold), Paragraph("0.96\" I2C OLED (SSD1306)", table_cell), Paragraph("GPIO 21 (SDA), 22 (SCL)", table_cell), Paragraph("I2C Bus (400 kHz)", table_cell), Paragraph("3.3V VCC", table_cell)],
        [Paragraph("Offline Storage", table_cell_bold), Paragraph("MicroSD SPI Breakout", table_cell), Paragraph("GPIO 18, 19, 23, 5 (CS)", table_cell), Paragraph("SPI Serial Bus (10 MHz)", table_cell), Paragraph("3.3V VCC", table_cell)],
        [Paragraph("Power Management", table_cell_bold), Paragraph("TP4056 + MT3608 Boost", table_cell), Paragraph("VIN / 5V Rail", table_cell), Paragraph("Regulated 5.0V & 3.3V Rails", table_cell), Paragraph("3.7V Li-ion to 5.0V", table_cell)],
        [Paragraph("Audio-Visual Alerts", table_cell_bold), Paragraph("Active Piezo + Bi-Color LED", table_cell), Paragraph("GPIO 25 (Buzzer), 26, 27", table_cell), Paragraph("Digital Output / PWM", table_cell), Paragraph("3.3V Logic", table_cell)],
    ]
    t_pin = Table(pin_data, colWidths=[105, 120, 110, 120, 77])
    t_pin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_pin)
    
    # ---------------------------------------------------------
    # 4. MATHEMATICAL FORMULATION & CALIBRATION ALGORITHMS
    # ---------------------------------------------------------
    story.append(Paragraph("4. Physical Models, Calibration & Compensation Algorithms", h1_style))
    story.append(Paragraph(
        "To achieve laboratory-grade reliability with low-cost analog transducers, AquaCheck integrates deterministic "
        "chemical and optical physics compensation routines into its embedded firmware loop:",
        body_style
    ))
    
    story.append(Paragraph("<b>A. Temperature-Compensated Electrical Conductivity (EC) and TDS:</b>", h2_style))
    story.append(Paragraph(
        "The mobility of dissolved ions in water increases with temperature at approximately 1.9% per °C. Standard TDS readings "
        "must be normalized to a standard 25.0°C baseline reference. The compensation formula is:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>EC<sub>25</sub> = EC<sub>measured</sub> / [ 1.0 + 0.019 × (T<sub>water</sub> - 25.0) ]</b><br/>"
        "Total Dissolved Solids (TDS in parts-per-million) is subsequently computed using the conversion factor:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>TDS (ppm) = EC<sub>25</sub> (μS/cm) × 0.50</b>",
        body_style
    ))
    
    story.append(Paragraph("<b>B. Nernstian Temperature Slope Scaling for pH:</b>", h2_style))
    story.append(Paragraph(
        "The theoretical output voltage of a glass pH electrode is governed by the Nernst Equation. The millivolts generated per pH unit "
        "(the electrode sensitivity slope S) is directly proportional to absolute thermodynamic temperature:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>S(T) = (2.3026 × R × T<sub>Kelvin</sub>) / F</b> &nbsp;&nbsp;[= 54.20 mV/pH at 0°C; 59.16 mV/pH at 25°C; 62.13 mV/pH at 40°C]<br/>"
        "AquaCheck applies a two-point calibration using standard buffer solutions (pH 4.01 and pH 6.86):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>pH<sub>corrected</sub> = 7.0 + [ (V<sub>neutral</sub> - V<sub>probe</sub>) / S(T) ]</b>",
        body_style
    ))
    
    story.append(Paragraph("<b>C. Non-Linear Polynomial Characteristic for Optical Turbidity:</b>", h2_style))
    story.append(Paragraph(
        "The optical turbidity sensor utilizes an infrared transmitter-phototransistor pair. Light scattering caused by suspended "
        "particulate matter decreases the received phototransistor collector voltage non-linearly:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Turbidity (NTU) = -1120.4 × (V<sub>sensor</sub>)<sup>2</sup> + 5742.3 × V<sub>sensor</sub> - 4352.9</b> &nbsp;&nbsp;(for V<sub>sensor</sub> &lt; 2.50V)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>(When V<sub>sensor</sub> ≥ 2.50V, Turbidity is mapped to &lt; 0.5 NTU denoting crystal-clear water).</i>",
        body_style
    ))
    
    # ---------------------------------------------------------
    # 5. WATER QUALITY CLASSIFICATION BENCHMARKS
    # ---------------------------------------------------------
    story.append(Paragraph("5. Water Classification Matrix (SLS 614 & WHO Standards)", h1_style))
    
    thresh_headers = [Paragraph("<b>Water Quality Parameter</b>", table_header), Paragraph("<b>Ideal / Excellent</b>", table_header), Paragraph("<b>Permissible Limit (SLS 614)</b>", table_header), Paragraph("<b>Hazardous / Unsafe</b>", table_header), Paragraph("<b>Sensor Resolution</b>", table_header)]
    thresh_data = [
        thresh_headers,
        [Paragraph("pH (Acidity / Alkalinity)", table_cell_bold), Paragraph("6.5 – 7.5", table_cell), Paragraph("6.5 – 8.5", table_cell), Paragraph("&lt; 6.0 or &gt; 9.0", table_cell), Paragraph("±0.1 pH units", table_cell)],
        [Paragraph("TDS (Dissolved Solids)", table_cell_bold), Paragraph("&lt; 300 ppm", table_cell), Paragraph("300 – 500 ppm", table_cell), Paragraph("&gt; 1000 ppm (Saline/Hard)", table_cell), Paragraph("±10 ppm", table_cell)],
        [Paragraph("Turbidity (Water Clarity)", table_cell_bold), Paragraph("&lt; 1.0 NTU", table_cell), Paragraph("1.0 – 5.0 NTU", table_cell), Paragraph("&gt; 5.0 NTU (Muddy/Suspended)", table_cell), Paragraph("±0.5 NTU", table_cell)],
        [Paragraph("Temperature", table_cell_bold), Paragraph("20°C – 28°C", table_cell), Paragraph("15°C – 35°C", table_cell), Paragraph("&gt; 40°C (Abnormal thermal)", table_cell), Paragraph("±0.25°C", table_cell)],
    ]
    t_thresh = Table(thresh_data, colWidths=[115, 95, 125, 110, 87])
    t_thresh.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_thresh)
    
    # ---------------------------------------------------------
    # 6. FIRMWARE ARCHITECTURE & PSEUDOCODE
    # ---------------------------------------------------------
    story.append(Paragraph("6. Firmware Execution Flow & FreeRTOS Task Structure", h1_style))
    story.append(Paragraph(
        "To ensure deterministic sensor sampling without UI stutter, the ESP32 firmware is divided into two concurrent FreeRTOS tasks:<br/>"
        "• <b>Task_SensorAcquisition (Core 0):</b> Sequential time-multiplexed ADC reading (pH, then Turbidity, then TDS), "
        "DS18B20 1-Wire interrogation, temperature compensation math, and alert threshold checking.<br/>"
        "• <b>Task_UI_and_Logging (Core 1):</b> SSD1306 128x64 graphical rendering at 2 Hz and CSV data serialization to MicroSD card.",
        body_style
    ))
    
    code_text = (
        "void Task_SensorAcquisition(void *pvParameters) {\n"
        "  for(;;) {\n"
        "    digitalWrite(TDS_POWER_GATE, LOW);   // 1. Isolate TDS AC signal to eliminate noise on pH probe\n"
        "    float tempC = readDS18B20();          // 2. Sample liquid temperature baseline\n"
        "    float rawPH = readCalibratedPH(tempC); // 3. Sample pH with dynamic Nernst compensation\n"
        "    float turbidity = readTurbidityNTU(); // 4. Sample optical clarity\n"
        "    digitalWrite(TDS_POWER_GATE, HIGH);  // 5. Enable TDS excitation only during its dedicated window\n"
        "    vTaskDelay(pdMS_TO_TICKS(50));        // Stabilize AC excitation\n"
        "    float tdsPPM = readCompensatedTDS(tempC); // 6. Calculate 25°C-normalized TDS\n"
        "    digitalWrite(TDS_POWER_GATE, LOW);   // 7. Re-isolate TDS probe\n"
        "    evaluateSafetyLimits(rawPH, tdsPPM, turbidity); // 8. Check SLS 614 thresholds\n"
        "    vTaskDelay(pdMS_TO_TICKS(1000));      // Sample interval: 1.0 second\n"
        "  }\n"
        "}"
    )
    code_table = Table([[Paragraph(code_text.replace('\n', '<br/>'), code_block_style)]], colWidths=[532])
    code_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(code_table)
    
    # ---------------------------------------------------------
    # 7. BILL OF MATERIALS & LOCAL BUDGET ESTIMATE
    # ---------------------------------------------------------
    story.append(Paragraph("7. Comprehensive Bill of Materials (BOM) & Budget (Sri Lanka Market)", h1_style))
    story.append(Paragraph(
        "Current market prices collected from verified Sri Lankan electronic suppliers (Tronic.lk, Duino.lk, Microchip.lk):",
        body_style
    ))
    
    bom_headers = [Paragraph("<b>Component / Module</b>", table_header), Paragraph("<b>Qty</b>", table_header), Paragraph("<b>Est. Unit (LKR)</b>", table_header), Paragraph("<b>Total (LKR)</b>", table_header), Paragraph("<b>Recommended Local Supplier</b>", table_header)]
    bom_data = [
        bom_headers,
        [Paragraph("Analog pH Sensor Kit V1.1 (Probe + Signal Board)", table_cell_bold), Paragraph("1", table_cell), Paragraph("4,200", table_cell), Paragraph("4,200", table_cell), Paragraph("Tronic.lk / Duino.lk", table_cell)],
        [Paragraph("Analog Optical Turbidity Sensor Module (TS-300B)", table_cell_bold), Paragraph("1", table_cell), Paragraph("2,850", table_cell), Paragraph("2,850", table_cell), Paragraph("Duino.lk / Microchip.lk", table_cell)],
        [Paragraph("Gravity Analog TDS Sensor Module + Probe", table_cell_bold), Paragraph("1", table_cell), Paragraph("1,950", table_cell), Paragraph("1,950", table_cell), Paragraph("Tronic.lk / Duino.lk", table_cell)],
        [Paragraph("DS18B20 Waterproof Stainless Steel Probe", table_cell_bold), Paragraph("1", table_cell), Paragraph("550", table_cell), Paragraph("550", table_cell), Paragraph("Microchip.lk / Tronic.lk", table_cell)],
        [Paragraph("ESP32 DevKit V1 30-Pin Microcontroller Board", table_cell_bold), Paragraph("1", table_cell), Paragraph("1,100", table_cell), Paragraph("1,100", table_cell), Paragraph("Duino.lk / StemLabs", table_cell)],
        [Paragraph("0.96\" I2C OLED Display (SSD1306 128x64)", table_cell_bold), Paragraph("1", table_cell), Paragraph("850", table_cell), Paragraph("850", table_cell), Paragraph("Local Hobby Stores / Daraz", table_cell)],
        [Paragraph("MicroSD Card SPI Module + 8GB Class 10 Card", table_cell_bold), Paragraph("1", table_cell), Paragraph("900", table_cell), Paragraph("900", table_cell), Paragraph("Daraz.lk / Local Shop", table_cell)],
        [Paragraph("18650 Li-ion Cell (2600mAh) + TP4056 USB-C Board", table_cell_bold), Paragraph("1", table_cell), Paragraph("750", table_cell), Paragraph("750", table_cell), Paragraph("Tronic.lk / Duino.lk", table_cell)],
        [Paragraph("MT3608 DC-DC Step-Up Boost Module (3.7V to 5V)", table_cell_bold), Paragraph("1", table_cell), Paragraph("180", table_cell), Paragraph("180", table_cell), Paragraph("Duino.lk / Tronic.lk", table_cell)],
        [Paragraph("Power Gating MOSFET (2N7000) & Passives", table_cell_bold), Paragraph("Lot", table_cell), Paragraph("350", table_cell), Paragraph("350", table_cell), Paragraph("Pettah Electronics Market", table_cell)],
        [Paragraph("Handheld ABS/Acrylic Enclosure & Probe Wand", table_cell_bold), Paragraph("1", table_cell), Paragraph("800", table_cell), Paragraph("800", table_cell), Paragraph("Makerspace 3D Print / Acrylic", table_cell)],
        [Paragraph("<b>TOTAL ESTIMATED PROJECT BUDGET:</b>", table_cell_bold), Paragraph("<b>--</b>", table_cell), Paragraph("<b>--</b>", table_cell), Paragraph("<b>LKR 14,480</b>", table_cell_bold), Paragraph("<b>~$47.50 USD (Sub-$50 Target)</b>", table_cell_bold)]
    ]
    t_bom = Table(bom_data, colWidths=[165, 26, 95, 95, 151])
    t_bom.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_light]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_bom)
    
    # ---------------------------------------------------------
    # 8. IMPLEMENTATION ROADMAP (6-WEEK PLAN)
    # ---------------------------------------------------------
    story.append(Paragraph("8. Project Implementation Roadmap & Milestones (6-Week Gantt Structure)", h1_style))
    
    plan_headers = [Paragraph("<b>Phase & Timeline</b>", table_header), Paragraph("<b>Key Engineering Milestones & Deliverables</b>", table_header), Paragraph("<b>Measurable Verification Criteria</b>", table_header)]
    plan_data = [
        plan_headers,
        [Paragraph("<b>Week 1:</b> Procurement & Subsystem Testing", table_cell), Paragraph("Procure sensors and components from local vendors. Test individual analog outputs with breadboard sketches.", table_cell), Paragraph("Clean oscilloscope/serial ADC stream from each sensor independently.", table_cell)],
        [Paragraph("<b>Week 2:</b> Calibration & Compensation Lab", table_cell), Paragraph("Perform 2-point pH buffer calibration (pH 4.01/6.86). Calibrate TDS sensor using standard NaCl calibration solutions.", table_cell), Paragraph("Measurement error &lt; 2.5% compared to known chemical reference standards.", table_cell)],
        [Paragraph("<b>Week 3:</b> Dual-Core FreeRTOS Architecture", table_cell), Paragraph("Develop FreeRTOS tasks: Sensor acquisition, Nernst/EC math routines, OLED screen layout, and CSV data logging.", table_cell), Paragraph("2 Hz stable display refresh rate with zero dropped sensor readings.", table_cell)],
        [Paragraph("<b>Week 4:</b> Power & Hardware Integration", table_cell), Paragraph("Integrate TP4056 USB-C charging, 18650 cell, and MT3608 boost converter on custom perfboard / prototype PCB.", table_cell), Paragraph("Sustained battery runtime &gt; 8 hours under active continuous sampling.", table_cell)],
        [Paragraph("<b>Week 5:</b> Field Sample Validation", table_cell), Paragraph("Collect and test 5 diverse water samples: Distilled water, municipal tap water, agrochemical well water, pond, and saline solution.", table_cell), Paragraph("Statistically distinct classification of safe vs contaminated samples.", table_cell)],
        [Paragraph("<b>Week 6:</b> Enclosure Assembly & Final Defense", table_cell), Paragraph("Mount electronics into handheld casing with probe wand holder. Finalize project proposal report and demonstration rig.", table_cell), Paragraph("Functional, self-contained prototype ready for live evaluator demonstration.", table_cell)],
    ]
    t_plan = Table(plan_data, colWidths=[120, 235, 177])
    t_plan.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_plan)
    
    # ---------------------------------------------------------
    # 9. TESTING & DEMONSTRATION PROTOCOL
    # ---------------------------------------------------------
    story.append(Paragraph("9. Live Demonstration & Verification Testing Protocol", h1_style))
    story.append(Paragraph(
        "A compelling project defense hinges on demonstrating clear differentiation between real liquid samples. "
        "The following 4-vial evaluation protocol will be executed during the project examination:",
        body_style
    ))
    
    demo_headers = [Paragraph("<b>Sample Test Vial</b>", table_header), Paragraph("<b>Expected pH</b>", table_header), Paragraph("<b>Expected TDS</b>", table_header), Paragraph("<b>Expected Turbidity</b>", table_header), Paragraph("<b>System Classification Verdict</b>", table_header)]
    demo_data = [
        demo_headers,
        [Paragraph("<b>Vial A:</b> Deionized / Bottled Water", table_cell), Paragraph("6.8 – 7.2", table_cell), Paragraph("&lt; 50 ppm", table_cell), Paragraph("&lt; 0.5 NTU", table_cell), Paragraph("SAFE (Green LED, Clean)", table_cell)],
        [Paragraph("<b>Vial B:</b> Municipal Tap Water", table_cell), Paragraph("7.0 – 7.5", table_cell), Paragraph("150 – 250 ppm", table_cell), Paragraph("&lt; 2.0 NTU", table_cell), Paragraph("SAFE / PERMISSIBLE", table_cell)],
        [Paragraph("<b>Vial C:</b> Muddy Runoff / Silt Water", table_cell), Paragraph("6.5 – 7.8", table_cell), Paragraph("200 – 400 ppm", table_cell), Paragraph("&gt; 25.0 NTU (Cloudy)", table_cell), Paragraph("UNSAFE (Turbidity Alert)", table_cell)],
        [Paragraph("<b>Vial D:</b> High-Saline / Mineral Well", table_cell), Paragraph("7.5 – 8.8", table_cell), Paragraph("&gt; 1200 ppm (High)", table_cell), Paragraph("&lt; 3.0 NTU", table_cell), Paragraph("HAZARDOUS (Mineral Overload)", table_cell)],
    ]
    t_demo = Table(demo_data, colWidths=[130, 90, 95, 107, 110])
    t_demo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_demo)
    
    # ---------------------------------------------------------
    # 10. ENGINEERING RISKS & MITIGATION STRATEGIES
    # ---------------------------------------------------------
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
    story.append(Paragraph("10. Engineering Challenges, Failure Modes & Mitigations", h1_style))
    story.append(Paragraph("• <b>Challenge 1: Cross-Probe Electrical Noise (Galvanic Coupling):</b> The TDS sensor applies an active AC excitation waveform into the fluid. When the high-impedance glass bulb pH probe is placed in the same liquid, this excitation introduces severe millivolt offsets, corrupting the pH reading.<br/>"
                           "&nbsp;&nbsp;&nbsp;&nbsp;<i>Mitigation Strategy:</i> Hardware Power Gating. The ESP32 drives an N-channel MOSFET switch (2N7000) that completely cuts power to the TDS excitation circuitry while the pH probe is being sampled. The sensors are never powered concurrently.", body_style))
    story.append(Paragraph("• <b>Challenge 2: ESP32 ADC Non-Linearity at Signal Margins:</b> The built-in 12-bit SAR ADC on the ESP32 exhibits significant non-linear saturation below 0.12V and above 2.80V.<br/>"
                           "&nbsp;&nbsp;&nbsp;&nbsp;<i>Mitigation Strategy:</i> Signal Conditioning & Multi-Point Calibration. All sensor amplifier boards are biased so their operational range falls between 0.40V and 2.40V (the linear region). Furthermore, the ESP-IDF `esp_adc_cal` library with eFuse Vref calibration is utilized.", body_style))
    story.append(Paragraph("• <b>Challenge 3: Sensor Bio-Fouling & Probe Degradation:</b> Submerging optical and glass sensors continuously leads to algal film deposition and electrolyte depletion in the pH reference junction.<br/>"
                           "&nbsp;&nbsp;&nbsp;&nbsp;<i>Mitigation Strategy:</i> Dip-and-Rinse Operational Protocol. AquaCheck is engineered as an on-demand spot tester rather than a continuous immersion buoy. A protective cap with 3M KCl soaking sponge is provided for probe storage.", body_style))
    
    # ---------------------------------------------------------
    # 11. EXPECTED DELIVERABLES & EVALUATOR SIGN-OFF
    # ---------------------------------------------------------
    story.append(Paragraph("11. Expected Deliverables & Academic Sign-off", h1_style))
    story.append(Paragraph(
        "Upon successful project completion, the following deliverables will be formally submitted for evaluation:<br/>"
        "1. Fully integrated, handheld AquaCheck prototype housed in a durable 3D-printed enclosure.<br/>"
        "2. Complete open-source firmware repository containing calibration math, FreeRTOS tasks, and OLED UI code.<br/>"
        "3. Experimental validation report analyzing accuracy benchmarks against certified reference buffer solutions.<br/>"
        "4. Project Demonstration Video and Technical Documentation Dossier.",
        body_style
    ))
    story.append(Spacer(1, 3))
    
    sign_data = [
        [
            Paragraph("<b>Prepared By:</b> ___________________________<br/>Student Investigator / Candidate", table_cell),
            Paragraph("<b>Endorsed By:</b> ___________________________<br/>Project Supervisor / Advisor", table_cell),
            Paragraph("<b>Department Approval:</b> ___________________________<br/>Head of Department / Examiner", table_cell)
        ],
        [
            Paragraph("Date: ____ / ____ / 2026", table_cell),
            Paragraph("Date: ____ / ____ / 2026", table_cell),
            Paragraph("Date: ____ / ____ / 2026", table_cell)
        ]
    ]
    t_sign = Table(sign_data, colWidths=[177, 177, 178])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_light),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sign)

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built: {filename}")

if __name__ == "__main__":
    create_pdf()
