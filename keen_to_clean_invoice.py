"""
Keen To Clean — Invoice Calculator
Reads jobs from a CSV, applies royalty (10% or 20%), admin (5%),
insurance ($100 flat per job), and saves a PDF invoice.
"""

import csv
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

# ── Constants ────────────────────────────────────────────────────────────────
ADMIN_RATE    = 0.05
INSURANCE_FEE = 100.00
BRAND_NAME    = "Keen To Clean"
BRAND_TAGLINE = "Professional Cleaning Services"

TEAL  = colors.HexColor("#009999")
DARK  = colors.HexColor("#1e1e1e")
LIGHT = colors.HexColor("#f0fafa")
GREEN = colors.HexColor("#00a050")
RED   = colors.HexColor("#cc1e1e")
GREY  = colors.HexColor("#787878")
WHITE = colors.white

# ── Data loading ─────────────────────────────────────────────────────────────
def load_jobs(csv_path: str) -> list[dict]:
    """Read jobs from CSV. Required columns:
       job_id, client_name, service_description, job_date, amount, royalty_rate
    """
    jobs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["amount"]       = float(row["amount"])
            row["royalty_rate"] = int(row["royalty_rate"])
            jobs.append(row)
    return jobs

# ── Calculation ───────────────────────────────────────────────────────────────
def calculate(job: dict) -> dict:
    gross   = job["amount"]
    royalty = gross * (job["royalty_rate"] / 100)
    admin   = gross * ADMIN_RATE
    net     = gross - royalty - admin - INSURANCE_FEE
    return {**job, "royalty": royalty, "admin": admin,
            "insurance": INSURANCE_FEE, "net": net}

