"""Biochar pyrolysis plant: financial assessment model.

Reads inputs.csv, builds the project cash flow, and writes every figure the
assessment reports to outputs/results.json and outputs/results.md.

Method (follows the ADB financial analysis format, e.g. RRP IND 41626):
  1. Incremental cash flows: with-project minus without-project (no plant, no flows).
  2. Year 0 = construction (capital outlay). Years 1..life = operation.
  3. Output in year t = feedstock x yield x capacity use (ramp in years 1 and 2).
  4. Revenue = biochar sales + credit sales net of fees.
  5. Operating cost = feedstock cost + direct production cost.
  6. Salvage value is added in the final operating year.
  7. Pre-tax, nominal, prices held flat. No financing flows in the cash flow;
     financing enters only through the weighted average cost of capital (WACC).
  8. Viability: FIRR > WACC (equivalently NPV at WACC > 0).
  9. Sensitivity: standard ADB-style tests (+/-10%, one-year delay) with
     switching values, plus one-at-a-time low/high ranges from the inputs,
     scenarios, and break-even values.

Run from the repository root:  python model/model.py
"""
import csv
import json
from pathlib import Path

import numpy as np
import numpy_financial as npf
from scipy.optimize import brentq

HERE = Path(__file__).parent
OUTDIR = HERE.parent / "outputs"


def load_inputs(path=HERE / "inputs.csv"):
    with open(path, newline="") as f:
        return {r["id"]: float(r["value"]) for r in csv.DictReader(f)}


def wacc(p):
    return p["debt_share"] * p["debt_rate"] + (1 - p["debt_share"]) * p["equity_rate"]


def cash_flows(p, rev_mult=1.0, cost_mult=1.0, char_mult=1.0, credit_mult=1.0,
               capex_mult=1.0, delay_years=0, credit_on=True):
    """Return (list of net flows from year 0, list of per-year detail rows)."""
    life = int(p["life"])
    capex = p["capex"] * capex_mult
    ramp = {1: p["ramp_y1"], 2: p["ramp_y2"]}
    flows = [-capex] + [0.0] * delay_years
    rows = [dict(year=0, biochar_t=0, char_sales=0, credit_sales=0, capital=capex,
                 feedstock=0, production=0, salvage=0, net=-capex)]
    for t in range(1, life + 1):
        use = ramp.get(t, 1.0)
        feed = p["feed_tonnes"] * use
        char_t = feed * p["yield"]
        char_sales = char_t * p["char_price"] * char_mult * rev_mult
        credit_sales = (char_t * p["co2_per_t"] * p["credit_price"] * credit_mult
                        * (1 - p["credit_fee"]) * rev_mult) if credit_on else 0.0
        feedstock = feed * p["feed_cost"] * cost_mult
        production = char_t * p["prod_cost"] * cost_mult
        salvage = p["salvage_share"] * capex if t == life else 0.0
        net = char_sales + credit_sales - feedstock - production + salvage
        flows.append(net)
        rows.append(dict(year=t + delay_years, biochar_t=char_t, char_sales=char_sales,
                         credit_sales=credit_sales, capital=0, feedstock=feedstock,
                         production=production, salvage=salvage, net=net))
    return flows, rows


def metrics(flows, rate):
    npv = npf.npv(rate, flows)
    irr = npf.irr(flows)
    cum = np.cumsum(flows)
    payback = None
    for i in range(1, len(cum)):
        if cum[i] >= 0:
            payback = (i - 1) + (-cum[i - 1]) / flows[i]
            break
    return dict(npv=float(npv), firr=None if np.isnan(irr) else float(irr), payback=payback)


def run(p, rate, **kw):
    flows, _ = cash_flows(p, **kw)
    return metrics(flows, rate)


def with_inputs(p, **changes):
    q = dict(p)
    q.update(changes)
    return q


