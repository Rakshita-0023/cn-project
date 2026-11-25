#!/usr/bin/env python3
"""Generate the results index and printable report from actual test output.

Requires reportlab only for this optional document export; project services and
tests otherwise use Python's standard library. Prefer the Codex bundled Python.
"""
import datetime
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def results_document(data):
    target = ROOT / "docs/phase2/TEST_RESULTS.md"
    marker = "<!-- LIVE RESULTS -->"
    existing = target.read_text().split(marker, 1)[1] if target.exists() and marker in target.read_text() else """

## Live acceptance evidence

See FINAL_REPORT.md for the reviewed live results, evidence scope and remaining
faculty/peer/packet verification items. No live pass is inferred from local tests.
"""
    passed = sum(case["status"] == "PASS" for case in data["cases"])
    lines = ["# Phase 2 test results", "", f"Observed: {data['observed_at']}", "",
             f"**Executed locally: {passed}/{data['run']} passed; {data['failures']} failures; {data['errors']} errors; {data['skipped']} skipped.**", "",
             "Scope: one accessible Mac, real loopback processes and ephemeral ports. Mock safety tests are identified by their test names. No live DNS settings, Keychain trust or PF rules were installed by the test suite.", "",
             "Actual command: `make test-local`. [Complete text output](../../evidence/phase2/local-tests.txt), [per-case JSON](../../evidence/phase2/local-tests.json), [original baseline](../../evidence/phase2/phase1-baseline.txt).", "",
             "| Test case | Actual result | Seconds |", "|---|---|---|"]
    for case in data["cases"]:
        lines.append(f"| `{case['test']}` | {case['status']} | {case['seconds']:.3f} |")
    lines += ["", "The standalone `make ttl-lab` writes independent TTL/flush output. Initial failed timing assumptions and intermediate debugging logs are retained in [the evidence index](../../evidence/phase2/README.md). They are not counted as passing results.", "", marker, existing]
    target.write_text("\n".join(lines))


