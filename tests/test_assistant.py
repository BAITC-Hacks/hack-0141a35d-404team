import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from fastapi.testclient import TestClient
import app as backend
from src.aml_graph.assistant import Memory, Retriever, answer
from src.aml_graph.pipeline import run_pipeline

class FakeResponses:
    def __init__(self,gid):self.requests=[];self.gid=gid
    def create(self,**kwargs):
        self.requests.append(kwargs)
        if len(self.requests)==1:
            call=NS(type='function_call',name='query_data',call_id='call-1',arguments=json.dumps({'kind':'node','gids':[self.gid],'limit':1}))
            return NS(output=[call],output_text='',usage=NS(input_tokens=100,output_tokens=20))
        return NS(output=[],output_text=f'Review observed flow [gid:{self.gid}].',usage=NS(input_tokens=150,output_tokens=30))

class AssistantTests(unittest.TestCase):
    def test_request_budget_stops_uncooperative_tool_loop(self):
        import networkx as nx
        files={'nodes_roles.csv':b'gid,role,role_score,cluster_id,priority_score,evidence\n1,peripheral,0,1,1,Limited\n',
               'top_nodes.csv':b'rank,gid,role,priority_score,why\n1,1,peripheral,1,Limited\n',
               'clusters.csv':b'cluster_id,n_nodes,n_seed,sum_kzt_internal,top_gids,hypothesis\n1,1,0,0,1,Limited\n'}
        class Loop:
            calls=0
            def create(self,**kwargs):
                self.calls+=1
                return NS(output=[NS(type='function_call',name='unapproved_tool',arguments='{}',call_id=str(self.calls))],output_text='',usage=None)
        loop=Loop()
        with self.assertRaisesRegex(ValueError,'budget exhausted'):
            answer({'graph':nx.DiGraph(),'report':{}},files,[],'Hi','1','en',NS(responses=loop))
        self.assertEqual(loop.calls,5)

    def test_memory_is_local_and_dataset_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Memory(Path(folder)/'memory.sqlite3')
            store.save('abc','dataset1',[{'role':'user','content':'Prior question'}])
            self.assertEqual(Memory(store.path).read('abc','dataset1')[0]['content'],'Prior question')
            with self.assertRaises(ValueError):store.read('abc','dataset2')
            store.clear('abc');self.assertEqual(store.read('abc','dataset1'),[])

    @unittest.skipUnless(Path('entryset/nodes.parquet').exists(),'Local dataset required')
    def test_bounded_retrieval_tools_and_api_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_pipeline('entryset',folder)
            files={p.name:p.read_bytes() for p in result['paths'].values()}
            gid=str(result['metrics'].gid.iloc[0])
            retriever=Retriever(result,files,[])
            self.assertEqual(len(retriever.query({'kind':'top','limit':1000})['rows']),10)
            fake=FakeResponses(gid)
            output=answer(result,files,[{'role':'user','content':'earlier question','selected_gid':gid}],'Explain it',gid,'en',NS(responses=fake))
            self.assertEqual(output['gids'],[gid])
            self.assertFalse(fake.requests[0]['store'])
            self.assertEqual(fake.requests[0]['max_output_tokens'],1400)
            self.assertIn('earlier question',json.dumps(fake.requests[0]['input'][:3]))
            self.assertEqual(len(output['queries']),1)
            client=TestClient(backend.app)
            public=client.post('/api/analyze',json={}).json()
            dataset=public['dataset_id'];store=Memory(Path(folder)/'chat.sqlite3')
            with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
                self.assertEqual(client.post('/api/chat',json={'dataset_id':dataset,'session_id':'test','message':'Hi'}).status_code,503)
            with patch.dict('os.environ',{'OPENAI_API_KEY':'unit-test-placeholder'}),patch.object(backend,'memory',return_value=store),patch.object(backend,'answer',return_value=output):
                response=client.post('/api/chat',json={'dataset_id':dataset,'session_id':'test','message':'Explain','selected_gid':gid})
                self.assertEqual(response.status_code,200)
                history=client.get(f'/api/chat/history/test?dataset_id={dataset}').json()
                self.assertEqual(len(history['messages']),2)
                self.assertEqual(client.post('/api/chat',json={'dataset_id':'stale','session_id':'test','message':'Hi'}).status_code,409)
                self.assertEqual(client.delete('/api/chat/history/test').status_code,200)
                self.assertEqual(store.read('test',dataset),[])
            self.assertEqual(client.get(f'/api/nodes/{gid}/card?dataset_id={dataset}').status_code,200)
            self.assertEqual(client.post('/api/resilience',json={'dataset_id':dataset,'n':3}).json()['after']['nodes'],len(result['metrics'])-3)
