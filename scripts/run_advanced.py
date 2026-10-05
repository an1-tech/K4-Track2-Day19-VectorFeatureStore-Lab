"""Execute NB5-NB8 with the active Python environment (Windows/macOS/Linux)."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import jupytext
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("05", "06", "07", "08"))
    args = parser.parse_args()
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    os.environ.update(QDRANT_MODE="memory", EMBEDDING_BACKEND="fastembed", PYTHONUTF8="1")
    core = {p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "notebooks").glob("0[1-4]*.ipynb")}
    names = [p for p in sorted((ROOT / "notebooks").glob("0[5-8]*.py"))
             if args.only is None or p.name.startswith(args.only)]
    for source in names:
        print(f"RUN {source.name}", flush=True)
        notebook = jupytext.read(source)
        notebook.metadata["kernelspec"] = {
            "name": "python3", "display_name": "Python 3 (ipykernel)", "language": "python"}
        target = source.with_suffix(".ipynb")
        try:
            NotebookClient(notebook, timeout=900, kernel_name="python3",
                           resources={"metadata": {"path": str(source.parent)}}).execute()
        finally:
            nbformat.write(notebook, target)
        for cell in notebook.cells:
            for output in cell.get("outputs", []):
                if output.output_type == "stream":
                    print(output.text, end="", flush=True)
        print(f"PASS {target.name}", flush=True)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in core.items()), \
        "Core notebooks unexpectedly changed"


if __name__ == "__main__":
    main()
