"""Static SVG diagrams for the report: process flow, results chain, implementation timeline, cover art."""
from pathlib import Path
import math

OUT = Path(__file__).parent / "fig"
FOREST, MOSS, SAGE, EMBER, RUST, INK, QUIET, GRID = "#1F3A2E", "#4E7A5A", "#A9BFA8", "#C8892B", "#B5523B", "#22262A", "#6B7178", "#D9DED9"
FONT = "font-family='Source Sans 3, sans-serif'"


def box(cx, cy, w, h, label, main=False, sub=None):
    fill = FOREST if main else "#FFFFFF"
    tc = "#FFFFFF" if main else INK
    s = f"<rect x='{cx-w/2}' y='{cy-h/2}' width='{w}' height='{h}' rx='10' fill='{fill}' stroke='{FOREST if main else SAGE}' stroke-width='1.6'/>"
    s += f"<text x='{cx}' y='{cy+5}' text-anchor='middle' font-size='14' font-weight='600' fill='{tc}'>{label}</text>"
    return s


def arrow_defs():
    return (f"<defs><marker id='a' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{QUIET}'/></marker>"
            f"<marker id='h' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{EMBER}'/></marker></defs>")


def process_flow():
    W, H, rowA, rowB = 150, 52, 70, 220
    c1, c2, c3, c4, fx, FW = 90, 270, 450, 650, 360, 240
    s = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 760 300' {FONT}>" + arrow_defs()
    for a, b in ((c1, c2), (c2, c3), (c3, c4)):
        s += f"<path d='M{a+W/2} {rowA}H{b-W/2}' stroke='{QUIET}' stroke-width='1.6' fill='none' marker-end='url(#a)'/>"
    s += f"<path d='M{c3+30} {rowA+H/2}V{rowB-H/2}' stroke='{QUIET}' stroke-width='1.6' fill='none' marker-end='url(#a)'/>"
    s += f"<path d='M{c2} {rowB-H/2}V{rowA+H/2}' stroke='{EMBER}' stroke-width='2' fill='none' marker-end='url(#h)'/>"
    s += f"<path d='M{c3-30} {rowB-H/2}V{rowA+H/2}' stroke='{EMBER}' stroke-width='2' fill='none' marker-end='url(#h)'/>"
    s += f"<path d='M{fx+FW/2} {rowB}H{fx+FW/2+90}' stroke='{EMBER}' stroke-width='2' stroke-dasharray='5 4' fill='none' marker-end='url(#h)'/>"
    s += box(c1, rowA, W, H, "Forest residue") + box(c2, rowA, W, H, "Chip dryer") + box(c3, rowA, W, H, "Thermal reactor")
    s += box(c4, rowA, W, H, "Biochar", main=True) + box(fx, rowB, FW, H, "Heat-recovery furnace")
    t = lambda x, y, txt, anchor="middle", col=QUIET, size=12: f"<text x='{x}' y='{y}' text-anchor='{anchor}' font-size='{size}' fill='{col}'>{txt}</text>"
    s += t(c1, rowA + 46, "45,360 dry t a year")
    s += t(c4, rowA + 46, "36% yield: 16,330 t a year", col=INK) + t(c4, rowA + 64, "soil product and") + t(c4, rowA + 80, "certified carbon removal")
    s += t(c2 - 10, 152, "heat to dry chips", "end") + t(c3 - 40, 152, "heat to reactor", "end") + t(c3 + 40, 182, "pyrolysis gases", "start")
    s += t(fx + FW / 2 + 98, rowB + 5, "excess heat vented", "start")
    s += "</svg>"
    (OUT / "process_flow.svg").write_text(s)


