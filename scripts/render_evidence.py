"""Export real saved notebook outputs into readable HTML evidence pages."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re

import nbformat

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "submission" / "evidence"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
STYLE = """
body{margin:0;background:#eef2f6;color:#172b43;font-family:Segoe UI,Arial,sans-serif}
main{max-width:1080px;margin:24px auto;padding:24px;background:white;border-radius:10px}
h1{font-size:26px;margin:0 0 12px}h2{font-size:18px;margin-top:24px}
p{color:#516276;line-height:1.6}pre{font:14px/1.5 Consolas,monospace;white-space:pre-wrap;
overflow-wrap:anywhere;background:#f5f7fa;border:1px solid #dce3eb;padding:14px;border-radius:6px}
.provenance{font-size:12px}code{overflow-wrap:anywhere}
"""


def page(title, body):
    return f'<!doctype html><html lang="vi"><meta charset="utf-8"><title>{html.escape(title)}</title><style>{STYLE}</style><main><h1>{html.escape(title)}</h1>{body}</main></html>'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for source in sorted((ROOT / "notebooks").glob("0[5-8]*.ipynb")):
        notebook = nbformat.read(source, as_version=4)
        heading = "Notebook output"
        parts, plain = [], []
        for index, cell in enumerate(notebook.cells, 1):
            if cell.cell_type == "markdown":
                headings = re.findall(r"^#{1,3} (.+)$", cell.source, flags=re.M)
                if headings:
                    heading = headings[-1]
                continue
            texts = []
            for output in cell.get("outputs", []):
                if output.output_type == "error":
                    raise RuntimeError(f"{source.name} contains an error: {output.ename}")
                if output.output_type == "stream":
                    texts.append(output.text)
                elif "text/plain" in output.get("data", {}):
                    texts.append(output.data["text/plain"])
            if texts:
                value = ANSI.sub("", "\n".join(texts))
                label = f"Cell {index} · {heading}"
                parts.append(f"<h2>{html.escape(label)}</h2><pre>{html.escape(value)}</pre>")
                plain.extend([label, value, ""])
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        provenance = (f'<p>Output thật từ <code>{html.escape(source.name)}</code>, được xuất sau khi chạy notebook. '
                      'Đây là trang bằng chứng được render, không phải ảnh giao diện Jupyter.</p>'
                      f'<p class="provenance">SHA-256: <code>{digest}</code></p>')
        stem = f"nb{source.name[:2].lstrip('0')}"
        (OUT / f"{stem}.html").write_text(page(source.stem, provenance + "".join(parts)), encoding="utf-8")
        (OUT / f"{stem}_outputs.txt").write_text("\n".join(plain), encoding="utf-8")
    for name, logs in [("validation", ["tests_clean", "verify_lite_clean", "dependency_check"]),
                       ("bonus", ["bonus_demo_clean"])]:
        parts = []
        for log in logs:
            path = OUT / f"{log}.txt"
            if not path.exists():
                continue
            value = ANSI.sub("", path.read_text(encoding="utf-8"))
            if name == "bonus" and "QUERY 1:" in value:
                blocks = re.split(r"(?:^|\n)QUERY (\d+): ([^\n]+)\n", value)
                compact = []
                for i in range(1, len(blocks), 3):
                    number, question, block = blocks[i:i+3]
                    context, _ = json.JSONDecoder().raw_decode(block.lstrip())
                    compact.extend([f"QUERY {number}: {question}",
                                    f"user_id={context['user_id']}  mode={context['mode']}",
                                    json.dumps(context['features'], ensure_ascii=False, indent=2)])
                    compact.extend(f"memory {j}: {m['text']}"
                                   for j, m in enumerate(context['memories'], 1))
                    compact.append("")
                value = ("Selected fields from actual JSON contexts; full stdout in bonus_demo_clean.txt\n\n"
                         + "\n".join(compact) + "\n" + value[value.rfind("PASS:"):])
            parts.append(f"<h2>{html.escape(path.name)}</h2><pre>{html.escape(value)}</pre>")
        (OUT / f"{name}.html").write_text(page(name, "".join(parts)), encoding="utf-8")
    print("Exported real notebook and validation outputs to submission/evidence")


if __name__ == "__main__":
    main()
