"""Assemble a Tree from branch JSON blobs.

A "branch blob" is the structure the research/generation step produces:
  {"branch": str, "stage": str, "description": str, "children": [child, ...]}
where each child is:
  {"name","value_chain_stage","description","scores":{...},"rationale":{...},
   "dach_signals":{...},"confidence",int,"sources":[{...}], "children":[...]}

Both the human-research path (subagents writing branch_*.json) and the
LLM-generation path (`generate.py`) emit this shape, so one ingester serves both.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Tree, Scores, DachSignals, Source
from .scoring import apply_scores


def _add_children(tree: Tree, parent_id: str, children: list[dict]) -> None:
    for ch in children or []:
        name = (ch.get("name") or "").strip()
        if not name:
            continue
        sc = ch.get("scores") or {}
        sig = ch.get("dach_signals") or {}
        node = tree.add_node(
            name,
            parent_id,
            value_chain_stage=(ch.get("value_chain_stage") or "").strip(),
            description=(ch.get("description") or "").strip(),
            scores=Scores(
                recurring=_i(sc.get("recurring")),
                fragmentation=_i(sc.get("fragmentation")),
                compliance=_i(sc.get("compliance")),
            ).clamp(),
            rationale={k: str(v) for k, v in (ch.get("rationale") or {}).items()},
            dach_signals=DachSignals(
                est_players=str(sig.get("est_players") or ""),
                revenue_band_eur=str(sig.get("revenue_band_eur") or ""),
                example_companies=list(sig.get("example_companies") or []),
                regulation=list(sig.get("regulation") or []),
            ),
            confidence=_i(ch.get("confidence")),
            sources=[
                Source(title=str(s.get("title") or ""), url=str(s.get("url") or ""), note=str(s.get("note") or ""))
                for s in (ch.get("sources") or [])
                if s.get("url")
            ],
            status="grounded" if (ch.get("sources") or sc) else "stub",
        )
        _add_children(tree, node.id, ch.get("children") or [])


def build_tree(root_industry: str, branches: list[dict], region: str = "DACH") -> Tree:
    """Build a full Tree: a synthetic root + one node per branch + descendants."""
    tree = Tree(root_industry=root_industry, region=region)
    root = tree.add_node(
        f"{root_industry} value chain",
        None,
        value_chain_stage="root",
        description=f"Root of the {region} {root_industry.lower()} value chain.",
    )
    for b in branches:
        bname = (b.get("branch") or "").strip()
        if not bname:
            continue
        bnode = tree.add_node(
            bname,
            root.id,
            value_chain_stage=(b.get("stage") or "").strip(),
            description=(b.get("description") or "").strip(),
        )
        _add_children(tree, bnode.id, b.get("children") or [])
    apply_scores(tree)
    return tree


def load_branch_files(paths: list[str | Path]) -> list[dict]:
    out = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        try:
            out.append(json.loads(p.read_text()))
        except json.JSONDecodeError as e:
            raise ValueError(f"{p}: invalid JSON ({e})") from e
    return out


def _i(v) -> int:
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0
