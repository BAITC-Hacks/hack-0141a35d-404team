from __future__ import annotations

import networkx as nx
import pandas as pd


def build_graph(nodes: pd.DataFrame, edges: pd.DataFrame) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from((int(r.gid), {"gid": int(r.gid), "depth": int(r.depth), "is_seed": bool(r.is_seed)}) for r in nodes.itertuples())
    graph.add_edges_from((int(r.src), int(r.dst), {"sum_kzt": float(r.sum_kzt), "n_tx": int(r.n_tx), "depth": int(r.depth)}) for r in edges.itertuples())
    return graph

