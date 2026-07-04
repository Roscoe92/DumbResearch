"""Scoring rubric and composite fit score for screening nodes.

Rubric anchors (1-5) — keep prompt and human interpretation aligned:

recurring (recurring / reoccurring revenue)
  1  one-off transactional; no repeat relationship
  3  repeat project work or replacement cycles, but re-won each time
  5  contractual subscription / mandatory maintenance / statutory-funded recurring

fragmentation (decentralized, low professionalism)
  1  concentrated; a few large professional players dominate
  3  moderately fragmented; regional mid-caps plus a long tail
  5  hundreds of owner-operated firms, EUR 1-5m revenue, no dominant consolidator

compliance (compliance- / sovereignty-driven)
  1  discretionary spend; little regulation
  3  regulated but not the core purchase driver
  5  mandatory spend driven by law/norm/certification or data/operational sovereignty
"""

from __future__ import annotations

from .schema import Tree, Node, CRITERIA

DEFAULT_WEIGHTS = {"recurring": 1.0, "fragmentation": 1.0, "compliance": 1.0}


def composite_score(node: Node, weights: dict[str, float] | None = None) -> float:
    """Weighted mean of the three 1-5 criteria, scaled to 0-100.

    Returns 0.0 if the node is unscored (any criterion still 0).
    """
    w = weights or DEFAULT_WEIGHTS
    vals = {c: getattr(node.scores, c) for c in CRITERIA}
    if any(v <= 0 for v in vals.values()):
        return 0.0
    num = sum(vals[c] * w.get(c, 1.0) for c in CRITERIA)
    den = sum(w.get(c, 1.0) for c in CRITERIA) or 1.0
    mean_1_5 = num / den
    return round((mean_1_5 - 1) / 4 * 100, 1)   # 1->0, 5->100


def apply_scores(tree: Tree, weights: dict[str, float] | None = None) -> Tree:
    """Recompute every node's composite in place using the tree weights."""
    w = weights or tree.weights or DEFAULT_WEIGHTS
    tree.weights = w
    for node in tree.nodes.values():
        node.scores.clamp()
        node.composite = composite_score(node, w)
    return tree


def ranked_leaf_rows(tree: Tree, min_level: int = 2) -> list[dict]:
    """Shortlist rows (list of dicts) — no pandas dependency."""
    rows = []
    for n in tree.leaves():
        if n.level < min_level or n.composite <= 0:
            continue
        rows.append(
            {
                "path": " > ".join(n.path),
                "name": n.name,
                "composite": n.composite,
                "recurring": n.scores.recurring,
                "fragmentation": n.scores.fragmentation,
                "compliance": n.scores.compliance,
                "players_dach": n.dach_signals.est_players,
                "revenue_band": n.dach_signals.revenue_band_eur,
                "confidence": n.confidence,
                "n_sources": len(n.sources),
            }
        )
    rows.sort(key=lambda r: r["composite"], reverse=True)
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
