from __future__ import annotations

from pathlib import Path
import pandas as pd


def export_outputs(scored: pd.DataFrame, clusters: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    root = Path(output_dir); root.mkdir(parents=True, exist_ok=True)
    nodes = scored[["gid", "role", "role_score", "cluster_id", "priority_score", "evidence"]].sort_values("gid")
    top = scored.sort_values(["priority_score", "role_score", "gid"], ascending=[False, False, True]).head(max(20, min(100, len(scored)))).copy(); top.insert(0, "rank", range(1, len(top) + 1))
    top["why"] = top.apply(lambda r: f"Observed flow {r.total_flow:,.2f} KZT; volume rank score {r.priority_score:.6f}. {r.evidence}", axis=1)
    top = top[["rank", "gid", "role", "priority_score", "why"]]
    paths = {"nodes_roles": root / "nodes_roles.csv", "clusters": root / "clusters.csv", "top_nodes": root / "top_nodes.csv"}
    if len(nodes) != len(scored) or nodes["gid"].duplicated().any(): raise ValueError("Invalid nodes_roles output")
    if not nodes["role"].isin({"consolidator", "transit", "distributor", "terminal", "coordinator", "peripheral"}).all(): raise ValueError("Unknown role in output")
    if not nodes["evidence"].str.len().between(1, 200).all(): raise ValueError("Invalid evidence length")
    if len(top) < 20 and len(scored) >= 20: raise ValueError("top_nodes.csv must contain at least 20 rows")
    if not nodes[["role_score", "priority_score"]].apply(lambda s: s.between(0, 1).all()).all(): raise ValueError("Scores must be finite and in [0, 1]")
    if nodes.isna().any().any() or clusters.isna().any().any(): raise ValueError("Output fields must be populated")
    if set(nodes["cluster_id"]) != set(clusters["cluster_id"]) or clusters["n_nodes"].sum() != len(nodes): raise ValueError("Incomplete cluster coverage")
    nodes.to_csv(paths["nodes_roles"], index=False); clusters.to_csv(paths["clusters"], index=False); top.to_csv(paths["top_nodes"], index=False)
    return paths

