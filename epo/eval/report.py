"""Generated reports: the README results block and the charts. Never edited by hand."""
from __future__ import annotations

import json
from pathlib import Path

from epo.config import ROOT

REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
README = ROOT / "README.md"
START, END = "<!-- results:start -->", "<!-- results:end -->"
AS_FOUND, AI_GREEN, PLATFORM = "#C2410C", "#00897B", "#1D4ED8"     # validated for colour-blind separation
INK, MUTED, GRID, SURFACE = "#1F2430", "#5E6573", "#E4E6EA", "#FCFCFB"
FONT = 'font-family="Inter, system-ui, sans-serif"'


def load(name: str) -> dict | None:
    p = REPORTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def write(name: str, obj: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{name}.json").write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def _n(x: float | None, d: int = 1) -> str:
    return "–" if x is None else f"{x:,.{d}f}"


def _svg(w: int, h: int, title: str, sub: str, body: list[str]) -> str:
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" {FONT} role="img" aria-label="{title}">',
                      f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
                      f'<text x="20" y="28" font-size="15" font-weight="600" fill="{INK}">{title}</text>',
                      f'<text x="20" y="46" font-size="12" fill="{MUTED}">{sub}</text>', *body, "</svg>"]) + "\n"


def chart_bars(s: dict, order: list[str], key: str, ci: str | None, title: str, sub: str, unit: str) -> str:
    d = s["designs"]
    rows = [n for n in order if n in d]
    W, L, R, T, rh = 780, 330, 70, 62, 26
    H = T + rh * len(rows) + 20
    vmax = max(max(d[n][key], (d[n][ci][1] if ci else 0)) for n in rows) * 1.05 or 1

    def X(v):
        return L + (W - L - R) * v / vmax

    body = []
    for i, n in enumerate(rows):
        y = T + i * rh
        col = PLATFORM if n == "platform" else AS_FOUND if n == "as_found" else AI_GREEN if n == "ai_on_green" else "#A3A9A6"
        wt = ' font-weight="600"' if n == "platform" else ""
        body.append(f'<text x="{L - 10}" y="{y + 15}" font-size="12" text-anchor="end" fill="{INK}"{wt}>{d[n]["label"].split(":")[0]}</text>')
        body.append(f'<rect x="{L}" y="{y + 5}" width="{max(X(d[n][key]) - L, 1):.1f}" height="14" rx="3" fill="{col}"/>')
        if ci:
            lo, hi = d[n][ci]
            body.append(f'<line x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="{y + 12}" y2="{y + 12}" stroke="{INK}" stroke-width="1.5"/>')
        body.append(f'<text x="{max(X(d[n][key]), X(d[n][ci][1]) if ci else 0) + 8:.1f}" y="{y + 16}" font-size="11" fill="{MUTED}">'
                    f'{_n(d[n][key])} {unit}</text>')
    return _svg(W, H, title, sub, body)


def charts(s: dict, order: list[str]) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    (CHARTS / "engineer_hours.svg").write_text(chart_bars(
        s, order, "engineer_hours_per_week", None, "Engineering hours lost per week",
        "Flaky reruns, broken main, pages, reviews, false blocks and manual job fixes, same org for every design", "h"))
    (CHARTS / "pages.svg").write_text(chart_bars(
        s, order, "pages_per_week", "pages_ci", "Pages per week", "With 95% intervals over org-weeks", ""))


