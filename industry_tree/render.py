"""Render a Tree to a self-contained interactive HTML file (no external deps).

The template (`templates/tree_template.html`) embeds a dependency-free vanilla-JS
collapsible tidy-tree, so the output opens offline and satisfies a strict CSP
(e.g. published as an Artifact). Two placeholders are substituted:
  __TREE_JSON__  -> nested tree (from Tree.to_nested)
  __META_JSON__  -> {root_industry, region, generated_at, weights, n_nodes, ...}
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Tree
from .scoring import apply_scores

_TEMPLATE = Path(__file__).parent / "templates" / "tree_template.html"


def _build_body(tree: Tree, *, rescore: bool = True) -> str:
    if rescore:
        apply_scores(tree)
    nested = tree.to_nested()
    meta = {
        "root_industry": tree.root_industry,
        "region": tree.region,
        "generated_at": tree.generated_at,
        "weights": tree.weights,
        "n_nodes": len(tree.nodes),
    }
    template = _TEMPLATE.read_text()
    # json.dumps is safe inside a <script type="application/json"> block; guard </script>
    tree_json = json.dumps(nested, ensure_ascii=False).replace("</", "<\\/")
    meta_json = json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("__TREE_JSON__", tree_json).replace("__META_JSON__", meta_json)


def render_html(tree: Tree, out_path: str | Path, *, rescore: bool = True) -> Path:
    """Write a complete standalone HTML document (opens directly in a browser)."""
    body = _build_body(tree, rescore=rescore)
    title = f"{tree.root_industry} value chain — {tree.region}"
    html = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{title}</title>\n"
        "<style>html,body{margin:0;padding:0;height:100%}</style>\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path


def render_fragment(tree: Tree, out_path: str | Path, *, rescore: bool = True) -> Path:
    """Write the body fragment only (no <!doctype>/<html>/<head>/<body>).

    For hosts that supply their own page wrapper (e.g. the Artifact publisher).
    """
    body = _build_body(tree, rescore=rescore)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body)
    return out_path
