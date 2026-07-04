# industry_tree — DACH industry value-chain screening

Build, score and visualise a **detailed value-chain tree** of an industry to find
non-obvious **buy-and-build / roll-up** targets in the DACH region (DE/AT/CH).

Every node is scored 1–5 on the Peak Two thesis criteria and grounded in real
web sources, on **two axes**:

**Attractiveness** (is this a good market?)
1. **recurring** — recurring / reoccurring revenue.
2. **fragmentation** — many owner-operated firms, no dominant consolidator.
3. **regulatory demand** — regulation-mandated spend (the `compliance` field).
4. **scale** — platform / TAM potential (can you build a €50–150m platform?).
5. **margin** — margin quality & asset-lightness.
6. **growth** — structural demand tailwind (ageing, mandate expansion).
   *minus* a **reimbursement-risk** penalty (statutory funding ≠ pure upside).

**Actionability** (can we still win / own it?)
7. **headroom** — consolidation whitespace / how early (5 = virgin, no PE yet).
8. **confidence** — evidence confidence.
   *gated by* **investability** ∈ {open, restricted, **blocked**} — a hard flag
   for structurally un-ownable niches (e.g. pharmacy Fremdbesitzverbot,
   person-bound Kassensitz, member-owned cooperatives).

The two axes drive a **2×2 portfolio map** — *Act now · Too late · Watchlist ·
Pass* (plus *Too small* and *Blocked*) — and a **blended score**
(attractiveness × actionability) that ranks the shortlist so crowded and
un-ownable niches sink. The interactive HTML has a **Tree** view and a **◱ Map**
view, a **⚙ Weights** popover to retune every criterion live, and an auto-ranked
top-candidate list. The top candidates are additionally **verified** (✓): a
"why now" catalyst, known PE consolidators, and confirmed player/revenue figures.

## The interactive tree

`data/medical_dach.html` is a **self-contained** interactive file (no external
dependencies — opens offline, works in any browser):

- collapsible tidy-tree of the value chain, **nodes coloured by fit score**;
- click a node → detail panel with the three score bars + rationale, DACH signals
  (player counts, revenue band, example companies, regulation) and **source links**;
- search box, expand/collapse, and an auto-ranked **"Top roll-up candidates"** list.

Just open the `.html` file in a browser.

## Regenerate / extend a tree (needs your own API key)

The renderer needs no key. Auto-**generating** a fresh, web-grounded tree uses a
pluggable LLM backend — the default is OpenAI's Responses API with the built-in
`web_search` tool, so every node is web-validated:

```bash
pip install openai                       # backend dependency
export OPENAI_API_KEY=sk-...
python -m industry_tree generate --root "Medical" --region DACH --depth 3 --breadth 6
# -> writes data/medical_dach.json + data/medical_dach.html
```

Swap in another provider by implementing `backends.LLMBackend.expand(...)` and
passing it to `generate.generate_tree(..., backend=YourBackend())`.

## Other commands

```bash
# render an existing tree to HTML (no key)
python -m industry_tree render data/medical_dach.json

# assemble a tree from research blobs (branch_*.json in the shared schema)
python -m industry_tree assemble --root "Medical" --out data/medical_dach.json --html branch_*.json

# print the ranked roll-up shortlist
python -m industry_tree shortlist data/medical_dach.json --top 20
```

## How the current Medical tree was built

This container had no LLM/search API key, so the first `data/medical_dach.json`
was researched directly (parallel web-research agents, one per value-chain
branch) and assembled with `industry_tree assemble`. The schema, scoring and
rendering are identical to what `generate` produces, so you can extend it later
with your own key. Sources on each node are real URLs consulted during research;
treat scores as evidence-based hypotheses to validate in diligence.

## Layout

```
industry_tree/
  schema.py     # Node/Tree dataclasses, JSON persistence, validation
  scoring.py    # 1-5 rubric + weighted composite + leaf ranking
  ingest.py     # assemble a Tree from branch JSON blobs
  render.py     # Tree -> self-contained interactive HTML
  backends.py   # LLMBackend interface + OpenAIBackend (web_search) + EchoBackend
  generate.py   # recursive expand+score pipeline over a backend
  cli.py        # render | assemble | shortlist | generate
  templates/tree_template.html   # dependency-free D3-free JS tree
data/
  medical_dach.json / .html      # the DACH medical value-chain tree
```
