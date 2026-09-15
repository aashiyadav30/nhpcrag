"""
Sample PDF Generator Script
Creates sample PDF documents (Company Leave Policy & IT Security Guide) for testing RAG.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

SAMPLE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def create_leave_policy_pdf():
    pdf_path = SAMPLE_DIR / "Company_Leave_Policy.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    story = []
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    # Page 1: Annual Leave & Sick Leave
    story.append(Paragraph("Acme Corp - Employee Leave Policy 2026", title_style))
    story.append(Paragraph("Document Reference: POL-HR-2026-01 | Effective Date: Jan 1, 2026", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Annual Paid Leave Allowance", heading_style))
    story.append(Paragraph(
        "All full-time employees of Acme Corp are entitled to 24 business days of paid annual leave per calendar year. "
        "Leave accrues at the rate of 2.0 days per completed month of continuous service.", body_style
    ))
    story.append(Paragraph(
        "A maximum of 8 unused annual leave days may be carried forward into the next calendar year. "
        "Carried-forward days must be utilized before March 31st of the new year, after which they expire.", body_style
    ))

    story.append(Paragraph("2. Sick and Medical Leave", heading_style))
    story.append(Paragraph(
        "Employees are granted 12 days of paid sick leave annually. Sick leave is intended for personal medical illness, "
        "doctor appointments, or caring for immediate family members.", body_style
    ))
    story.append(Paragraph(
        "For any continuous sick leave exceeding 3 consecutive business days, a certified medical certificate signed "
        "by a licensed healthcare practitioner must be submitted to HR within 48 hours of returning to work.", body_style
    ))

    # Page 2: Parental Leave & Emergency Leave
    story.append(PageBreak())
    story.append(Paragraph("Acme Corp - Employee Leave Policy 2026 (Continued)", title_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Parental and Family Leave", heading_style))
    story.append(Paragraph(
        "Primary caregivers (maternity leave) are eligible for 16 weeks of fully paid parental leave. "
        "Secondary caregivers (paternity leave) are eligible for 4 weeks of fully paid parental leave.", body_style
    ))
    story.append(Paragraph(
        "Parental leave must be requested at least 30 days prior to the expected date of birth or adoption placement.", body_style
    ))

    story.append(Paragraph("4. Casual and Emergency Leave", heading_style))
    story.append(Paragraph(
        "Employees receive 5 days of casual leave per year for urgent personal matters. Casual leave cannot be combined "
        "with annual leave without prior written approval from the department head.", body_style
    ))

    story.append(Paragraph("5. Leave Application & Approval Process", heading_style))
    story.append(Paragraph(
        "All leave requests must be submitted through the internal HR Portal at least 5 business days in advance for annual leave. "
        "Urgent casual or sick leave must be reported to the line manager by 9:00 AM on the day of absence.", body_style
    ))

    doc.build(story)
    print(f"Created: {pdf_path}")


def create_it_guide_pdf():
    pdf_path = SAMPLE_DIR / "IT_Security_and_Equipment_Guide.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    story = []
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    # Page 1: Password & VPN
    story.append(Paragraph("Acme Corp - IT Security & Remote Equipment Guide", title_style))
    story.append(Paragraph("Document Reference: POL-IT-2026-04 | Department: Information Technology", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Password Security Standards", heading_style))
    story.append(Paragraph(
        "All corporate user accounts require passwords to be a minimum of 14 characters in length, including at least one uppercase letter, "
        "one lowercase letter, one numeric digit, and one special character (!@#$%^&*). Passwords expire every 90 days.", body_style
    ))
    story.append(Paragraph(
        "Multi-Factor Authentication (MFA) via the official Authenticator App is mandatory for all system logins.", body_style
    ))

    story.append(Paragraph("2. Remote Access and VPN Usage", heading_style))
    story.append(Paragraph(
        "Employees connecting from remote locations or home networks MUST connect through the Acme Secure VPN (vpn.acme.corp). "
        "Connecting to company servers or intranet resources over unsecured public Wi-Fi without VPN is strictly prohibited.", body_style
    ))

    # Page 2: Laptop & Hardware Policy
    story.append(PageBreak())
    story.append(Paragraph("Acme Corp - IT Security & Remote Equipment Guide (Continued)", title_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Laptop Hardware Replacement & Upgrades", heading_style))
    story.append(Paragraph(
        "Company-issued laptops are eligible for standard hardware replacement every 3 years. "
        "In the event of hardware malfunction or accidental damage, submit a ticket to IT Support (support@acme.corp).", body_style
    ))
    story.append(Paragraph(
        "Hardware repair requests are typically fulfilled within 24 to 48 business hours. Temporary loaner laptops are available upon request.", body_style
    ))

    doc.build(story)
    print(f"Created: {pdf_path}")


if __name__ == "__main__":
    create_leave_policy_pdf()
    create_it_guide_pdf()
