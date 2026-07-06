"""Deal-origination layer: turn scored niches into a per-company target long-list.

A *TargetBook* is a flat list of `schema.Target` companies (each keyed to a leaf
niche by `niche_path`) plus per-niche metadata carried over from the screen
(sector, blended score, market size, buy-and-build angle). This module ingests
the research blobs, computes a transparent 0-100 `fit_score` per company, and
renders both a filterable interactive company database (HTML) and a per-company
CSV built for CRM/register import.

Reuses the screen's colour palette and the template-injection render pattern from
`portfolio.py`.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .schema import Target, Source
from .portfolio import PALETTE

_TEMPLATE = Path(__file__).parent / "templates" / "target_universe_template.html"


# ---- fit scoring ----------------------------------------------------------
# Transparent 0-100 composite; components are stored on Target.fit so the score
# is fully explainable in the UI. PE/listed/strategic-owned firms are dropped
# upstream (status="dropped"), not scored.
FIT_WEIGHTS = {"size": 25, "independence": 25, "succession": 25, "platform": 15, "geography": 10}


def _revenue_mid_eur_m(band: str) -> float | None:
    """Parse a revenue band like 'EUR 2-5m' / '10 Mio' / '~3m' -> midpoint in EUR m."""
    if not band:
        return None
    s = band.lower().replace(",", ".")
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums:
        return None
    vals = [float(n) for n in nums]
    # if it looks like it's expressed in thousands/euros without 'm', keep as-is only for m/mio
    mid = sum(vals[:2]) / len(vals[:2])
    return mid


def _size_score(band: str) -> int:
    mid = _revenue_mid_eur_m(band)
    if mid is None:
        return 14  # unknown -> neutral-ish
    # sweet spot EUR 2-20m; taper below/above
    if 2 <= mid <= 20:
        return 25
    if 1 <= mid < 2:
        return 18
    if 20 < mid <= 30:
        return 18
    if 0.5 <= mid < 1:
        return 10
    if 30 < mid <= 60:
        return 10
    return 5


def _succession_score(sig: str) -> int:
    if not sig:
        return 6  # unknown
    s = sig.lower()
    strong = any(k in s for k in ("no successor", "keine nachfolge", "60+", "65", "retire",
                                  "ruhestand", "nachfolge gesucht", "nachfolge offen", "70",
                                  "generationswechsel", "altersbedingt"))
    some = any(k in s for k in ("founder", "gründer", "inhaber", "anniversary", "jubiläum",
                                "family", "familie", "50", "55", "second generation", "2. generation"))
    if strong:
        return 25
    if some:
        return 15
    return 10


def _geo_score(hq: str) -> int:
    h = (hq or "").lower()
    if not h:
        return 6
    if any(k in h for k in ("schweiz", "switzerland", " ch", "zürich", "zurich", "basel", "bern", "genf", "geneva")):
        return 8
    if any(k in h for k in ("österreich", "austria", " at", "wien", "vienna", "graz", "linz", "salzburg", "innsbruck")):
        return 8
    return 10  # Germany / DACH core


def fit_score(t: Target) -> Target:
    """Compute component scores + composite; mark PE/listed/strategic as dropped."""
    if not t.independent:
        t.status = "dropped"
        t.fit = {"independence": 0}
        t.fit_score = 0.0
        return t
    comp = {
        "size": _size_score(t.est_revenue_band),
        "independence": 25,
        "succession": _succession_score(t.succession_signal),
        "platform": 15 if (t.role or "").lower() == "platform" else 10,
        "geography": _geo_score(t.hq_region),
    }
    t.fit = comp
    t.fit_score = float(sum(comp.values()))
    if t.status not in ("verified", "dropped"):
        t.status = "candidate"
    return t


# ---- TargetBook I/O -------------------------------------------------------
def save_book(targets: list[Target], niches: list[dict], out_path: str | Path,
              generated_at: str = "") -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": generated_at,
        "niches": niches,
        "targets": [t.to_dict() for t in targets],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return out_path


def load_book(path: str | Path) -> tuple[list[Target], list[dict]]:
    d = json.loads(Path(path).read_text())
    targets = [Target.from_dict(x) for x in d.get("targets", [])]
    return targets, d.get("niches", [])


# ---- ingest research blobs ------------------------------------------------
def _norm_name(s: str) -> str:
    s = (s or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "", s)


def ingest_longlists(blobs: list[dict], niche_meta: dict[str, dict]) -> list[Target]:
    """Turn research blobs {niche_path, companies[]} into scored Targets.

    `niche_meta` maps a niche key (" > ".join(path)) -> {sector, niche, blended, ...}.
    De-duplicates companies within a niche by normalized name.
    """
    out: list[Target] = []
    for blob in blobs:
        path = blob.get("niche_path") or []
        key = " > ".join(path)
        meta = niche_meta.get(key, {})
        seen = set()
        for c in blob.get("companies") or []:
            name = (c.get("name") or "").strip()
            if not name:
                continue
            nk = _norm_name(name)
            if nk in seen:
                continue
            seen.add(nk)
            srcs = [Source(title=str(s.get("title") or ""), url=str(s.get("url") or ""),
                           note=str(s.get("note") or ""))
                    for s in (c.get("sources") or []) if isinstance(s, dict) and s.get("url")]
            t = Target(
                name=name,
                legal_name=str(c.get("legal_name") or ""),
                website=str(c.get("website") or ""),
                sector=meta.get("sector", ""),
                niche=meta.get("niche", path[-1] if path else ""),
                niche_path=path,
                hq_region=str(c.get("hq_region") or ""),
                founded=str(c.get("founded") or ""),
                est_revenue_band=str(c.get("est_revenue_band") or ""),
                est_employees=str(c.get("est_employees") or ""),
                ownership=str(c.get("ownership") or ""),
                independent=bool(c.get("independent", True)),
                succession_signal=str(c.get("succession_signal") or ""),
                role=str(c.get("role") or "bolt-on"),
                approach_note=str(c.get("approach_note") or ""),
                confidence=_int(c.get("confidence")),
                sources=srcs,
            )
            fit_score(t)
            out.append(t)
    return out


# ---- review / verify verdicts ---------------------------------------------
_ADJUSTABLE = ("legal_name", "hq_region", "founded", "est_revenue_band",
               "est_employees", "ownership", "website", "role", "succession_signal")


def apply_verdicts(targets: list[Target], verdicts: list[dict]) -> dict:
    """Apply a review/adjust/verify pass under the DROP-UNLESS-VERIFIED policy.

    Each verdict: {name, niche?, verdict: verified|flag|drop, reason?, fields?{...}}.
    Matched by normalized name (disambiguated by niche when supplied). verified/flag
    keep the company (merge non-empty `fields`, re-run fit_score); flag appends the
    reason to approach_note. drop -> status="dropped". Any target NOT covered by a
    verdict is ALSO dropped (default-drop when unconfirmed). Returns counts.
    """
    by_key: dict[tuple, list[Target]] = {}
    for t in targets:
        by_key.setdefault((_norm_name(t.name), " > ".join(t.niche_path)), []).append(t)
    by_name: dict[str, list[Target]] = {}
    for t in targets:
        by_name.setdefault(_norm_name(t.name), []).append(t)

    seen: set[int] = set()
    counts = {"verified": 0, "flag": 0, "drop": 0, "unmatched": 0}
    for v in verdicts:
        nm = _norm_name(v.get("name") or "")
        if not nm:
            continue
        niche = " > ".join(v.get("niche_path") or []) if v.get("niche_path") else None
        cands = by_key.get((nm, niche)) if niche else None
        if not cands:
            cands = by_name.get(nm)
        if not cands:
            counts["unmatched"] += 1
            continue
        t = cands[0]
        verdict = (v.get("verdict") or "drop").lower()
        fields = v.get("fields") or {}
        if verdict in ("verified", "flag", "ok", "keep"):
            for k in _ADJUSTABLE:
                if fields.get(k):
                    setattr(t, k, fields[k])
            if "independent" in fields:
                t.independent = bool(fields["independent"])
            if verdict in ("flag",) and v.get("reason"):
                t.approach_note = (t.approach_note + f"  [Verify: {v['reason']}]").strip()
            fit_score(t)  # re-score after field changes
            t.status = "flagged" if verdict == "flag" else "verified"
            counts["flag" if verdict == "flag" else "verified"] += 1
        else:  # drop / anything else
            t.status = "dropped"
            if v.get("reason"):
                t.approach_note = (t.approach_note + f"  [Dropped: {v['reason']}]").strip()
            counts["drop"] += 1
        seen.add(id(t))
    # default-drop: any target not addressed by a verdict
    for t in targets:
        if id(t) not in seen and t.status != "dropped":
            t.status = "dropped"
            counts["drop"] += 1
    return counts


# ---- CSV ------------------------------------------------------------------
def write_longlist_csv(targets: list[Target], out_path: str | Path) -> Path:
    cols = ["sector", "niche", "company", "legal_name", "website", "hq_region", "founded",
            "est_revenue_band", "est_employees", "ownership", "independent",
            "succession_signal", "role", "fit_score", "status", "confidence",
            "approach_note", "source_url"]
    out_path = Path(out_path)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for t in sorted(targets, key=lambda x: (-x.fit_score, x.sector)):
            w.writerow([t.sector, t.niche, t.name, t.legal_name, t.website, t.hq_region,
                        t.founded, t.est_revenue_band, t.est_employees, t.ownership,
                        "yes" if t.independent else "no", t.succession_signal, t.role,
                        round(t.fit_score), t.status, t.confidence, t.approach_note,
                        t.sources[0].url if t.sources else ""])
    return out_path


# ---- HTML -----------------------------------------------------------------
def _company_row(t: Target, color: str) -> dict:
    return {
        "name": t.name, "legal_name": t.legal_name, "website": t.website,
        "sector": t.sector, "niche": t.niche, "color": color,
        "hq": t.hq_region, "founded": t.founded, "revenue": t.est_revenue_band,
        "employees": t.est_employees, "ownership": t.ownership,
        "succession": t.succession_signal, "role": t.role,
        "approach": t.approach_note, "fit": round(t.fit_score),
        "fitc": t.fit, "conf": t.confidence, "status": t.status,
        "sources": [{"title": s.title, "url": s.url, "note": s.note} for s in t.sources],
    }


def render_target_universe(targets: list[Target], niches: list[dict], out_path: str | Path,
                           title: str = "DACH target universe — Peak Two",
                           standalone: bool = True) -> Path:
    # colour per sector, ordered as niches list (which follows sector order)
    sectors, colmap = [], {}
    for m in niches:
        s = m.get("sector", "")
        if s and s not in colmap:
            colmap[s] = PALETTE[len(colmap) % len(PALETTE)]
            sectors.append({"name": s, "color": colmap[s]})
    rows = [_company_row(t, colmap.get(t.sector, "#888"))
            for t in targets if t.status != "dropped"]
    rows.sort(key=lambda r: -r["fit"])
    meta = {"title": title, "sectors": sectors, "n_companies": len(rows),
            "n_niches": len({r["niche"] for r in rows}),
            "n_succession": sum(1 for r in rows if r["succession"]),
            "niches": niches}
    tmpl = _TEMPLATE.read_text()
    body = (tmpl.replace("__DATA_JSON__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__META_JSON__", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")))
    if standalone:
        body = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                f"<title>{title}</title>\n<style>html,body{{margin:0;padding:0;height:100%}}</style>\n"
                "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body)
    return out_path


def _int(v) -> int:
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0
