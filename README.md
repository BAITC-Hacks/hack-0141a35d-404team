# AML Graph Analysis

Local, explainable analysis of a directed transaction graph starting from known seed accounts. It produces the required CSV exports and a searchable Streamlit visualization.

## Run

```powershell
python -m pip install -r requirements.txt
python run_pipeline.py --input entryset --output outputset
streamlit run app.py
```

The pipeline reads `nodes.parquet`, `edges.parquet`, and `transactions.parquet`, preserving isolated nodes and validating required columns.

The UI uses a lightweight inline SVG renderer rather than Plotly. Select English or Russian in the sidebar, focus a `gid`, and hover a node in the single network view. The bottom-right card shows its role, priority, and concise evidence. Streamlit's visible branding is hidden by the local page stylesheet.

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
