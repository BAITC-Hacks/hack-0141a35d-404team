# AML Graph Analysis

Local analysis of a directed transaction graph with a React frontend and a Python FastAPI backend. The original analytical modules and CSV schemas are unchanged by the frontend migration.

## Run

```powershell
python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
python app.py
```

The pipeline reads `nodes.parquet`, `edges.parquet`, and `transactions.parquet`, preserving isolated nodes and validating required columns.

Open http://127.0.0.1:8000 and click **Run analysis**. After the initial frontend build, `python app.py` serves both the API and React app. Requires Python 3.11+ and Node.js 22+. All runtime assets are local; no CDN, Streamlit, Plotly, or external service is used.

The custom canvas renderer fills the graph workspace. Scroll to zoom, drag to pan, or use Fit view. Search the exact gid or select a priority row to show a neighborhood. Click nodes to select them and hover for concise bottom-right evidence. Filter clusters and switch role/cluster colors. English/Russian text and role descriptions come from a local dictionary; the language choice persists in the browser. Layout coordinates are display-only and never enter analytical calculations.

The folder field accepts a folder on the Python server containing all three parquet files, defaulting to `entryset/`. A web run generates its exports in a temporary folder and keeps the download bytes in local server memory until the next successful run or restart. Existing CLI outputs are not overwritten. This is a local, single-analyst application bound to loopback, without authentication or multi-user run isolation.

The original batch command still writes all three outputs:

```powershell
python run_pipeline.py --input entryset --output outputset
```

For frontend development, run `python app.py` in one terminal and `npm run dev` from `frontend/` in another. Vite proxies `/api` to port 8000.

## API and verification

- `POST /api/analyze` with `{"input_dir":"entryset"}` runs the unchanged pipeline and returns report, nodes, edges, clusters, and execution time. IDs are strings in JSON to preserve int64 precision in JavaScript; CSV IDs remain unchanged.
- `GET /api/exports/{name}` downloads one of the three fixed CSV filenames from the latest successful web run.
- `GET /api/health` checks the backend; interactive API docs are at `/api/docs`.

```powershell
python -m unittest discover -s tests -v
cd frontend
npm test
npm run build
# With python app.py running; browser test uses installed Microsoft Edge:
node tests/browser.mjs
```

The API regression test compares all three CSV downloads byte-for-byte with the direct pipeline and checks exact IDs, invalid inputs, and concurrent-run rejection. The browser test exercises analysis, search, zoom, translation, export, and mobile viewport rendering.

## Task document and preserved baseline

The task document defines required deliverables, role meanings, explainability, and data limitations; it does not prescribe exact scoring formulas. The rules below are the existing implementation's choices, preserved for this migration. Binary rule-match scores are not calibrated probabilities. In particular, the existing coordinator rule selects only maximally connected seeds, terminal rules may classify isolated nodes as terminals, and flow-ratio rules still operate on incomplete observations. This migration does not correct those analytical limitations or claim exact compliance with a document-defined formula.

## Role rules

Roles are deterministic structural hypotheses with precedence: coordinator, consolidator, distributor, transit, terminal, peripheral. The implementation uses only direct facts in the supplied graph: seed status, depth, incoming/outgoing edge counts, unique counterparties, and observed sums. A coordinator is the seed account with the highest observed connectivity. A consolidator has at least two senders and more observed incoming than outgoing flow. A distributor has at least three receivers and more observed outgoing than incoming flow. A transit node has incoming and outgoing flow with a pass-through ratio from 0.80 to 1.20. A terminal has no outgoing edge unless it is at the depth-4 boundary. Remaining nodes are peripheral. These rules use no learned values or weighted composite metrics.

`role_score` is 1 when a required structural rule matches and 0 for peripheral nodes. `priority_score` is the percentile rank of observed total flow, with no invented weights. Evidence is generated for every node and capped at 200 characters. All outputs are review hypotheses, not assertions of wrongdoing.

## Outputs

- `nodes_roles.csv`: one row per input node with role, scores, cluster, and evidence.
- `clusters.csv`: weakly connected component summaries and behavioral hypotheses.
- `top_nodes.csv`: ranked review candidates, with at least 20 rows when the input has at least 20 nodes.

## Limitations and scaling

The graph only contains observed in-bank transfers above the supplied threshold and four hops from seeds. Seed incoming flow is incomplete, and depth-4 leaves may be truncated rather than true terminals. No external identity or customer attributes are inferred.

For approximately one million nodes, replace the NetworkX in-memory graph with columnar/streaming graph representation, compute aggregates with pandas/Polars or SQL, use sparse centrality/community algorithms, and render only filtered neighborhoods.

## Work Pipeline

Development follows planning and design, isolated-branch development, testing and review, integration into `main`, and deployment. Feature branches should be submitted for review before integration.
