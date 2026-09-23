from __future__ import annotations

import networkx as nx
import pandas as pd


def calculate_metrics(graph: nx.DiGraph, transactions: pd.DataFrame) -> pd.DataFrame:
    components = sorted(nx.weakly_connected_components(graph), key=lambda c: min(c) if c else -1)
    component_map = {node: idx + 1 for idx, comp in enumerate(components) for node in comp}
    component_size = {node: len(comp) for comp in components for node in comp}
    rows = []
    for node, attrs in graph.nodes(data=True):
        incoming = list(graph.in_edges(node, data=True)); outgoing = list(graph.out_edges(node, data=True))
        in_amount = sum(float(d["sum_kzt"]) for _, _, d in incoming); out_amount = sum(float(d["sum_kzt"]) for _, _, d in outgoing)
        # Seeds have systematically incomplete incoming observations.
        pass_through = out_amount / in_amount if in_amount > 0 and not attrs.get("is_seed", False) else None
        temporal = transactions[(transactions["dst"] == node) | (transactions["src"] == node)]
        rows.append({"gid": int(node), "depth": int(attrs.get("depth", 0)), "is_seed": bool(attrs.get("is_seed", False)),
                     "in_degree": len(incoming), "out_degree": len(outgoing), "n_senders": len({u for u, _, _ in incoming}),
                     "n_receivers": len({v for _, v, _ in outgoing}), "in_amount": in_amount, "out_amount": out_amount,
                     "total_flow": in_amount + out_amount, "pass_through_ratio": pass_through,
                     "retention_ratio": max(0.0, 1.0 - pass_through) if pass_through is not None else None, "component_id": component_map.get(node, 0),
                     "component_size": component_size.get(node, 1), "is_depth4_boundary": int(attrs.get("depth", 0)) >= 4 and len(outgoing) == 0,
                     "n_observed_transactions": len(temporal)})
    metrics = pd.DataFrame(rows)
    metrics["counterparty_count"] = [len(set(graph.predecessors(gid)) | set(graph.successors(gid))) for gid in metrics["gid"]]
    return metrics.reset_index(drop=True)