def results_chain():
    W, H, y = 168, 128, 10
    xs = [92, 282, 472, 662]
    heads = ["Inputs", "Outputs", "Outcome", "Impact"]
    lines = [["Capital $19.1M", "Forest residue", "26.5 staff"],
             ["Plant commissioned", "Offtake signed", "Local jobs"],
             ["16,330 t biochar a year", "40,824 t CO2 credited", "Full capacity, year 3"],
             ["Residue turned into", "stable soil carbon", "and a farm input"]]
    s = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 760 150' {FONT}>" + arrow_defs()
    for i in range(3):
        s += f"<path d='M{xs[i]+W/2} {y+H/2}H{xs[i+1]-W/2}' stroke='{QUIET}' stroke-width='1.6' marker-end='url(#a)'/>"
    for i, x in enumerate(xs):
        main = i == 2
        s += f"<rect x='{x-W/2}' y='{y}' width='{W}' height='{H}' rx='10' fill='{FOREST if main else '#F3F6F2'}' stroke='{FOREST if main else SAGE}' stroke-width='1.4'/>"
        s += f"<text x='{x}' y='{y+30}' text-anchor='middle' font-size='14' font-weight='700' fill='{'#FFFFFF' if main else FOREST}' letter-spacing='0.5'>{heads[i].upper()}</text>"
        for j, ln in enumerate(lines[i]):
            s += f"<text x='{x}' y='{y+62+j*20}' text-anchor='middle' font-size='12' fill='{'#FFFFFF' if main else INK}'>{ln}</text>"
    s += "</svg>"
    (OUT / "results_chain.svg").write_text(s)


def timeline():
    rows = [("Site selection, feedstock survey", 0, 4), ("Lab tests, registry method", 2, 6), ("Offtake and feedstock contracts", 4, 8),
            ("Fixed-price bids, re-run model", 6, 9), ("Financial close gate", 9, 9), ("Permitting and construction", 9, 21),
            ("Commissioning", 21, 21), ("Operating years 1 and 2 (60%, 85%)", 21, 45), ("Operating year 3 (full capacity)", 45, 57),
            ("Full-capacity review", 57, 57)]
    hi = 60
    X = lambda m: 270 + m / hi * 430
    Y = lambda i: 46 + i * 28
    s = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 760 340' {FONT}>"
    for m in range(0, hi + 1, 6):
        s += f"<line x1='{X(m)}' x2='{X(m)}' y1='30' y2='{Y(len(rows))-8}' stroke='{GRID}'/>"
        s += f"<text x='{X(m)}' y='22' text-anchor='middle' font-size='11' fill='{QUIET}'>{m}</text>"
    s += f"<line x1='{X(9)}' x2='{X(9)}' y1='{Y(4)-12}' y2='{Y(len(rows))-8}' stroke='{EMBER}' stroke-width='1.6' stroke-dasharray='5 4'/>"
    for i, (n, a, b) in enumerate(rows):
        y = Y(i)
        gate = n.startswith("Financial")
        s += f"<text x='10' y='{y+4}' font-size='12' font-weight='{700 if gate else 400}' fill='{INK}'>{n}</text>"
        if a == b:
            c = EMBER if gate else FOREST
            s += f"<path d='M{X(a)} {y-8}l8 8l-8 8l-8 -8z' fill='{c}'/>"
            s += f"<text x='{X(a)+14}' y='{y+4}' font-size='11' fill='{INK if gate else QUIET}' font-weight='{700 if gate else 400}'>month {a}</text>"
        else:
            col = MOSS if a >= 9 else SAGE
            s += f"<rect x='{X(a)}' y='{y-7}' width='{X(b)-X(a)}' height='14' rx='7' fill='{col}'/>"
            s += f"<text x='{X(b)+8}' y='{y+4}' font-size='11' fill='{QUIET}'>{a} to {b}</text>"
    s += f"<text x='{X(30)}' y='{Y(len(rows))+16}' text-anchor='middle' font-size='11' fill='{QUIET}'>Months after approval</text></svg>"
    (OUT / "timeline.svg").write_text(s)


def cover_art():
    """Abstract contour lines suggesting forest terrain and growth rings."""
    s = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 816 1056' preserveAspectRatio='xMidYMid slice'>"
    cx, cy = 690, 820
    for i in range(1, 38):
        r = i * 22
        pts = []
        for k in range(0, 361, 4):
            a = math.radians(k)
            wob = 1 + 0.045 * math.sin(3 * a + i * 0.5) + 0.03 * math.sin(7 * a - i * 0.3)
            pts.append(f"{cx + r * wob * math.cos(a):.1f},{cy + r * 0.82 * wob * math.sin(a):.1f}")
        op = max(0.05, 0.32 - i * 0.007)
        s += f"<polyline points='{' '.join(pts)}' fill='none' stroke='#A9BFA8' stroke-opacity='{op:.3f}' stroke-width='1.1'/>"
    s += "</svg>"
    (OUT / "cover_art.svg").write_text(s)


process_flow(); results_chain(); timeline(); cover_art()
print("diagrams written")
