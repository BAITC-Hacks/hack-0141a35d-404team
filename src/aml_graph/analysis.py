from __future__ import annotations

import numpy as np
import networkx as nx
import pandas as pd


def _norm(series: pd.Series) -> pd.Series:
    values = series.astype(float).fillna(0.0)
    lo, hi = float(values.min()), float(values.max())
    return pd.Series(0.0, index=values.index) if hi <= lo else (values - lo) / (hi - lo)


def calculate_metrics(graph: nx.DiGraph, transactions: pd.DataFrame) -> pd.DataFrame:
    pagerank = nx.pagerank(graph, weight="sum_kzt") if graph.number_of_nodes() else {}
    betweenness = nx.betweenness_centrality(graph, weight=None, normalized=True)
    components = sorted(nx.weakly_connected_components(graph), key=lambda c: min(c) if c else -1)
    component_map = {node: idx + 1 for idx, comp in enumerate(components) for node in comp}
    component_size = {node: len(comp) for comp in components for node in comp}
    rows = []
    for node, attrs in graph.nodes(data=True):
        incoming = list(graph.in_edges(node, data=True)); outgoing = list(graph.out_edges(node, data=True))
        in_amount = sum(float(d["sum_kzt"]) for _, _, d in incoming); out_amount = sum(float(d["sum_kzt"]) for _, _, d in outgoing)
        pass_through = out_amount / in_amount if in_amount > 0 else 0.0
        temporal = transactions[(transactions["dst"] == node) | (transactions["src"] == node)]
        rows.append({"gid": int(node), "depth": int(attrs.get("depth", 0)), "is_seed": bool(attrs.get("is_seed", False)),
                     "in_degree": len(incoming), "out_degree": len(outgoing), "n_senders": len({u for u, _, _ in incoming}),
                     "n_receivers": len({v for _, v, _ in outgoing}), "in_amount": in_amount, "out_amount": out_amount,
                     "total_flow": in_amount + out_amount, "pass_through_ratio": pass_through,
                     "retention_ratio": max(0.0, 1.0 - pass_through), "pagerank": float(pagerank.get(node, 0.0)),
                     "betweenness": float(betweenness.get(node, 0.0)), "component_id": component_map.get(node, 0),
                     "component_size": component_size.get(node, 1), "is_depth4_boundary": int(attrs.get("depth", 0)) >= 4 and len(outgoing) == 0,
                     "n_observed_transactions": len(temporal)})
    metrics = pd.DataFrame(rows)
    for column in ["in_amount", "out_amount", "total_flow", "n_senders", "n_receivers", "pagerank", "betweenness"]:
        metrics[f"{column}_norm"] = _norm(metrics[column])
    metrics["centrality_norm"] = (metrics["pagerank_norm"] + metrics["betweenness_norm"]) / 2
    metrics["counterparty_norm"] = _norm(metrics["n_senders"] + metrics["n_receivers"])
    return metrics.reset_index(drop=True)
