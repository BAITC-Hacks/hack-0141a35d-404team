from __future__ import annotations

from pathlib import Path
from .analysis import calculate_metrics
from .clustering import assign_clusters, summarize_clusters
from .exports import export_outputs
from .graph import build_graph
from .io import load_data, validation_report
from .roles import assign_roles
from .patterns import analyze_patterns


def run_pipeline(input_dir: str | Path = "entryset", output_dir: str | Path = "outputset") -> dict:
    data = load_data(input_dir); graph = build_graph(data["nodes"], data["edges"])
    scored = assign_roles(calculate_metrics(graph, data["transactions"]))
    scored = assign_clusters(graph, scored)
    clusters = summarize_clusters(graph, scored); paths = export_outputs(scored, clusters, output_dir)
    report = validation_report(data)
    seeds = scored[scored["is_seed"]]
    report.update(n_isolated_seed=int((seeds["counterparty_count"] == 0).sum()),
                  n_seed_without_outgoing=int((seeds["out_degree"] == 0).sum()),
                  n_boundary=int(scored["is_depth4_boundary"].sum()),
                  n_components=int(scored['component_id'].nunique()),
                  n_connected_components=int(scored.loc[scored['component_size'] > 1, 'component_id'].nunique()),
                  n_clusters=len(clusters), clustering_method='amount-weighted Louvain (seed=42, resolution=1)')
    return {"report": report, "graph": graph, "metrics": scored, "clusters": clusters, "paths": paths,
            "insights": analyze_patterns(graph, data["transactions"], scored)}

