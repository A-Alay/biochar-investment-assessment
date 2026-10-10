"""Builds the PDF report: cover + body (with running header and footer), two passes for contents page numbers."""
import json
import re
from pathlib import Path

import pdfplumber
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).parent
FIG = HERE / "fig"
R = json.load(open(HERE.parent / "outputs" / "results.json"))
EV = json.load(open(FIG / "evidence.json"))
CSS = (HERE / "style.css").read_text()
TITLE = "Forest-Residue Biochar Pyrolysis Plant"


def img(name):
    import base64
    data = base64.b64encode((FIG / name).read_bytes()).decode()
    return f"data:image/svg+xml;base64,{data}"


def fig(name, title, caption, num):
    return (f"<figure><div class='fig-title'>{title}</div><img src='{img(name)}'/>"
            f"<figcaption><b>Figure {num}.</b> {caption}</figcaption></figure>")


def section(num, title, lead, body, brk=False):
    return (f"<div class='{ 'page-break' if brk else ''}'><div class='sec-num'>Section {num}</div>"
            f"<h2 class='section'>{title}</h2><div class='sec-rule'></div><p class='lead'>{lead}</p>{body}</div>")


def annex(letter, title, lead, body, brk=True):
    return (f"<div class='{ 'page-break' if brk else ''}'><div class='sec-num'>Annex {letter}</div>"
            f"<h2 class='section'>{title}</h2><div class='sec-rule'></div><p class='lead'>{lead}</p>{body}</div>")


