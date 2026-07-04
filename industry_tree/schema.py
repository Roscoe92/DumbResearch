"""Data model for a DACH industry value-chain screening tree.

A tree is a flat map of nodes keyed by a stable slug id. Each node carries a
value-chain definition plus a three-criteria roll-up score grounded in real web
sources. The flat map makes single-node insert/update O(1) (expansion is
incremental); the nested view is assembled on demand for rendering.

The three screening criteria (Peak Two thesis):
  1. recurring    - recurring / reoccurring revenue
  2. fragmentation- decentralized, low professionalism, many sub-scale players
  3. compliance   - compliance- / sovereignty-driven mandatory spend
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 1
CRITERIA = ("recurring", "fragmentation", "compliance")


def slugify(text: str) -> str:
    """Lowercase ascii slug, safe as an id fragment and filename."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "node"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Scores:
    """1-5 per criterion (1 = clearly absent, 5 = textbook fit)."""

    recurring: int = 0
    fragmentation: int = 0
    compliance: int = 0

    def clamp(self) -> "Scores":
        self.recurring = _clamp15(self.recurring)
        self.fragmentation = _clamp15(self.fragmentation)
        self.compliance = _clamp15(self.compliance)
        return self


@dataclass
class Source:
    title: str = ""
    url: str = ""
    note: str = ""


@dataclass
class DachSignals:
    est_players: str = ""          # e.g. "300-600 firms"
    revenue_band_eur: str = ""     # e.g. "EUR 1-5m typical company revenue"
    example_companies: list[str] = field(default_factory=list)
    regulation: list[str] = field(default_factory=list)


@dataclass
class Node:
    id: str
    name: str
    parent_id: Optional[str] = None
    level: int = 0
    path: list[str] = field(default_factory=list)      # ancestor names incl. self
    value_chain_stage: str = ""                         # upstream/manufacturing/...
    description: str = ""
    scores: Scores = field(default_factory=Scores)
    rationale: dict[str, str] = field(default_factory=dict)   # per-criterion one-liner
    composite: float = 0.0                              # 0-100, set by scoring.py
    dach_signals: DachSignals = field(default_factory=DachSignals)
    sources: list[Source] = field(default_factory=list)
    confidence: int = 0                                 # 1-5 evidence confidence
    status: str = "stub"                                # "stub" | "grounded"
    child_ids: list[str] = field(default_factory=list)

    # ---- serialization ----------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        d = dict(d)
        d["scores"] = Scores(**(d.get("scores") or {}))
        d["dach_signals"] = DachSignals(**(d.get("dach_signals") or {}))
        d["sources"] = [Source(**s) for s in (d.get("sources") or [])]
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Tree:
    root_industry: str
    region: str = "DACH"
    version: int = SCHEMA_VERSION
    generated_at: str = field(default_factory=_now)
    weights: dict[str, float] = field(
        default_factory=lambda: {"recurring": 1.0, "fragmentation": 1.0, "compliance": 1.0}
    )
    root_id: str = ""
    nodes: dict[str, Node] = field(default_factory=dict)

    # ---- construction helpers --------------------------------------------
    def make_id(self, name: str, parent_id: Optional[str]) -> str:
        base = slugify(name) if parent_id is None else f"{parent_id}/{slugify(name)}"
        cid, n = base, 2
        while cid in self.nodes:
            cid = f"{base}-{n}"
            n += 1
        return cid

    def add_node(self, name: str, parent_id: Optional[str], **kw) -> Node:
        nid = self.make_id(name, parent_id)
        parent = self.nodes.get(parent_id) if parent_id else None
        level = 0 if parent is None else parent.level + 1
        path = ([] if parent is None else list(parent.path)) + [name]
        node = Node(id=nid, name=name, parent_id=parent_id, level=level, path=path, **kw)
        self.nodes[nid] = node
        if parent is not None and nid not in parent.child_ids:
            parent.child_ids.append(nid)
        if parent is None and not self.root_id:
            self.root_id = nid
        return node

    def children(self, node_id: str) -> list[Node]:
        return [self.nodes[c] for c in self.nodes[node_id].child_ids if c in self.nodes]

    def leaves(self) -> list[Node]:
        return [n for n in self.nodes.values() if not n.child_ids]

    def sibling_names(self, parent_id: Optional[str]) -> list[str]:
        if parent_id is None:
            return [n.name for n in self.nodes.values() if n.parent_id is None]
        return [c.name for c in self.children(parent_id)]

    # ---- nested view for rendering ---------------------------------------
    def to_nested(self, node_id: Optional[str] = None) -> dict:
        nid = node_id or self.root_id
        node = self.nodes[nid]
        d = node.to_dict()
        d["children"] = [self.to_nested(c) for c in node.child_ids if c in self.nodes]
        d.pop("child_ids", None)
        return d

    # ---- serialization ----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "root_industry": self.root_industry,
            "region": self.region,
            "version": self.version,
            "generated_at": self.generated_at,
            "weights": self.weights,
            "root_id": self.root_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Tree":
        tree = cls(
            root_industry=d["root_industry"],
            region=d.get("region", "DACH"),
            version=d.get("version", SCHEMA_VERSION),
            generated_at=d.get("generated_at", _now()),
            weights=d.get("weights", {"recurring": 1.0, "fragmentation": 1.0, "compliance": 1.0}),
            root_id=d.get("root_id", ""),
        )
        tree.nodes = {k: Node.from_dict(v) for k, v in d.get("nodes", {}).items()}
        if not tree.root_id:
            for n in tree.nodes.values():
                if n.parent_id is None:
                    tree.root_id = n.id
                    break
        return tree

    def save(self, path: str | Path, snapshot: bool = False) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        if snapshot:
            snap = path.with_suffix(f".v{int(datetime.now(timezone.utc).timestamp())}.json")
            snap.write_text(path.read_text())
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Tree":
        return cls.from_dict(json.loads(Path(path).read_text()))


def _clamp15(v) -> int:
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        return 0
    return max(1, min(5, v)) if v else 0


def validate(tree: Tree) -> list[str]:
    """Return a list of human-readable problems (empty = valid)."""
    problems: list[str] = []
    if not tree.root_id or tree.root_id not in tree.nodes:
        problems.append("missing or dangling root_id")
    for nid, node in tree.nodes.items():
        if node.id != nid:
            problems.append(f"{nid}: id mismatch ({node.id})")
        if node.parent_id and node.parent_id not in tree.nodes:
            problems.append(f"{nid}: dangling parent_id {node.parent_id}")
        for c in node.child_ids:
            if c not in tree.nodes:
                problems.append(f"{nid}: dangling child {c}")
            elif tree.nodes[c].parent_id != nid:
                problems.append(f"{nid}: child {c} disagrees on parent")
    return problems