def build_pdf(data):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

    navy, teal = colors.HexColor("#12253e"), colors.HexColor("#117e78")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=navy, spaceAfter=18))
    styles.add(ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=10, leading=15, textColor=colors.HexColor("#293d50"), spaceAfter=9))
    styles.add(ParagraphStyle(name="ReportH2", fontName="Helvetica-Bold", fontSize=15, leading=20, textColor=navy, spaceBefore=16, spaceAfter=10, keepWithNext=True))
    styles.add(ParagraphStyle(name="ReportH3", fontName="Helvetica-Bold", fontSize=11, leading=16, textColor=teal, spaceBefore=10, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8, leading=11, textColor=navy))
    styles.add(ParagraphStyle(name="CellHead", parent=styles["Cell"], fontName="Helvetica-Bold", textColor=colors.white))
    styles.add(ParagraphStyle(name="Small", parent=styles["ReportBody"], fontSize=8, leading=12))

    def markup(text):
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = html.escape(text.replace("`", ""))
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    def architecture():
        d = Drawing(490, 226)
        d.add(Rect(0, 0, 490, 226, fillColor=colors.HexColor("#f2f6fa"), strokeColor=None))
        for x, title, dns, edge, backend in [(10, "Mac 1 / Rakshita", "Primary DNS :53", "Standby nginx :8443", "Backend A :3001"), (260, "Mac 2 / Lakshya", "Backup DNS :53", "Primary nginx :8443", "Backend B :3002")]:
            d.add(Rect(x, 56, 220, 158, rx=8, fillColor=colors.white, strokeColor=colors.HexColor("#bfd2dd")))
            d.add(String(x+12, 193, title, fontName="Helvetica-Bold", fontSize=12, fillColor=navy))
            d.add(String(x+12, 182, "10.7.12.26" if x == 10 else "10.7.7.242", fontName="Helvetica", fontSize=8, fillColor=teal))
            for y, label, fill in [(151, dns, "#e5f5f1"), (111, edge, "#eaf0fc"), (71, backend, "#fff1dd")]:
                d.add(Rect(x+10, y, 200, 28, rx=4, fillColor=colors.HexColor(fill), strokeColor=None))
                d.add(String(x+20, y+10, label, fontName="Helvetica", fontSize=10, fillColor=navy))
        for x1,y1,x2,y2 in [(220,125,270,85), (270,125,220,85), (210,111,210,102), (460,111,460,102)]:
            d.add(Line(x1,y1,x2,y2, strokeColor=teal, strokeWidth=1.5))
        d.add(String(13, 34, "Both clients: DNS -> TCP -> TLS -> either edge -> A or B", fontName="Helvetica-Bold", fontSize=10, fillColor=navy))
        d.add(String(13, 15, "Both-host UID firewall guard; DNS migration keeps old edge alive through TTL", fontName="Helvetica", fontSize=9, fillColor=teal))
        return d

    output = ROOT / "output/pdf/phase2-final-report.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=46, leftMargin=46,
                            topMargin=48, bottomMargin=48, title="Codexers - Phase 2 Final Report", author="Rakshita and Lakshya")
    story, paragraphs = [], []
    def flush():
        if paragraphs:
            story.append(Paragraph(markup(" ".join(paragraphs)), styles["ReportBody"]))
            paragraphs.clear()
    source = (ROOT / "docs/phase2/FINAL_REPORT.md").read_text().splitlines()
    i = 0
    while i < len(source):
        line = source[i].strip()
        if not line:
            flush()
        elif line.startswith("# "):
            flush()
            story.append(Paragraph(markup(line[2:]), styles["ReportTitle"]))
            story.append(Paragraph("PHASE 2 / HARDEN, RECOVER &amp; TROUBLESHOOT", styles["ReportH3"]))
            passed = sum(case["status"] == "PASS" for case in data["cases"])
            story.append(Paragraph(f"<b>Actual local verification: {passed}/{data['run']} passed.</b> Live results and specific remaining evidence gaps are documented below. Local suite snapshot: {html.escape(data['observed_at'])}.", styles["ReportBody"]))
        elif line.startswith("## "):
            flush()
            story.append(Paragraph(markup(line[3:]), styles["ReportH2"]))
            if line.startswith("## 2."):
                story.append(architecture())
                story.append(Spacer(1, 12))
        elif line.startswith("### "):
            flush()
            story.append(Paragraph(markup(line[4:]), styles["ReportH3"]))
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(source) and source[i].strip().startswith("|"):
                cells = [cell.strip() for cell in source[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-:]+", cell) for cell in cells):
                    rows.append(cells)
                i += 1
            table = Table([[Paragraph(markup(cell), styles["CellHead" if n == 0 else "Cell"]) for cell in row] for n, row in enumerate(rows)],
                          colWidths=[66, 175, 62, 200], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), navy), ("VALIGN",(0,0),(-1,-1),"TOP"),
                                       ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f0f6fa"),colors.white]),
                                       ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
                                       ("TOPPADDING",(0,0),(-1,-1),9), ("BOTTOMPADDING",(0,0),(-1,-1),9),
                                       ("LINEBELOW",(0,0),(-1,0),1,teal)]))
            story.append(table)
            story.append(Spacer(1,12))
            continue
        else:
            paragraphs.append(line)
        i += 1
    flush()
    def page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(teal)
        canvas.line(46, A4[1]-30, A4[0]-46, A4[1]-30)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(navy)
        canvas.drawString(46, 28, "CODEXERS / Computer Networks / Phase 2")
        canvas.drawRightString(A4[0]-46, 28, str(doc.page))
        canvas.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)
    print(output)


if __name__ == "__main__":
    data = json.loads((ROOT / "evidence/phase2/local-tests.json").read_text())
    if not data["successful"] or data["skipped"]:
        raise SystemExit("Resolve failing/skipped required local checks before generating the final report")
    results_document(data)
    build_pdf(data)
