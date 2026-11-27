#!/usr/bin/env python3
"""Extract page-aware plain text from a paper.

Usage:
  python3 extract_text.py --input <paper.pdf | paper.txt | paper.md>
                          --out-text /app/work/paper.txt
                          --out-pages /app/work/pages.json
                          [--layout layout|raw]   (default: layout)

PDF path (preferred when a real PDF is supplied):
  uses `pdftotext` (poppler, pdf-text-tool) page by page with -layout so every
  paragraph keeps the page it came from. Page count comes from `pdfinfo`.
  If pdftotext/pdfinfo is absent, exits non-zero with a clear message and the
  caller must fall back to the degraded path in SKILL.md (read the PDF by
  whatever tool the harness provides, or record status=partial).
  --layout raw re-extracts with `pdftotext -raw` (no column preservation):
  use it when segment.py warns of a possible two-column layout, then
  compare the two extractions and record which layout was kept in
  sources; never silently mix pages from both.

Plain-text / Markdown input (.txt/.md): read as UTF-8, one logical page
(page 1), form-feed characters split pages if present.

Output:
  paper.txt  -- full text, with a page marker line "[[PAGE n]]" before each page.
  pages.json -- [{"page": 1, "text": "..."}, ...]

Stdlib only. No network. Deterministic.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def extract_pdf(path, out_text, out_pages, layout="layout"):
    pdftotext = shutil.which("pdftotext")
    pdfinfo = shutil.which("pdfinfo")
    if not pdftotext or not pdfinfo:
        missing = [t for t, p in (("pdftotext", pdftotext), ("pdfinfo", pdfinfo)) if not p]
        print(f"ERROR: missing tool(s) for PDF extraction: {', '.join(missing)}. "
              "No Python PDF library is bundled (stdlib only). "
              "Use the harness pdf-text-tool if available, otherwise record "
              "status=partial and note the missing tool.", file=sys.stderr)
        return 2
    info = subprocess.run([pdfinfo, path], capture_output=True, text=True)
    if info.returncode != 0:
        print(f"ERROR: pdfinfo failed on {path}: {info.stderr.strip()}", file=sys.stderr)
        return 3
    pages = 0
    encrypted = False
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":", 1)[1].strip())
        if line.startswith("Encrypted:") and "yes" in line.lower():
            encrypted = True
    if encrypted:
        print("ERROR: PDF is encrypted / permission-restricted; text extraction "
              "refused. Record status=partial, reason=encrypted_pdf, and ask a "
              "human for an unlocked copy. Do not guess content.", file=sys.stderr)
        return 4
    if pages <= 0:
        print("ERROR: pdfinfo reports no pages.", file=sys.stderr)
        return 3
    page_texts = []
    mode_flag = "-layout" if layout == "layout" else "-raw"
    for n in range(1, pages + 1):
        r = subprocess.run([pdftotext, "-f", str(n), "-l", str(n),
                            mode_flag, "-enc", "UTF-8", path, "-"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ERROR: pdftotext failed on page {n}: {r.stderr.strip()}",
                  file=sys.stderr)
            return 3
        page_texts.append({"page": n, "text": r.stdout})
    write_outputs(page_texts, out_text, out_pages)
    total_chars = sum(len(p["text"]) for p in page_texts)
    print(f"extracted {pages} page(s), {total_chars} chars from {path}")
    if total_chars < 200:
        print("WARNING: very little text extracted (<200 chars). The PDF may be "
              "a scanned image (needs ocr-tool) or mostly figures. Record "
              "status=partial and the low-text warning; do not invent content.",
              file=sys.stderr)
    return 0


def extract_text_file(path, out_text, out_pages):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    chunks = raw.split("\f")
    page_texts = [{"page": i + 1, "text": c} for i, c in enumerate(chunks)]
    write_outputs(page_texts, out_text, out_pages)
    print(f"read text file {path}: {len(page_texts)} page(s), "
          f"{len(raw)} chars")
    return 0


def write_outputs(page_texts, out_text, out_pages):
    for d in (os.path.dirname(out_text), os.path.dirname(out_pages)):
        if d:
            os.makedirs(d, exist_ok=True)
    with open(out_text, "w", encoding="utf-8") as f:
        for p in page_texts:
            f.write(f"\n[[PAGE {p['page']}]]\n")
            f.write(p["text"])
            if not p["text"].endswith("\n"):
                f.write("\n")
    with open(out_pages, "w", encoding="utf-8") as f:
        json.dump(page_texts, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-text", required=True)
    ap.add_argument("--out-pages", required=True)
    ap.add_argument("--layout", choices=["layout", "raw"], default="layout",
                    help="pdftotext mode: layout (default) or raw "
                         "(two-column fallback, see SKILL.md)")
    args = ap.parse_args()
    if not os.path.exists(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1
    ext = os.path.splitext(args.input)[1].lower()
    if ext == ".pdf":
        return extract_pdf(args.input, args.out_text, args.out_pages,
                           layout=args.layout)
    if ext in (".txt", ".md", ".markdown"):
        return extract_text_file(args.input, args.out_text, args.out_pages)
    print(f"ERROR: unsupported input type '{ext}'. Supported: .pdf, .txt, .md",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
