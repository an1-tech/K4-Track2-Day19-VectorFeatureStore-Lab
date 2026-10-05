"""Validate tests, smoke test and bonus in a fresh venv and isolated source copy."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".validation" / "clean_workspace"
EVIDENCE = ROOT / "submission" / "evidence"
# JupyterLab ships long asset names; keep Windows site-packages near the drive root.
VENV = ROOT.parent / ".day19-clean-venv" if os.name == "nt" else WORK / ".venv"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    ignored = shutil.ignore_patterns("__pycache__", "data", "*.db", "*.db-*", ".venv")
    for name in ("app", "bonus", "scripts", "tests"):
        shutil.copytree(ROOT / name, WORK / name, ignore=ignored, dirs_exist_ok=True)
    shutil.copy2(ROOT / "pyproject.toml", WORK / "pyproject.toml")
    # Exact installed public package versions; no private index URLs or credentials.
    packages = sorted({f"{d.metadata['Name']}=={d.version}"
                       for d in importlib.metadata.distributions()
                       if d.metadata["Name"].lower() not in {"pip", "setuptools"}})
    lock = EVIDENCE / "requirements-windows-py312.lock.txt"
    lock.write_text("# Snapshot of the validated Windows/Python 3.12 Lite environment.\n"
                    + "\n".join(packages) + "\n", encoding="utf-8")
    if not VENV.exists():
        venv.EnvBuilder(with_pip=True).create(VENV)
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = {**os.environ, "QDRANT_MODE": "memory", "EMBEDDING_BACKEND": "fastembed",
           "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    steps = [
        ("clean_install", ["-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-r", str(lock)]),
        ("dependency_check", ["-m", "pip", "check"]),
        ("seed_corpus", ["scripts/seed_corpus.py"]),
        ("gen_agent_queries", ["scripts/gen_agent_queries.py"]),
        ("gen_spend", ["scripts/gen_spend.py"]),
        ("tests_clean", ["-m", "pytest", "-q"]),
        ("verify_lite_clean", ["scripts/verify_lite.py"]),
        ("bonus_demo_clean", ["bonus/demo.py"]),
    ]
    results = {"python": platform.python_version(), "platform": platform.platform(),
               "scope": "fresh virtual environment and project copy on the same Windows machine; embedding cache reused",
               "steps": []}
    for name, args in steps:
        print(f"RUN {name}", flush=True)
        with (EVIDENCE / f"{name}.txt").open("w", encoding="utf-8") as log:
            completed = subprocess.run([str(python), *args], cwd=WORK, env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
        results["steps"].append({"name": name, "exit_code": completed.returncode})
        (EVIDENCE / "validation.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: exit={completed.returncode}", flush=True)
        if completed.returncode:
            print((EVIDENCE / f"{name}.txt").read_text(encoding="utf-8")[-8000:])
            raise SystemExit(completed.returncode)
    print("PASS: isolated clean-environment validation", flush=True)


if __name__ == "__main__":
    main()
