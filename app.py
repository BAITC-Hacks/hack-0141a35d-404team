from __future__ import annotations

import math
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

from src.aml_graph.pipeline import run_pipeline


ROLE_COLORS = {
    "coordinator": "#d64545",
    "consolidator": "#f08a24",
    "distributor": "#2ea66f",
    "transit": "#3276c3",
    "terminal": "#8759a8",
    "peripheral": "#a9b2bd",
}


def _neighborhood(graph, gid: int, hops: int = 1) -> set[int]:
    nodes = {gid}
    frontier = {gid}
    for _ in range(hops):
        frontier = {n for node in frontier for n in graph.predecessors(node)} | {n for node in frontier for n in graph.successors(node)}
        nodes |= frontier
    return nodes


def _make_graph_figure(graph, metrics, selected_gid: int, hovered_gid: int | None) -> go.Figure:
    visible = _neighborhood(graph, selected_gid, hops=1)
    positions = {selected_gid: (0.50, 0.52)}
    others = sorted(visible - {selected_gid})
    for i, node in enumerate(others):
        angle = 2 * math.pi * i / max(1, len(others))
        positions[node] = (0.50 + 0.36 * math.cos(angle), 0.52 + 0.36 * math.sin(angle))

    fig = go.Figure()
    max_flow = max((float(data["sum_kzt"]) for _, _, data in graph.edges(data=True)), default=1.0)
    for src, dst, data in graph.edges(data=True):
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line={"color": "#d5dbe2", "width": max(1, min(5, 1 + 4 * float(data["sum_kzt"]) / max_flow))},
            hoverinfo="text", text=f"{src} → {dst}<br>{float(data['sum_kzt']):,.0f} KZT",
            showlegend=False,
        ))

    node_ids = list(positions)
    node_rows = metrics.loc[node_ids]
    node_sizes = [22 if gid == selected_gid else 18 if gid == hovered_gid else 12 for gid in node_ids]
    node_colors = [ROLE_COLORS.get(role, "#a9b2bd") for role in node_rows["role"]]
    customdata = [[int(row.gid), str(row.role), float(row.priority_score), str(row.evidence)] for row in node_rows.itertuples()]
    fig.add_trace(go.Scatter(
        x=[positions[gid][0] for gid in node_ids], y=[positions[gid][1] for gid in node_ids],
        mode="markers+text", text=[str(gid) for gid in node_ids], textposition="top center",
        marker={"size": node_sizes, "color": node_colors, "line": {"color": "white", "width": 1}},
        customdata=customdata,
        hovertemplate="gid=%{customdata[0]}<br>role=%{customdata[1]}<br>priority=%{customdata[2]:.2f}<extra>Hover for explanation</extra>",
        showlegend=False,
    ))

    explanation = "Hover a colored node to inspect its AML review signal."
    if hovered_gid is not None and hovered_gid in metrics.index:
        hovered = metrics.loc[hovered_gid]
        suspicious = hovered.role != "peripheral" or hovered.priority_score >= 0.45
        if suspicious:
            explanation = f"gid {hovered_gid} · {hovered.role} · priority {hovered.priority_score:.2f}<br>{hovered.evidence}"
        else:
            explanation = f"gid {hovered_gid} · peripheral · no strong structural signal observed"
    fig.add_annotation(
        x=0.98, y=0.03, xref="paper", yref="paper", xanchor="right", yanchor="bottom",
        text=explanation, align="left", showarrow=False,
        bgcolor="rgba(255,255,255,0.95)", bordercolor="#d5dbe2", borderwidth=1, borderpad=8,
        font={"size": 12, "color": "#263238"},
    )
    fig.update_layout(
        height=560, margin={"l": 0, "r": 0, "t": 10, "b": 0},
        paper_bgcolor="#fbfcfe", plot_bgcolor="#fbfcfe",
        xaxis={"visible": False, "range": [0, 1]}, yaxis={"visible": False, "range": [0, 1]},
        hovermode="closest",
    )
    return fig


st.set_page_config(page_title="AML Graph", page_icon="◎", layout="wide")
st.title("AML Graph")
st.caption("Minimal directed network view for explainable AML review.")

with st.sidebar:
    st.header("Data")
    input_dir = st.text_input("Input folder", "entryset")
    output_dir = st.text_input("Output folder", "outputset")
    if st.button("Run analysis", type="primary", use_container_width=True):
        with st.spinner("Building graph..."):
            try:
                st.session_state["result"] = run_pipeline(input_dir, output_dir)
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")

result = st.session_state.get("result")
if result is None:
    st.info("Run the analysis from the sidebar to open the network view.")
    st.stop()

metrics = result["metrics"].set_index("gid", drop=False)
graph = result["graph"]
report = result["report"]
selected_gid = st.selectbox("Focus on gid", sorted(metrics.index), format_func=str)
selected = metrics.loc[selected_gid]

summary = st.columns(4)
summary[0].metric("Nodes", report["n_nodes"])
summary[1].metric("Edges", report["n_edges"])
summary[2].metric("Focused role", selected.role)
summary[3].metric("Priority", f"{selected.priority_score:.2f}")

st.subheader(f"Network around {selected_gid}")
st.caption("Node colors represent roles. Hover a node to update the explanation card in the lower-right corner.")
if selected.is_seed:
    st.warning("Seed account: incoming flow is incomplete by construction.")
if selected.is_depth4_boundary:
    st.warning("Depth-4 boundary: no outgoing edge may reflect graph truncation.")

hovered = st.session_state.get("hovered_gid")
events = plotly_events(
    _make_graph_figure(graph, metrics, selected_gid, hovered),
    hover_event=True, click_event=True, select_event=False, override_height=560, key=f"network-{selected_gid}",
)
if events:
    point = events[-1]
    customdata = point.get("customdata")
    if customdata:
        st.session_state["hovered_gid"] = int(customdata[0])
        st.rerun()

st.subheader("Focused node")
st.write(selected.evidence)
st.dataframe(
    metrics.sort_values("priority_score", ascending=False).head(20)[["gid", "role", "priority_score", "evidence"]],
    use_container_width=True, hide_index=True,
)

for name, path in result["paths"].items():
    st.download_button(f"Download {name}.csv", Path(path).read_bytes(), file_name=Path(path).name, mime="text/csv")
