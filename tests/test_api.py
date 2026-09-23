import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app import app, lock, state, ROOT
from src.aml_graph.pipeline import run_pipeline

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_errors(self):
        self.assertEqual(self.client.get('/api/health').json(), {'status': 'ok'})
        self.assertEqual(self.client.post('/api/analyze', json={'input_dir': 'nonexistent-folder'}).status_code, 400)
        self.assertEqual(self.client.get('/api/exports/unknown.csv').status_code, 404)
        lock.acquire()
        try:
            self.assertEqual(self.client.post('/api/analyze', json={}).status_code, 409)
        finally:
            lock.release()

    @unittest.skipUnless((ROOT / 'entryset/nodes.parquet').exists(), 'Local parquet inputs required')
    def test_api_matches_pipeline(self):
        with tempfile.TemporaryDirectory() as output:
            baseline = run_pipeline(ROOT / 'entryset', output)
            response = self.client.post('/api/analyze', json={})
            self.assertEqual(response.status_code, 200, response.text[:300])
            data = response.json()
            self.assertEqual(len(data['nodes']), len(baseline['metrics']))
            self.assertEqual({n['gid'] for n in data['nodes']}, set(baseline['metrics']['gid'].map(str)))
            self.assertTrue(all(isinstance(e['src'], str) and isinstance(e['dst'], str) for e in data['edges']))
            self.assertEqual(len(data['edges']), baseline['graph'].number_of_edges())
            for name, path in baseline['paths'].items():
                export = self.client.get('/api/exports/' + path.name)
                self.assertEqual(export.status_code, 200)
                self.assertEqual(export.content, path.read_bytes(), name)
            self.assertLess(data['elapsed_seconds'], 300)
            print(f"API parity: {len(data['nodes'])} nodes, {len(data['edges'])} edges in {data['elapsed_seconds']}s")

if __name__ == '__main__':
    unittest.main()
