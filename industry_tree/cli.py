"""Command-line entry point for industry_tree.

    # render an existing tree.json to interactive HTML (no API key needed)
    python -m industry_tree render data/medical_dach.json

    # assemble a tree from branch_*.json research blobs
    python -m industry_tree assemble --root "Medical" --out data/medical_dach.json branch_*.json

    # print the ranked roll-up shortlist of a tree
    python -m industry_tree shortlist data/medical_dach.json

    # auto-generate a fresh tree with your own OpenAI key (web-grounded)
    OPENAI_API_KEY=... python -m industry_tree generate --root "Medical" --depth 3 --breadth 6
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from .schema import Tree, validate
from .scoring import apply_scores, ranked_leaf_rows
from .render import render_html
from .ingest import build_tree, load_branch_files


def _default_html(json_path: Path) -> Path:
    return json_path.with_suffix(".html")


def cmd_render(args) -> int:
    from .render import render_fragment
    tree = Tree.load(args.tree)
    out = Path(args.out) if args.out else _default_html(Path(args.tree))
    (render_fragment if args.fragment else render_html)(tree, out)
    kind = "fragment" if args.fragment else "standalone HTML"
    print(f"rendered {len(tree.nodes)} nodes ({kind}) -> {out}")
    return 0


def cmd_assemble(args) -> int:
    files: list[str] = []
    for pat in args.branches:
        files.extend(sorted(glob.glob(pat)) or [pat])
    branches = load_branch_files(files)
    if not branches:
        print("no branch files found", file=sys.stderr)
        return 2
    tree = build_tree(args.root, branches, region=args.region)
    problems = validate(tree)
    if problems:
        print("VALIDATION WARNINGS:", *problems, sep="\n  ", file=sys.stderr)
    out = Path(args.out)
    tree.save(out, snapshot=True)
    print(f"assembled {len(branches)} branches, {len(tree.nodes)} nodes -> {out}")
    if args.html:
        html = render_html(tree, _default_html(out))
        print(f"rendered -> {html}")
    return 0


def cmd_shortlist(args) -> int:
    tree = Tree.load(args.tree)
    apply_scores(tree)
    rows = ranked_leaf_rows(tree, min_level=args.min_level)[: args.top]
    for i, r in enumerate(rows, 1):
        print(f"{i:2d}. {r['composite']:5.1f}  {r['path']}")
        print(f"       rec {r['recurring']} · frag {r['fragmentation']} · comp {r['compliance']}"
              f"  | {r['players_dach']} | {r['revenue_band']}")
    return 0


def cmd_generate(args) -> int:
    from .generate import generate_tree
    out = Path(args.out) if args.out else Path(f"data/{args.root.lower().replace(' ', '_')}_{args.region.lower()}.json")
    tree = generate_tree(
        args.root, region=args.region, depth=args.depth, breadth=args.breadth,
        save_path=out, on_progress=lambda path, n: print(f"  expanded {' > '.join(path)} -> {n} children"),
    )
    print(f"generated {len(tree.nodes)} nodes -> {out}")
    render_html(tree, _default_html(out))
    print(f"rendered -> {_default_html(out)}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="industry_tree", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="tree.json -> interactive HTML")
    r.add_argument("tree")
    r.add_argument("--out")
    r.add_argument("--fragment", action="store_true", help="emit body fragment only (for hosted embeds)")
    r.set_defaults(func=cmd_render)

    a = sub.add_parser("assemble", help="branch_*.json -> tree.json")
    a.add_argument("branches", nargs="+")
    a.add_argument("--root", required=True)
    a.add_argument("--region", default="DACH")
    a.add_argument("--out", required=True)
    a.add_argument("--html", action="store_true")
    a.set_defaults(func=cmd_assemble)

    s = sub.add_parser("shortlist", help="print ranked roll-up leaves")
    s.add_argument("tree")
    s.add_argument("--top", type=int, default=20)
    s.add_argument("--min-level", type=int, default=2)
    s.set_defaults(func=cmd_shortlist)

    g = sub.add_parser("generate", help="auto-generate a tree via an LLM backend (needs API key)")
    g.add_argument("--root", required=True)
    g.add_argument("--region", default="DACH")
    g.add_argument("--depth", type=int, default=3)
    g.add_argument("--breadth", type=int, default=6)
    g.add_argument("--out")
    g.set_defaults(func=cmd_generate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
