import tempfile
import unittest
from pathlib import Path
import networkx as nx
import pandas as pd
from src.aml_graph.clustering import assign_clusters, summarize_clusters
from src.aml_graph.pipeline import run_pipeline


class ClusteringTests(unittest.TestCase):
    def test_bridge_splits_communities_but_retains_components_and_isolate(self):
        graph = nx.DiGraph()
        graph.add_nodes_from(range(9))
        for members in [range(4), range(4, 8)]:
            for u in members:
                for v in members:
                    if u != v: graph.add_edge(u, v, sum_kzt=10000, n_tx=1)
        graph.add_edge(3, 4, sum_kzt=1, n_tx=1)
        scored = pd.DataFrame({'gid': range(9), 'component_id': [1]*8+[2],
                               'role': ['peripheral']*9, 'priority_score': [0.5]*9,
                               'is_seed': [False]*9})
        clustered = assign_clusters(graph, scored)
        summary = summarize_clusters(graph, clustered)
        self.assertEqual(summary.n_nodes.tolist(), [4, 4, 1])
        self.assertEqual(summary.cluster_id.tolist(), [1, 2, 3])
        self.assertEqual(summary.sum_kzt_internal.sum(), 240000)
        self.assertEqual(clustered.component_id.tolist(), scored.component_id.tolist())
        reversed_graph = nx.DiGraph()
        reversed_graph.add_nodes_from(reversed(list(graph)))
        reversed_graph.add_edges_from(reversed(list(graph.edges(data=True))))
        reversed_scored = assign_clusters(reversed_graph, scored.iloc[::-1])
        self.assertEqual(clustered.set_index('gid').cluster_id.to_dict(), reversed_scored.set_index('gid').cluster_id.to_dict())
        self.assertIn('Isolated', summary.hypothesis.iloc[-1])

    def test_all_isolates_remain_separate(self):
        graph = nx.DiGraph()
        graph.add_nodes_from([1, 2, 3])
        scored = assign_clusters(graph, pd.DataFrame({'gid':[1,2,3]}))
        self.assertEqual(scored.cluster_id.tolist(), [1, 2, 3])

    @unittest.skipUnless(Path('entryset/nodes.parquet').exists(), 'Local dataset required')
    def test_real_communities_cover_all_accounts_without_changing_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_pipeline('entryset', folder)
            scored, report = result['metrics'], result['report']
            self.assertGreater(report['n_clusters'], report['n_components'])
            components = sorted(nx.weakly_connected_components(result['graph']), key=min)
            expected = {gid: cid for cid, group in enumerate(components, 1) for gid in group}
            self.assertEqual(scored.set_index('gid').component_id.to_dict(), expected)
            self.assertLess(result['clusters'].n_nodes.max(), scored.component_size.max())
            self.assertEqual(result['clusters'].n_nodes.sum(), len(scored))
            for _, group in scored.groupby('cluster_id'):
                self.assertEqual(group.component_id.nunique(), 1)
                self.assertTrue(nx.is_weakly_connected(result['graph'].subgraph(group.gid)))
            expected = scored.set_index('gid').cluster_id.to_dict()
            pd.testing.assert_series_equal(scored.priority_score, scored.total_flow.rank(method='min', pct=True).round(6), check_names=False)
            exports = pd.read_csv(result['paths']['nodes_roles'])
            self.assertEqual(exports.set_index('gid').cluster_id.to_dict(), expected)
            print('Communities:', report['n_clusters'], 'largest:', result['clusters'].n_nodes.max())