def table(head, rows, num_cols=(), total_last=False, cls=""):
    h = "".join(f"<th class='{'num' if i in num_cols else ''}'>{c}</th>" for i, c in enumerate(head))
    b = ""
    for ri, r in enumerate(rows):
        tr = " class='total'" if total_last and ri == len(rows) - 1 else ""
        b += f"<tr{tr}>" + "".join(f"<td class='{'num' if i in num_cols else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return f"<table class='{cls}'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def kpis(items, cls=""):
    return f"<div class='kpis {cls}'>" + "".join(
        f"<div class='kpi {'accent' if a else ''}'><div class='v'>{v}</div><div class='l'>{l}</div></div>" for v, l, a in items) + "</div>"


P = lambda s: f"<span class='pill p-src'>{s}</span>"
SRC, ASM, CMP = "<span class='pill p-src'>Sourced</span>", "<span class='pill p-asm'>Assumption</span>", "<span class='pill p-cmp'>Computed</span>"
HIGH, MED, LOW = "<span class='pill p-high'>High</span>", "<span class='pill p-med'>Medium</span>", "<span class='pill p-low'>Low</span>"

b = R["base"]
SESS = "<a href='https://extensionweb.forestry.oregonstate.edu/sites/default/files/BiocharForest-to-Farm2019.pdf'>Sessions et al. (2019)</a>"

# ---------- Contents (page numbers filled on second pass) ----------
TOC = [("", "Key figures at a glance"), ("", "Executive summary"), ("1", "Investment overview"), ("2", "Technology description"),
       ("3", "Market context"), ("4", "Development impact and monitoring framework"), ("5", "Project cost and financing plan"),
       ("6", "Operating economics"), ("7", "Basis of the financial analysis"), ("8", "Financial analysis"),
       ("9", "Sensitivity and scenario analysis"), ("10", "Risk assessment"), ("11", "Implementation arrangements"),
       ("12", "Safeguards and social due diligence"), ("13", "Recommendation and conditions"),
       ("A", "Assumption register"), ("B", "Model, method and checks"), ("C", "Sources")]


def contents(pages):
    rows = ""
    for no, ti in TOC:
        pg = pages.get(ti, "")
        cls = "annex" if no.isalpha() else ""
        rows += f"<div class='row {cls}'><span class='no'>{no}</span><span class='ti'>{ti}</span><span class='pg'>{pg}</span></div>"
    return (f"<div><div class='sec-num'>Contents</div><h2 class='section'>Inside this assessment</h2><div class='sec-rule'></div>"
            f"<div class='toc'>{rows}</div>"
            f"<div class='callout' style='margin-top:18pt'><div class='k'>How to read this report</div>"
            f"<p>Every number in this report comes from one run of a documented financial model. Each input is marked "
            f"{SRC} when it is taken from a named source, with the page or table, or {ASM} when it is a planning assumption. "
            f"The model files are listed in Annex B.</p></div>"
            f"</div>")


# ---------- Body ----------
def body(pages):
    h = []
    h.append(contents(pages))

    # At a glance
    h.append("<div class='page-break'><div class='sec-num'>At a glance</div><h2 class='section'>Key figures at a glance</h2><div class='sec-rule'></div>")
    h.append(kpis([(f"{b['firr']*100:.1f}%", "Financial internal rate of return", True),
                   (f"{R['wacc']*100:.1f}%", "Weighted average cost of capital (the hurdle)", False),
                   (f"${b['npv']/1e6:.1f}M", "Net present value at the cost of capital", True),
                   ("$19.1M", "Project cost, including engineering and a 15% contingency", False),
                   (f"{b['payback']:.1f} yrs", "Simple payback from start of operation", False),
                   (f"${R['breakeven']['char_price_with_credits']:.0f}/t", "Biochar price below which value turns negative", True)]))
    h.append("<div class='callout dark'><div class='k'>Recommendation</div><p>Proceed to the development stage. Commit the $19.1 million "
             "construction budget only once biochar offtake is signed and credit terms are confirmed, under the five conditions in Section 13.</p></div>")
    h.append(table(["Item", "Value"], [
        ["Project", "Slow pyrolysis plant converting forest residue to biochar"],
        ["Reference design", "Worden, Oregon site; thermal pyrolysis; heat recovery only (Scenario 2 in Sessions et al. 2019)"],
        ["Feedstock", "45,360 dry tonnes a year of forest thinning and logging residue"],
        ["Products", "16,330 tonnes a year of biochar; 40,824 tonnes of CO2 credited a year"],
        ["Financing plan", "60% debt, 40% equity (assumption)"],
        ["Evaluation period", "1 construction year plus 20 operating years"],
        ["Price basis", "US dollars, prices and costs held flat, pre-tax"]], cls="kv"))
    h.append("<p class='small'>In this report, \"$\" refers to US dollars, \"t\" to metric tonnes, and \"CO2\" to tonnes of carbon dioxide.</p></div>")

    # Executive summary
    h.append("<div class='page-break'><div class='sec-num'>Summary</div><h2 class='section'>Executive summary</h2><div class='sec-rule'></div>")
    h.append(f"<p class='lead'>The plant clears its cost of capital by a wide margin: a return of {b['firr']*100:.1f}% against a hurdle of "
             f"{R['wacc']*100:.1f}%, and a net present value of ${b['npv']/1e6:.1f} million.</p>")
    h.append("<p>Recommendation: proceed to the development stage, with the $19.1 million construction commitment conditional on signed "
             "biochar offtake and confirmed credit terms.</p>")
    h.append("<div class='grid2'>"
             "<div class='tile'><div class='t'>The biochar price decides the case</div><p>With credits, biochar must sell above $192 a tonne for "
             "the value to stay positive. Without credits it must sell above $507 a tonne, just above the $500 assumed here; at $500 and no "
             "credits the net present value is minus $0.8 million.</p></div>"
             "<div class='tile'><div class='t'>Standard adverse tests leave it viable</div><p>A 10% fall in revenue lowers the return to 28.1%. "
             "A one-year delay with 10% higher capital lowers it to 25.0%. Revenue can fall 37.8% before the project stops covering its "
             "cost of capital.</p></div></div>")
    h.append(fig("standard_tests.svg", "The return stays well above the 10.5% hurdle under every standard test",
                 "Financial internal rate of return in the base case and under each standard adverse test. Source: model run.", 1))
    h.append("<div class='callout ember'><div class='k'>Evidence base</div><p>The plant design, capital, yield, feedstock cost, production cost, life "
             "and salvage value come from one reference design in a published engineering study of forest-residue biochar plants in Oregon and "
             "California. That study does not state the year of its dollars, and its figures are not adjusted to today. The biochar price, credit "
             "volume, credit fees, start-up curve and financing terms are assumptions.</p></div></div>")

    # 1 Investment overview
    h.append(section(1, "Investment overview",
        "A stand-alone slow pyrolysis plant takes forest thinning and logging residue and sells two products: biochar and certified carbon removal credits.",
        table(["Item", "Value", "Source"], [
            ["Feedstock", "Forest residue, 45,360 dry tonnes a year", "Sessions et al. 2019, p. 177"],
            ["Biochar yield", "36% of dry feedstock weight", "Sessions et al. 2019, p. 178, Table 2"],
            ["Biochar output", "16,330 tonnes a year at full capacity", "Sessions et al. 2019, p. 184"],
            ["Staff", "26.5 full-time workers", "Sessions et al. 2019, p. 181, Table 6"],
            ["Operating life", "20 years", "Sessions et al. 2019, p. 182, Table 9"],
            ["Start-up", "60% of capacity in year 1, 85% in year 2, full from year 3", "Assumption"]])
        + f"<p>The reference design is the Worden, Oregon site with thermal pyrolysis and heat recovery only, which {SESS} label Scenario 2. "
          "In that design the pyrolysis gases are burned in a furnace whose heat dries the wood chips and drives the reactor; no electricity is generated.</p>",
        brk=True))

    # 2 Technology
    h.append(section(2, "Technology description",
        "Slow pyrolysis heats dried biomass to several hundred degrees with little or no oxygen. The wood does not burn: it breaks down into a solid, "
        "carbon-rich char, plus gases and vapors that the plant burns for its own heat.",
        fig("process_flow.svg", "Burning the pyrolysis gases heats the dryer and reactor; biochar is the one product",
            "Process flow of the reference design. Grey arrows show material, amber arrows show heat. Source: Sessions et al. 2019, p. 178, Table 3.", 2)
        + "<p>Slow pyrolysis is chosen over fast pyrolysis because it maximizes the solid product. "
          "<a href='https://www.biorenew.iastate.edu/research/thermochemical/biochar/productionscenarios'>Iowa State's Bioeconomy Institute</a> reports "
          "char yields of up to 40% of feedstock weight for slow pyrolysis, against a lower char yield for fast pyrolysis, which favors liquid bio-oil.</p>"
          "<p>The carbon in biochar is stable in soil for long periods, which is why it can earn carbon removal credits. Biochar is also sold as a soil "
          "amendment for farms and nurseries.</p>"
          "<p>Sessions et al. compared thermal and microwave pyrolysis at two sites under four energy-recovery designs. In their cost table (p. 182, Table 9), "
          "thermal pyrolysis at Worden with heat recovery only has the lowest total cost of the 16 cases: $446 per tonne of biochar, covering feedstock, "
          "production and capital. That is the reference design here.</p>"))

    # 3 Market
    h.append(section(3, "Market context",
        "Biochar is the volume leader in delivered carbon removal, but demand is concentrated in a few large buyers.",
        kpis([("86%", "Biochar share of delivered durable carbon removal credits (CDR.fyi, Sep. 2025)", False),
              ("$148/t", "U.S. biochar credit price for 2026 delivery (S&amp;P Global, Oct. 2025)", True),
              ("46%", "Microsoft's share of biochar credits contracted (CDR.fyi, Sep. 2025)", False)])
        + table(["Indicator", "Value", "Source"], [
            ["Biochar removal price corridor, base case", "EUR 120 to 180 per tonne", "<a href='https://www.senken.io/reports/carbon-removal-prices-2026-2040'>Senken, Aug. 2026</a>"],
            ["Biochar removal market value, 2024", "$181.5 million", "<a href='https://www.cdr.fyi/blog/biochar-carbon-removal-market-snapshot-2025'>CDR.fyi, Sep. 2025</a>"],
            ["Delivered as share of contracted, through Q2 2025", "about 22%", "<a href='https://www.cdr.fyi/blog/biochar-carbon-removal-market-snapshot-2025'>CDR.fyi, Sep. 2025</a>"],
            ["Biochar minimum selling price, slow pyrolysis", "$188 to $260 per tonne", "<a href='https://research-hub.nrel.gov/en/publications/process-feasibility-analysis-of-waste-biomass-valorization-to-bio/'>NREL, 2025</a>"],
            ["U.S. biochar credit price, 2026 delivery", "about $148 per tonne CO2", "S&amp;P Global, via <a href='https://carboncredits.com/?p=39628'>Carbon Credits</a>"]])
        + "<p>Credit demand is real but narrow. The top four buyers, Microsoft, Google, BCG and JPMorgan, account for 57% of biochar credit purchases, "
          "and the median buyer took fewer than 100 tonnes in the first half of 2025.</p>"
          "<div class='callout ember'><div class='k'>Price of the product itself</div><p>The biochar product price has no single market benchmark. "
          "Sessions et al. cite a 2014 survey average wholesale price of $1,500 a tonne among 28 U.S. producers (p. 183), and estimate that a plant of "
          "this size could produce biochar for $500 to $600 a tonne. This assessment assumes a sale price of $500 a tonne and tests $250 to $700.</p></div>",
        brk=True))

    # 4 DMF
    h.append(section(4, "Development impact and monitoring framework",
        "The outcome is a plant running at full capacity from operating year 3, turning 45,360 dry tonnes of forest residue a year into biochar and certified carbon removal.",
        fig("results_chain.svg", "Capital and residue become a running plant, which delivers biochar and carbon removal",
            "Results chain, following the ADB design and monitoring framework format.", 3)
        + table(["Results chain", "Indicators, targets and baselines", "Data sources", "Risks and assumptions"], [
            ["<b>Impact:</b> forest residue converted into stable soil carbon and a farm input", "Not measured at project level", "Not applicable", "Assumption: biochar and credit markets continue to grow"],
            ["<b>Outcome:</b> biochar plant operating at full capacity", "16,330 t of biochar a year by operating year 3 (baseline 0); 40,824 t CO2 credited a year (baseline 0); 45,360 dry t of residue processed a year (baseline 0)", "Plant production records; registry issuance records", "Risk: feedstock supply short of contract; credit buyers withdraw"],
            ["<b>Output 1:</b> plant constructed and commissioned", "Capacity of 45,360 dry t a year installed (baseline 0)", "Commissioning certificate; supplier performance test", "Risk: delayed commissioning"],
            ["<b>Output 2:</b> offtake secured", "Biochar and credit contracts covering at least 5 years signed before construction (baseline 0)", "Signed contracts", "Risk: buyers only commit short term"],
            ["<b>Output 3:</b> local jobs created", "26.5 full-time operating jobs (baseline 0)", "Payroll records", "Assumption: staff can be hired locally"]])
        + "<p class='tnote'>Targets come from the plant design in this assessment. The credited tonnage is 16,330 t of biochar times the assumed 2.5 t CO2 per tonne.</p>",
        brk=True))

    # 5 Cost and financing
    h.append(section(5, "Project cost and financing plan",
        "The project costs $19.1 million, financed 60% by debt and 40% by equity, for a weighted average cost of capital of 10.5%.",
        fig("designs.svg", "The reference design has the lowest total cost per tonne of the 16 designs studied",
            "Capital cost against total cost per tonne of biochar (feedstock, production and capital) for every site, technology and energy-recovery "
            "design in Sessions et al. 2019 (p. 180, Table 5; p. 182, Table 9). Model input: designs.csv.", 4)
        + "<p>The sensitivity tests use the lowest capital of the 16 designs, $17.0 million (Yreka, microwave, Scenario 1), and the highest, $28.1 million "
          "(Worden, thermal, Scenario 4). The study's capital estimates include site preparation, buildings, equipment installation, engineering, contractor "
          "and owner costs, and a 15% contingency (p. 180). They do not mention working capital, and they are not adjusted for construction cost inflation "
          "since the study's 2019 publication.</p>"
        + "<h3>Weighted average cost of capital</h3>"
        + table(["Source", "Amount ($ million)", "Weight (%)", "Nominal cost (%)", "Composite cost (%)"],
                [["Senior debt", "11.46", "60", "7.5", "4.5"], ["Sponsor equity", "7.64", "40", "15.0", "6.0"], ["Total", "19.10", "100", "", "10.5"]],
                num_cols=(1, 2, 3, 4), total_last=True)
        + "<p>The debt share, debt rate and cost of equity are assumptions, to be replaced by lender term sheets. The cost of capital is pre-tax and nominal, "
          "matching the pre-tax cash flows. The project is judged viable when its financial internal rate of return exceeds this cost of capital, the test ADB "
          "applies in its <a href='https://www.adb.org/sites/default/files/linked-documents/41626-01-ind-fa.pdf'>financial analysis for the Bihar Power System "
          "Improvement Project</a>.</p>",
        brk=True))

    # 6 Operating economics
    f = R["full_capacity_year"]
    h.append(section(6, "Operating economics",
        "At full capacity the plant earns $13.3 million a year against $5.9 million of running cost, leaving $7.4 million of operating cash.",
        fig("waterfall.svg", "Each full-capacity year turns $13.3M of revenue into $7.4M of operating cash",
            "Revenue and operating cost in a full-capacity year (operating year 3 onward), base case. Source: model run.", 5)
        + fig("mix.svg", "Biochar sales carry six-tenths of revenue; production is the larger cost",
              "Shares of revenue and of operating cost in a full-capacity year. Source: model run.", 6)
        + "<p>Each line is a quantity times a price: biochar sales are 16,330 t at $500; credit sales are 16,330 t times 2.5 t CO2 per tonne at $148, less 15% "
          "fees; feedstock is 45,360 t at $55; production is 16,330 t at $207. Biochar tonnage is 45,360 t times 36%, or 16,329.6 t, shown rounded.</p>"
          "<div class='grid2'><div class='tile'><div class='t'>Feedstock: $55 a dry tonne</div><p>The planning cost Sessions et al. use for the Worden site "
          "(p. 181). Their range of collection and delivery cost to Worden runs from $43 to $135 a tonne (p. 179).</p></div>"
          "<div class='tile'><div class='t'>Production: $207 a tonne of biochar</div><p>The study's direct production cost for the reference design (p. 182, "
          "Table 9): staffing, purchased energy, raw materials and other plant costs, excluding feedstock and capital. For thermal pyrolysis it ranges from $184 to $254.</p></div></div>"
          "<div class='callout ember'><div class='k'>Assumptions to confirm</div><p>The credit volume of 2.5 tonnes of CO2 per tonne of biochar and the 15% fee share "
          "are assumptions. The credited amount depends on the biochar's carbon content and the registry's method, and must be confirmed by lab testing and the chosen registry.</p></div>",
        brk=False))

    # 7 Basis
    basis = [("Price basis", "All prices and costs are held flat in nominal US dollars over the evaluation period. No price escalation and no price contingency are applied. The source study does not state the year of its dollars."),
             ("Evaluation period", "One construction year, then 20 operating years. Output starts at 60% of capacity in year 1, 85% in year 2, and 100% from year 3."),
             ("Salvage", "20% of capital is recovered in operating year 20, as in the source study."),
             ("Tax", "Cash flows are before income tax, so they are compared with a pre-tax cost of capital."),
             ("Financing", "Interest during construction and loan repayments are excluded from the project cash flows; financing enters only through the cost of capital."),
             ("Excluded", "Depreciation, working capital, government grants, and non-market benefits such as wildfire hazard reduction."),
             ("Revenue", "Biochar sales plus carbon removal credits, net of 15% credit fees. Every tonne produced is assumed sold."),
             ("Decision rule", "The project is financially viable if its internal rate of return exceeds the 10.5% cost of capital, the same as a positive net present value at that rate.")]
    h.append(section(7, "Basis of the financial analysis",
        "The analysis counts only the cash flows the plant creates, compared against a without-project case in which no plant is built and no revenue or cost arises.",
        "<div class='grid2'>" + "".join(f"<div class='tile'><div class='t'>{t}</div><p>{d}</p></div>" for t, d in basis) + "</div>"
        ,
        brk=False))

    # 8 Financial analysis
    def k(v):
        return f"({abs(v)/1000:,.0f})" if v < 0 else f"{v/1000:,.0f}"
    rr = R["cash_flow_rows"]
    t = R["totals"]
    cf_rows = [["0", k(0), k(0), k(rr[0]["capital"]), k(0), k(0), k(0), k(rr[0]["net"])]]
    for i in (1, 2):
        r = rr[i]
        cf_rows.append([str(i), k(r["char_sales"]), k(r["credit_sales"]), "0", k(r["feedstock"]), k(r["production"]), "0", k(r["net"])])
    r = rr[3]
    cf_rows.append(["3 to 19, each year", k(r["char_sales"]), k(r["credit_sales"]), "0", k(r["feedstock"]), k(r["production"]), "0", k(r["net"])])
    r = rr[20]
    cf_rows.append(["20", k(r["char_sales"]), k(r["credit_sales"]), "0", k(r["feedstock"]), k(r["production"]), k(r["salvage"]), k(r["net"])])
    cf_rows.append(["Total, years 0 to 20", k(t["char_sales"]), k(t["credit_sales"]), k(t["capital"]), k(t["feedstock"]), k(t["production"]), k(t["salvage"]), k(t["net"])])
    h.append(section(8, "Financial analysis",
        f"The financial internal rate of return is {b['firr']*100:.1f}%, against a {R['wacc']*100:.1f}% cost of capital, which supports the financial viability of the project.",
        kpis([(f"{b['firr']*100:.1f}%", "Financial internal rate of return", True), (f"${b['npv']/1e6:.1f}M", "NPV at 10.5%", False),
              (f"${b['npv_at_8pct']/1e6:.1f}M", "NPV at 8% (rate used by Sessions et al.)", False), (f"${b['npv_at_12pct']/1e6:.1f}M", "NPV at 12%", False),
              (f"{b['payback']:.1f} yrs", "Simple payback from start of operation", False)], cls="five")
        + "<h3>Calculation of the financial internal rate of return ($ thousand)</h3>"
        + table(["Year", "Biochar sales", "Credit sales", "Capital", "Feedstock", "Production", "Salvage", "Net benefit"], cf_rows, num_cols=(1, 2, 3, 4, 5, 6, 7), total_last=True)
        + "<p class='tnote'>( ) = negative. Figures may not add exactly because of rounding. Credit sales are net of 15% fees. Source: model run, outputs/results.md.</p>"
        + fig("cumulative_cash.svg", "Cumulative cash recovers the $19.1M outlay in year 4",
              "Cumulative pre-tax project cash flow, base case. Year 20 includes salvage value. Source: model run.", 7)
        + "<p>These returns assume every tonne of biochar sells at $500 and earns credits at $148. Section 9 shows how fast they fall when either price slips.</p>",
        brk=True))

    # 9 Sensitivity
    st = R["standard_tests"]
    sv = R["switching_values_pct"]
    sens_rows = [["Base case", "", f"{b['firr']*100:.1f}", f"{b['npv']/1e6:.1f}", ""],
                 ["Revenue reduced", "minus 10%", f"{st['revenue_minus_10']['firr']*100:.1f}", f"{st['revenue_minus_10']['npv']/1e6:.1f}", f"minus {abs(sv['revenue']):.1f}"],
                 ["Biochar price reduced", "minus 10%", f"{st['biochar_price_minus_10']['firr']*100:.1f}", f"{st['biochar_price_minus_10']['npv']/1e6:.1f}", f"minus {abs(sv['biochar_price']):.1f}"],
                 ["Capital cost increased", "plus 10%", f"{st['capital_plus_10']['firr']*100:.1f}", f"{st['capital_plus_10']['npv']/1e6:.1f}", f"plus {sv['capital']:.1f}"],
                 ["Operating cost increased", "plus 10%", f"{st['operating_cost_plus_10']['firr']*100:.1f}", f"{st['operating_cost_plus_10']['npv']/1e6:.1f}", f"plus {sv['operating_cost']:.1f}"],
                 ["Credit price reduced", "minus 10%", f"{st['credit_price_minus_10']['firr']*100:.1f}", f"{st['credit_price_minus_10']['npv']/1e6:.1f}", f"minus {abs(sv['credit_price']):.1f}"],
                 ["One-year delay and capital cost increased", "1 year; plus 10%", f"{st['delay_1yr_capital_plus_10']['firr']*100:.1f}", f"{st['delay_1yr_capital_plus_10']['npv']/1e6:.1f}", ""],
                 ["Weighted average cost of capital", "", f"{R['wacc']*100:.1f}", "", ""]]
    sc = R["scenarios"]
    be = R["breakeven"]
    h.append(section(9, "Sensitivity and scenario analysis",
        "The return stays above the 10.5% cost of capital under every standard adverse test; revenue is the input the project is most sensitive to.",
        "<h3>Results of financial sensitivity analyses</h3>"
        + table(["Sensitivity parameter", "Variation", "FIRR (%)", "NPV at 10.5% ($ million)", "Switching value (%)"], sens_rows, num_cols=(2, 3, 4), total_last=True)
        + "<p class='tnote'>The switching value is the change in an input, on its own, that brings the net present value at 10.5% down to zero. Operating cost covers feedstock and production.</p>"
        + fig("tornado.svg", "Biochar sale price swings project value more than any other input",
              "Net present value when one input moves to its low or high value and all others stay at base. Ranges for capital, feedstock cost and production "
              "cost are from Sessions et al. (2019); ranges for prices and credit volume are assumptions. Source: model run.", 8)
        + fig("price_curve.svg", "Biochar must sell above $192 a tonne with credits, or $507 without",
              "Net present value at the 10.5% cost of capital across biochar prices, with and without credit revenue. Every $50 a tonne moves value by $6.3 million. "
              "Source: model run, price_curve in outputs/results.json.", 9)
        + kpis([(f"${be['char_price_with_credits']:.0f}", "Biochar price needed per tonne, with credits", True),
                (f"${be['char_price_without_credits']:.0f}", "Biochar price needed per tonne, without credits", False),
                (f"${be['credit_price']:.0f}", "Credit price needed per tonne CO2, at $500 biochar", False),
                (f"${be['feed_cost']:.0f}", "Feedstock cost the project can carry per dry tonne", False),
                (f"${be['capital']/1e6:.1f}M", "Capital the project can carry", False)], cls="five")
        + fig("scenarios.svg", "Only the combined downside, or losing all credit revenue, sinks the project",
              "Net present value at 10.5% under four scenarios. Source: model run.", 10)
        + table(["Scenario", "Inputs", "NPV at 10.5%", "FIRR", "Payback"], [
            ["Upside", "Biochar $600, credits $180, capital $17.0M, production $184, feedstock $43", f"${sc['upside']['npv']:,.0f}", f"{sc['upside']['firr']*100:.1f}%", f"{sc['upside']['payback']:.1f} years"],
            ["Base", "As in the assumption register", f"${b['npv']:,.0f}", f"{b['firr']*100:.1f}%", f"{b['payback']:.1f} years"],
            ["No credits sold", "Base, with zero credit revenue", f"minus ${abs(sc['no_credits']['npv']):,.0f}", f"{sc['no_credits']['firr']*100:.1f}%", f"{sc['no_credits']['payback']:.1f} years"],
            ["Downside", "Biochar $300, credits $100, capital $28.1M, production $254, feedstock $80", f"minus ${abs(sc['downside']['npv']):,.0f}", f"minus {abs(sc['downside']['firr'])*100:.1f}%", "Not reached"]],
            num_cols=(2, 3))
        + "<div class='callout ember'><div class='k'>What to secure first</div><p>At $500 biochar, a credit price of only $3 a tonne is enough to clear the cost "
          "of capital; with no credit revenue at all, the project falls just short. The biochar sale price is the input to secure first.</p></div>",
        brk=True))

    # 10 Risk
    h.append(section(10, "Risk assessment",
        "Overall risk is rated substantial, driven by market risks outside the sponsor's control; project-specific risks are moderate and can be reduced by contract before construction.",
        "<h3>External risks</h3>"
        + table(["Risk", "Effect if it happens", "Rating", "Mitigation"], [
            ["Biochar sells below $192 a tonne", "Net present value turns negative", HIGH, "Multi-year offtake with farm, nursery and landscaping distributors before financial close"],
            ["Credit buyers pull back", "At zero credit revenue, value falls to minus $0.8 million", HIGH, "Forward offtake for at least 5 years of credits; registry certification before start-up"],
            ["Registry method credits less CO2 per tonne", "At 1.8 t, value falls to $27.8 million", MED, "Confirm the registry method and lab-test biochar during design"]])
        + "<h3>Project-specific risks</h3>"
        + table(["Risk", "Effect if it happens", "Rating", "Mitigation"], [
            ["Feedstock cost rises to $135 a tonne", "Value falls to $10.8 million; break-even at $166", MED, "Long-term supply contracts with forest owners and land agencies; site near the residue source"],
            ["Capital overrun", "At $28.1 million, value is $30.2 million; break-even at $59.1 million", LOW, "Fixed-price engineering and construction contract; brownfield or sawmill site"],
            ["Start-up delayed one year, capital up 10%", "Return falls to 25.0%", MED, "Supplier performance guarantees on throughput and yield"],
            ["Cost data from a 2019 study with no stated dollar year", "Real costs may be higher today", MED, "Replace study figures with vendor quotes before approval"]])
        + "<p class='tnote'>Ratings are the assessor's judgment, based on how far each input can move the value. They are not probabilities.</p>",
        brk=False))

    # 11 Implementation
    h.append(section(11, "Implementation arrangements",
        "The plan runs from approval to a full-capacity review at the end of operating year 3, 57 months after approval, with construction held behind a financial close gate.",
        table(["Aspect", "Arrangement"], [
            ["Sponsor and management", "Open question: sponsor and operating company to be named"],
            ["Implementation period", "About 21 months from approval to commissioning"],
            ["Construction", "Fixed-price engineering, procurement and construction contract"],
            ["Technology supplier", "Conventional thermal slow pyrolysis with heat recovery, selected by competitive bid"],
            ["Feedstock supply", "Long-term contracts with forest owners and land agencies at about $55 a dry tonne delivered"],
            ["Revenue structure", "Biochar offtake contracts plus carbon removal credit offtake contracts, each covering at least 5 years"],
            ["Operating cost structure", "Feedstock 42% and production 58% of operating cost at full capacity"],
            ["Staffing", "26.5 full-time workers"],
            ["Performance monitoring", "Production and registry issuance reports against the indicators in the monitoring framework"]], cls="kv")
        + fig("timeline.svg", "Construction starts only after the financial close gate at month 9",
              "Plan from approval to the full-capacity review, in months after approval. Durations are planning assumptions, to be confirmed with the chosen technology supplier.", 11)
        + "<ol class='steps'>"
          "<li>Site selection, with priority on brownfield or sawmill co-location; feedstock supply survey within haul distance.</li>"
          "<li>Lab tests of biochar from site feedstock; confirm credited CO2 per tonne with the chosen registry.</li>"
          "<li>Sign biochar and credit offtake agreements; sign feedstock supply contracts.</li>"
          "<li>Fixed-price engineering and construction bids; replace study cost figures with quotes; re-run the model.</li>"
          "<li>Permitting and construction.</li>"
          "<li>Commissioning, then operating years 1 and 2 at 60% and 85% of capacity.</li>"
          "<li>Review at the end of operating year 3 against full-capacity output of 16,330 tonnes and operating cash of $7.4 million.</li></ol>"
          "<div class='callout'><div class='k'>Financial close gate</div><p>Step 4 is the gate: no construction contract is signed until quoted capital and signed "
          "offtake keep the net present value positive.</p></div>",
        brk=True))

    # 12 Safeguards
    h.append(section(12, "Safeguards and social due diligence",
        "No environmental or social review has been done for this assessment. The following must be completed and cleared before the construction commitment.",
        "<ul class='clean'>"
        "<li><b>Environmental review</b> of the chosen site, covering air emissions from the pyrolysis units, noise, water use and ash or fines handling, with the permits these require.</li>"
        "<li><b>Feedstock sourcing review</b> confirming where the residue comes from and that it meets the chosen registry's feedstock rules.</li>"
        "<li><b>Worker health and safety plan</b> covering fire and dust risks at the plant and in feedstock storage.</li>"
        "<li><b>Land and site status</b> confirming ownership or lease of the site and any access or power line rights.</li>"
        "<li><b>Stakeholder consultation</b> with nearby communities and land agencies, with a grievance mechanism for complaints.</li>"
        "<li><b>Environmental and social management plan</b> setting out mitigation measures, with semiannual monitoring reports during construction and annual reports in operation.</li></ul>"
        "<p class='small'>The monitoring schedule follows the arrangement in the ADB Southern Thailand Waste-to-Energy Project report, where the borrower reports semiannually during construction and annually thereafter.</p>",
        brk=False))

    # 13 Recommendation
    conds = ["Signed biochar offtake for most of the planned output at $500 a tonne or more, with a floor no lower than $192.",
             "Signed credit offtake for at least 5 years, with registry certification in place before start-up.",
             "Lab tests confirm credited CO2 near 2.5 tonnes per tonne of biochar.",
             "Feedstock contracts lock delivered cost at or near $55 a dry tonne.",
             "Fixed-price quotes keep capital at or below $28.1 million."]
    h.append(section(13, "Recommendation and conditions",
        "Approve the project to the development stage, with the $19.1 million construction commitment subject to five conditions.",
        "<div class='conds'>" + "".join(f"<div class='cond'><div class='n'>{i+1}</div><div>{c}</div></div>" for i, c in enumerate(conds)) + "</div>"
        + "<div class='callout dark' style='margin-top:16pt'><div class='k'>If a condition fails</div><p>Re-run this assessment with the new figures before committing capital.</p></div>", brk=True))

    # Annex A
    reg = [["Dry feedstock processed", "45,360 t a year", SRC, "Sessions et al. 2019, p. 177, Section 2.2.1"],
           ["Biochar yield, thermal pyrolysis", "36%", SRC, "Sessions et al. 2019, p. 178, Section 2.2.2 and Table 2"],
           ["Capital, reference design", "$19.1 million", SRC, "Sessions et al. 2019, p. 180, Table 5 (Worden, thermal, Scenario 2)"],
           ["Capital range", "$17.0M to $28.1M", SRC, "Sessions et al. 2019, p. 180, Table 5 (lowest and highest of 16 designs)"],
           ["Delivered feedstock cost", "$55 a dry t", SRC, "Sessions et al. 2019, p. 181, Section 3.5 (Worden)"],
           ["Feedstock cost range", "$43 to $135 a dry t", SRC, "Sessions et al. 2019, p. 179, Section 3.1"],
           ["Direct production cost", "$207 per t biochar", SRC, "Sessions et al. 2019, p. 182, Table 9 (Worden, thermal, Scenario 2)"],
           ["Production cost range, thermal", "$184 to $254 per t", SRC, "Sessions et al. 2019, p. 182, Table 9"],
           ["Operating life", "20 years", SRC, "Sessions et al. 2019, p. 182, Table 9 header"],
           ["Salvage value", "20% of capital", SRC, "Sessions et al. 2019, p. 182, Table 9 header"],
           ["Staff", "26.5 FTE", SRC, "Sessions et al. 2019, p. 181, Table 6"],
           ["Credit price", "$148 per t CO2", SRC, "S&amp;P Global, Oct. 2025, as reported by Carbon Credits, Dec. 3, 2025"],
           ["Biochar sale price", "$500 per t (tested $250 to $700)", ASM, "Context: 2014 survey wholesale average $1,500 per t, Sessions et al. 2019, p. 183"],
           ["Credit price range", "$80 to $220 per t CO2", ASM, "None"],
           ["CO2 credited", "2.5 t per t biochar (tested 1.8 to 3.0)", ASM, "To be replaced by lab test and registry method"],
           ["Credit fees", "15% of credit revenue", ASM, "None"],
           ["Start-up", "60%, 85%, then 100%", ASM, "None"],
           ["Debt share and rate", "60% at 7.5% nominal", ASM, "To be replaced by lender term sheet"],
           ["Equity share and cost", "40% at 15.0% nominal", ASM, "To be replaced by sponsor hurdle rate"],
           ["Weighted average cost of capital", "10.5% nominal, pre-tax", CMP, "From the two rows above"],
           ["Prices and costs", "Flat in nominal terms, pre-tax", ASM, "None"]]
    h.append(annex("A", "Assumption register",
        "Every model input, with its status and the exact place it comes from.",
        f"<figure><img src='{img('evidence.svg')}'/><figcaption><b>Figure 12.</b> Entries in the model input file, inputs.csv, by status "
        "(sensitivity bounds counted as separate entries).</figcaption></figure>"
        + table(["Input", "Value", "Status", "Source and exact location"], reg)))

    # Annex B
    method = ["The project is compared with a without-project case in which no plant is built; only the cash flows the plant creates are counted.",
              "Year 0 is construction, when the capital is spent. Years 1 to 20 are operation.",
              "Each year, biochar output is dry feedstock times yield times capacity use (60% in year 1, 85% in year 2, 100% after).",
              "Revenue is biochar tonnes times the biochar price, plus biochar tonnes times CO2 credited per tonne times the credit price, less the credit fee share.",
              "Operating cost is feedstock tonnes times delivered feedstock cost, plus biochar tonnes times direct production cost.",
              "Salvage value, 20% of capital, is added in year 20.",
              "Net benefit each year is revenue minus operating cost plus salvage. All flows are pre-tax and in flat nominal dollars.",
              "The weighted average cost of capital is the debt share times the debt rate plus the equity share times the cost of equity.",
              "The financial internal rate of return is the discount rate at which net benefits sum to zero in present value. The net present value is the sum of net benefits discounted at the cost of capital. Payback is the time until cumulative net benefit turns positive.",
              "Standard tests change revenue, biochar price, credit price, operating cost or capital by 10%, and delay operation one year with 10% more capital. The switching value is the percentage change in one input that brings the net present value to zero, found by numerical root search.",
              "Range tests set one input at a time to its low and high value. Scenarios change several inputs together. Break-even values are found by root search on the net present value."]
    h.append(annex("B", "Model, method and checks",
        "Every number in this report comes from one run of a Python model, model.py, reading one input file, inputs.csv. Changing an input and rerunning the model regenerates every figure.",
        table(["File", "Contents"], [
            ["inputs.csv", "Every input: value, unit, status, source and exact page, table or section"],
            ["designs.csv", "Capital (p. 180, Table 5) and total cost per tonne (p. 182, Table 9) for the 16 designs in Sessions et al. 2019"],
            ["model.py", "The model: cash flow, return measures, sensitivity, scenarios, break-even values, price curve, checks"],
            ["outputs/results.md and results.json", "Results of the run, including every year of the cash flow"]])
        + "<h3>Method</h3><ol class='steps'>" + "".join(f"<li>{m}</li>" for m in method) + "</ol>"
        + "<h3>Checks against the source study</h3>"
        + table(["Check", "Model", "Sessions et al. 2019", "Location"], [
            ["Biochar output at full capacity", "16,329.6 t", "about 16,330 t", "p. 184, Section 4"],
            ["Direct production plus feedstock cost per t biochar", "$359.8", "$359", "p. 182, Table 9"]])
        + "<p class='tnote'>The study's capital charge of $86 per tonne (p. 182, Table 9) is not reproduced: the model values capital through the cash flow instead of a capital charge.</p>"
        + f"<p class='small'>Run on October 10, 2026. Results: cost of capital {R['wacc']*100:.1f}%; return {b['firr']*100:.1f}%; net present value ${b['npv']:,.0f}; payback {b['payback']:.1f} years.</p>"))

    # Annex C
    src = [("Can biochar link forest restoration with commercial agriculture?", "https://extensionweb.forestry.oregonstate.edu/sites/default/files/BiocharForest-to-Farm2019.pdf", "J. Sessions et al., Biomass and Bioenergy 123: 175 to 185, 2019"),
           ("Estimating profitability of two biochar production scenarios: slow pyrolysis vs fast pyrolysis", "https://www.biorenew.iastate.edu/research/thermochemical/biochar/productionscenarios", "Iowa State University Bioeconomy Institute (T. Brown, M. Wright, R. Brown, 2010)"),
           ("Biochar Carbon Credits in 2025: Stable Prices Amid Weakening Demand", "https://carboncredits.com/?p=39628", "Carbon Credits, Dec. 3, 2025 (reporting S&amp;P Global prices)"),
           ("Biochar carbon removal market snapshot 2025", "https://www.cdr.fyi/blog/biochar-carbon-removal-market-snapshot-2025", "CDR.fyi, Sep. 9, 2025"),
           ("Carbon removal prices 2026 to 2040", "https://www.senken.io/reports/carbon-removal-prices-2026-2040", "Senken, Aug. 20, 2026"),
           ("Process Feasibility Analysis of Waste Biomass Valorization to Biochar and Bio-Oil via Slow and Fast Pyrolysis", "https://research-hub.nrel.gov/en/publications/process-feasibility-analysis-of-waste-biomass-valorization-to-bio/", "NREL, Energy and Fuels, 2025")]
    bench = [("Financial Analysis, Bihar Power System Improvement Project (RRP IND 41626)", "https://www.adb.org/sites/default/files/linked-documents/41626-01-ind-fa.pdf", "Asian Development Bank"),
             ("Report and Recommendation of the President: Southern Thailand Waste-to-Energy Project (49067-001)", "https://ewsdata.rightsindevelopment.org/files/documents/01/ADB-49067-001.pdf", "Asian Development Bank, Sept. 2017"),
             ("Report and Recommendation of the President: GWTE Circular Economy Project (58132-001)", "https://www.adb.org/sites/default/files/project-documents/58132/58132-001-rrp-en.pdf", "Asian Development Bank, Feb. 2026")]
    li = lambda xs: "<ul class='src-list'>" + "".join(f"<li><a href='{u}'>{t}</a>, {d}</li>" for t, u, d in xs) + "</ul>"
    h.append(annex("C", "Sources", "Sources of data, and the published reports used as format benchmarks.",
                   "<h3>Data sources</h3>" + li(src) + "<h3>Format benchmarks</h3>" + li(bench), brk=False))
    return "".join(h)


def cover():
    return f"""<html><head><style>
@page {{ size: Letter; margin: 0; }}
body {{ margin:0; font-family:'Source Sans 3',sans-serif; -webkit-print-color-adjust: exact; }}
.c {{ position:relative; width:8.5in; height:11in; background:#1F3A2E; color:#fff; overflow:hidden; }}
.art {{ position:absolute; inset:0; width:100%; height:100%; }}
.band {{ position:absolute; left:0; top:0; width:0.32in; height:100%; background:#C8892B; }}
.top {{ position:absolute; left:0.95in; top:0.9in; font-size:9pt; letter-spacing:2.4pt; text-transform:uppercase; color:#C8D6C6; }}
.t {{ position:absolute; left:0.95in; top:3.0in; width:6.3in; }}
.kick {{ font-size:10pt; letter-spacing:2.2pt; text-transform:uppercase; color:#C8892B; font-weight:700; }}
h1 {{ font-family:'Merriweather',serif; font-weight:600; font-size:40pt; line-height:1.08; margin:12pt 0 14pt; color:#fff; }}
.sub {{ font-size:13pt; color:#DCE6DA; line-height:1.45; }}
.stats {{ position:absolute; left:0.95in; bottom:1.45in; display:flex; gap:0.42in; }}
.s .v {{ font-family:'Merriweather',serif; font-size:24pt; color:#fff; }}
.s .l {{ font-size:8pt; letter-spacing:1pt; text-transform:uppercase; color:#C8D6C6; margin-top:2pt; }}
.foot {{ position:absolute; left:0.95in; bottom:0.7in; right:0.9in; display:flex; justify-content:space-between; font-size:9pt; color:#C8D6C6; border-top:1px solid rgba(255,255,255,0.25); padding-top:9pt; }}
</style></head><body><div class='c'><img class='art' src='{img('cover_art.svg')}'/><div class='band'></div>
<div class='top'>Investment assessment</div>
<div class='t'><div class='kick'>Bioeconomy &middot; Carbon removal</div><h1>{TITLE}</h1>
<div class='sub'>Financial, development and risk assessment of a 45,360 dry-tonne-a-year slow pyrolysis plant producing biochar and certified carbon removal</div></div>
<div class='stats'><div class='s'><div class='v'>{R['base']['firr']*100:.1f}%</div><div class='l'>Return</div></div>
<div class='s'><div class='v'>${R['base']['npv']/1e6:.1f}M</div><div class='l'>NPV at 10.5%</div></div>
<div class='s'><div class='v'>$19.1M</div><div class='l'>Project cost</div></div>
<div class='s'><div class='v'>16,330 t</div><div class='l'>Biochar a year</div></div></div>
<div class='foot'><span>Prepared by Ahmed Alayidi</span><span>October 10, 2026</span></div></div></body></html>"""


HEADER = f"<div style='font-family:'Source Sans 3',sans-serif;font-size:7.5pt;color:#6B7178;width:100%;padding:0 0.8in;display:flex;justify-content:space-between;'><span>Investment Assessment</span><span>{TITLE}</span></div>"
FOOTER = "<div style='font-family:'Source Sans 3',sans-serif;font-size:7.5pt;color:#6B7178;width:100%;padding:0 0.8in;display:flex;justify-content:space-between;'><span>October 2026</span><span><span class='pageNumber'></span></span></div>"


def render(html_body, path, browser):
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
    pg = browser.new_page()
    pg.set_content(html, wait_until="networkidle")
    pg.pdf(path=str(path), format="Letter", print_background=True, display_header_footer=True,
           header_template=HEADER, footer_template=FOOTER,
           margin={"top": "0.85in", "bottom": "0.85in", "left": "0.8in", "right": "0.8in"})
    pg.close()


def find_pages(path):
    pages = {}
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(pdf.pages):
            txt = p.extract_text() or ""
            for _, ti in TOC:
                if ti in pages:
                    continue
                lines = [l.strip() for l in txt.splitlines()]
                if ti in lines and i > 0:
                    pages[ti] = i + 1  # matches the printed footer number
    return pages


def main():
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        pg.set_content(cover(), wait_until="networkidle")
        pg.pdf(path=str(HERE / "cover.pdf"), width="8.5in", height="11in", print_background=True)
        pg.close()
        render(body({}), HERE / "body.pdf", br)
        pages = find_pages(HERE / "body.pdf")
        render(body(pages), HERE / "body.pdf", br)
        br.close()
    w = PdfWriter()
    for f in ("cover.pdf", "body.pdf"):
        for page in PdfReader(str(HERE / f)).pages:
            w.add_page(page)
    w.add_metadata({"/Title": f"Investment Assessment: {TITLE}", "/Author": "Ahmed Alayidi"})
    out = HERE / "rebuild" / "Investment_Assessment_rebuild.pdf"
    out.parent.mkdir(exist_ok=True)
    with open(out, "wb") as fh:
        w.write(fh)
    print(out, len(PdfReader(str(out)).pages), "pages", pages)


main()
