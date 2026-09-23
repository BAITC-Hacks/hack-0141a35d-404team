from __future__ import annotations

import math
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st
from src.aml_graph.pipeline import run_pipeline

st.set_page_config(page_title="AML Graph Analysis", layout="wide")
st.title("AML Graph Analysis")
st.caption("Explainable structural hypotheses for analyst review — not conclusions of criminal responsibility.")
input_dir = st.sidebar.text_input("Input directory", "entryset")
output_dir = st.sidebar.text_input("Output directory", "outputset")
if st.sidebar.button("Run analysis", type="primary"):
    with st.spinner("Loading data and calculating graph analysis..."):
        try: st.session_state["result"] = run_pipeline(input_dir, output_dir); st.success("Analysis complete and CSV outputs written.")
        except Exception as exc: st.error(f"Analysis failed: {exc}")
result = st.session_state.get("result")
if result is None: st.info("Choose an input directory and click Run analysis to begin."); st.stop()
metrics, report = result["metrics"].set_index("gid", drop=False), result["report"]
cols = st.columns(5)
for col, label, value in zip(cols, ["Nodes", "Edges", "Transactions", "Seeds", "Total edge flow"], [report["n_nodes"], report["n_edges"], report["n_transactions"], report["n_seed"], f"{report['total_edge_kzt']:,.0f} KZT"]): col.metric(label, value)
if report["n_invalid_dates"]: st.warning(f"{report['n_invalid_dates']} transaction dates could not be parsed.")
selected_gid = st.sidebar.selectbox("Find gid", sorted(metrics["gid"].tolist()))
row = metrics.loc[selected_gid]
st.subheader(f"Node {selected_gid}")
detail = st.columns(5)
for col, label, value in zip(detail, ["Role", "Role score", "Priority", "Depth", "Cluster"], [row.role, f"{row.role_score:.2f}", f"{row.priority_score:.2f}", int(row.depth), int(row.component_id)]): col.metric(label, value)
st.write(row.evidence)
if row.is_seed: st.warning("Seed node: incoming flow is incomplete by construction.")
if row.is_depth4_boundary: st.warning("Depth-4 boundary node: no outgoing edge may reflect graph truncation.")
graph = result["graph"]; neighborhood = {selected_gid} | set(graph.predecessors(selected_gid)) | set(graph.successors(selected_gid)); positions = {selected_gid: (0.5, 0.5)}
others = sorted(neighborhood - {selected_gid})
for i, node in enumerate(others):
    angle = 2 * math.pi * i / max(1, len(others)); positions[node] = (0.5 + 0.4 * math.cos(angle), 0.5 + 0.4 * math.sin(angle))
fig = go.Figure()
for u, v, data in graph.edges(data=True):
    if u in positions and v in positions: fig.add_trace(go.Scatter(x=[positions[u][0], positions[v][0]], y=[positions[u][1], positions[v][1]], mode="lines", line={"color": "#aaa", "width": 2}, hoverinfo="text", text=f"{u} → {v}: {data['sum_kzt']:,.0f} KZT", showlegend=False))
colors = {"coordinator": "#d62728", "consolidator": "#ff7f0e", "distributor": "#2ca02c", "transit": "#1f77b4", "terminal": "#9467bd", "peripheral": "#9e9e9e"}
for node, (x, y) in positions.items():
    role = metrics.loc[node, "role"]; fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[str(node)], textposition="top center", marker={"size": 18 if node == selected_gid else 12, "color": colors.get(role, "#999")}, hovertemplate=f"gid={node}<br>role={role}<extra></extra>", showlegend=False))
fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False}, height=500, margin={"l": 0, "r": 0, "t": 10, "b": 0})
st.subheader("Selected-node neighborhood"); st.plotly_chart(fig, use_container_width=True)
st.subheader("Priority nodes"); st.dataframe(metrics.sort_values("priority_score", ascending=False).head(50)[["gid", "role", "priority_score", "evidence"]], use_container_width=True, hide_index=True)
for name, path in result["paths"].items(): st.download_button(f"Download {name}.csv", Path(path).read_bytes(), file_name=Path(path).name, mime="text/csv")
