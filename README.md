# AML Graph Analysis

Local analysis of a directed transaction graph with a React frontend and a Python FastAPI backend. The CSV schemas remain fixed; the coverage audit adds conservative handling of seed inflows, isolates, and truncated boundary nodes.

## Run

```powershell
python -m pip install -r requirements.txt
# First setup only: copy the blank template, then put your key in .env.
if (!(Test-Path .env)) { Copy-Item .env.example .env }
cd frontend
npm ci
npm run build
cd ..
python app.py
```

The pipeline reads `nodes.parquet`, `edges.parquet`, and `transactions.parquet`, preserving isolated nodes and validating required columns.

Open http://127.0.0.1:8000 and click **Run analysis**. After the initial frontend build, `python app.py` serves both the API and React app. Requires Python 3.12+ (tested on 3.13; NetworkX excludes 3.14.1) and Node.js 22+. All graph assets and analytics are local; no CDN, Streamlit or Plotly is used. Only explicitly submitted AI chat questions use an external service (OpenAI). Skip the copy command if `.env` already exists.

The custom canvas renderer fills the graph workspace. Scroll to zoom, drag to pan, or use Fit view. Search the exact gid or select a priority row to show a neighborhood. The seed selector includes every seed, even isolated accounts, and shows incoming/outgoing edge counts. Select 1–4 hops and incoming/outgoing/both tracing. Click nodes to follow connections: the previous node stays visible with a clickable back-arrow badge, and the starting seed remains available as a shortcut. Blue arrows enter the selected account; peach arrows leave it; other edges are muted. Curved links separate reciprocal and collinear routes. Camera and node positions animate, respecting reduced-motion preferences. Filter clusters and switch role/cluster colors. English/Russian text and role descriptions come from a local dictionary. Layout and animation values never enter analytical calculations.

The folder field accepts a folder on the Python server containing all three parquet files, defaulting to `entryset/`. A web run generates its exports in a temporary folder and keeps the download bytes in local server memory until the next successful run or restart. Existing CLI outputs are not overwritten. This is a local, single-analyst application bound to loopback, without authentication or multi-user run isolation.

The original batch command still writes all three outputs:

```powershell
python run_pipeline.py --input entryset --output outputset
```

For frontend development, run `python app.py` in one terminal and `npm run dev` from `frontend/` in another. Vite proxies `/api` to port 8000.

## API and verification

- `POST /api/analyze` with `{"input_dir":"entryset"}` runs the pipeline and returns report, nodes, edges, clusters, and execution time. Coverage counts include isolated seeds, seeds without outgoing edges, boundary leaves, and component counts. IDs are strings in JSON to preserve int64 precision in JavaScript; CSV IDs remain unchanged.
- `GET /api/exports/{name}` downloads one of the three fixed CSV filenames from the latest successful web run.
- `GET /api/health` checks the backend; interactive API docs are at `/api/docs`.

```powershell
python -m unittest discover -s tests -v
cd frontend
npm test
npm run build
# With python app.py running; browser test uses installed Microsoft Edge:
node tests/browser.mjs
node tests/seeds.mjs
node tests/features.mjs
```

The API regression test compares all three CSV downloads byte-for-byte with the direct pipeline and checks exact IDs, invalid inputs, and concurrent-run rejection. The browser test exercises analysis, search, zoom, translation, export, and mobile viewport rendering.

## Task document and verification

The task document defines deliverables, role meanings, explainability, and data limitations; it does not prescribe exact scoring formulas. Rules below are documented implementation choices, not formulas supplied by the document. Binary rule-match scores are not calibrated probabilities. No labelled ground truth exists, so tests establish reproducibility and rule correctness, not predictive accuracy.

Checks on the supplied dataset: 2,248 accounts, 81 seeds, 19 isolated seeds, 31 seeds without outgoing transfers, and 444 depth-4 leaves. There are 16 non-singleton weakly connected components plus 19 isolated accounts: 35 components, not 35 behavioural communities. Community detection yields 105 clusters, with at most 272 accounts in the largest, on this dataset and the tested NetworkX version. Counts are computed, never hardcoded. No full balances, below-5,000-KZT activity, external flows, or customer attributes are inferred. Tests verify all-node roles, score bounds, evidence length, cluster coverage, at least 20 ranked nodes, explanatory ranking text, and the five-minute limit. Real browser tests cover search, isolated seed viewing, navigation history, direction colors, translations, and rendering.

## Role rules

Rules run in this order:

1. Depth-4-or-deeper leaves and isolated accounts are peripheral with explicit evidence of missing visibility.
2. Coordinator: a connected seed with the maximum number of distinct counterparties among seeds (all ties qualify). This remains a limited coordination hypothesis, not an organizer detector.
3. Consolidator: non-seed with at least two senders and more observed incoming than outgoing flow.
4. Distributor: at least three receivers; seeds use only this structural condition, while non-seeds additionally require observed outgoing greater than incoming.
5. Transit: non-seed with positive incoming/outgoing and pass-through ratio 0.80–1.20.
6. Terminal: non-seed with positive observed incoming and no outgoing edge, after boundary exclusion. This is only an observed terminal hypothesis, not evidence of retained funds.
7. All remaining nodes are peripheral. Seed pass-through/retention ratios are undefined and are never used for roles. External inflows remain unobserved for other nodes too.

