"""Local API and production React host; analytics remain in src/aml_graph."""
from pathlib import Path
from threading import Lock
from tempfile import TemporaryDirectory
import json
import time
import hashlib
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import OpenAIError
from src.aml_graph.pipeline import run_pipeline
from src.aml_graph.patterns import resilience
from src.aml_graph.assistant import Memory, answer
from src.aml_graph.config import settings

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="AML Graph", docs_url="/api/docs", openapi_url="/api/openapi.json")
lock = Lock()
state = {"result": None, "files": {}, "snapshot": None}
chat_lock = Lock()

def memory():
    return Memory(ROOT / '.local/chat.sqlite3')

def snapshot(dataset_id):
    with lock:
        result, files, public = state['snapshot'], state['files'], state['result']
    if result is None:
        raise HTTPException(409, 'Run analysis first')
    if public['dataset_id'] != dataset_id:
        raise HTTPException(409, 'Dataset changed. Run analysis again.')
    return result, files, public

class AnalysisRequest(BaseModel):
    input_dir: str = "entryset"

@app.get("/api/health")
def health():
    return {"status": "ok"}

def serialize(result):
    nodes = result["metrics"].copy()
    nodes["gid"] = nodes["gid"].map(str)
    return {
        "report": result["report"],
        "nodes": json.loads(nodes.to_json(orient="records")),
        "clusters": json.loads(result["clusters"].to_json(orient="records")),
        "edges": [{"src": str(u), "dst": str(v), **d} for u, v, d in result["graph"].edges(data=True)],
        "insights_summary": result['insights']['summary'],
    }

@app.post("/api/analyze")
def analyze(request: AnalysisRequest):
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Analysis is already running")
    try:
        directory = Path(request.input_dir)
        if not directory.is_absolute():
            directory = ROOT / directory
        started = time.perf_counter()
        with TemporaryDirectory(prefix="aml-analysis-") as output:
            result = run_pipeline(directory, output)
            payload = serialize(result)
            payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            files = {p.name: p.read_bytes() for p in result["paths"].values()}
            digest = hashlib.sha256()
            for name in ['nodes', 'edges', 'transactions']:
                digest.update((directory / (name + '.parquet')).read_bytes())
            for name in sorted(files): digest.update(files[name])
            payload['dataset_id'] = digest.hexdigest()
        state.update(result=payload, files=files, snapshot=result)
        return payload
    except (ValueError, FileNotFoundError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Analysis failed. Check the input parquet schemas.") from exc
    finally:
        lock.release()

@app.get("/api/exports/{name}")
def download(name: str):
    if name not in {"nodes_roles.csv", "clusters.csv", "top_nodes.csv"}:
        raise HTTPException(404, "Unknown export")
    with lock:
        content = state["files"].get(name)
    if content is None:
        raise HTTPException(404, "Run analysis first")
    return Response(content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})

@app.get("/")
def index():
    page = ROOT / "frontend/dist/index.html"
    if not page.exists():
        raise HTTPException(503, "Build the frontend: npm --prefix frontend run build")
    return FileResponse(page)

app.mount("/assets", StaticFiles(directory=ROOT / "frontend/dist/assets", check_dir=False), name="assets")

@app.get('/api/nodes/{gid}/card')
def node_card(gid: str, dataset_id: str):
    result, _, public = snapshot(dataset_id)
    node = next((n for n in public['nodes'] if n['gid'] == gid), None)
    if node is None: raise HTTPException(404, 'Account not found')
    return {'node': node, 'insights': result['insights']['nodes'][gid]}

class ResilienceRequest(BaseModel):
    dataset_id: str
    n: int = Field(default=5, ge=0, le=100)

@app.post('/api/resilience')
def simulate(request: ResilienceRequest):
    result, _, _ = snapshot(request.dataset_id)
    return resilience(result['graph'], result['metrics'], request.n)

@app.get('/api/chat/status')
def chat_status():
    config = settings()
    return {'configured': bool(config['api_key']), 'model': config['model']}

class ChatRequest(BaseModel):
    dataset_id: str
    session_id: str = Field(pattern=r'^[a-zA-Z0-9-]{1,80}$')
    message: str = Field(min_length=1, max_length=2000)
    selected_gid: str | None = Field(default=None, pattern=r'^\d{1,20}$')
    language: Literal['en', 'ru'] = 'en'

@app.get('/api/chat/history/{session_id}')
def chat_history(session_id: str, dataset_id: str):
    snapshot(dataset_id)
    try:
        messages = memory().read(session_id, dataset_id)
        return {'messages': messages[-100:], 'total': len(messages)}
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc

@app.delete('/api/chat/history/{session_id}')
def clear_chat(session_id: str):
    if not chat_lock.acquire(blocking=False): raise HTTPException(409, 'Wait for the current answer')
    try: memory().clear(session_id)
    finally: chat_lock.release()
    return {'cleared': True}

@app.post('/api/chat')
def chat(request: ChatRequest):
    if not settings()['api_key']:
        raise HTTPException(503, 'Set OPENAI_API_KEY in the server .env file, then reopen the chat.')
    result, files, public = snapshot(request.dataset_id)
    if request.selected_gid and not any(n['gid'] == request.selected_gid for n in public['nodes']):
        raise HTTPException(400, 'Selected account not found')
    if not request.message.strip(): raise HTTPException(400, 'Message is empty')
    if not chat_lock.acquire(blocking=False): raise HTTPException(409, 'Another answer is in progress')
    try:
        store = memory()
        history = store.read(request.session_id, request.dataset_id)
        response = answer(result, files, history, request.message, request.selected_gid, request.language)
        messages = history + [{'role': 'user', 'content': request.message, 'selected_gid': request.selected_gid},
                              {'role': 'assistant', 'content': response['answer'], 'gids': response['gids']}]
        store.save(request.session_id, request.dataset_id, messages)
        return response
    except OpenAIError as exc:
        raise HTTPException(502, 'OpenAI request failed. Check server key, model access, quota or connection.') from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        chat_lock.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