def main():
    p = load_inputs()
    r = wacc(p)
    out = {"wacc": r}

    # Base case
    flows, rows = cash_flows(p)
    out["base"] = metrics(flows, r)
    out["base"]["npv_at_8pct"] = float(npf.npv(0.08, flows))
    out["base"]["npv_at_12pct"] = float(npf.npv(0.12, flows))
    out["cash_flow_rows"] = rows
    full = rows[3]
    out["full_capacity_year"] = {k: full[k] for k in
                                 ("biochar_t", "char_sales", "credit_sales", "feedstock", "production", "net")}
    out["totals"] = {k: float(sum(row[k] for row in rows)) for k in
                     ("char_sales", "credit_sales", "capital", "feedstock", "production", "salvage", "net")}
    out["co2_credited_full"] = full["biochar_t"] * p["co2_per_t"]

    # Standard tests (ADB style) and switching values
    tests = {
        "revenue_minus_10": dict(rev_mult=0.9),
        "biochar_price_minus_10": dict(char_mult=0.9),
        "operating_cost_plus_10": dict(cost_mult=1.1),
        "capital_plus_10": dict(capex_mult=1.1),
        "credit_price_minus_10": dict(credit_mult=0.9),
        "delay_1yr_capital_plus_10": dict(delay_years=1, capex_mult=1.1),
    }
    out["standard_tests"] = {k: run(p, r, **v) for k, v in tests.items()}

    def switching(key):
        return brentq(lambda x: run(p, r, **{key: 1 + x})["npv"], -0.999, 50) * 100
    out["switching_values_pct"] = {
        "revenue": switching("rev_mult"),
        "biochar_price": switching("char_mult"),
        "operating_cost": switching("cost_mult"),
        "capital": switching("capex_mult"),
        "credit_price": switching("credit_mult"),
    }

    # One-at-a-time ranges for the tornado chart
    ranges = {
        "char_price": (p["char_price_low"], p["char_price_high"]),
        "credit_price": (p["credit_price_low"], p["credit_price_high"]),
        "feed_cost": (p["feed_cost_high"], p["feed_cost_low"]),
        "prod_cost": (p["prod_cost_high"], p["prod_cost_low"]),
        "co2_per_t": (p["co2_per_t_low"], p["co2_per_t_high"]),
        "capex": (p["capex_high"], p["capex_low"]),
    }
    out["tornado"] = {k: {"low_input": lo, "low_npv": run(with_inputs(p, **{k: lo}), r)["npv"],
                          "high_input": hi, "high_npv": run(with_inputs(p, **{k: hi}), r)["npv"]}
                      for k, (lo, hi) in ranges.items()}

    # Scenarios
    up = with_inputs(p, char_price=600, credit_price=180,
                     capex=p["capex_low"], prod_cost=p["prod_cost_low"], feed_cost=p["feed_cost_low"])
    down = with_inputs(p, char_price=300, credit_price=100, capex=p["capex_high"],
                       prod_cost=p["prod_cost_high"], feed_cost=80)
    out["scenarios"] = {
        "upside": run(up, r) | {"inputs": "biochar 600, credits 180, capital 17.0M, production 184, feedstock 43"},
        "no_credits": run(p, r, credit_on=False),
        "downside": run(down, r) | {"inputs": "biochar 300, credits 100, capital 28.1M, production 254, feedstock 80"},
    }

    # Break-even values at WACC
    out["breakeven"] = {
        "char_price_with_credits": brentq(lambda v: run(with_inputs(p, char_price=v), r)["npv"], -5000, 5000),
        "char_price_without_credits": brentq(lambda v: run(with_inputs(p, char_price=v), r, credit_on=False)["npv"], -5000, 5000),
        "credit_price": brentq(lambda v: run(with_inputs(p, credit_price=v), r)["npv"], -5000, 5000),
        "capital": brentq(lambda v: run(with_inputs(p, capex=v), r)["npv"], 1e6, 5e8),
        "feed_cost": brentq(lambda v: run(with_inputs(p, feed_cost=v), r)["npv"], -500, 2000),
    }

    # NPV at the cost of capital across biochar prices, with and without credits
    out["price_curve"] = [
        {"char_price": v,
         "npv_with_credits": run(with_inputs(p, char_price=v), r)["npv"],
         "npv_without_credits": run(with_inputs(p, char_price=v), r, credit_on=False)["npv"]}
        for v in range(150, 751, 50)]

    # The 16 designs in the source study (capital: Table 5; total cost per t: Table 9)
    with open(HERE / "designs.csv", newline="") as f:
        designs = [dict(row) for row in csv.DictReader(f)]
    out["designs"] = designs
    out["lowest_total_cost_design"] = min(designs, key=lambda d: float(d["total_cost_per_t"]))

    # Checks against the source study
    out["checks"] = {
        "biochar_output_full_t": p["feed_tonnes"] * p["yield"],
        "source_biochar_output_t": 16330,
        "direct_plus_feedstock_per_t": p["prod_cost"] + p["feed_cost"] / p["yield"],
        "source_direct_plus_feedstock_per_t": 359,
    }

    OUTDIR.mkdir(exist_ok=True)
    with open(OUTDIR / "results.json", "w") as f:
        json.dump(out, f, indent=2, default=float)
    write_markdown(p, out)
    return out