def _headline(s: dict, title: str) -> list[str]:
    d = s["designs"]
    cols = [n for n in ("platform", "ai_on_green", "as_found") if n in d]
    names = {"platform": "Platform", "ai_on_green": "AI changes on green CI", "as_found": "As found"}
    rows = [
        ("PR feedback, median / p90 (minutes)", lambda x: f"{_n(x['feedback_p50'])} / {_n(x['feedback_p90'])}"),
        ("Red builds from flaky tests per week", lambda x: f"{_n(x['flaky_red_per_week'])} ({_n(x['flaky_red_ci'][0])}–{_n(x['flaky_red_ci'][1])})"),
        ("Hours main is broken per week", lambda x: _n(x["main_broken_hours_per_week"])),
        ("CI runners per month", lambda x: f"€{x['runner_eur_per_month']:,.0f}"),
        ("Pages per week (95% interval)", lambda x: f"{_n(x['pages_per_week'])} ({_n(x['pages_ci'][0])}–{_n(x['pages_ci'][1])})"),
        ("... outside working hours", lambda x: _n(x["after_hours_pages_per_week"])),
        ("Page-worthy incidents paged for", lambda x: f"{x['detected_share']:.0%} of {x['page_worthy']}"),
        ("Harmful infrastructure changes applied", lambda x: f"{x['harmful_applied']} of {x['harmful']}"),
        ("Review hours per week", lambda x: _n(x["review_hours_per_week"])),
        ("Median hours from plan to apply", lambda x: _n(x["hours_to_apply_median"])),
        ("Duplicate grant records from job retries", lambda x: f"{x['duplicate_grants']:,}"),
        ("Equity jobs finished late", lambda x: f"{x['late_runs']} of {x['job_runs']:,}"),
        ("API minutes down per month in region outages", lambda x: _n(x["down_minutes_per_month"])),
        ("Standby region per month", lambda x: f"€{x['standby_eur_per_month']:,.0f}"),
        ("Engineering hours lost per week", lambda x: _n(x["engineer_hours_per_week"])),
    ]
    out = [f"| {title} | " + " | ".join(names[c] for c in cols) + " |", "|---|" + "---:|" * len(cols)]
    for lab, f in rows:
        out.append(f"| {lab} | " + " | ".join(("**" + f(d[c]) + "**") if c == "platform" else f(d[c]) for c in cols) + " |")
    w = s["world"]
    out += ["", f"{w['orgs']} simulated orgs, {w['weeks']} weeks each: {w['prs']:,} pull requests, {w['incidents']} incidents "
                f"({w['page_worthy']} page-worthy), {w['changes']:,} infrastructure changes, {w['job_runs']:,} equity job runs."]
    return out


def _designs(s: dict, order: list[str]) -> list[str]:
    d = s["designs"]
    out = ["| Design | Feedback p90 | Flaky reds / wk | Main broken h / wk | Pages / wk | Harmful applied | Duplicates | Late jobs | Eng. hours / wk |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n in order:
        if n in d:
            x = d[n]
            b = "**" if n == "platform" else ""
            out.append(f"| {b}{x['label'].split(':')[0]}{b} | {_n(x['feedback_p90'])} | {_n(x['flaky_red_per_week'])} | "
                       f"{_n(x['main_broken_hours_per_week'])} | {_n(x['pages_per_week'])} | {x['harmful_applied']} | "
                       f"{x['duplicate_grants']:,} | {x['late_runs']} | {_n(x['engineer_hours_per_week'])} |")
    return out


def readme(order: list[str], check: bool = False) -> bool:
    from epo.eval.gate import gate

    dev, ho = load("dev"), load("heldout")
    if dev is None:
        block = f"{START}\n_No results yet: run `python -m epo.eval.cli evaluate`._\n{END}"
    else:
        lines = [START, "", "### Dashboard (development orgs)", "", *_headline(dev, "Development"), "",
                 "![Engineering hours lost per week](reports/charts/engineer_hours.svg)", "",
                 "![Pages per week](reports/charts/pages.svg)", "", "### Every design on the same orgs", "", *_designs(dev, order)]
        if ho:
            fails = gate(ho)
            lines += ["", "### Held-out orgs (run once)", "", *_headline(ho, "Held-out"), "",
                      "Gate (`config/gate.yaml`) on the held-out orgs: " +
                      ("**passed**." if not fails else "**not passed**: " + "; ".join(fails) + "."),
                      "", "The record of that run: [docs/heldout.md](docs/heldout.md)."]
        lines += ["", END]
        block = "\n".join(lines)
    text = README.read_text()
    a, b = text.index(START), text.index(END) + len(END)
    new = text[:a] + block + text[b:]
    changed = new != text
    if changed and not check:
        README.write_text(new)
    return changed


def path(p: str) -> Path:
    return ROOT / p
