import unittest
import networkx as nx
import pandas as pd
from src.aml_graph.patterns import analyze_patterns, resilience
from src.aml_graph.analysis import calculate_metrics
from src.aml_graph.roles import assign_roles

class PatternTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for day in [1,2,3]:
            rows.extend([(1,2,f'2026-07-{day:02d} 10:00',10000), (2,3,f'2026-07-{day:02d} 12:00',10000)])
        # Repeated amounts, synchronized inflows, and a genuine structural 3-cycle.
        rows.extend([(4,2,'2026-07-03 09:00',6000),(5,2,'2026-07-03 09:00',6000),
                     (3,1,'2026-07-04',5000),(2,3,'2026-07-03 13:00',10000),(2,3,'2026-07-03 14:00',10000)])
        tx=pd.DataFrame(rows,columns=['src','dst','date','sum_kzt'])
        tx['date']=pd.to_datetime(tx.date,format='mixed')
        graph=nx.DiGraph()
        for i in range(1,7):graph.add_node(i,depth=4 if i==6 else 1,is_seed=i==1)
        for (src,dst),group in tx.groupby(['src','dst']):graph.add_edge(src,dst,sum_kzt=float(group.sum_kzt.sum()),n_tx=len(group),depth=1)
        metrics=assign_roles(calculate_metrics(graph,tx))
        return graph,tx,metrics

    def test_temporal_routes_cycles_and_repeated_amounts(self):
        graph,tx,metrics=self.fixture()
        result=analyze_patterns(graph,tx,metrics)
        node=result['nodes']['2']
        self.assertGreaterEqual(node['matched_48h_kzt'],30000)
        self.assertIn('synchronous_incoming',node['signals'])
        self.assertIn('repeated_amounts',node['signals'])
        self.assertTrue(any(r['gids']==['1','2','3'] and r['matching_events']>=3 for r in result['routes']))
        self.assertTrue(any(r['gids']==['1','2','3'] for r in result['cycles']))
        self.assertIn('extend_boundary',result['nodes']['6']['requests'])
        self.assertIn('seed_inflows',result['nodes']['1']['requests'])

    def test_window_and_simulation_do_not_mutate_graph(self):
        graph,tx,metrics=self.fixture()
        tx.loc[tx.src==2,'date'] += pd.Timedelta(days=10)
        result=analyze_patterns(graph,tx,metrics)
        self.assertEqual(result['nodes']['2']['matched_48h_kzt'],0)
        initial=(graph.number_of_nodes(),graph.number_of_edges())
        removal=resilience(graph,metrics,2)
        self.assertEqual(removal['after']['nodes'],initial[0]-2)
        self.assertEqual((graph.number_of_nodes(),graph.number_of_edges()),initial)
        self.assertEqual(resilience(graph,metrics,0)['before'],resilience(graph,metrics,0)['after'])

    def test_fifo_fragments_are_not_repeated_routes(self):
        graph,tx,metrics=self.fixture()
        tx=pd.DataFrame([(1,2,pd.Timestamp('2026-07-01 09:00'),5000),
                         (1,2,pd.Timestamp('2026-07-01 10:00'),5000),
                         (2,3,pd.Timestamp('2026-07-01 11:00'),10000)],columns=tx.columns)
        result=analyze_patterns(graph,tx,metrics)
        self.assertEqual(result['nodes']['2']['matched_48h_kzt'],10000)
        self.assertFalse(result['routes'])

    def test_48_hour_limit_is_inclusive_and_never_overallocates(self):
        graph,tx,metrics=self.fixture()
        tx=pd.DataFrame([(1,2,pd.Timestamp('2026-07-01'),10000),
                         (2,3,pd.Timestamp('2026-07-03'),6000),
                         (2,3,pd.Timestamp('2026-07-03 00:00:01'),6000)],columns=tx.columns)
        result=analyze_patterns(graph,tx,metrics)
        self.assertEqual(result['nodes']['2']['matched_48h_kzt'],6000)

    def test_burst_and_depth_outlier(self):
        graph,tx,metrics=self.fixture()
        extras=pd.DataFrame([(1,2,pd.Timestamp('2026-07-05'),5000)]*15,columns=tx.columns)
        tx=pd.concat([tx,extras],ignore_index=True)
        peers=pd.concat([metrics]*2,ignore_index=True)
        peers['gid']=range(100,100+len(peers));peers['total_flow']=list(range(len(peers)-1))+[10000000]
        peers['depth']=1
        for gid in peers.gid: graph.add_node(gid,depth=1,is_seed=False)
        # Existing fixture checks bursts separately; peer threshold is deterministic.
        result=analyze_patterns(graph,tx,metrics)
        self.assertIn('activity_burst',result['nodes']['2']['signals'])
        peer_result=analyze_patterns(graph.subgraph(peers.gid).copy(),tx.iloc[:0],peers)
        self.assertIn('depth_volume_outlier',peer_result['nodes'][str(peers.gid.iloc[-1])]['signals'])
