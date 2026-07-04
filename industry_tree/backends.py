"""Pluggable LLM+web-search backends for automated tree generation.

A backend takes a node context and returns a `{"children": [...]}` blob in the
same shape `ingest.py` consumes. The default OpenAIBackend uses the Responses
API with the built-in `web_search` tool so every expansion is web-grounded and
returns real source URLs — satisfying the "web-search-validate every node"
requirement when the user runs it with their own OPENAI_API_KEY.

This module is import-safe without the `openai` package installed; the import
happens lazily inside OpenAIBackend so the render/ingest path needs no key.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol

PE_SYSTEM = (
    "You are a senior private-equity analyst at a DACH (Germany/Austria/Switzerland) "
    "buy-and-build fund. You map industries into MECE value-chain sub-sectors and assess "
    "roll-up attractiveness on three criteria: recurring revenue, fragmentation / low "
    "professionalism, and compliance/sovereignty-driven demand. You ground every claim in "
    "web evidence and return STRICT JSON only."
)

SCORING_ANCHORS = (
    "Scoring anchors (1-5): "
    "recurring 1=one-off, 3=repeat/replacement re-won each time, 5=contractual/subscription/"
    "statutory-funded recurring. "
    "fragmentation 1=concentrated few large players, 3=regional mid-caps + long tail, "
    "5=hundreds of owner-operated firms EUR 1-5m revenue no consolidator. "
    "compliance 1=discretionary, 3=regulated but not the buying driver, 5=mandatory spend by "
    "law/norm/certification or data/operational sovereignty."
)

CHILD_SCHEMA = (
    '{"children":[{"name","value_chain_stage","description",'
    '"scores":{"recurring":int,"fragmentation":int,"compliance":int},'
    '"rationale":{"recurring","fragmentation","compliance"},'
    '"dach_signals":{"est_players","revenue_band_eur","example_companies":[],"regulation":[]},'
    '"confidence":int,"sources":[{"title","url","note"}]}]}'
)


class LLMBackend(Protocol):
    def expand(self, *, root_industry: str, region: str, path: list[str],
               existing_siblings: list[str], breadth: int) -> dict:
        ...


def build_prompt(root_industry, region, path, existing_siblings, breadth) -> str:
    where = " > ".join(path)
    sib = ", ".join(existing_siblings) if existing_siblings else "(none yet)"
    return (
        f"Root industry: {root_industry} ({region}).\n"
        f"Expand this node into its next-level sub-sectors: {where}.\n"
        f"Return exactly {breadth} MECE children (mutually exclusive, collectively exhaustive; "
        f"no overlaps). Do NOT repeat any of these existing siblings: {sib}.\n"
        f"Favour granular, NON-OBVIOUS, fragmented niches over household-name categories. "
        f"Everything must be specific to {region} (firm counts, revenue bands, regulation).\n"
        f"Use web_search to verify player counts, revenue bands and regulatory drivers; put the "
        f"real URLs you consulted in each node's sources.\n"
        f"{SCORING_ANCHORS}\n"
        f"Respond with STRICT JSON only, shape: {CHILD_SCHEMA}"
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))


class OpenAIBackend:
    """OpenAI Responses API backend with the built-in web_search tool."""

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

    def expand(self, *, root_industry, region, path, existing_siblings, breadth) -> dict:
        from openai import OpenAI  # lazy import

        client = OpenAI(api_key=self.api_key)
        prompt = build_prompt(root_industry, region, path, existing_siblings, breadth)
        resp = client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            input=[
                {"role": "system", "content": PE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        text = getattr(resp, "output_text", None) or str(resp)
        return _extract_json(text)


class EchoBackend:
    """Test backend: returns deterministic stub children (no network, no key)."""

    def expand(self, *, root_industry, region, path, existing_siblings, breadth) -> dict:
        base = path[-1]
        return {
            "children": [
                {
                    "name": f"{base} sub-sector {i+1}",
                    "value_chain_stage": "services",
                    "description": f"Stub child {i+1} of {base}.",
                    "scores": {"recurring": 3, "fragmentation": 3, "compliance": 3},
                    "rationale": {"recurring": "stub", "fragmentation": "stub", "compliance": "stub"},
                    "dach_signals": {"est_players": "n/a", "revenue_band_eur": "n/a",
                                     "example_companies": [], "regulation": []},
                    "confidence": 1,
                    "sources": [],
                }
                for i in range(breadth)
                if f"{base} sub-sector {i+1}" not in existing_siblings
            ]
        }
