"""Two-axis screening model: Attractiveness x Actionability.

Every criterion is 1-5 (1 = clearly absent, 5 = textbook fit); 0 = unscored and
excluded from its axis so partial data still scores.

Attractiveness (market quality)
  recurring       recurring / reoccurring revenue
  fragmentation   many small owner-operated targets, no dominant consolidator
  compliance      regulatory-mandated demand (UI label: "Regulatory demand")
  scale           platform / TAM potential (can you build a EUR 50-150m platform)
  margin          margin quality & asset-lightness
  growth          structural demand tailwind (ageing, mandate expansion)
  (penalty) reimbursement_risk  1-5, 5 = high; deducts up to REIMB_MAX points

Actionability (can we win / own it)
  headroom        consolidation whitespace / how early (5 = virgin, no PE yet)
  confidence      evidence confidence (Node.confidence)
  gate: investability open -> pass; restricted -> cap; blocked -> ~0

blended = attractiveness * actionability / 100  (crowded/blocked niches sink)
quadrant: Act now / Too late / Watchlist / Pass  (+ Too small, Blocked overlays)
"""

from __future__ import annotations

from .schema import Tree, Node, ATTRACT_CRITERIA

# per-criterion weights (attractiveness + actionability share one dict)
DEFAULT_WEIGHTS = {
    "recurring": 1.0, "fragmentation": 1.0, "compliance": 1.0,
    "scale": 1.0, "margin": 1.0, "growth": 1.0,   # attractiveness
    "headroom": 1.0, "confidence": 0.5,           # actionability
}
REIMB_MAX = 20.0                 # max attractiveness points removed at reimbursement_risk=5
GATE_CAP = {"open": 100.0, "restricted": 45.0, "blocked": 8.0}
QUAD_ATTR = 55.0                 # attractiveness threshold for the 2x2
QUAD_ACT = 50.0                  # actionability threshold for the 2x2


def _axis(vals: dict[str, int], weights: dict[str, float]) -> float:
    """Weighted mean of present (>0) 1-5 values, scaled 0-100; 0 if none present."""
    present = {k: v for k, v in vals.items() if v and v > 0}
    if not present:
        return 0.0
    num = sum(v * weights.get(k, 1.0) for k, v in present.items())
    den = sum(weights.get(k, 1.0) for k in present) or 1.0
    return round((num / den - 1) / 4 * 100, 1)


def attractiveness(node: Node, weights: dict[str, float] | None = None) -> float:
    """0-100 market-quality score, net of the reimbursement-risk penalty."""
    w = weights or DEFAULT_WEIGHTS
    base = _axis({c: getattr(node.scores, c) for c in ATTRACT_CRITERIA}, w)
    if base <= 0:
        return 0.0
    r = node.scores.reimbursement_risk
    penalty = (r - 1) / 4 * REIMB_MAX if r and r > 0 else 0.0
    return round(max(0.0, base - penalty), 1)


def actionability(node: Node, weights: dict[str, float] | None = None) -> float:
    """0-100 can-we-win score: headroom (+ confidence), gated by investability.

    Returns 0 when the node has not been scored on headroom — actionability is
    undefined without it, so unscored nodes don't inflate on confidence alone.
    """
    if not node.scores.headroom:
        return 0.0
    w = weights or DEFAULT_WEIGHTS
    base = _axis({"headroom": node.scores.headroom, "confidence": node.confidence}, w)
    cap = GATE_CAP.get(node.investability or "open", 100.0)
    return round(min(base, cap), 1)


def blended(node: Node, weights: dict[str, float] | None = None) -> float:
    return round(attractiveness(node, weights) * actionability(node, weights) / 100.0, 1)


def quadrant(node: Node, weights: dict[str, float] | None = None) -> str:
    if (node.investability or "open") == "blocked":
        return "Blocked"
    if not node.scores.headroom:
        return "Unrated"                       # not assessed on the actionability axis
    if node.scores.scale and node.scores.scale <= 2:
        return "Too small"
    a = attractiveness(node, weights)
    x = actionability(node, weights)
    if a >= QUAD_ATTR and x >= QUAD_ACT:
        return "Act now"
    if a >= QUAD_ATTR and x < QUAD_ACT:
        return "Too late"
    if a < QUAD_ATTR and x >= QUAD_ACT:
        return "Watchlist"
    return "Pass"


def apply_scores(tree: Tree, weights: dict[str, float] | None = None) -> Tree:
    """Recompute attractiveness/actionability/composite in place."""
    w = weights or tree.weights or DEFAULT_WEIGHTS
    tree.weights = w
    for node in tree.nodes.values():
        node.scores.clamp()
        # `composite` stays populated (== attractiveness) for back-compat / HTML fallback
        node.composite = attractiveness(node, w)
    return tree


# retained name for the CLI / back-compat
def composite_score(node: Node, weights: dict[str, float] | None = None) -> float:
    return attractiveness(node, weights)


def ranked_leaf_rows(tree: Tree, min_level: int = 2) -> list[dict]:
    """Shortlist rows (list of dicts), sorted by blended score descending."""
    w = tree.weights or DEFAULT_WEIGHTS
    rows = []
    for n in tree.leaves():
        if n.level < min_level or attractiveness(n, w) <= 0:
            continue
        s = n.scores
        rows.append(
            {
                "path": " > ".join(n.path),
                "name": n.name,
                "attractiveness": attractiveness(n, w),
                "actionability": actionability(n, w),
                "blended": blended(n, w),
                "quadrant": quadrant(n, w),
                "investability": n.investability or "open",
                "recurring": s.recurring,
                "fragmentation": s.fragmentation,
                "regulatory_demand": s.compliance,
                "scale": s.scale,
                "margin": s.margin,
                "growth": s.growth,
                "headroom": s.headroom,
                "reimbursement_risk": s.reimbursement_risk,
                "players_dach": n.dach_signals.est_players,
                "revenue_band": n.dach_signals.revenue_band_eur,
                "pe_activity": " | ".join(n.pe_activity),
                "why_now": n.why_now,
                "confidence": n.confidence,
                "status": n.status,
                "n_sources": len(n.sources),
            }
        )
    rows.sort(key=lambda r: r["blended"], reverse=True)
    return rows


def ranked_leaves(tree: Tree, min_level: int = 2, top: int | None = None):
    """Same shortlist as a pandas DataFrame (lazy import; falls back to rows)."""
    rows = ranked_leaf_rows(tree, min_level=min_level)
    if top:
        rows = rows[:top]
    try:
        import pandas as pd
    except ModuleNotFoundError:
        return rows
    return pd.DataFrame(rows)
