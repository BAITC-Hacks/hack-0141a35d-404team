import tempfile
import unittest
from pathlib import Path
import networkx as nx
import pandas as pd
from src.aml_graph.analysis import calculate_metrics
from src.aml_graph.roles import assign_roles
from src.aml_graph.pipeline import run_pipeline

class RequirementsTests(unittest.TestCase):
    def test_boundary_seeds_and_isolates(self):
        g = nx.DiGraph()
        for gid in range(1, 11):
            g.add_node(gid, depth=4 if gid == 4 else 1, is_seed=gid in {1, 8, 9})
        for u, v, amount in [(2,1,100),(1,3,100),(2,4,100),(3,4,100),(6,4,100),(2,5,100),
                             (9,2,100),(9,3,100),(9,6,200),(6,7,100)]:
            g.add_edge(u,v,sum_kzt=amount,n_tx=1,depth=1)
        scored = assign_roles(calculate_metrics(g,pd.DataFrame(columns=['src','dst']))).set_index('gid')
        self.assertEqual(scored.loc[4,'role'],'peripheral')
        self.assertIn('boundary',scored.loc[4,'evidence'])
        self.assertEqual(scored.loc[8,'role'],'peripheral')
        self.assertEqual(scored.loc[10,'role'],'peripheral')
        self.assertEqual(scored.loc[1,'role'],'peripheral')
        self.assertTrue(pd.isna(scored.loc[1,'pass_through_ratio']))
        self.assertEqual(scored.loc[5,'role'],'terminal')
        self.assertEqual(scored.loc[6,'role'],'transit')
        expected=scored['total_flow'].rank(method='min',pct=True).round(6)
        pd.testing.assert_series_equal(scored['priority_score'],expected,check_names=False)

    @unittest.skipUnless(Path('entryset/nodes.parquet').exists(),'Dataset required')
    def test_deliverables_and_dataset_limitations(self):
        with tempfile.TemporaryDirectory() as out:
            result=run_pipeline('entryset',out)
            m=result['metrics']; r=result['report']
            self.assertEqual(len(m),len(pd.read_parquet('entryset/nodes.parquet')))
            self.assertTrue((m.loc[m.is_depth4_boundary,'role']=='peripheral').all())
            self.assertTrue(m.loc[m.is_seed,'pass_through_ratio'].isna().all())
            self.assertTrue((m.loc[m.counterparty_count==0,'role']=='peripheral').all())
            n=pd.read_csv(Path(out)/'nodes_roles.csv');c=pd.read_csv(Path(out)/'clusters.csv');t=pd.read_csv(Path(out)/'top_nodes.csv')
            self.assertEqual(n.columns.tolist(),['gid','role','role_score','cluster_id','priority_score','evidence'])
            self.assertTrue(n.gid.is_unique)
            self.assertTrue(n.evidence.str.len().between(1,200).all())
            self.assertTrue(n[['role_score','priority_score']].apply(lambda s:s.between(0,1).all()).all())
            self.assertEqual(set(n.cluster_id),set(c.cluster_id))
            self.assertGreaterEqual(len(t),20)
            self.assertTrue(t.why.str.contains('Observed flow').all())
            self.assertTrue(t.priority_score.is_monotonic_decreasing)
            print('Dataset coverage:',{k:r[k] for k in ['n_seed','n_isolated_seed','n_seed_without_outgoing','n_boundary','n_components','n_connected_components']})

if __name__=='__main__': unittest.main()
