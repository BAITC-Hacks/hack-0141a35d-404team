"""Local API and production React host; analytics remain in src/aml_graph."""
from pathlib import Path
from threading import Lock
from tempfile import TemporaryDirectory
import json
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from src.aml_graph.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="AML Graph", docs_url="/api/docs", openapi_url="/api/openapi.json")
lock = Lock()
state = {"result": None, "files": {}}

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
        state.update(result=payload, files=files)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
