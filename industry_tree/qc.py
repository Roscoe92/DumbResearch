"""Quality-control utilities: source coverage + link liveness.

`source_coverage` runs anywhere (offline) and reports which scored leaves lack a
source. `check_links` performs real HTTP validation of every source URL — it
works in an unrestricted environment; inside a sandboxed egress proxy that
blocks outbound fetches it will report those URLs as 'unreachable (blocked)'
rather than a true 404, so treat a fully-blocked run as "not validated here".
"""

from __future__ import annotations

import concurrent.futures
import ssl
import urllib.request
from pathlib import Path

from .schema import Tree


def source_coverage(tree: Tree, scored_only: bool = True) -> dict:
    """Report source coverage. Returns counts + the list of nodes missing sources."""
    missing = []
    total = 0
    for n in tree.nodes.values():
        if n.level == 0:
            continue
        if scored_only and not n.scores.headroom:
            continue
        total += 1
        if not n.sources:
            missing.append(" > ".join(n.path))
    return {
        "scope": "scored leaves" if scored_only else "all nodes",
        "total": total,
        "with_sources": total - len(missing),
        "missing": missing,
        "coverage_pct": round((total - len(missing)) / total * 100, 1) if total else 0.0,
    }


def all_urls(tree: Tree) -> list[tuple[str, str]]:
    """Return (url, node_path) for every source url in the tree (deduped by url)."""
    seen, out = set(), []
    for n in tree.nodes.values():
        for s in n.sources:
            if s.url and s.url not in seen:
                seen.add(s.url)
                out.append((s.url, " > ".join(n.path)))
    return out


def _probe(url: str, timeout: int = 15, ca_bundle: str | None = "/root/.ccr/ca-bundle.crt") -> tuple[str, int | str]:
    ctx = ssl.create_default_context(cafile=ca_bundle) if ca_bundle and Path(ca_bundle).exists() \
        else ssl.create_default_context()
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 (linkcheck)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return url, r.status
    except urllib.error.HTTPError as e:
        return url, e.code
    except Exception as e:  # noqa: BLE001 — report any failure verbatim
        msg = str(e)
        if "403 Forbidden" in msg and "Tunnel" in msg:
            return url, "unreachable (blocked)"
        return url, f"error: {type(e).__name__}"


def check_links(tree: Tree, workers: int = 8) -> dict:
    """HTTP-validate every source URL. Returns per-url status + a summary."""
    urls = all_urls(tree)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for url, status in ex.map(lambda u: _probe(u[0]), urls):
            results[url] = status
    ok = sum(1 for s in results.values() if isinstance(s, int) and 200 <= s < 400)
    dead = [u for u, s in results.items() if isinstance(s, int) and s >= 400]
    blocked = [u for u, s in results.items() if s == "unreachable (blocked)"]
    return {
        "total_urls": len(urls),
        "ok": ok,
        "dead": dead,
        "blocked": blocked,
        "results": results,
    }