def money(x):
    return f"({abs(x)/1000:,.0f})" if x < 0 else f"{x/1000:,.0f}"


def write_markdown(p, o):
    b = o["base"]
    lines = ["# Model results", "", f"WACC: {o['wacc']*100:.1f}%",
             f"FIRR: {b['firr']*100:.1f}%  NPV at WACC: {b['npv']:,.0f}  Payback: {b['payback']:.1f} years",
             f"NPV at 8%: {b['npv_at_8pct']:,.0f}  NPV at 12%: {b['npv_at_12pct']:,.0f}", "",
             "## Cash flow ($ thousand)", "",
             "| Year | Biochar t | Biochar sales | Credit sales | Capital | Feedstock | Production | Salvage | Net |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in o["cash_flow_rows"]:
        lines.append(f"| {row['year']} | {row['biochar_t']:,.0f} | {money(row['char_sales'])} | {money(row['credit_sales'])} | "
                     f"{money(row['capital'])} | {money(row['feedstock'])} | {money(row['production'])} | "
                     f"{money(row['salvage'])} | {money(row['net'])} |")
    t = o["totals"]
    lines.append(f"| Total | | {money(t['char_sales'])} | {money(t['credit_sales'])} | {money(t['capital'])} | "
                 f"{money(t['feedstock'])} | {money(t['production'])} | {money(t['salvage'])} | {money(t['net'])} |")
    lines += ["", "## Standard tests", ""]
    for k, v in o["standard_tests"].items():
        lines.append(f"- {k}: FIRR {v['firr']*100:.1f}%, NPV {v['npv']:,.0f}")
    lines += ["", "## Switching values (%)", ""] + [f"- {k}: {v:.1f}" for k, v in o["switching_values_pct"].items()]
    lines += ["", "## Tornado", ""] + [f"- {k}: {v['low_input']} -> {v['low_npv']:,.0f}; {v['high_input']} -> {v['high_npv']:,.0f}"
                                     for k, v in o["tornado"].items()]
    lines += ["", "## Scenarios", ""]
    for k, v in o["scenarios"].items():
        firr = "not reached" if v["firr"] is None else f"{v['firr']*100:.1f}%"
        pb = "not reached" if v["payback"] is None else f"{v['payback']:.1f} years"
        lines.append(f"- {k}: NPV {v['npv']:,.0f}, FIRR {firr}, payback {pb}")
    lines += ["", "## Break-even values", ""] + [f"- {k}: {v:,.2f}" for k, v in o["breakeven"].items()]
    lines += ["", "## Checks", ""] + [f"- {k}: {v:,.1f}" for k, v in o["checks"].items()]
    (OUTDIR / "results.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
    print((OUTDIR / "results.md").read_text())
