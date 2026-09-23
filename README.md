# AML Graph Analysis

Local, explainable analysis of a directed transaction graph starting from known seed accounts. It produces the required CSV exports and a searchable Streamlit visualization.

## Run

```powershell
python -m pip install -r requirements.txt
python run_pipeline.py --input entryset --output outputset
streamlit run app.py
```

The pipeline reads `nodes.parquet`, `edges.parquet`, and `transactions.parquet`, preserving isolated nodes and validating required columns.

## Role rules

Roles are deterministic structural hypotheses with precedence: coordinator, consolidator, distributor, transit, terminal, peripheral. Coordinators combine high centrality or seed status with broad connectivity. Consolidators have at least two senders and materially more incoming than outgoing flow. Distributors have at least three receivers and substantial outgoing flow. Transit nodes have incoming and outgoing flow with a pass-through ratio between 0.70 and 1.30. Terminals have no outgoing edge unless they are depth-4 boundary nodes. Boundary leaves are kept conservative because the graph is truncated at depth four.

Scores combine centrality, flow, counterparties, role strength, and incoming volume. Evidence is generated for every node and capped at 200 characters. Priority scores are review signals, not assertions of wrongdoing.

## Outputs

- `nodes_roles.csv`: one row per input node with role, scores, cluster, and evidence.
- `clusters.csv`: weakly connected component summaries and behavioral hypotheses.
- `top_nodes.csv`: ranked review candidates, with at least 20 rows when the input has at least 20 nodes.

## Limitations and scaling

The graph only contains observed in-bank transfers above the supplied threshold and four hops from seeds. Seed incoming flow is incomplete, and depth-4 leaves may be truncated rather than true terminals. No external identity or customer attributes are inferred.

For approximately one million nodes, replace the NetworkX in-memory graph with columnar/streaming graph representation, compute aggregates with pandas/Polars or SQL, use sparse centrality/community algorithms, and render only filtered neighborhoods.

## Work Pipeline

Development follows planning and design, isolated-branch development, testing and review, integration into `main`, and deployment. Feature branches should be submitted for review before integration.
