#!/usr/bin/env python3
"""Segment extracted paper text into the paper's OWN sections.

Usage:
  python3 segment.py --pages /app/work/pages.json --out /app/work/sections.json

What it does (deterministic, rule-based, stdlib only):
  1. Joins page texts in page order, splits into paragraphs (blank-line
     separated; also splits long single-line-wrapped blocks conservatively).
  2. Detects section headings in the paper's own wording, English and
     Chinese, numbered ("1 Introduction", "3.2 Methods", "2: Methods")
     and unnumbered ("Abstract", "摘要", "Results and Discussion", "结论",
     "Experimental Setup", "Data Availability Statement", "Future Work").
     A trailing full stop on a short known heading ("Introduction.") is
     tolerated; a body sentence such as "3.5 g of sample was added." is
     not promoted to a heading.
     Headings are NEVER invented: a section exists only if a heading line
     is found. Text before the first heading goes to section "front-matter".
  3. Assigns every paragraph an id "<section-order>.<para-n>" and the page
     it came from, so every later note can anchor to section/paragraph/page.
  4. Records figure/table mentions per paragraph (Fig./Figure/Table/图/表
     + number) so anchors can cite them.
  5. Flags warnings: no headings found, duplicate heading titles,
     two-column reading-order risk (pages whose lines are mostly short
     fragments are flagged; column order is NOT repaired -- the agent
     checks a rendered page or re-extracts with -raw, see SKILL.md).
     A page with many short lines usually means `pdftotext -layout`
     split two columns into interleaved fragments.

Output sections.json:
  {"sections": [{"order": 1, "id": "s1", "title": "Introduction",
                 "level": 1, "page_start": 1, "page_end": 2,
                 "paragraphs": [{"id": "s1.p1", "page": 1, "text": "...",
                                  "figures": ["Figure 1"], "tables": []}]}],
   "warnings": [...], "heading_lines_found": n, "total_paragraphs": n}

A section with no detected heading is NOT silently merged into a generic
"Summary" -- it stays under its real heading or under "front-matter" /
"unsectioned" so the notes skeleton follows the paper, not a template.
"""
import argparse
import json
import re
import sys

# Heading keywords, longest first. Case-insensitive for English.
KNOWN = [
    "abstract", "摘要",
    "introduction", "引言", "绪论", "背景",
    "related works", "related work", "相关工作", "文献综述",
    "background and motivation",
    "materials and methods", "methods", "methodology", "method",
    "材料与方法", "实验方法", "方法", "实验",
    "experimental setup", "experimental section", "experimental",
    "sample preparation", "materials", "material",
    "characterization",
    "statistical analysis", "research design", "research methods",
    "study area", "case study", "theoretical analysis",
    "results and discussion", "results", "结果与讨论", "结果",
    "experimental results", "numerical results",
    "discussion", "讨论",
    "conclusion", "conclusions", "concluding remarks",
    "结论", "总结", "展望",
    "future work", "future perspectives",
    "limitations", "limitation", "局限性", "不足",
    "references", "参考文献",
    "acknowledgements", "acknowledgments", "致谢",
    "appendix", "附录",
    "supplementary information", "supporting information",
    "data availability statement", "data availability", "数据可用性",
    "author contributions", "funding", "ethics",
    "competing interests", "conflict of interest",
    "nomenclature", "abbreviations",
    "theory", "理论", "model", "模型",
]
KNOWN_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+)?(" + "|".join(re.escape(k) for k in KNOWN) + r")"
    r"(?:\s*[:：\-–—]\s*(.*))?$", re.IGNORECASE)

NUMBERED_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)*)\.?[:]?\s+([A-Z\u4e00-\u9fff][^\n]{1,80})$")

FIG_RE = re.compile(r"\b(?:Fig\.?|Figure)\s*(\d+[A-Za-z]?)", re.IGNORECASE)
FIG_ZH_RE = re.compile(r"图\s*(\d+[A-Za-z]?)")
TAB_RE = re.compile(r"\bTable\s*(\d+[A-Za-z]?)", re.IGNORECASE)
TAB_ZH_RE = re.compile(r"表\s*(\d+[A-Za-z]?)")


def _match_heading(s):
    """Match one candidate line against the known/numbered patterns."""
    m = KNOWN_RE.match(s)
    if m:
        title = (m.group(1) + (" " + m.group(2) if m.group(2) else "")).strip()
        return title
    m = NUMBERED_RE.match(s)
    if m:
        # Numbered heading only if the title part has no sentence-ending
        # period inside and is short; avoids swallowing body sentences
        # such as "3.5 g of sample was added."
        title = m.group(2).strip()
        if len(title.split()) <= 8 and not re.search(r"[.;。；]$", title):
            return f"{m.group(1)} {title}"
    return None


