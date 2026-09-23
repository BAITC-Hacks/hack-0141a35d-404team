from __future__ import annotations

import networkx as nx
import pandas as pd


def assign_clusters(graph: nx.DiGraph, scored: pd.DataFrame) -> pd.DataFrame:
    """Reproducible communities weighted only by observed transfer amounts.

    Components remain independent reachability metrics. Isolates are retained;
    no target group count or target size is imposed on the input data.
    """
    undirected = nx.Graph()
    undirected.add_nodes_from(sorted(graph))
    for u, v, attrs in sorted(graph.edges(data=True)):
        amount = float(attrs['sum_kzt'])
        if undirected.has_edge(u, v):
            undirected[u][v]['sum_kzt'] += amount
        else:
            undirected.add_edge(u, v, sum_kzt=amount)
    groups = []
    for members in sorted(nx.connected_components(undirected), key=min):
        subgraph = undirected.subgraph(sorted(members)).copy()
        if len(members) == 1 or subgraph.size(weight='sum_kzt') <= 0:
            groups.append(members)
        else:
            communities = nx.community.louvain_communities(
                subgraph, weight='sum_kzt', resolution=1, seed=42)
            for community in communities:
                groups.extend(nx.connected_components(subgraph.subgraph(community)))
    groups.sort(key=lambda members: (-len(members), min(members)))
    mapping = {gid: cid for cid, members in enumerate(groups, 1) for gid in members}
    result = scored.copy()
    result['cluster_id'] = result['gid'].map(mapping)
    if result['cluster_id'].isna().any():
        raise ValueError('Cluster assignment must cover every account')
    return result


def summarize_clusters(graph: nx.DiGraph, scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cluster_id, group in scored.groupby("cluster_id", sort=True):
        members = set(group["gid"])
        internal = sum(float(d["sum_kzt"]) for u, v, d in graph.edges(data=True) if u in members and v in members)
        top = group.sort_values(["priority_score", "gid"], ascending=[False, True]).head(5)["gid"].tolist()
        dominant = group["role"].value_counts().index[0]
        hypothesis = {"consolidator": "Potential collection/consolidation structure", "distributor": "Potential outward distribution structure", "transit": "Potential pass-through routing structure", "coordinator": "Central seed-connected coordination candidate", "terminal": "Downstream receiving structure"}.get(dominant, "Mixed or peripheral activity; requires review")
        rows.append({"cluster_id": int(cluster_id), "n_nodes": len(group), "n_seed": int(group["is_seed"].sum()), "sum_kzt_internal": round(internal, 2), "top_gids": ",".join(map(str, top)), "hypothesis": hypothesis})
    isolated = {int(row.cluster_id) for row in scored.itertuples() if graph.degree(row.gid) == 0}
    for row in rows:
        if row['cluster_id'] in isolated:
            row['hypothesis'] = 'Isolated account; no observed connections to support a group hypothesis'
    return pd.DataFrame(rows)
