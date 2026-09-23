from __future__ import annotations

import html
import json
import math
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.aml_graph.pipeline import run_pipeline


TEXT = {
    "en": {
        "language": "Language", "english": "English", "russian": "Russian", "data": "Data",
        "input": "Input folder", "output": "Output folder", "run": "Run analysis", "run_hint": "Run the analysis to open the network view.",
        "nodes": "Nodes", "edges": "Edges", "role": "Focused role", "priority": "Priority", "focus": "Focus on gid",
        "network": "Transaction network", "network_hint": "Hover a node to see its concise explanation in the bottom-right corner.",
        "seed_warning": "Seed account: incoming flow is incomplete by construction.", "boundary_warning": "Depth-4 boundary: no outgoing edge may reflect graph truncation.",
        "focused": "Focused node", "top": "Priority nodes", "no_signal": "No strong structural signal observed.",
        "hover_hint": "Hover a node to inspect its role and evidence.", "download": "Download",
        "disclaimer": "Structural hypotheses for AML review, not conclusions of wrongdoing.",
    },
    "ru": {
        "language": "Язык", "english": "Английский", "russian": "Русский", "data": "Данные",
        "input": "Папка входных данных", "output": "Папка результатов", "run": "Запустить анализ", "run_hint": "Запустите анализ, чтобы открыть граф.",
        "nodes": "Узлы", "edges": "Связи", "role": "Роль узла", "priority": "Приоритет", "focus": "Найти gid",
        "network": "Граф переводов", "network_hint": "Наведите курсор на узел: объяснение появится в правом нижнем углу.",
        "seed_warning": "Seed-счёт: входящий поток неполный по конструкции графа.", "boundary_warning": "Граница глубины 4: отсутствие исходящей связи может быть обрывом графа.",
        "focused": "Выбранный узел", "top": "Приоритетные узлы", "no_signal": "Сильных структурных признаков не выявлено.",
        "hover_hint": "Наведите курсор на узел, чтобы увидеть роль и обоснование.", "download": "Скачать",
        "disclaimer": "Структурные гипотезы для AML-проверки, не утверждения о виновности.",
    },
}
ROLE_TEXT = {
    "en": {"coordinator": "coordinator", "consolidator": "consolidator", "distributor": "distributor", "transit": "transit", "terminal": "terminal", "peripheral": "peripheral"},
    "ru": {"coordinator": "координатор", "consolidator": "консолидатор", "distributor": "распределитель", "transit": "транзит", "terminal": "конечный получатель", "peripheral": "периферия"},
}
ROLE_COLORS = {"coordinator": "#d64545", "consolidator": "#f08a24", "distributor": "#2ea66f", "transit": "#3276c3", "terminal": "#8759a8", "peripheral": "#a9b2bd"}


def evidence_text(row, lang: str) -> str:
    if lang == "en":
        return str(row.evidence)
    if row.role == "coordinator":
        return f"Seed-счёт с наибольшей наблюдаемой связностью среди seed-счетов: {row.counterparty_count} контрагентов."
    if row.role == "consolidator":
        return f"Получает средства от {row.n_senders} отправителей; входящий поток выше исходящего."
    if row.role == "distributor":
        return f"Отправляет средства {row.n_receivers} получателям; исходящий поток выше входящего."
    if row.role == "transit":
        return f"Коэффициент пропуска наблюдаемого потока: {row.pass_through_ratio:.2f}; есть входящие и исходящие связи."
    if row.role == "terminal":
        return f"Нет наблюдаемых исходящих связей; получено {row.in_amount:,.0f} KZT."
    if row.is_depth4_boundary:
        return "Нет исходящей связи, но глубина 4 является границей графа; статус конечного получателя неизвестен."
    return "Обязательное структурное правило роли не сработало."


