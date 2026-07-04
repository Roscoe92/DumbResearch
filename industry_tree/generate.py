"""Automated tree generation over a pluggable backend.

Recursively expands a root industry into a web-grounded, scored value-chain tree.
Requires a backend (default OpenAIBackend + OPENAI_API_KEY). Expansion is
breadth/depth-capped, de-duplicating against existing siblings, and resumable:
a partially-built tree can be re-run and only unexpanded nodes are expanded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .schema import Tree
from .scoring import apply_scores
from .ingest import _add_children
from .backends import LLMBackend, OpenAIBackend


def generate_tree(
    root_industry: str,
    *,
    region: str = "DACH",
    depth: int = 3,
    breadth: int = 6,
    backend: Optional[LLMBackend] = None,
    save_path: str | Path | None = None,
    on_progress=None,
) -> Tree:
    backend = backend or OpenAIBackend()
    tree = Tree(root_industry=root_industry, region=region)
    root = tree.add_node(
        f"{root_industry} value chain", None,
        value_chain_stage="root",
        description=f"Root of the {region} {root_industry.lower()} value chain.",
    )

    def expand(node_id: str, level: int) -> None:
        if level >= depth:
            return
        node = tree.nodes[node_id]
        existing = [c.name for c in tree.children(node_id)]
        if not existing:  # not yet expanded
            blob = backend.expand(
                root_industry=root_industry, region=region,
                path=node.path, existing_siblings=existing, breadth=breadth,
            )
            _add_children(tree, node_id, blob.get("children") or [])
            apply_scores(tree)
            if save_path:
                tree.save(save_path)
            if on_progress:
                on_progress(node.path, len(tree.children(node_id)))
        for child in list(tree.children(node_id)):
            expand(child.id, level + 1)

    expand(root.id, 0)
    apply_scores(tree)
    if save_path:
        tree.save(save_path)
    return tree