def is_heading(line):
    s = line.strip()
    if not s or len(s) > 90:
        return None
    if s.endswith(".") and not re.match(r"^\s*\d", s):
        # Ordinary sentence, not a heading -- unless it is a short known
        # heading with a trailing full stop ("Introduction.").
        if len(s.split()) > 6:
            return None
    title = _match_heading(s)
    if title is not None:
        return title
    if s.endswith(".") and len(s.split()) <= 8:
        # Retry without the trailing stop: "1. Introduction." is a
        # heading, but "3.5 g of sample was added." must stay body text --
        # it only counts if the stripped line matches a known heading.
        return _match_heading(s[:-1].rstrip())
    return None


def split_paragraphs(page_text):
    # Blank-line split; also treat a line that looks like a lone heading
    # as its own paragraph so it is not glued to body text.
    paras, buf = [], []
    for raw in page_text.splitlines():
        line = raw.strip()
        if not line:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        if is_heading(line):
            if buf:
                paras.append(" ".join(buf))
                buf = []
            paras.append(line)
            continue
        buf.append(line)
    if buf:
        paras.append(" ".join(buf))
    return [p for p in paras if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.pages, encoding="utf-8") as f:
        pages = json.load(f)

    sections = []
    warnings = []
    cur = {"order": 0, "id": "s0", "title": "front-matter", "level": 0,
           "page_start": pages[0]["page"] if pages else 1, "page_end": None,
           "paragraphs": []}
    sections.append(cur)
    total_paras = 0
    heading_lines = 0
    for pg in pages:
        for para_text in split_paragraphs(pg["text"]):
            total_paras += 1
            title = is_heading(para_text)
            if title is not None and not (
                    len(para_text.split()) > 12 and cur["paragraphs"]):
                # Start a new section. Guard: a heading-like line deep in
                # body text with many words is treated as body, not heading.
                heading_lines += 1
                level = 1
                mnum = re.match(r"^\s*(\d+(?:\.\d+)*)", title)
                if mnum:
                    level = mnum.group(1).count(".") + 1
                cur["page_end"] = pg["page"]
                cur = {"order": len(sections), "id": f"s{len(sections)}",
                       "title": title, "level": level,
                       "page_start": pg["page"], "page_end": pg["page"],
                       "paragraphs": []}
                sections.append(cur)
                continue
            figs = [f"Figure {n}" for n in FIG_RE.findall(para_text)]
            figs += [f"图 {n}" for n in FIG_ZH_RE.findall(para_text)]
            tabs = [f"Table {n}" for n in TAB_RE.findall(para_text)]
            tabs += [f"表 {n}" for n in TAB_ZH_RE.findall(para_text)]
            pid = f"{cur['id']}.p{len(cur['paragraphs']) + 1}"
            cur["paragraphs"].append(
                {"id": pid, "page": pg["page"], "text": para_text,
                 "figures": sorted(set(figs)), "tables": sorted(set(tabs))})
            cur["page_end"] = pg["page"]
    # Drop an empty front-matter section; keep it if it holds the title/abstract.
    if not sections[0]["paragraphs"] and len(sections) > 1:
        sections.pop(0)
        for i, s in enumerate(sections):
            s["order"] = i
            s["id"] = f"s{i}"
            for j, p in enumerate(s["paragraphs"], 1):
                p["id"] = f"{s['id']}.p{j}"
    if heading_lines == 0:
        warnings.append("no section headings detected: notes will use a "
                        "single 'unsectioned' section; chapter alignment "
                        "cannot be verified -- record as a limit.")
    titles = [s["title"].lower() for s in sections]
    if len(titles) != len(set(titles)):
        warnings.append("duplicate section titles detected; section ids "
                        "(s0, s1, ...) disambiguate them -- use ids in anchors.")
    if total_paras == 0:
        warnings.append("no paragraphs found in extracted text.")
    # Two-column suspicion: a page of mostly short lines usually means
    # -layout interleaved two columns. Heuristic only -- the agent must
    # verify against a rendered page or re-extract with -raw (SKILL.md).
    suspect_pages = []
    for pg in pages:
        lines = [ln for ln in pg["text"].splitlines() if ln.strip()]
        if len(lines) >= 20:
            short = [ln for ln in lines if len(ln.strip()) < 45]
            if len(short) / len(lines) > 0.6:
                suspect_pages.append(pg["page"])
    if suspect_pages:
        warnings.append(
            "possible two-column layout on page(s) "
            f"{', '.join(str(p) for p in suspect_pages)}: most lines are "
            "short fragments, so reading order may be scrambled. Verify "
            "against a rendered page if pdf-render-tool is available, or "
            "re-extract with extract_text.py --layout raw and compare; "
            "record which layout was used in sources.")
    out = {"sections": sections, "warnings": warnings,
           "heading_lines_found": heading_lines,
           "total_paragraphs": total_paras}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"segmented into {len(sections)} section(s), "
          f"{total_paras} paragraph(s), {heading_lines} heading line(s)")
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
