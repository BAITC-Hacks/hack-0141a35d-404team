from __future__ import annotations

import networkx as nx
import pandas as pd


def summarize_clusters(graph: nx.DiGraph, scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cluster_id, group in scored.groupby("component_id", sort=True):
        members = set(group["gid"])
        internal = sum(float(d["sum_kzt"]) for u, v, d in graph.edges(data=True) if u in members and v in members)
        top = group.sort_values("priority_score", ascending=False).head(5)["gid"].tolist()
        dominant = group["role"].value_counts().index[0]
        hypothesis = {"consolidator": "Potential collection/consolidation structure", "distributor": "Potential outward distribution structure", "transit": "Potential pass-through routing structure", "coordinator": "Central seed-connected coordination candidate", "terminal": "Downstream receiving structure"}.get(dominant, "Mixed or peripheral activity; requires review")
        rows.append({"cluster_id": int(cluster_id), "n_nodes": len(group), "n_seed": int(group["is_seed"].sum()), "sum_kzt_internal": round(internal, 2), "top_gids": ",".join(map(str, top)), "hypothesis": hypothesis})
    return pd.DataFrame(rows)