`role_score` is 1 when a named structural rule matches and 0 for peripheral nodes; it is a rule indicator, not measured confidence. Evidence is populated for every node and capped at 200 characters.

`priority_score = rank_min(in_amount + out_amount, ascending=True) / number_of_accounts`, rounded to six decimals. Equal volumes share the minimum rank in the tie group. Example: observed flows [0, 10, 10, 40] produce [0.25, 0.50, 0.50, 1.00]. The score orders review by observed volume; it is not a wrongdoing probability, centrality, or balance. It gives even zero-flow nodes a small nonzero rank and can double-count the same funds as they pass through accounts. Priority weights are not added. The top CSV explains both observed volume and role. UI help is available in English and Russian.

## Outputs

- `nodes_roles.csv`: one row per input node with role, scores, cluster, and evidence.
- `clusters.csv`: amount-weighted Louvain community summaries and behavioral hypotheses.
- `top_nodes.csv`: ranked review candidates, with at least 20 rows when the input has at least 20 nodes.

## Limitations and scaling

The graph only contains observed in-bank transfers above the supplied threshold and four hops from seeds. Seed incoming flow is incomplete, and depth-4 leaves may be truncated rather than true terminals. No external identity or customer attributes are inferred.

For approximately one million nodes, replace the NetworkX in-memory graph with columnar/streaming graph representation, compute aggregates with pandas/Polars or SQL, use sparse centrality/community algorithms, and render only filtered neighborhoods.

## Clustering

The old baseline grouped weakly connected components, so a single bridging transfer could put thousands of accounts into one cluster. Inspection of the older processing code confirmed a rollback would retain that behaviour. We keep `component_id` and `component_size` for real connectivity, and separately derive `cluster_id` using NetworkX Louvain within each weak component. The undirected projection sums observed KZT amounts in both directions; sorted input insertion, seed 42 and the standard resolution 1 make repeated runs reproducible. These are algorithm settings, not additional risk-score weights. NetworkX is pinned to the tested version 3.7 for replay. Community membership can change when the input changes; a cluster ID is not a permanent identity.

IDs are ordered by descending group size then smallest gid. Disconnected accounts remain singleton groups: merging them would invent relationships. Cluster volume counts only edges with both endpoints inside that community; cross-community edges remain visible in the graph but are not counted as internal. The filter, colours, node card, assistant and exports all use the same `cluster_id`. The compact overview arranges communities separately; its spacing has no effect on analysis.

## Node patterns and AI assistant

The redundant **Investigation** panel has been removed. Click an account: its bottom-corner card automatically shows role, flow, connections and signal badges. Expand **Patterns and evidence** for 48-hour transit, bursts, synchronous inflows, repeated routes, cycles and amount/depth anomalies. **Suggested data requests** explains coverage gaps; **Download node card** saves the brief. Hovering still shows a compact preview without issuing a new request on every mouse move. **Network resilience** in the sidebar simulates removal of the top N accounts and compares connectivity before/after without changing the source graph. The original CSV schemas and role/priority formulas are retained. See [pattern rules](docs/pattern-rules.md) for thresholds, truncation limits and interpretation.

The expandable **Analyst assistant** sits above the map controls. Copy `.env.example` to `.env` once and set `OPENAI_API_KEY` in `.env` (never commit the real key). `OPENAI_MODEL` defaults to `gpt-5.4-nano`. Configuration is reread on each chat request: after editing the key, close and reopen chat; no Python restart is needed. Environment variables override `.env`, which overrides `.env.example`; an explicitly empty environment key disables AI. The example file also works as a fallback for local trials, but keep real credentials in ignored `.env` before sharing or committing. Start `python app.py`, run analysis, then ask “Explain this account”, “Who receives money from these five gids?”, or “Why is this cluster important?”. Click cited gids to navigate the graph.

Questions send bounded excerpts to OpenAI. The API key stays on the server. Chat history stays in local SQLite and is scoped by dataset, with a Clear memory action. The app works without the key; only AI chat is unavailable. See the [local memory design](docs/assistant-memory.md) for context budgets, retrieval, retention, model documentation and failure handling.

Additional endpoints: `GET /api/nodes/{gid}/card?dataset_id=...`, `POST /api/resilience`, `GET /api/chat/status`, `POST /api/chat`, and `GET/DELETE /api/chat/history/{session_id}`. Node-card, resilience and chat requests reject stale dataset IDs.

`python -m unittest discover -s tests -v` covers deterministic signals, window boundaries, resilience immutability, bounded retrieval, local memory and mocked tool calls. Live OpenAI access is not exercised by the automated suite.

## Work Pipeline

Development follows planning and design, isolated-branch development, testing and review, integration into `main`, and deployment. Feature branches should be submitted for review before integration.
