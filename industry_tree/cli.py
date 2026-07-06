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
    tree = Tree.load(tree_path := args.tree)
    apply_scores(tree)
    rows = ranked_leaf_rows(tree, min_level=args.min_level)[: args.top]
    for i, r in enumerate(rows, 1):
        gate = "" if r["investability"] == "open" else f" [{r['investability']}]"
        print(f"{i:2d}. blend {r['blended']:5.1f}  (A {r['attractiveness']:.0f} / X {r['actionability']:.0f})"
              f"  {r['quadrant']:9s}{gate}  {r['name']}")
        print(f"       {' > '.join(r['path'].split(' > ')[1:3])}"
              f"  | {r['players_dach']} | {r['revenue_band']}")
        if r["pe_activity"]:
            print(f"       PE: {r['pe_activity'][:110]}")
    return 0


def cmd_coverage(args) -> int:
    from .qc import source_coverage
    tree = Tree.load(args.tree)
    rep = source_coverage(tree, scored_only=not args.all)
    print(f"source coverage ({rep['scope']}): {rep['with_sources']}/{rep['total']} = {rep['coverage_pct']}%")
    for m in rep["missing"][:40]:
        print(f"  missing sources: {m}")
    if len(rep["missing"]) > 40:
        print(f"  … and {len(rep['missing']) - 40} more")
    return 0


def cmd_linkcheck(args) -> int:
    from .qc import check_links
    tree = Tree.load(args.tree)
    rep = check_links(tree)
    print(f"links: {rep['ok']}/{rep['total_urls']} OK · {len(rep['dead'])} dead · {len(rep['blocked'])} unreachable")
    for u in rep["dead"]:
        print(f"  DEAD {rep['results'][u]}  {u}")
    if rep["blocked"]:
        print(f"  ({len(rep['blocked'])} URLs unreachable from here — likely a sandboxed egress proxy; re-run outside it)")
    return 0


def cmd_portfolio(args) -> int:
    from .portfolio import render_portfolio, write_master_csv
    trees = [Tree.load(p) for p in args.trees]
    for t in trees:
        apply_scores(t)
    render_portfolio(trees, args.out, title=args.title, standalone=not args.fragment)
    write_master_csv(trees, args.csv)
    n = sum(1 for t in trees for leaf in t.leaves() if leaf.scores.headroom > 0)
    print(f"portfolio: {len(trees)} industries, {n} scored niches -> {args.out} + {args.csv}")
    return 0


def cmd_origination(args) -> int:
    from .origination import load_book, render_target_universe, write_longlist_csv
    targets, niches = load_book(args.book)
    live = [t for t in targets if t.status != "dropped"]
    render_target_universe(targets, niches, args.out, title=args.title, standalone=not args.fragment)
    write_longlist_csv(live, args.csv)
    n_niches = len({" > ".join(t.niche_path) for t in live})
    print(f"target universe: {len(live)} companies across {n_niches} niches -> {args.out} + {args.csv}")
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

    cov = sub.add_parser("coverage", help="report source coverage of a tree (offline)")
    cov.add_argument("tree")
    cov.add_argument("--all", action="store_true", help="all nodes, not just scored leaves")
    cov.set_defaults(func=cmd_coverage)

    lc = sub.add_parser("linkcheck", help="HTTP-validate every source URL in a tree")
    lc.add_argument("tree")
    lc.set_defaults(func=cmd_linkcheck)

    pf = sub.add_parser("portfolio", help="combine several trees into a cross-industry 2x2 map")
    pf.add_argument("trees", nargs="+", help="tree.json paths (one per industry)")
    pf.add_argument("--out", default="data/dach_portfolio.html")
    pf.add_argument("--csv", default="data/dach_master_shortlist.csv")
    pf.add_argument("--title", default="DACH cross-industry portfolio")
    pf.add_argument("--fragment", action="store_true", help="emit body fragment only (for hosted embeds)")
    pf.set_defaults(func=cmd_portfolio)

    og = sub.add_parser("origination", help="TargetBook -> filterable company long-list HTML + CSV")
    og.add_argument("book", help="dach_targets.json TargetBook")
    og.add_argument("--out", default="data/dach_target_universe.html")
    og.add_argument("--csv", default="data/dach_target_longlist.csv")
    og.add_argument("--title", default="DACH target universe — Peak Two")
    og.add_argument("--fragment", action="store_true", help="emit body fragment only (for hosted embeds)")
    og.set_defaults(func=cmd_origination)

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
