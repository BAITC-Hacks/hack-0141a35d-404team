from __future__ import annotations
import argparse, json, sys
from src.aml_graph.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AML graph analysis pipeline")
    parser.add_argument("--input", default="entryset"); parser.add_argument("--output", default="outputset")
    args = parser.parse_args()
    try: result = run_pipeline(args.input, args.output)
    except Exception as exc: print(f"Pipeline failed: {exc}", file=sys.stderr); return 1
    print(json.dumps({"report": result["report"], "outputs": {k: str(v) for k, v in result["paths"].items()}}, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())

