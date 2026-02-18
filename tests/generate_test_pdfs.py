"""Generate synthetic test PDFs for the claims-packet-agent.

Creates multiple test scenarios with different document type combinations
to exercise the full pipeline including the 4 new document types.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_docs")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="SmallRight", parent=styles["Normal"], fontSize=8, alignment=TA_RIGHT))
styles.add(ParagraphStyle(name="Header", parent=styles["Normal"], fontSize=14, spaceAfter=6, textColor=colors.HexColor("#003366")))
styles.add(ParagraphStyle(name="SubHeader", parent=styles["Normal"], fontSize=11, spaceAfter=4, textColor=colors.HexColor("#336699")))
styles.add(ParagraphStyle(name="SmallBold", parent=styles["Normal"], fontSize=9, spaceAfter=2))
styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9))
styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER))


def _table(data, col_widths=None, header=True):
    """Build a formatted table."""
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style_cmds))
    return t


# ─── Scenario 1: Dental visit with EOB mismatch ────────────────────────────

def make_dental_claim():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_5_dental_billing_mismatch", "dental_claim_bright_smiles.pdf"), pagesize=letter)
    story = []
    story.append(Paragraph("ADA Dental Claim Form", styles["TitleCenter"]))
    story.append(Spacer(1, 12))

    info = [
        ["Patient Name:", "Maria Gonzalez", "Date of Birth:", "04/15/1985"],
        ["Member ID:", "DEN-9987654", "Group #:", "GRP-5500"],
        ["Insurance:", "Delta Dental PPO", "Policy #:", "DD-2024-5500"],
    ]
    story.append(_table(info, col_widths=[1.2*inch, 2*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Billing Provider", styles["SubHeader"]))
    story.append(Paragraph("Bright Smiles Dental Group<br/>NPI: 1234567890<br/>456 Oak Avenue, Suite 200, Austin, TX 78701", styles["Small"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Treating Dentist: Dr. James Chen, DDS", styles["SmallBold"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Service Lines", styles["SubHeader"]))
    svc = [
        ["Date", "Tooth #", "Surface", "CDT Code", "Description", "Fee"],
        ["01/10/2025", "14", "MOD", "D2392", "Resin composite - 3 surfaces, posterior", "$285.00"],
        ["01/10/2025", "19", "O", "D2391", "Resin composite - 2 surfaces, posterior", "$215.00"],
        ["01/10/2025", "", "", "D0120", "Periodic oral evaluation", "$55.00"],
        ["01/10/2025", "", "", "D1110", "Prophylaxis - adult", "$120.00"],
        ["01/10/2025", "", "", "D0274", "Bitewing - four radiographic images", "$65.00"],
    ]
    story.append(_table(svc, col_widths=[0.8*inch, 0.6*inch, 0.6*inch, 0.8*inch, 2.5*inch, 0.8*inch]))
    story.append(Spacer(1, 12))

    totals = [
        ["Total Fee:", "$740.00"],
        ["Diagnosis Codes:", "K02.52, K05.10"],
    ]
    story.append(_table(totals, col_widths=[2*inch, 2*inch], header=False))

    doc.build(story)


def make_dental_eob():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_5_dental_billing_mismatch", "eob_delta_dental.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("EXPLANATION OF BENEFITS", styles["TitleCenter"]))
    story.append(Paragraph("Delta Dental PPO", styles["TitleCenter"]))
    story.append(Spacer(1, 12))

    info = [
        ["Claim #:", "DDC-2025-00891", "Date Processed:", "01/25/2025"],
        ["Patient:", "Maria Gonzalez", "Member ID:", "DEN-9987654"],
        ["Provider:", "Bright Smiles Dental Group", "Date of Service:", "01/10/2025"],
    ]
    story.append(_table(info, col_widths=[1.2*inch, 2*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    # Intentional mismatch: allowed less than billed for composite fillings
    lines = [
        ["CDT Code", "Description", "Billed", "Allowed", "Ins Paid", "Patient Resp", "Remark"],
        ["D2392", "Resin composite 3 surf post", "$285.00", "$195.00", "$156.00", "$39.00", ""],
        ["D2391", "Resin composite 2 surf post", "$215.00", "$155.00", "$124.00", "$31.00", ""],
        ["D0120", "Periodic oral evaluation", "$55.00", "$45.00", "$45.00", "$0.00", ""],
        ["D1110", "Prophylaxis - adult", "$120.00", "$95.00", "$76.00", "$19.00", ""],
        ["D0274", "Bitewing x-rays", "$65.00", "$52.00", "$41.60", "$10.40", ""],
    ]
    story.append(_table(lines, col_widths=[0.7*inch, 1.8*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.7*inch]))
    story.append(Spacer(1, 12))

    totals = [
        ["Total Billed:", "$740.00"],
        ["Total Allowed:", "$542.00"],
        ["Insurance Paid:", "$442.60"],
        ["Patient Responsibility:", "$99.40"],
    ]
    story.append(_table(totals, col_widths=[2.5*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Claim Status: PROCESSED", styles["SmallBold"]))
    story.append(Paragraph("Note: Amounts exceeding the allowed amount are the patient's responsibility per plan terms.", styles["Small"]))

    doc.build(story)


def make_dental_bill():
    """Bill that charges more than EOB allowed - triggers billing reconciliation."""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_5_dental_billing_mismatch", "bill_bright_smiles.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("PATIENT STATEMENT", styles["TitleCenter"]))
    story.append(Paragraph("Bright Smiles Dental Group", styles["Header"]))
    story.append(Paragraph("456 Oak Avenue, Suite 200, Austin, TX 78701<br/>Phone: (512) 555-0199", styles["Small"]))
    story.append(Spacer(1, 12))

    info = [
        ["Patient:", "Maria Gonzalez", "Account #:", "BSG-44210"],
        ["Statement Date:", "02/01/2025", "Date of Service:", "01/10/2025"],
    ]
    story.append(_table(info, col_widths=[1.2*inch, 2*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    # Bill charges the full billed amount minus insurance paid, not the allowed amount
    # This means balance_due = $297.40 instead of the correct $99.40 from EOB
    charges = [
        ["CPT/CDT", "Description", "Amount"],
        ["D2392", "Resin composite - 3 surfaces", "$285.00"],
        ["D2391", "Resin composite - 2 surfaces", "$215.00"],
        ["D0120", "Periodic oral evaluation", "$55.00"],
        ["D1110", "Prophylaxis - adult", "$120.00"],
        ["D0274", "Bitewing radiographs", "$65.00"],
    ]
    story.append(_table(charges, col_widths=[1*inch, 3*inch, 1*inch]))
    story.append(Spacer(1, 12))

    summary = [
        ["Total Charges:", "$740.00"],
        ["Insurance Payment:", "-$442.60"],
        ["Balance Due:", "$297.40"],
    ]
    story.append(_table(summary, col_widths=[2*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>AMOUNT DUE: $297.40</b>", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Payment due within 30 days. Please contact our billing department with questions.", styles["Small"]))

    doc.build(story)


# ─── Scenario 2: Prior Auth approved but EOB denied ─────────────────────────

def make_prior_auth_approved():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_6_prior_auth_vs_denial", "prior_auth_bcbs_approved.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("PRIOR AUTHORIZATION APPROVAL", styles["TitleCenter"]))
    story.append(Paragraph("BlueCross BlueShield of Texas", styles["Header"]))
    story.append(Spacer(1, 12))

    info = [
        ["Authorization #:", "PA-2025-78432", "Date Issued:", "12/15/2024"],
        ["Patient:", "Robert Williams", "Member ID:", "BCB-5567890"],
        ["Requesting Provider:", "Advanced Orthopedics Associates", "NPI:", "9876543210"],
        ["Plan:", "BCBS PPO Gold", "Group #:", "EMP-7700"],
    ]
    story.append(_table(info, col_widths=[1.5*inch, 2*inch, 1*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Authorization Status: APPROVED", styles["SubHeader"]))
    story.append(Paragraph("Authorization Type: Elective Surgical Procedure", styles["SmallBold"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Authorized Services", styles["SubHeader"]))
    svcs = [
        ["CPT Code", "Description", "Qty", "Approved Amount"],
        ["27447", "Total knee arthroplasty", "1", "$32,500.00"],
        ["99213", "Office visit - established patient (post-op)", "3", "$450.00"],
    ]
    story.append(_table(svcs, col_widths=[1*inch, 3*inch, 0.5*inch, 1.5*inch]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Details", styles["SubHeader"]))
    details = [
        ["Effective Date:", "01/01/2025"],
        ["Expiration Date:", "06/30/2025"],
        ["Place of Service:", "Inpatient Hospital"],
        ["Diagnosis Codes:", "M17.11 (Primary osteoarthritis, right knee)"],
        ["Total Approved Amount:", "$32,950.00"],
    ]
    story.append(_table(details, col_widths=[2*inch, 4*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Conditions:", styles["SmallBold"]))
    story.append(Paragraph("1. Services must be rendered within the effective date range.<br/>"
                           "2. Must be performed at an in-network facility.<br/>"
                           "3. Pre-operative clearance documentation required.", styles["Small"]))

    doc.build(story)


def make_denied_eob_with_prior_auth():
    """EOB that denies a service that was pre-authorized - triggers prior_auth_vs_denial."""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_6_prior_auth_vs_denial", "eob_bcbs_denied.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("EXPLANATION OF BENEFITS", styles["TitleCenter"]))
    story.append(Paragraph("BlueCross BlueShield of Texas", styles["Header"]))
    story.append(Spacer(1, 12))

    info = [
        ["Claim #:", "BCBS-2025-44321", "Date Processed:", "02/10/2025"],
        ["Patient:", "Robert Williams", "Member ID:", "BCB-5567890"],
        ["Provider:", "Advanced Orthopedics Associates", "Date of Service:", "01/20/2025"],
    ]
    story.append(_table(info, col_widths=[1.2*inch, 2*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Claim Status: DENIED", styles["SubHeader"]))
    story.append(Spacer(1, 8))

    lines = [
        ["CPT", "Description", "Billed", "Allowed", "Ins Paid", "Patient Resp", "Denial Reason"],
        ["27447", "Total knee arthroplasty", "$38,500.00", "$0.00", "$0.00", "$38,500.00",
         "Not medically necessary per plan guidelines"],
        ["99213", "Office visit post-op", "$175.00", "$0.00", "$0.00", "$175.00",
         "Associated with denied primary service"],
    ]
    story.append(_table(lines, col_widths=[0.6*inch, 1.5*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.8*inch, 1.4*inch]))
    story.append(Spacer(1, 12))

    totals = [
        ["Total Billed:", "$38,675.00"],
        ["Total Allowed:", "$0.00"],
        ["Insurance Paid:", "$0.00"],
        ["Patient Responsibility:", "$38,675.00"],
    ]
    story.append(_table(totals, col_widths=[2.5*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Appeal Deadline: 04/10/2025", styles["SmallBold"]))
    story.append(Paragraph("To appeal this decision, submit a written request with supporting medical documentation "
                           "to: BCBS Appeals Department, PO Box 660044, Dallas, TX 75266-0044", styles["Small"]))

    doc.build(story)


def make_knee_hospital_bill():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_6_prior_auth_vs_denial", "bill_st_davids_hospital.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("HOSPITAL BILLING STATEMENT", styles["TitleCenter"]))
    story.append(Paragraph("St. David's Medical Center", styles["Header"]))
    story.append(Paragraph("919 E 32nd Street, Austin, TX 78705", styles["Small"]))
    story.append(Spacer(1, 12))

    info = [
        ["Patient:", "Robert Williams", "Account #:", "SDM-88210"],
        ["Admission:", "01/20/2025", "Discharge:", "01/22/2025"],
        ["Attending:", "Advanced Orthopedics Associates", "", ""],
    ]
    story.append(_table(info, col_widths=[1.2*inch, 2*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    charges = [
        ["CPT Code", "Description", "Amount"],
        ["27447", "Total knee replacement", "$38,500.00"],
        ["99213", "Post-op evaluation", "$175.00"],
    ]
    story.append(_table(charges, col_widths=[1*inch, 3.5*inch, 1.2*inch]))
    story.append(Spacer(1, 12))

    summary = [
        ["Total Charges:", "$38,675.00"],
        ["Insurance Payment:", "$0.00"],
        ["Balance Due:", "$38,675.00"],
    ]
    story.append(_table(summary, col_widths=[2*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>BALANCE DUE: $38,675.00</b>", styles["Normal"]))

    doc.build(story)


# ─── Scenario 3: Appeal overturned + itemized statement ──────────────────────

def make_appeal_decision():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_7_appeal_overturned_itemized", "appeal_decision_aetna_overturned.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("APPEAL DECISION LETTER", styles["TitleCenter"]))
    story.append(Paragraph("Aetna Health Insurance", styles["Header"]))
    story.append(Paragraph("151 Farmington Avenue, Hartford, CT 06156", styles["Small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("February 5, 2025", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("RE: Appeal of Denied Claim", styles["SubHeader"]))
    story.append(Spacer(1, 8))

    info = [
        ["Appeal Reference #:", "APL-2025-33201"],
        ["Original Claim #:", "AET-2024-99876"],
        ["Patient:", "Susan Park"],
        ["Member ID:", "AET-3345678"],
        ["Provider:", "Capital City Surgical Center"],
        ["Date of Service:", "11/15/2024"],
        ["Original Authorization #:", "AUTH-2024-55678"],
    ]
    story.append(_table(info, col_widths=[2*inch, 4*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Original Denial Information", styles["SubHeader"]))
    story.append(Paragraph("Original Denial Date: 12/01/2024<br/>"
                           "Original Denial Reason: Procedure not medically necessary - conservative treatment "
                           "not fully exhausted<br/>"
                           "Original Billed Amount: $14,250.00", styles["Small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Appeal Decision: OVERTURNED", styles["SubHeader"]))
    story.append(Paragraph("Appeal Level: Level 1 - Internal Review", styles["SmallBold"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Decision Rationale:", styles["SmallBold"]))
    story.append(Paragraph(
        "After thorough review of the submitted medical records, including documentation of 6 months "
        "of physical therapy, two cortisone injections, and MRI findings showing significant labral tear, "
        "the medical reviewer has determined that the arthroscopic procedure (CPT 29881) was medically "
        "necessary. The original denial is hereby overturned.", styles["Small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Approved Services", styles["SubHeader"]))
    svcs = [
        ["CPT Code", "Description", "Approved Amount"],
        ["29881", "Arthroscopy, knee, surgical; with meniscectomy", "$8,500.00"],
        ["29877", "Arthroscopy, knee, debridement/shaving", "$3,200.00"],
        ["99213", "Post-operative follow-up visit", "$550.00"],
    ]
    story.append(_table(svcs, col_widths=[1*inch, 3.5*inch, 1.5*inch]))
    story.append(Spacer(1, 12))

    summary = [
        ["Approved Amount:", "$12,250.00"],
        ["Adjusted Patient Responsibility:", "$2,000.00"],
    ]
    story.append(_table(summary, col_widths=[2.5*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 8))
    story.append(Paragraph("CPT Codes: 29881, 29877, 99213", styles["SmallBold"]))
    story.append(Paragraph("Diagnosis Codes: M23.211, S83.511A", styles["SmallBold"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Please allow 10-15 business days for reprocessing of the claim and issuance of payment.", styles["Small"]))

    doc.build(story)


def make_itemized_statement():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_7_appeal_overturned_itemized", "itemized_statement_capital_city.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("ITEMIZED STATEMENT", styles["TitleCenter"]))
    story.append(Paragraph("Capital City Surgical Center", styles["Header"]))
    story.append(Paragraph("1200 Congress Avenue, Austin, TX 78701<br/>Phone: (512) 555-0300", styles["Small"]))
    story.append(Spacer(1, 12))

    info = [
        ["Patient:", "Susan Park", "Account #:", "CCSC-77891"],
        ["Medical Record #:", "MRN-554432", "Statement Date:", "02/10/2025"],
        ["Admission Date:", "11/15/2024", "Discharge Date:", "11/15/2024"],
        ["Date of Service:", "11/15/2024", "", ""],
    ]
    story.append(_table(info, col_widths=[1.5*inch, 1.8*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Itemized Charges", styles["SubHeader"]))
    charges = [
        ["Date", "Rev Code", "CPT", "Department", "Description", "Qty", "Unit Price", "Amount"],
        ["11/15/24", "0360", "29881", "OR", "Arthroscopy - meniscectomy", "1", "$8,500.00", "$8,500.00"],
        ["11/15/24", "0360", "29877", "OR", "Arthroscopy - debridement", "1", "$3,200.00", "$3,200.00"],
        ["11/15/24", "0370", "", "Anesthesia", "General anesthesia - 90 min", "1", "$1,800.00", "$1,800.00"],
        ["11/15/24", "0250", "", "Pharmacy", "Ketorolac 30mg IV", "2", "$12.50", "$25.00"],
        ["11/15/24", "0250", "", "Pharmacy", "Ondansetron 4mg IV", "1", "$8.00", "$8.00"],
        ["11/15/24", "0270", "", "Supplies", "Surgical supplies", "1", "$425.00", "$425.00"],
        ["11/15/24", "0710", "", "Recovery", "Recovery room - 2 hours", "1", "$292.00", "$292.00"],
    ]
    story.append(_table(charges, col_widths=[0.6*inch, 0.5*inch, 0.5*inch, 0.7*inch, 1.8*inch, 0.3*inch, 0.7*inch, 0.7*inch]))
    story.append(Spacer(1, 12))

    summary = [
        ["Total Charges:", "$14,250.00"],
        ["Adjustments:", "-$0.00"],
        ["Insurance Payments:", "-$0.00"],
        ["Patient Payments:", "-$0.00"],
        ["Balance Due:", "$14,250.00"],
    ]
    story.append(_table(summary, col_widths=[2*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Total Line Items: 7 | Page: 1 of 1", styles["Small"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Note: Insurance claim is under appeal. Balance may be adjusted upon resolution.", styles["Small"]))

    doc.build(story)


def make_appeal_eob():
    """EOB showing the original denial that was later appealed."""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_7_appeal_overturned_itemized", "eob_aetna_denied.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("EXPLANATION OF BENEFITS", styles["TitleCenter"]))
    story.append(Paragraph("Aetna Health Insurance", styles["Header"]))
    story.append(Spacer(1, 12))

    info = [
        ["Claim #:", "AET-2024-99876", "Date Processed:", "12/01/2024"],
        ["Patient:", "Susan Park", "Member ID:", "AET-3345678"],
        ["Provider:", "Capital City Surgical Center", "Date of Service:", "11/15/2024"],
    ]
    story.append(_table(info, col_widths=[1.2*inch, 2*inch, 1.2*inch, 2*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Claim Status: DENIED", styles["SubHeader"]))
    story.append(Spacer(1, 8))

    lines = [
        ["CPT", "Description", "Billed", "Allowed", "Ins Paid", "Patient Resp", "Denial Reason"],
        ["29881", "Arthroscopy - meniscectomy", "$8,500.00", "$0.00", "$0.00", "$8,500.00",
         "Not medically necessary"],
        ["29877", "Arthroscopy - debridement", "$3,200.00", "$0.00", "$0.00", "$3,200.00",
         "Not medically necessary"],
        ["99213", "Post-op follow-up", "$550.00", "$0.00", "$0.00", "$550.00",
         "Associated with denied service"],
    ]
    story.append(_table(lines, col_widths=[0.6*inch, 1.5*inch, 0.7*inch, 0.6*inch, 0.6*inch, 0.8*inch, 1.5*inch]))
    story.append(Spacer(1, 12))

    totals = [
        ["Total Billed:", "$12,250.00"],
        ["Insurance Paid:", "$0.00"],
        ["Patient Responsibility:", "$12,250.00"],
    ]
    story.append(_table(totals, col_widths=[2.5*inch, 1.5*inch], header=False))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Appeal Deadline: 03/01/2025", styles["SmallBold"]))
    story.append(Paragraph("You have the right to appeal this decision. Submit appeal to Aetna Appeals, "
                           "PO Box 14463, Lexington, KY 40512.", styles["Small"]))

    doc.build(story)


# ─── Scenario 4: Denied prior auth with appeal upheld ────────────────────────

def make_denied_prior_auth():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_8_denied_prior_auth_appeal_upheld", "prior_auth_uhc_denied.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("PRIOR AUTHORIZATION DETERMINATION", styles["TitleCenter"]))
    story.append(Paragraph("UnitedHealthcare", styles["Header"]))
    story.append(Spacer(1, 12))

    info = [
        ["Authorization #:", "UHC-PA-2025-12099"],
        ["Reference #:", "REF-667788"],
        ["Date:", "01/05/2025"],
        ["Patient:", "Thomas Anderson"],
        ["Member ID:", "UHC-7789012"],
        ["Requesting Provider:", "Spine & Pain Management Center"],
        ["Plan:", "UHC Choice Plus"],
        ["Group #:", "CORP-8800"],
    ]
    story.append(_table(info, col_widths=[2*inch, 4*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Authorization Status: DENIED", styles["SubHeader"]))
    story.append(Paragraph("Authorization Type: Surgical Procedure", styles["SmallBold"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Requested Services", styles["SubHeader"]))
    svcs = [
        ["CPT Code", "Description", "Qty", "Requested Amount"],
        ["22551", "Cervical fusion, anterior approach", "1", "$45,000.00"],
        ["22845", "Anterior instrumentation 2-3 vertebral segments", "1", "$12,000.00"],
    ]
    story.append(_table(svcs, col_widths=[1*inch, 3*inch, 0.5*inch, 1.5*inch]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Denial Reason:", styles["SmallBold"]))
    story.append(Paragraph(
        "The requested cervical fusion procedure does not meet medical necessity criteria at this time. "
        "Documentation does not demonstrate failure of conservative treatment including physical therapy "
        "(minimum 12 weeks), epidural steroid injections (minimum 2), and medication management.", styles["Small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Diagnosis Codes: M50.12 (Cervical disc disorder with radiculopathy, mid-cervical region)", styles["SmallBold"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Appeal Information", styles["SubHeader"]))
    appeal = [
        ["Appeal Deadline:", "04/05/2025"],
        ["Appeal Instructions:", "Submit written appeal with supporting medical records to: "
         "UHC Appeals, PO Box 30555, Salt Lake City, UT 84130-0555. "
         "Include documentation of conservative treatment attempts."],
    ]
    story.append(_table(appeal, col_widths=[1.5*inch, 4.5*inch], header=False))

    doc.build(story)


def make_appeal_upheld():
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "scenario_8_denied_prior_auth_appeal_upheld", "appeal_decision_uhc_upheld.pdf"), pagesize=letter)
    story = []

    story.append(Paragraph("APPEAL DECISION NOTICE", styles["TitleCenter"]))
    story.append(Paragraph("UnitedHealthcare", styles["Header"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("March 1, 2025", styles["Normal"]))
    story.append(Spacer(1, 8))

    info = [
        ["Appeal Reference #:", "UHC-APL-2025-08844"],
        ["Original Claim #:", "UHC-CLM-2025-45600"],
        ["Original Authorization #:", "UHC-PA-2025-12099"],
        ["Patient:", "Thomas Anderson"],
        ["Member ID:", "UHC-7789012"],
        ["Provider:", "Spine & Pain Management Center"],
        ["Date of Service:", "N/A (pre-service denial)"],
    ]
    story.append(_table(info, col_widths=[2*inch, 4*inch], header=False))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Original Denial", styles["SubHeader"]))
    story.append(Paragraph("Original Denial Date: 01/05/2025<br/>"
                           "Original Denial Reason: Procedure not medically necessary - conservative treatment "
                           "not fully exhausted<br/>"
                           "Original Billed Amount: $57,000.00", styles["Small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Appeal Decision: UPHELD (Denial Stands)", styles["SubHeader"]))
    story.append(Paragraph("Appeal Level: Level 1 - Internal Review<br/>"
                           "Decision Date: 03/01/2025", styles["SmallBold"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Decision Rationale:", styles["SmallBold"]))
    story.append(Paragraph(
        "The medical review panel has upheld the original denial. While the submitted documentation "
        "includes 8 weeks of physical therapy records, the plan criteria requires a minimum of 12 weeks. "
        "Additionally, only one epidural steroid injection was documented; two are required before surgical "
        "intervention will be considered. The reviewer recommends completing the required conservative "
        "treatment course before resubmission.", styles["Small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("CPT Codes: 22551, 22845", styles["SmallBold"]))
    story.append(Paragraph("Diagnosis Codes: M50.12", styles["SmallBold"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Next Steps", styles["SubHeader"]))
    next_steps = [
        ["Next Appeal Level:", "Level 2 - External Independent Review"],
        ["Next Appeal Deadline:", "06/01/2025"],
        ["External Review Available:", "Yes"],
        ["External Review Instructions:",
         "You may request an independent external review by contacting the Texas Department of Insurance "
         "at 1-800-252-3439 or submitting a request online at www.tdi.texas.gov. An external review must "
         "be requested within 4 months of this decision."],
    ]
    story.append(_table(next_steps, col_widths=[2*inch, 4.5*inch], header=False))

    doc.build(story)


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Create scenario subdirectories
    scenarios = [
        "scenario_5_dental_billing_mismatch",
        "scenario_6_prior_auth_vs_denial",
        "scenario_7_appeal_overturned_itemized",
        "scenario_8_denied_prior_auth_appeal_upheld",
    ]
    for s in scenarios:
        os.makedirs(os.path.join(OUTPUT_DIR, s), exist_ok=True)

    print("Generating Scenario 5: Dental visit with billing mismatch...")
    make_dental_claim()
    make_dental_eob()
    make_dental_bill()

    print("Generating Scenario 6: Prior auth approved but EOB denied...")
    make_prior_auth_approved()
    make_denied_eob_with_prior_auth()
    make_knee_hospital_bill()

    print("Generating Scenario 7: Appeal overturned + itemized statement...")
    make_appeal_decision()
    make_itemized_statement()
    make_appeal_eob()

    print("Generating Scenario 8: Denied prior auth + appeal upheld...")
    make_denied_prior_auth()
    make_appeal_upheld()

    # List what was created
    total = 0
    for s in scenarios:
        scenario_dir = os.path.join(OUTPUT_DIR, s)
        files = sorted(f for f in os.listdir(scenario_dir) if f.endswith(".pdf"))
        total += len(files)
        print(f"\n{s}/")
        for f in files:
            size = os.path.getsize(os.path.join(scenario_dir, f))
            print(f"  {f} ({size:,} bytes)")
    print(f"\nTotal: {total} PDFs generated")
