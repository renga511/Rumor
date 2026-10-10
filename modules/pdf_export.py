"""
PDF Export Module - Generates analysis report as PDF
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os
from datetime import datetime

# ─── Font Registration ───────────────────────────────────────────────────────
def register_fonts():
    try:
        # Enable complex text layout (CTL) via harfbuzz globally
        try:
            from reportlab.lib.shaping import set_shaper
            set_shaper('harfbuzz')
        except:
            pass

        # Standard paths on Windows
        fonts_dir = 'C:\\Windows\\Fonts'
        times_path = os.path.join(fonts_dir, 'times.ttf')
        times_bd_path = os.path.join(fonts_dir, 'timesbd.ttf')
        # Nirmala UI for Indic scripts (Hindi, Tamil, etc.)
        indic_path = os.path.join(fonts_dir, 'Nirmala.ttc')

        if os.path.exists(times_path):
            pdfmetrics.registerFont(TTFont('Times-New-Roman', times_path))
            pdfmetrics.registerFont(TTFont('Times-New-Roman-Bold', times_bd_path))
        
        if os.path.exists(indic_path):
            # Register using TTFont. Shaping is enabled by default in RL 4.0 if uharfbuzz is present
            pdfmetrics.registerFont(TTFont('IndicFont', indic_path))
    except Exception as e:
        print(f"Font registration error: {e}")

register_fonts()

def generate_pdf_report(data):
    """Generate a professional PDF report of the fact-check analysis."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    
    # Custom styles - Using Times-New-Roman as requested
    title_style = ParagraphStyle('Title', parent=styles['Title'],
        fontSize=22, textColor=colors.HexColor('#0f172a'),
        spaceAfter=6, fontName='Times-New-Roman-Bold', alignment=TA_CENTER)
    
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#64748b'),
        spaceAfter=20, alignment=TA_CENTER, fontName='Times-New-Roman')

    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#1e40af'),
        spaceBefore=14, spaceAfter=6, fontName='Times-New-Roman-Bold')

    body_style = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#1e293b'),
        spaceAfter=8, leading=15, fontName='Times-New-Roman')
    
    # Special style for Indic scripts (Tamil, Hindi, etc.)
    # Enable shaping=1 to force complex text layout in ReportLab 4.0+
    indic_body_style = ParagraphStyle('IndicBody', parent=body_style,
        fontName='IndicFont', fontSize=10, shaping=1)
    
    indic_verdict_style = ParagraphStyle('IndicV', parent=body_style,
        fontSize=14, textColor=colors.HexColor('#166534'), 
        fontName='IndicFont', shaping=1) # Fallback to Indic for verdict if needed

    story = []

    # Header
    story.append(Paragraph("🌐 AI Rumor Propagation Analyzer", title_style))
    story.append(Paragraph(f"Analysis Report  |  Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3b82f6'), spaceAfter=16))

    # Claim
    claim = data.get("claim", "Unknown claim")
    story.append(Paragraph("Analyzed Claim", heading_style))
    # Use Indic style for the claim to ensure local languages load correctly
    claim_table = Table([[Paragraph(f'"{claim}"', indic_body_style)]], colWidths=[17*cm])
    claim_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eff6ff')),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor('#3b82f6')),
        ('ROUNDEDCORNERS', [6]),
        ('PADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(claim_table)
    story.append(Spacer(1, 4))
    
    # Translation Info (if applicable)
    if data.get("original_language") and data.get("original_language") != "en":
        story.append(Paragraph(f"<b>Detected Language:</b> {data.get('original_language').upper()}", body_style))
        story.append(Paragraph(f"<b>English Translation:</b> {data.get('translated_text')}", body_style))
    
    story.append(Spacer(1, 12))

    # Verdict
    verdict = data.get("prediction", "INCONCLUSIVE")
    verdict_cls = data.get("verdict_cls", "inconclusive")
    confidence = data.get("confidence", 50)
    
    verdict_color = {'real': '#166534', 'fake': '#991b1b'}.get(verdict_cls, '#78350f')
    verdict_bg = {'real': '#dcfce7', 'fake': '#fee2e2'}.get(verdict_cls, '#fef3c7')

    story.append(Paragraph("Verdict", heading_style))
    # Verdict text also uses IndicFont as fallback for symbols/local text
    verdict_data = [
        [Paragraph(f"<b>{verdict}</b>", ParagraphStyle('V', fontSize=14, textColor=colors.HexColor(verdict_color), fontName='IndicFont'))],
        [Paragraph(f"Confidence Score: {confidence}%", ParagraphStyle('C', fontSize=11, textColor=colors.HexColor(verdict_color), fontName='Times-New-Roman'))]
    ]
    vt = Table(verdict_data, colWidths=[17*cm])
    vt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(verdict_bg)),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor(verdict_color)),
        ('PADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(vt)
    story.append(Spacer(1, 12))

    # AI Summary Section
    ai_summary = data.get("ai_summary")
    if ai_summary:
        story.append(Paragraph("AI Intelligent Summary", heading_style))
        # Use IndicFont for the AI summary which might be in local language
        ai_table = Table([[Paragraph(ai_summary, indic_body_style)]], colWidths=[17*cm])
        ai_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
            ('LINEABOVE', (0,0), (-1,0), 1, colors.HexColor('#4ade80')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(ai_table)
        story.append(Spacer(1, 12))

    # Score Breakdown
    breakdown = data.get("score_breakdown", {})
    if breakdown:
        story.append(Paragraph("Score Breakdown", heading_style))
        score_rows = [
            [Paragraph("<b>Factor</b>", body_style), Paragraph("<b>Score</b>", body_style)],
            ["Wikipedia Match", str(breakdown.get("wikipedia_score", 0))],
            ["Live RSS News", str(breakdown.get("rss_score", 0))],
            ["Reputable Sources Bonus", f"+{breakdown.get('rep_bonus', 0)}"],
            ["Keyword Boost", f"+{breakdown.get('keyword_boost', 0)}"],
            ["Penalty (low coverage)", f"-{breakdown.get('keyword_penalty', 0)}"],
        ]
        st = Table(score_rows, colWidths=[12*cm, 5*cm])
        st.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(st)
        story.append(Spacer(1, 12))

    # Sources
    sources = data.get("top_sources", [])
    if sources:
        story.append(Paragraph("Sources Found", heading_style))
        for i, src in enumerate(sources[:8], 1):
            src_title = src.get("title", "")[:90]
            src_name = src.get("source", "")
            rep = "✓ Reputable" if src.get("reputable") else ""
            story.append(Paragraph(
                f"<b>{i}.</b> [{src_name}] {src_title} <i>{rep}</i>",
                body_style
            ))
        story.append(Spacer(1, 12))

    # Regional coverage
    regions = data.get("hits_by_region", {})
    if regions:
        story.append(Paragraph("Regional Coverage", heading_style))
        reg_rows = [[Paragraph("<b>Region</b>", body_style), Paragraph("<b>News Hits</b>", body_style)]]
        for region, count in regions.items():
            reg_rows.append([region, str(count)])
        rt = Table(reg_rows, colWidths=[12*cm, 5*cm])
        rt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(rt)
        story.append(Spacer(1, 12))

    # Propagation Analysis (Professional Description)
    story.append(Paragraph("Network Propagation Analysis", heading_style))
    is_true = data.get("is_true_news", False)
    if is_true:
        propagation_desc = (
            "Based on the verified nature of this news, the simulation indicates a 'Green Network' spread pattern. "
            "Information propagates through high-authority nodes (influencers) who act as validators. "
            "The spread is sustained by high credibility, leading to organic and rapid adoption across the network topology."
        )
    else:
        propagation_desc = (
            "The system identifies this as a potential rumor, triggering a 'Red Network' spread pattern. "
            "Rumors typically exploit emotional triggers and spread through echo chambers. The simulation shows "
            "rapid initial infestation (infected nodes) which can be contained via strategic mass-immunization or "
            "influencer-led correction campaigns."
        )
    
    story.append(Paragraph(propagation_desc, body_style))
    story.append(Paragraph(
        f"<b>Simulation Parameters:</b> Network Type: Scale-Free (BA), Node Count: 300, Spread Basis: {'Truth Verification' if is_true else 'Rumor Infestation'}",
        ParagraphStyle('Small', parent=body_style, fontSize=9, italic=True)
    ))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#94a3b8')))
    story.append(Paragraph(
        "Generated by AI Rumor Propagation Simulator | For academic and research purposes only.",
        ParagraphStyle('Footer', fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