def make_network_html(graph, metrics, selected_gid: int, lang: str) -> str:
    visible = {selected_gid}
    frontier = {selected_gid}
    for _ in range(1):
        frontier = {n for node in frontier for n in graph.predecessors(node)} | {n for node in frontier for n in graph.successors(node)}
        visible |= frontier
    positions = {selected_gid: (500, 280)}
    others = sorted(visible - {selected_gid})
    for i, node in enumerate(others):
        angle = 2 * math.pi * i / max(1, len(others))
        positions[node] = (500 + 210 * math.cos(angle), 280 + 210 * math.sin(angle))
    edges = []
    for src, dst, data in graph.edges(data=True):
        if src in positions and dst in positions:
            edges.append({"src": src, "dst": dst, "amount": float(data["sum_kzt"]), "x1": positions[src][0], "y1": positions[src][1], "x2": positions[dst][0], "y2": positions[dst][1]})
    nodes = []
    for gid, (x, y) in positions.items():
        row = metrics.loc[gid]
        nodes.append({"gid": int(gid), "x": x, "y": y, "role": row.role, "role_text": ROLE_TEXT[lang][row.role], "color": ROLE_COLORS[row.role], "priority": float(row.priority_score), "evidence": evidence_text(row, lang), "suspicious": bool(row.role != "peripheral" or row.priority_score >= 0.45), "selected": gid == selected_gid})
    payload = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False).replace("</", "<\\/")
    t = TEXT[lang]
    return f"""
    <style>
      * {{ box-sizing: border-box; }} body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #fbfcfe; color: #263238; }}
      #network {{ position: relative; width: 100%; height: 590px; border: 1px solid #e1e6eb; border-radius: 14px; overflow: hidden; background: radial-gradient(#eef2f6 1px, transparent 1px); background-size: 20px 20px; }}
      svg {{ width: 100%; height: 100%; }} .edge {{ stroke: #b8c2cc; stroke-width: 2; opacity: .8; }} .node {{ cursor: pointer; stroke: white; stroke-width: 2; transition: r .12s, stroke-width .12s; }} .node:hover, .node.active {{ stroke: #17212b; stroke-width: 4; }}
      .label {{ font-size: 11px; fill: #34424e; pointer-events: none; }} #card {{ position: absolute; right: 14px; bottom: 14px; width: min(390px, 52%); padding: 12px 14px; border: 1px solid #d5dce3; border-radius: 10px; background: rgba(255,255,255,.96); box-shadow: 0 4px 18px rgba(33,45,55,.12); font-size: 12px; line-height: 1.4; }} #card strong {{ font-size: 13px; }} #hint {{ color: #657481; }}
    </style>
    <div id="network"><svg viewBox="0 0 1000 560" aria-label="AML transaction network">
      <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#9aa6b2"></path></marker></defs>
      <g id="edges"></g><g id="nodes"></g>
    </svg><div id="card"><strong>{html.escape(t["hover_hint"])}</strong><div id="hint">{html.escape(t["network_hint"])}</div></div></div>
    <script>
      const data = {payload}; const edgeLayer = document.getElementById('edges'); const nodeLayer = document.getElementById('nodes'); const card = document.getElementById('card');
      data.edges.forEach(e => {{ const line = document.createElementNS('http://www.w3.org/2000/svg','line'); line.setAttribute('x1',e.x1); line.setAttribute('y1',e.y1); line.setAttribute('x2',e.x2); line.setAttribute('y2',e.y2); line.setAttribute('class','edge'); line.setAttribute('marker-end','url(#arrow)'); line.setAttribute('title', e.src+' → '+e.dst+' · '+Math.round(e.amount).toLocaleString()+' KZT'); edgeLayer.appendChild(line); }});
      function show(n) {{ document.querySelectorAll('.node').forEach(x => x.classList.remove('active')); document.getElementById('n-'+n.gid).classList.add('active'); card.innerHTML = '<strong>gid '+n.gid+' · '+n.role_text+' · '+n.priority.toFixed(2)+'</strong><div>'+n.evidence+'</div>'; }}
      data.nodes.forEach(n => {{ const circle = document.createElementNS('http://www.w3.org/2000/svg','circle'); circle.setAttribute('id','n-'+n.gid); circle.setAttribute('cx',n.x); circle.setAttribute('cy',n.y); circle.setAttribute('r',n.selected ? 15 : 10); circle.setAttribute('fill',n.color); circle.setAttribute('class','node'); circle.addEventListener('mouseenter', () => show(n)); nodeLayer.appendChild(circle); const label = document.createElementNS('http://www.w3.org/2000/svg','text'); label.setAttribute('x',n.x); label.setAttribute('y',n.y-17); label.setAttribute('text-anchor','middle'); label.setAttribute('class','label'); label.textContent=n.gid; nodeLayer.appendChild(label); }});
    </script>
    """


st.set_page_config(page_title="AML Graph", page_icon="◎", layout="wide")
st.markdown("<style>#MainMenu, footer, header {visibility: hidden;} .stAppDeployButton {display:none;} </style>", unsafe_allow_html=True)
language_label = st.sidebar.selectbox("Language / Язык", ["English", "Русский"])
lang = "ru" if language_label == "Русский" else "en"
t = TEXT[lang]
st.title("AML Graph" if lang == "en" else "AML Graph — анализ сети")
st.caption(t["disclaimer"])
with st.sidebar:
    st.header(t["data"])
    input_dir = st.text_input(t["input"], "entryset")
    output_dir = st.text_input(t["output"], "outputset")
    if st.button(t["run"], type="primary", use_container_width=True):
        with st.spinner(t["run"] + "..."):
            try:
                st.session_state["result"] = run_pipeline(input_dir, output_dir)
            except Exception as exc:
                st.error(str(exc))
result = st.session_state.get("result")
if result is None:
    st.info(t["run_hint"])
    st.stop()

metrics = result["metrics"].set_index("gid", drop=False)
graph = result["graph"]
report = result["report"]
selected_gid = st.selectbox(t["focus"], sorted(metrics.index), format_func=str)
selected = metrics.loc[selected_gid]
summary = st.columns(4)
summary[0].metric(t["nodes"], report["n_nodes"])
summary[1].metric(t["edges"], report["n_edges"])
summary[2].metric(t["role"], ROLE_TEXT[lang][selected.role])
summary[3].metric(t["priority"], f"{selected.priority_score:.2f}")
st.subheader(t["network"])
st.caption(t["network_hint"])
if selected.is_seed:
    st.warning(t["seed_warning"])
if selected.is_depth4_boundary:
    st.warning(t["boundary_warning"])
components.html(make_network_html(graph, metrics, selected_gid, lang), height=600, scrolling=False)
st.subheader(t["focused"])
st.write(evidence_text(selected, lang))
st.subheader(t["top"])
table = metrics.sort_values(["priority_score", "total_flow"], ascending=False).head(20)[["gid", "role", "priority_score", "evidence"]].copy()
table["role"] = table["role"].map(ROLE_TEXT[lang])
table["evidence"] = [evidence_text(metrics.loc[gid], lang) for gid in table.index]
st.dataframe(table, use_container_width=True, hide_index=True)
for name, path in result["paths"].items():
    st.download_button(f"{t['download']} {name}.csv", Path(path).read_bytes(), file_name=Path(path).name, mime="text/csv")
