"""Cross-industry portfolio: merge several scored trees into one 2x2 map.

Plots every leaf that has been scored on the actionability axis (headroom > 0)
from all supplied trees onto a single Attractiveness x Actionability chart,
coloured by industry, plus a master shortlist ranked by blended score. Uses the
default weights (the combined view is a fixed cross-sector comparison).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .schema import Tree, Node
from .scoring import attractiveness, actionability, blended, quadrant, DEFAULT_WEIGHTS

_TEMPLATE = Path(__file__).parent / "templates" / "portfolio_template.html"

# categorical, colour-blind-friendly industry palette (extend if >8 sectors)
PALETTE = ["#4c78a8", "#e4572e", "#3f9d58", "#b158d6", "#e6a817",
           "#17a2b8", "#d6336c", "#7f8c8d"]


def _point(tree: Tree, node: Node, industry: str) -> dict:
    s = node.scores
    return {
        "industry": industry,
        "name": node.name,
        "path": node.path,
        "attr": attractiveness(node),
        "act": actionability(node),
        "blended": blended(node),
        "quad": quadrant(node),
        "investability": node.investability or "open",
        "investability_note": node.investability_note,
        "stage": node.value_chain_stage,
        "description": node.description,
        "scores": {
            "recurring": s.recurring, "fragmentation": s.fragmentation,
            "compliance": s.compliance, "scale": s.scale, "margin": s.margin,
            "growth": s.growth, "headroom": s.headroom,
            "reimbursement_risk": s.reimbursement_risk,
        },
        "rationale": node.rationale,
        "dach": {
            "est_players": node.dach_signals.est_players,
            "revenue_band_eur": node.dach_signals.revenue_band_eur,
            "regulation": node.dach_signals.regulation,
            "example_companies": node.dach_signals.example_companies,
        },
        "why_now": node.why_now,
        "pe_activity": node.pe_activity,
        "actionable": node.actionable,
        "confidence": node.confidence,
        "status": node.status,
        "sources": [{"title": x.title, "url": x.url, "note": x.note} for x in node.sources],
    }


def build_points(trees: list[Tree]) -> tuple[list[dict], list[dict]]:
    """Return (points, industries) — scored leaves + the industry colour legend."""
    industries, points = [], []
    for i, tree in enumerate(trees):
        label = tree.root_industry
        industries.append({"name": label, "color": PALETTE[i % len(PALETTE)]})
        for n in tree.leaves():
            if n.scores.headroom > 0 and attractiveness(n) > 0:
                points.append(_point(tree, n, label))
    points.sort(key=lambda p: p["blended"], reverse=True)
    return points, industries


def render_portfolio(trees: list[Tree], out_path: str | Path,
                     title: str = "DACH cross-industry portfolio",
                     standalone: bool = True) -> Path:
    points, industries = build_points(trees)
    meta = {"title": title, "industries": industries, "n_points": len(points),
            "region": trees[0].region if trees else "DACH"}
    tmpl = _TEMPLATE.read_text()
    body = (tmpl.replace("__POINTS_JSON__", json.dumps(points, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__META_JSON__", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")))
    if standalone:
        body = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                f"<title>{title}</title>\n<style>html,body{{margin:0;padding:0;height:100%}}</style>\n"
                "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body)
    return out_path


def write_master_csv(trees: list[Tree], out_path: str | Path) -> Path:
    points, _ = build_points(trees)
    cols = ["industry", "name", "blended", "attr", "act", "quad", "investability",
            "recurring", "fragmentation", "compliance", "scale", "margin", "growth",
            "headroom", "reimbursement_risk", "confidence", "path"]
    out_path = Path(out_path)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for p in points:
            s = p["scores"]
            w.writerow([p["industry"], p["name"], p["blended"], p["attr"], p["act"],
                        p["quad"], p["investability"], s["recurring"], s["fragmentation"],
                        s["compliance"], s["scale"], s["margin"], s["growth"], s["headroom"],
                        s["reimbursement_risk"], p["confidence"], " > ".join(p["path"])])
    return out_path
