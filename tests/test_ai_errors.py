import unittest
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch
import httpx
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from fastapi.testclient import TestClient
import app
from src.aml_graph.ai_errors import describe_error


class AIErrorTests(unittest.TestCase):
    def test_errors_are_actionable_without_provider_bodies(self):
        request = httpx.Request('POST', 'https://api.openai.com/v1/responses')
        cases = [
            (APIConnectionError(request=request), 'connection'),
            (APITimeoutError(request=request), 'timeout'),
            (AuthenticationError('SENSITIVE_TEST_TOKEN', response=httpx.Response(401, request=request), body={}), 'authentication'),
            (RateLimitError('provider text', response=httpx.Response(429, request=request), body={'code':'insufficient_quota'}), 'quota'),
        ]
        for error, expected in cases:
            code, message = describe_error(error)
            self.assertEqual(code, expected)
            self.assertNotIn('SENSITIVE_TEST_TOKEN', message)
            self.assertNotIn('provider text', message)

    def test_explicit_connection_check_uses_no_graph_data(self):
        fake = MagicMock()
        fake.__enter__.return_value = fake
        fake.responses.create.return_value = NS(model='test-active-model', output_text='OK')
        with patch.object(app, 'settings', return_value={'api_key':'fixture-private', 'model':'test-active-model'}), patch.object(app, 'OpenAI', return_value=fake):
            response = TestClient(app.app).post('/api/chat/check')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'connected':True, 'model':'test-active-model'})
        args = fake.responses.create.call_args.kwargs
        self.assertEqual(args['input'], 'Reply with OK only.')
        self.assertFalse(args['store'])
        self.assertNotIn('fixture-private', response.text)

    def test_connection_check_reports_missing_key_and_releases_lock(self):
        with patch.object(app, 'settings', return_value={'api_key':'', 'model':'test-model'}):
            response = TestClient(app.app).post('/api/chat/check')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail']['code'], 'missing_key')
        self.assertFalse(app.chat_lock.locked())

    def test_connection_check_sanitizes_authentication_error(self):
        request = httpx.Request('POST', 'https://api.openai.com/v1/responses')
        error = AuthenticationError('SENSITIVE_TEST_TOKEN', response=httpx.Response(401, request=request), body={})
        with patch.object(app, 'settings', return_value={'api_key':'fixture-private','model':'test-model'}), patch.object(app, 'OpenAI', side_effect=error):
            response = TestClient(app.app).post('/api/chat/check')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['detail']['code'], 'authentication')
        self.assertNotIn('SENSITIVE_TEST_TOKEN', response.text)
        self.assertFalse(app.chat_lock.locked())
