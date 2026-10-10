"""Builds every figure for the PDF report from the model outputs (../outputs/results.json)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).parent
OUT = HERE / "fig"
OUT.mkdir(exist_ok=True)
R = json.load(open(HERE.parent / "outputs" / "results.json"))

# Palette
FOREST = "#1F3A2E"
MOSS = "#4E7A5A"
SAGE = "#A9BFA8"
EMBER = "#C8892B"
RUST = "#B5523B"
INK = "#22262A"
QUIET = "#6B7178"
GRID = "#E3E6E3"
PAPER = "#FFFFFF"

for f in fm.findSystemFonts():
    if "SourceSans3" in f or "Merriweather" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Source Sans 3", "font.size": 9.5, "axes.edgecolor": GRID, "axes.labelcolor": QUIET,
    "xtick.color": QUIET, "ytick.color": QUIET, "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "text.parse_math": False, "svg.fonttype": "none", "figure.facecolor": PAPER,
})


def save(fig, name):
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def musd(v, _=None):
    m = abs(v) / 1e6
    t = f"{m:.0f}" if abs(m - round(m)) < 0.05 else f"{m:.1f}"
    return f"-${t}M" if v < 0 else f"${t}M"


# 1. Cumulative cash
rows = R["cash_flow_rows"]
cum, run = [], 0
for r in rows:
    run += r["net"]
    cum.append(run)
fig, ax = plt.subplots(figsize=(7.2, 2.7))
years = [r["year"] for r in rows]
ax.bar(years, cum, color=[RUST if v < 0 else MOSS for v in cum], width=0.72, alpha=0.9)
ax.axhline(0, color=INK, lw=0.8)
ax.yaxis.set_major_formatter(FuncFormatter(musd))
ax.set_xticks(years)
ax.set_xlabel("Project year (0 = construction)")
pay = next(i for i, v in enumerate(cum) if v >= 0)
ax.annotate(f"Outlay recovered in year {pay}", xy=(pay, cum[pay]), xytext=(pay + 2.2, 38e6),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=QUIET, lw=0.8))
ax.annotate(f"{musd(cum[-1])} cumulative by year 20\n(includes salvage)", xy=(20, cum[-1]), xytext=(12.3, 112e6),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=QUIET, lw=0.8))
ax.text(0, cum[0] - 9e6, musd(cum[0]), ha="center", fontsize=8.5, color=RUST)
ax.grid(axis="x", visible=False)
save(fig, "cumulative_cash")

# 2. Waterfall, full-capacity year
f = R["full_capacity_year"]
steps = [("Biochar\nsales", f["char_sales"]), ("Credit\nsales", f["credit_sales"]), ("Revenue", None),
         ("Feedstock", -f["feedstock"]), ("Production", -f["production"]), ("Net operating\ncash", None)]
fig, ax = plt.subplots(figsize=(7.2, 2.7))
level = 0
for i, (lab, v) in enumerate(steps):
    if v is None:
        ax.bar(i, level, color=FOREST, width=0.62)
        ax.text(i, level + 0.25e6, f"${level/1e6:.1f}M", ha="center", va="bottom", fontsize=9.5, color=INK, weight="semibold")
    else:
        lo = level if v > 0 else level + v
        ax.bar(i, abs(v), bottom=lo, color=MOSS if v > 0 else RUST, width=0.62, alpha=0.85)
        ax.text(i, lo + abs(v) + 0.25e6, f"{'+' if v > 0 else '-'}${abs(v)/1e6:.1f}M", ha="center", va="bottom", fontsize=9.5, color=INK)
        level += v
    if i < len(steps) - 1:
        ax.plot([i + 0.31, i + 0.69], [level, level], color=QUIET, lw=0.7, ls=":")
ax.set_xticks(range(len(steps)), [s[0] for s in steps])
ax.yaxis.set_major_formatter(FuncFormatter(musd))
ax.set_ylim(0, 15.2e6)
ax.grid(axis="x", visible=False)
save(fig, "waterfall")

# 3. Tornado
names = {"char_price": "Biochar sale price ($/t)", "credit_price": "Credit price ($/t CO2)",
         "feed_cost": "Feedstock cost ($/dry t)", "co2_per_t": "CO2 credited (t per t)",
         "capex": "Capital cost", "prod_cost": "Production cost ($/t)"}
def lab(k, v):
    if k == "capex":
        return f"${v/1e6:.1f}M"
    if k == "co2_per_t":
        return f"{v:.1f}"
    return f"${v:,.0f}"
base = R["base"]["npv"]
items = sorted(R["tornado"].items(), key=lambda kv: kv[1]["high_npv"] - kv[1]["low_npv"])
fig, ax = plt.subplots(figsize=(7.2, 3.0))
for i, (k, v) in enumerate(items):
    ax.barh(i, v["low_npv"] - base, left=base, color=RUST, alpha=0.75, height=0.56)
    ax.barh(i, v["high_npv"] - base, left=base, color=MOSS, alpha=0.85, height=0.56)
    ax.text(v["low_npv"] - 0.9e6, i, f"{lab(k, v['low_input'])}  {musd(v['low_npv'])}", va="center", ha="right", fontsize=8.5, color=INK)
    ax.text(v["high_npv"] + 0.9e6, i, f"{musd(v['high_npv'])}  {lab(k, v['high_input'])}", va="center", ha="left", fontsize=8.5, color=INK)
ax.axvline(base, color=INK, lw=0.9)
ax.text(base, len(items) - 0.35, f"Base {musd(base)}", ha="center", fontsize=8.5, color=INK)
ax.set_yticks(range(len(items)), [names[k] for k, _ in items])
ax.xaxis.set_major_formatter(FuncFormatter(musd))
ax.set_xlim(-12e6, 82e6)
ax.set_xlabel("Net present value at the 10.5% cost of capital")
ax.grid(axis="y", visible=False)
save(fig, "tornado")

# 4. Price curve
pc = R["price_curve"]
p = [d["char_price"] for d in pc]
fig, ax = plt.subplots(figsize=(7.2, 2.8))
ax.plot(p, [d["npv_with_credits"] for d in pc], color=FOREST, lw=2.4, marker="o", ms=3.5, label="With credits at $148")
ax.plot(p, [d["npv_without_credits"] for d in pc], color=SAGE, lw=2.4, marker="o", ms=3.5, label="Without credits")
ax.axhline(0, color=INK, lw=0.8)
ax.axvline(500, color=EMBER, lw=1, ls="--")
ax.text(505, 66e6, "Base price $500", color=EMBER, fontsize=8.5)
for be, txt in ((R["breakeven"]["char_price_with_credits"], "break-even"), (R["breakeven"]["char_price_without_credits"], "break-even")):
    ax.plot(be, 0, "o", mfc="white", mec=INK, ms=7)
    ax.text(be + 10, -6.5e6, f"{txt} ${be:.0f}", fontsize=8.5, color=INK)
ax.yaxis.set_major_formatter(FuncFormatter(musd))
ax.set_xlabel("Biochar sale price ($ per tonne)")
ax.legend(frameon=False, loc="upper left")
save(fig, "price_curve")

# 5. Designs scatter
ds = R["designs"]
fig, ax = plt.subplots(figsize=(7.2, 2.8))
for d in ds:
    cap, cost = float(d["capital_musd"]), float(d["total_cost_per_t"])
    if d["reference"] == "1":
        ax.scatter(cap, cost, s=110, color=EMBER, zorder=3, edgecolor=INK, lw=0.6)
        ax.annotate(f"Reference: {d['site']}, thermal,\nScenario {d['scenario']} (${cap}M, ${cost:.0f}/t)",
                    xy=(cap, cost), xytext=(20.6, 452), fontsize=8.5, color=INK,
                    arrowprops=dict(arrowstyle="-", color=QUIET, lw=0.8))
    elif d["technology"] == "Thermal":
        ax.scatter(cap, cost, s=48, color=MOSS, zorder=2)
    else:
        ax.scatter(cap, cost, s=48, facecolor="white", edgecolor=MOSS, lw=1.4, zorder=2)
ax.scatter([], [], s=48, color=MOSS, label="Thermal pyrolysis")
ax.scatter([], [], s=48, facecolor="white", edgecolor=MOSS, lw=1.4, label="Microwave pyrolysis")
ax.legend(frameon=False, loc="upper center", ncol=2)
ax.set_xlabel("Capital cost ($ million)")
ax.set_ylabel("Total cost per tonne of biochar ($)")
ax.set_ylim(420, 700)
ax.text(17.9, 682, "Scenarios 1 and 2", ha="center", fontsize=8.5, color=QUIET)
ax.text(27.4, 682, "Scenarios 3 and 4", ha="center", fontsize=8.5, color=QUIET)
save(fig, "designs")

# 6. Standard tests: FIRR against cost of capital
st = R["standard_tests"]
lbl = {"revenue_minus_10": "Revenue -10%", "biochar_price_minus_10": "Biochar price -10%",
       "capital_plus_10": "Capital +10%", "operating_cost_plus_10": "Operating cost +10%",
       "credit_price_minus_10": "Credit price -10%", "delay_1yr_capital_plus_10": "1-year delay, capital +10%"}
keys = sorted(st, key=lambda k: st[k]["firr"])
fig, ax = plt.subplots(figsize=(7.2, 2.2))
ax.barh(len(keys), R["base"]["firr"] * 100, color=FOREST, height=0.6)
ax.text(R["base"]["firr"] * 100 + 0.6, len(keys), f"{R['base']['firr']*100:.1f}%", va="center", fontsize=9, color=INK, weight="semibold")
for i, k in enumerate(keys):
    ax.barh(i, st[k]["firr"] * 100, color=SAGE, height=0.6)
    ax.text(st[k]["firr"] * 100 + 0.6, i, f"{st[k]['firr']*100:.1f}%", va="center", fontsize=9, color=INK)
ax.axvline(R["wacc"] * 100, color=EMBER, lw=1.4, ls="--")
ax.text(R["wacc"] * 100 + 0.5, -0.9, "Cost of capital 10.5%", color=EMBER, fontsize=8.5)
ax.set_yticks(range(len(keys) + 1), [lbl[k] for k in keys] + ["Base case"])
ax.set_xlabel("Financial internal rate of return (%)")
ax.set_xlim(0, 40)
ax.set_ylim(-1.3, len(keys) + 0.6)
ax.grid(axis="y", visible=False)
save(fig, "standard_tests")

# 7. Scenarios
sc = R["scenarios"]
names_s = [("Upside", sc["upside"]["npv"]), ("Base", R["base"]["npv"]), ("No credits", sc["no_credits"]["npv"]), ("Downside", sc["downside"]["npv"])]
fig, ax = plt.subplots(figsize=(7.2, 2.4))
for i, (n, v) in enumerate(names_s):
    ax.barh(len(names_s) - 1 - i, v, color=MOSS if v >= 0 else RUST, height=0.58, alpha=0.9 if n != "Base" else 1)
    ax.text(v + (1.2e6 if v >= 0 else -1.2e6), len(names_s) - 1 - i, musd(v) if abs(v) > 2e6 else f"-${abs(v)/1e6:.1f}M",
            va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK)
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(range(len(names_s)), [n for n, _ in reversed(names_s)])
ax.xaxis.set_major_formatter(FuncFormatter(musd))
ax.set_xlim(-34e6, 80e6)
ax.set_xlabel("Net present value at the 10.5% cost of capital")
ax.grid(axis="y", visible=False)
save(fig, "scenarios")

# 8. Revenue mix donut and cost mix donut (full-capacity year)
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.2))
for ax, vals, labels, cols, title in (
        (axs[0], [f["char_sales"], f["credit_sales"]], ["Biochar sales", "Credit sales"], [FOREST, EMBER], "Revenue $13.3M"),
        (axs[1], [f["feedstock"], f["production"]], ["Feedstock", "Production"], [SAGE, MOSS], "Operating cost $5.9M")):
    w, _ = ax.pie(vals, colors=cols, startangle=90, counterclock=False, wedgeprops=dict(width=0.32, edgecolor="white"))
    ax.text(0, 0.06, title.split(" $")[0], ha="center", fontsize=9, color=QUIET)
    ax.text(0, -0.2, "$" + title.split(" $")[1], ha="center", fontsize=12, color=INK, weight="semibold")
    tot = sum(vals)
    ax.legend(w, [f"{l}  {v/tot*100:.0f}%" for l, v in zip(labels, vals)], frameon=False, loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=9)
save(fig, "mix")

# 9. Evidence base: sourced vs assumed inputs
import csv
inp = list(csv.DictReader(open(HERE.parent / "model" / "inputs.csv")))
n_s = sum(1 for r in inp if r["status"] == "Sourced")
n_a = sum(1 for r in inp if r["status"] == "Assumption")
fig, ax = plt.subplots(figsize=(7.2, 0.9))
ax.barh(0, n_s, color=FOREST, height=0.5)
ax.barh(0, n_a, left=n_s, color=EMBER, height=0.5)
ax.text(n_s / 2, 0, f"{n_s} sourced inputs", ha="center", va="center", color="white", fontsize=9.5, weight="semibold")
ax.text(n_s + n_a / 2, 0, f"{n_a} assumptions", ha="center", va="center", color="white", fontsize=9.5, weight="semibold")
ax.axis("off")
save(fig, "evidence")
json.dump({"sourced": n_s, "assumption": n_a}, open(OUT / "evidence.json", "w"))
print("figures written", n_s, n_a)
