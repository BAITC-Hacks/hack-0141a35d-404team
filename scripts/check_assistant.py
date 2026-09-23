"""Opt-in live smoke test. Sends synthetic fixtures, NEVER entryset account data.

Run: python scripts/check_assistant.py
Uses the server .env and consumes a small amount of API credit.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import networkx as nx
import pandas as pd
from openai import OpenAI, OpenAIError
from src.aml_graph.analysis import calculate_metrics
from src.aml_graph.roles import assign_roles
from src.aml_graph.clustering import assign_clusters, summarize_clusters
from src.aml_graph.exports import export_outputs
from src.aml_graph.patterns import analyze_patterns
from src.aml_graph.assistant import answer
from src.aml_graph.config import settings
from src.aml_graph.ai_errors import describe_error


def main():
    config = settings()
    if not config['api_key']:
        print('FAIL: Set OPENAI_API_KEY in .env on the Python server.')
        return 1
    graph = nx.DiGraph()
    for gid in (1, 2, 3):
        graph.add_node(gid, depth=gid-1, is_seed=gid == 1)
    graph.add_edge(1, 2, sum_kzt=10000, n_tx=1, depth=1)
    graph.add_edge(2, 3, sum_kzt=10000, n_tx=1, depth=2)
    transactions = pd.DataFrame({'src':[1,2], 'dst':[2,3],
                                 'date':pd.to_datetime(['2026-07-01','2026-07-02']),
                                 'sum_kzt':[10000,10000]})
    scored = assign_clusters(graph, assign_roles(calculate_metrics(graph, transactions)))
    clusters = summarize_clusters(graph, scored)
    result = {'graph': graph, 'metrics': scored, 'report': {'n_nodes':3, 'synthetic_test':True},
              'insights': analyze_patterns(graph, transactions, scored)}
    try:
        with tempfile.TemporaryDirectory() as folder, OpenAI(api_key=config['api_key'], timeout=35, max_retries=0) as client:
            files = {p.name:p.read_bytes() for p in export_outputs(scored, clusters, folder).values()}
            output = answer(result, files, [], 'Use query_data to retrieve the insights for selected account 2, then explain its observed transfers in one sentence. Cite its gid.', '2', 'en', client)
        if not output['answer'] or not output['queries']:
            print('FAIL: Expected a response and a local retrieval query.')
            return 1
        print('PASS: model=' + config['model'] + '; synthetic retrieval queries=' + str(len(output['queries']))
              + '; cited gids=' + ','.join(output['gids']))
        return 0
    except OpenAIError as exc:
        code, message = describe_error(exc)
        print('FAIL (' + code + '): ' + message)
        return 1
    except ValueError:
        print('FAIL: No completed assistant response. Check model compatibility or retry.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
