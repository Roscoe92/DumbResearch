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
import re
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


def _norm(s: str) -> str:
    """Normalize for tolerant matching: expand umlauts then keep alnum only.

    Makes 'häusliche', 'haeusliche' and 'hausliche' all compare equal, so a
    graft/enrich target still resolves despite German transliteration variance.
    """
    s = (s or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    import unicodedata as _u
    s = _u.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s)


def find_by_path(tree: Tree, names: list[str]) -> str | None:
    """Return the node id whose path (ancestor names incl. self) equals `names`."""
    if not names:
        return None
    for nid, node in tree.nodes.items():
        if node.path == names:
            return nid
    # fall back: exact match on the last name if unique
    matches = [nid for nid, n in tree.nodes.items() if n.name == names[-1]]
    if len(matches) == 1:
        return matches[0]
    # tolerant fallback: umlaut/transliteration-insensitive full-path match
    target = [_norm(x) for x in names]
    for nid, n in tree.nodes.items():
        if [_norm(x) for x in n.path] == target:
            return nid
    return None


def graft(tree: Tree, target_names: list[str], children: list[dict]) -> int:
    """Attach `children` under the node identified by `target_names` (its path).

    De-duplicates against existing children (casefold name match). Returns the
    number of nodes added. Raises if the target is not found.
    """
    tid = find_by_path(tree, target_names)
    if not tid:
        raise ValueError(f"graft target not found: {' > '.join(target_names)}")
    existing = {c.name.casefold() for c in tree.children(tid)}
    fresh = [c for c in (children or []) if (c.get("name") or "").strip().casefold() not in existing]
    before = len(tree.nodes)
    _add_children(tree, tid, fresh)
    return len(tree.nodes) - before


def apply_deepen_files(tree: Tree, paths: list[str | Path]) -> int:
    """Apply deepen blobs {"target_path":[...], "children":[...]} to a tree."""
    total = 0
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        blob = json.loads(p.read_text())
        blobs = blob if isinstance(blob, list) else [blob]
        for b in blobs:
            tp = b.get("target_path") or []
            if tp:
                total += graft(tree, tp, b.get("children") or [])
    apply_scores(tree)
    return total


def apply_enrich_files(tree: Tree, paths: list[str | Path]) -> int:
    """Merge verification/enrichment blobs into existing nodes (no new children).

    Blob shape: {"target_path":[...], "why_now":str, "pe_activity":[str],
                 "est_players":str?, "revenue_band_eur":str?, "confidence":int?,
                 "sources":[{title,url,note}]?}
    Updates in place, appends new sources (dedup by url), marks status="verified".
    Returns the number of nodes enriched.
    """
    n = 0
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        blob = json.loads(p.read_text())
        for b in (blob if isinstance(blob, list) else [blob]):
            tid = find_by_path(tree, b.get("target_path") or [])
            if not tid:
                continue
            node = tree.nodes[tid]
            if b.get("why_now"):
                node.why_now = str(b["why_now"])
            if b.get("pe_activity"):
                node.pe_activity = list(b["pe_activity"])
            if b.get("est_players"):
                node.dach_signals.est_players = str(b["est_players"])
            if b.get("revenue_band_eur"):
                node.dach_signals.revenue_band_eur = str(b["revenue_band_eur"])
            if b.get("confidence"):
                node.confidence = _i(b["confidence"])
            # new two-axis criteria (set on node.scores when present)
            for fld in ("scale", "margin", "growth", "headroom", "reimbursement_risk"):
                if b.get(fld) is not None:
                    setattr(node.scores, fld, _i(b[fld]))
            if b.get("investability") in ("open", "restricted", "blocked"):
                node.investability = b["investability"]
            if b.get("investability_note"):
                node.investability_note = str(b["investability_note"])
            have = {s.url for s in node.sources}
            for s in (b.get("sources") or []):
                if s.get("url") and s["url"] not in have:
                    node.sources.append(Source(title=str(s.get("title") or ""),
                                               url=str(s["url"]), note=str(s.get("note") or "")))
                    have.add(s["url"])
            node.status = "verified"
            n += 1
    return n


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
