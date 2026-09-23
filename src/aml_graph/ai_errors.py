"""Safe actionable errors: never forward provider bodies containing credentials."""
from openai import APIConnectionError, APITimeoutError


def describe_error(exc):
    status = getattr(exc, 'status_code', None)
    if isinstance(exc, APITimeoutError):
        return 'timeout', 'OpenAI timed out. Retry a shorter question or check the connection.'
    if isinstance(exc, APIConnectionError):
        return 'connection', 'Cannot reach OpenAI. Check internet access, proxy, firewall and TLS certificates on the Python server.'
    if status == 401:
        return 'authentication', 'OpenAI rejected the API key. Update OPENAI_API_KEY in the server .env; environment variables take precedence.'
    if status in (403, 404):
        return 'model_access', 'The API project cannot access the configured model. Check OPENAI_MODEL and project permissions.'
    if status == 429:
        if getattr(exc, 'code', None) == 'insufficient_quota':
            return 'quota', 'The API project has no available quota. Check API billing and project spending limits; a ChatGPT subscription does not supply API credit.'
        return 'rate_limit', 'OpenAI rate limit reached. Wait briefly, then retry.'
    if status == 400:
        return 'request', 'The configured model rejected the request. Use OPENAI_MODEL=gpt-5.4-nano and update the Python dependencies.'
    return 'provider', 'OpenAI is temporarily unavailable. Retry later.'
