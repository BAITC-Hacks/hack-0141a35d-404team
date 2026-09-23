# Analyst assistant: local memory and retrieval

## Implemented design

1. Python computes the graph, behavioural signals and fixed CSV exports once per analysis. A SHA-256 dataset ID covers the three parquet files and resulting CSVs. Identical inputs/results can reopen the same conversation; changed data starts a separate context.
2. The browser holds only a random conversation ID in localStorage, keyed by dataset ID. Messages are stored in `.local/chat.sqlite3`, never in Git. Server memory holds the current analysis; restart requires running analysis again before chatting.
3. Each user turn saves its selected gid alongside the message. The next prompt gets up to eight recent messages, roughly 8,000 characters, with selection context. Full older history stays in SQLite; a bounded history-search tool returns at most ten 600-character excerpts when requested. The UI loads the most recent 100 messages. Clearing memory deletes that conversation locally.
4. The server parses generated CSV bytes locally. It provides allowlisted queries for exact nodes (maximum five gids), top rows, clusters, common recipients, behavioural evidence, resilience and older messages. Each result is limited to ten rows and 8,000 characters. No SQL, filesystem path, Python code or arbitrary expression comes from the model.
5. A question makes at most five Responses API calls, four tool reads, with a 1,400-token output cap per call. Initial grounding is only the selected CSV row or three top rows. Only bounded recent dialogue and results leave the machine. No entire CSV upload, embeddings, vector database, web search or paid file-storage service is used.
6. `store=False` avoids saving Responses application state; OpenAI's separate API retention policies still apply. This does not mean requests never leave the machine. The UI makes data egress explicit. The key is read only by Python from `OPENAI_API_KEY`; it is never returned to React.
7. Text is rendered as plain React text. Account references `[gid:...]` become clickable only when the ID exists in locally retrieved evidence. Conversation excerpts and CSV cells are data, not instructions. Assistant output remains a review hypothesis and does not change scores or exports.

## Model and API

Default: `gpt-5.4-nano`, with reasoning disabled for lightweight evidence explanation. Override `OPENAI_MODEL` only with a Responses model supporting the same tools/reasoning parameters. Model access and quota depend on the API account.

- [GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano): lightweight model with function calling.
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling): structured local tool requests and `function_call_output` responses.
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state): manually supplied history with `store=False`.

## Failure handling and scope

Missing key disables Send with setup instructions. Model/network/quota errors preserve the existing conversation and allow retry. Failed turns do not commit partial memory. Stale datasets are rejected. Requests are serialized locally to avoid conflicting writes. Clear is blocked during an active answer. This remains a single-analyst, loopback application; the database is local plaintext, so do not expose the API as a multi-user service without authentication, access controls and encryption.

Configuration is read on demand from server environment variables, then UTF-8 `.env` (including a Windows BOM). The example is a template, never a credential source. An explicitly empty environment key disables AI. Editing `.env` needs no server restart; open chat refreshes configuration status every ten seconds. Only `configured` and model name leave `/api/chat/status`, never credentials. **Check connection** explicitly sends a tiny test message, with no graph data, through `POST /api/chat/check`; it consumes API credit. Authentication, model access, quota, rate limit, connection and timeout failures return safe error codes, not raw provider bodies. Follow the [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart) for server-side API-key setup. Commit only the blank example. If a real key ever enters Git history, rotate it; changing the current file is not enough.

Tests use a mocked OpenAI client; a live response requires configuring a valid key. No fabricated answer is substituted when the API is unavailable. Full transcripts persist until cleared; the model does not automatically see every old message, and history retrieval is relevance-based rather than guaranteed perfect recall.
