import tempfile
import unittest
from pathlib import Path
import networkx as nx
import pandas as pd
from src.aml_graph.clustering import assign_clusters, summarize_clusters
from src.aml_graph.pipeline import run_pipeline


class ClusteringTests(unittest.TestCase):
    def test_connected_communities_split_without_losing_isolates(self):
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
        clusters = assign_clusters(graph, scored)
        mapping = clusters.set_index('gid').cluster_id.to_dict()
        self.assertEqual(len(set(mapping[g] for g in range(4))), 1)
        self.assertEqual(len(set(mapping[g] for g in range(4, 8))), 1)
        self.assertNotEqual(mapping[0], mapping[4])
        self.assertNotIn(mapping[8], [mapping[0], mapping[4]])
        reordered = nx.DiGraph()
        reordered.add_nodes_from(reversed(list(graph)))
        reordered.add_edges_from(reversed(list(graph.edges(data=True))))
        other = assign_clusters(reordered, scored.iloc[::-1]).set_index('gid').cluster_id.to_dict()
        self.assertEqual(mapping, other)
        summary = summarize_clusters(graph, clusters)
        # The bridge between communities is not internal volume.
        self.assertEqual(summary.sum_kzt_internal.sum(), 240000)
        self.assertEqual(summary.n_nodes.sum(), 9)
        pd.testing.assert_series_equal(clusters.component_id, scored.component_id)

    @unittest.skipUnless(Path('entryset/nodes.parquet').exists(), 'Local dataset required')
    def test_real_data_communities_and_unchanged_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_pipeline('entryset', folder)
            scored, report = result['metrics'], result['report']
            self.assertGreater(report['n_clusters'], report['n_components'])
            self.assertLess(result['clusters'].n_nodes.max(), scored.component_size.max())
            self.assertTrue((scored.groupby('cluster_id').component_id.nunique() == 1).all())
            self.assertEqual(scored.cluster_id.nunique(), len(result['clusters']))
            pd.testing.assert_series_equal(scored.priority_score, scored.total_flow.rank(method='min', pct=True).round(6), check_names=False)
            print('Communities:',report['n_clusters'],'largest:',result['clusters'].n_nodes.max(),
                  'isolated accounts:',int((scored.counterparty_count==0).sum()))
