from __future__ import annotations

from pathlib import Path
import pandas as pd


def export_outputs(scored: pd.DataFrame, clusters: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    root = Path(output_dir); root.mkdir(parents=True, exist_ok=True)
    nodes = scored[["gid", "role", "role_score", "component_id", "priority_score", "evidence"]].rename(columns={"component_id": "cluster_id"}).sort_values("gid")
    top = scored.sort_values(["priority_score", "role_score", "gid"], ascending=[False, False, True]).head(max(20, min(100, len(scored)))).copy(); top.insert(0, "rank", range(1, len(top) + 1))
    top = top[["rank", "gid", "role", "priority_score", "evidence"]].rename(columns={"evidence": "why"})
    paths = {"nodes_roles": root / "nodes_roles.csv", "clusters": root / "clusters.csv", "top_nodes": root / "top_nodes.csv"}
    nodes.to_csv(paths["nodes_roles"], index=False); clusters.to_csv(paths["clusters"], index=False); top.to_csv(paths["top_nodes"], index=False)
    if len(nodes) != len(scored) or nodes["gid"].duplicated().any(): raise ValueError("Invalid nodes_roles output")
    if not nodes["role"].isin({"consolidator", "transit", "distributor", "terminal", "coordinator", "peripheral"}).all(): raise ValueError("Unknown role in output")
    if not nodes["evidence"].str.len().between(1, 200).all(): raise ValueError("Invalid evidence length")
    if len(top) < 20 and len(scored) >= 20: raise ValueError("top_nodes.csv must contain at least 20 rows")
    return paths

