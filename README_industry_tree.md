# industry_tree — DACH industry value-chain screening

Build, score and visualise a **detailed value-chain tree** of an industry to find
non-obvious **buy-and-build / roll-up** targets in the DACH region (DE/AT/CH).

Every node is scored 1–5 on the Peak Two thesis criteria and grounded in real
web sources:

1. **recurring** — recurring / reoccurring revenue (subscriptions, maintenance
   contracts, statutory-funded repeat spend).
2. **fragmentation** — decentralised / low professionalism: many owner-operated
   firms at low-single-digit-million EUR revenue, no dominant consolidator.
3. **compliance** — compliance- or sovereignty-driven mandatory spend.

A weighted **composite fit score (0–100)** ranks the tree; the interactive HTML
surfaces the top roll-up candidates automatically.

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
