import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.aml_graph.config import settings


class ConfigTests(unittest.TestCase):
    def test_example_fallback_private_override_reload_and_environment(self):
        # Fixture keys are deliberately not real OpenAI tokens.
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {}, clear=True):
            root = Path(folder)
            self.assertEqual(settings(root)['api_key'], '')
            (root/'.env.example').write_text('OPENAI_API_KEY=fixture-example\nOPENAI_MODEL=test-model\n')
            self.assertEqual(settings(root)['api_key'], 'fixture-example')
            (root/'.env').write_text('OPENAI_API_KEY=fixture-private\n')
            self.assertEqual(settings(root)['api_key'], 'fixture-private')
            (root/'.env').write_text('OPENAI_API_KEY=fixture-new\nOPENAI_MODEL=\n')
            self.assertEqual(settings(root)['api_key'], 'fixture-new')
            self.assertEqual(settings(root)['model'], 'gpt-5.4-nano')
            with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
                self.assertEqual(settings(root)['api_key'], '')

    def test_chat_status_never_exposes_key(self):
        import app
        from fastapi.testclient import TestClient
        with patch.object(app, 'settings', return_value={'api_key':'fixture-secret','model':'test-model'}):
            data = TestClient(app.app).get('/api/chat/status').json()
            self.assertEqual(data, {'configured':True, 'model':'test-model'})
