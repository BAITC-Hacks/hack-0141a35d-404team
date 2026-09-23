from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "nodes": {"gid", "depth", "is_seed"},
    "edges": {"src", "dst", "sum_kzt", "n_tx", "depth"},
    "transactions": {"src", "dst", "date", "sum_kzt"},
}


def _read(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {name} input: {path}")
    frame = pd.read_parquet(path)
    missing = REQUIRED_COLUMNS[name] - set(frame.columns)
    if missing:
        raise ValueError(f"{name}.parquet missing columns: {sorted(missing)}")
    return frame


def load_data(input_dir: str | Path) -> dict[str, pd.DataFrame]:
    root = Path(input_dir)
    nodes = _read(root / "nodes.parquet", "nodes").copy()
    edges = _read(root / "edges.parquet", "edges").copy()
    transactions = _read(root / "transactions.parquet", "transactions").copy()
    nodes["gid"] = pd.to_numeric(nodes["gid"], errors="raise").astype("int64")
    nodes["depth"] = pd.to_numeric(nodes["depth"], errors="raise").astype("int64")
    nodes["is_seed"] = nodes["is_seed"].astype(bool)
    for column in ["src", "dst"]:
        edges[column] = pd.to_numeric(edges[column], errors="raise").astype("int64")
        transactions[column] = pd.to_numeric(transactions[column], errors="raise").astype("int64")
    edges["sum_kzt"] = pd.to_numeric(edges["sum_kzt"], errors="raise").astype(float)
    edges["n_tx"] = pd.to_numeric(edges["n_tx"], errors="raise").astype("int64")
    edges["depth"] = pd.to_numeric(edges["depth"], errors="raise").astype("int64")
    transactions["sum_kzt"] = pd.to_numeric(transactions["sum_kzt"], errors="raise").astype(float)
    transactions["date"] = pd.to_datetime(transactions["date"], errors="coerce")
    node_ids = set(nodes["gid"])
    edges = edges[edges["src"].isin(node_ids) & edges["dst"].isin(node_ids) & (edges["src"] != edges["dst"])].copy()
    transactions = transactions[transactions["src"].isin(node_ids) & transactions["dst"].isin(node_ids) & (transactions["src"] != transactions["dst"])].copy()
    if nodes["gid"].duplicated().any():
        raise ValueError("nodes.parquet contains duplicate gid values")
    return {"nodes": nodes, "edges": edges, "transactions": transactions}


def validation_report(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    return {"n_nodes": int(len(data["nodes"])), "n_edges": int(len(data["edges"])),
            "n_transactions": int(len(data["transactions"])), "n_seed": int(data["nodes"]["is_seed"].sum()),
            "n_invalid_dates": int(data["transactions"]["date"].isna().sum()),
            "total_edge_kzt": float(data["edges"]["sum_kzt"].sum())}

