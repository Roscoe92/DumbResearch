"""industry_tree: build, score and visualize DACH industry value-chain trees.

Screening thesis (Peak Two): find non-obvious buy-and-build / roll-up targets
that are (1) recurring-revenue, (2) fragmented / low-professionalism, and
(3) compliance- or sovereignty-driven.

Runnable with no API key:  rendering a tree.json to interactive HTML.
Requires a key (OpenAI by default): auto-generating a new tree via `generate`.
"""

from .schema import Tree, Node, Scores, Source, DachSignals, slugify, validate
from .scoring import (
    composite_score, apply_scores, ranked_leaves, ranked_leaf_rows,
    attractiveness, actionability, blended, quadrant, DEFAULT_WEIGHTS,
)

__all__ = [
    "Tree",
    "Node",
    "Scores",
    "Source",
    "DachSignals",
    "slugify",
    "validate",
    "composite_score",
    "apply_scores",
    "ranked_leaves",
    "ranked_leaf_rows",
    "attractiveness",
    "actionability",
    "blended",
    "quadrant",
    "DEFAULT_WEIGHTS",
]
