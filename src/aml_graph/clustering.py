from __future__ import annotations

import networkx as nx
import pandas as pd


def assign_clusters(graph: nx.DiGraph, scored: pd.DataFrame) -> pd.DataFrame:
    """Amount-weighted Louvain communities within each real connected component.

    Use only observed amounts, with default modularity resolution (1). Sorted
    insertion and a fixed RNG seed make results independent of input row order.
    Components describe reachability; communities describe dense flow groups.
    """
    undirected = nx.Graph()
    undirected.add_nodes_from(sorted(graph))
    for u, v, data in sorted(graph.edges(data=True)):
        amount = float(data['sum_kzt'])
        if undirected.has_edge(u, v):
            undirected[u][v]['sum_kzt'] += amount
        else:
            undirected.add_edge(u, v, sum_kzt=amount)
    communities = []
    components = sorted(nx.connected_components(undirected), key=min)
    for members in components:
        subgraph = undirected.subgraph(sorted(members)).copy()
        if len(members) == 1 or subgraph.size(weight='sum_kzt') <= 0:
            communities.append(members)
        else:
            communities.extend(nx.community.louvain_communities(
                subgraph, weight='sum_kzt', resolution=1, seed=42))
    communities.sort(key=lambda members: (-len(members), min(members)))
    mapping = {gid: cid for cid, members in enumerate(communities, start=1) for gid in members}
    result = scored.copy()
    result['cluster_id'] = result['gid'].map(mapping)
    return result


def summarize_clusters(graph: nx.DiGraph, scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cluster_id, group in scored.groupby("cluster_id", sort=True):
        members = set(group["gid"])
        internal = sum(float(d["sum_kzt"]) for u, v, d in graph.edges(data=True) if u in members and v in members)
        top = group.sort_values(["priority_score", "gid"], ascending=[False, True]).head(5)["gid"].tolist()
        dominant = group["role"].value_counts().index[0]
        hypothesis = {"consolidator": "Potential collection/consolidation structure", "distributor": "Potential outward distribution structure", "transit": "Potential pass-through routing structure", "coordinator": "Central seed-connected coordination candidate", "terminal": "Downstream receiving structure"}.get(dominant, "Mixed or peripheral activity; requires review")
        if len(members) == 1 and graph.degree(next(iter(members))) == 0:
            hypothesis = "Isolated account; no observed connections to support a group hypothesis"
        rows.append({"cluster_id": int(cluster_id), "n_nodes": len(group), "n_seed": int(group["is_seed"].sum()), "sum_kzt_internal": round(internal, 2), "top_gids": ",".join(map(str, top)), "hypothesis": hypothesis})
    return pd.DataFrame(rows)