# ── PDF builder ───────────────────────────────────────────────────────────────
def build_pdf(jobs_calc: list[dict], output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm,  bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Header banner ────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(
            f'<font color="white" size="18"><b>{BRAND_NAME}</b></font><br/>'
            f'<font color="white" size="9">{BRAND_TAGLINE}</font>',
            ParagraphStyle("hdr", parent=styles["Normal"], leading=22)
        ),
        Paragraph(
            f'<font color="white" size="9">Invoice No: <b>KTC-{date.today().strftime("%Y%m%d")}</b><br/>'
            f'Date: <b>{date.today().strftime("%d %B %Y")}</b></font>',
            ParagraphStyle("hdr_r", parent=styles["Normal"], alignment=TA_RIGHT, leading=14)
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[110*mm, 70*mm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), TEAL),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Jobs table ───────────────────────────────────────────────────────────
    col_w = [18*mm, 36*mm, 40*mm, 22*mm, 20*mm, 24*mm, 16*mm, 4*mm]  # last col dummy
    col_w = [18*mm, 36*mm, 40*mm, 22*mm, 20*mm, 24*mm, 20*mm]

    def h(text):
        return Paragraph(f'<b>{text}</b>',
                         ParagraphStyle("th", parent=styles["Normal"],
                                        fontSize=8, textColor=WHITE))
    def c(text, align=TA_LEFT, colour=DARK):
        return Paragraph(text,
                         ParagraphStyle("td", parent=styles["Normal"],
                                        fontSize=8, alignment=align,
                                        textColor=colour))

    table_data = [[
        h("Job ID"), h("Client"), h("Service"), h("Date"),
        Paragraph('<b>Gross ($)</b>',  ParagraphStyle("th_r", parent=styles["Normal"], fontSize=8, textColor=WHITE, alignment=TA_RIGHT)),
        Paragraph('<b>Royalty ($)</b>',ParagraphStyle("th_r", parent=styles["Normal"], fontSize=8, textColor=WHITE, alignment=TA_RIGHT)),
        Paragraph('<b>Net ($)</b>',    ParagraphStyle("th_r", parent=styles["Normal"], fontSize=8, textColor=WHITE, alignment=TA_RIGHT)),
    ]]

    for j in jobs_calc:
        net_colour = GREEN if j["net"] >= 0 else RED
        table_data.append([
            c(j["job_id"]),
            c(j["client_name"]),
            c(j["service_description"], colour=GREY),
            c(j["job_date"]),
            c(f'{j["amount"]:,.2f}',  align=TA_RIGHT),
            c(f'{j["royalty"]:,.2f} ({j["royalty_rate"]}%)', align=TA_RIGHT),
            c(f'{j["net"]:,.2f}',     align=TA_RIGHT, colour=net_colour),
        ])

    tbl = Table(table_data, colWidths=col_w, repeatRows=1)

    row_styles = [
        ("BACKGROUND", (0,0), (-1,0), TEAL),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#ccdddd")),
    ]
    for i in range(1, len(table_data)):
        bg = LIGHT if i % 2 == 0 else WHITE
        row_styles.append(("BACKGROUND", (0,i), (-1,i), bg))

    tbl.setStyle(TableStyle(row_styles))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    # ── Totals breakdown ─────────────────────────────────────────────────────
    total_gross     = sum(j["amount"]    for j in jobs_calc)
    total_royalty   = sum(j["royalty"]   for j in jobs_calc)
    total_admin     = sum(j["admin"]     for j in jobs_calc)
    total_insurance = sum(j["insurance"] for j in jobs_calc)
    total_net       = sum(j["net"]       for j in jobs_calc)
    n               = len(jobs_calc)
    rates           = ", ".join(sorted(set(f'{j["royalty_rate"]}%' for j in jobs_calc)))

    def summary_row(label, value, bold=False, val_colour=DARK):
        fs   = 9 if bold else 8
        wt   = "bold" if bold else "normal"
        lbl  = Paragraph(f'<{wt}>{label}</{wt}>',
                         ParagraphStyle("sl", parent=styles["Normal"],
                                        fontSize=fs, alignment=TA_RIGHT))
        amt  = Paragraph(f'<{wt}>${value:,.2f}</{wt}>',
                         ParagraphStyle("sv", parent=styles["Normal"],
                                        fontSize=fs, alignment=TA_RIGHT,
                                        textColor=val_colour))
        return [lbl, amt]

    summary_data = [
        summary_row("Total Gross Revenue:",     total_gross),
        summary_row(f"Less Royalties ({rates}):", total_royalty),
        summary_row("Less Admin (5%):",          total_admin),
        summary_row(f"Less Insurance (${INSURANCE_FEE:.0f} × {n} jobs):", total_insurance),
        summary_row("NET PAYABLE:", total_net, bold=True,
                    val_colour=GREEN if total_net >= 0 else RED),
    ]

    sum_tbl = Table(summary_data, colWidths=[150*mm, 30*mm])
    sum_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 2),
        ("BOTTOMPADDING",(0,0), (-1,-1), 2),
        ("LINEABOVE",    (0,-1), (-1,-1), 0.8, TEAL),
        ("LINEBELOW",    (0,-1), (-1,-1), 0.8, TEAL),
        ("LINEABOVE",    (0,0),  (-1,0),  0.4, colors.HexColor("#ccdddd")),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Footer note ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "<i>Fee schedule: Royalty 10% (residential) or 20% (commercial) of gross job value. "
        "Admin 5% of gross job value. Insurance $100.00 flat fee per job.</i>",
        ParagraphStyle("note", parent=styles["Normal"],
                       fontSize=7.5, textColor=GREY)
    ))

    doc.build(story)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "keen_to_clean_jobs.csv"
    if not Path(csv_path).exists():
        print(f"Error: CSV file not found — {csv_path}")
        sys.exit(1)

    jobs      = load_jobs(csv_path)
    jobs_calc = [calculate(j) for j in jobs]

    # ── Terminal summary ─────────────────────────────────────────────────────
    print(f"\n{'═'*65}")
    print(f"  {BRAND_NAME} — Invoice Summary")
    print(f"{'═'*65}")
    print(f"  {'Job':<6} {'Client':<22} {'Gross':>9} {'Royalty':>12} {'Admin':>8} {'Ins':>7} {'Net':>10}")
    print(f"  {'─'*6} {'─'*22} {'─'*9} {'─'*12} {'─'*8} {'─'*7} {'─'*10}")
    for j in jobs_calc:
        print(f"  {j['job_id']:<6} {j['client_name']:<22} "
              f"${j['amount']:>8,.2f} "
              f"${j['royalty']:>8,.2f} ({j['royalty_rate']}%) "
              f"${j['admin']:>6,.2f} "
              f"${j['insurance']:>5,.0f} "
              f"${j['net']:>9,.2f}")
    print(f"  {'─'*65}")
    print(f"  {'TOTALS':<29} "
          f"${sum(j['amount']    for j in jobs_calc):>8,.2f} "
          f"${sum(j['royalty']   for j in jobs_calc):>10,.2f}  "
          f"${sum(j['admin']     for j in jobs_calc):>6,.2f} "
          f"${sum(j['insurance'] for j in jobs_calc):>5,.0f} "
          f"${sum(j['net']       for j in jobs_calc):>9,.2f}")
    print(f"{'═'*65}\n")

    # ── Save PDF ─────────────────────────────────────────────────────────────
    pdf_name = f"keen_to_clean_invoice_{date.today().strftime('%Y%m%d')}.pdf"
    build_pdf(jobs_calc, pdf_name)
    print(f"  PDF saved → {pdf_name}\n")


if __name__ == "__main__":
    main()
