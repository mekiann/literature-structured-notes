# Literature Structured Notes — Usage & Method (README)

Skill: `literature-structured-notes` (`SKILL.md`). Challenge:
product-arena-06-6d8cf72b — 文献总结与结构化笔记. Scoring: human review
only. No GitHub account is available, so no `GITHUB_URL.txt` is included
and the 5-point GitHub bonus is skipped by design.

## What it does

Turns one real research paper into chapter-aligned, verifiable, reusable
notes:

1. **Extract** the paper's text page by page (`scripts/extract_text.py`,
   `pdftotext`/`pdfinfo`).
2. **Segment** the text into the paper's own sections, in its own order
   (`scripts/segment.py`) — no generic summary template is imposed.
3. **Build a skeleton** (`scripts/build_notes.py`): a fixed-field paper
   card, one section note per detected section, extractive candidates and
   term candidates, plus a search index.
4. **Fill by reading**: the agent reads the sections in order and fills
   each slot only from the cited paragraph, attaching a source anchor
   (`section | paragraph id | page | figure/table`) to every key note.
   Unreported stays `NOT_REPORTED`; conflicts are recorded, never resolved
   silently.
5. **Validate** (`scripts/validate_notes.py`): rejects empty fields,
   unanchored filled claims, section-coverage mismatch, duplicate terms,
   and anchors pointing at non-existent paragraphs/pages.
6. **Deliver** to `/app/output`: `notes.json`, `notes.md`, `index.json`,
   `result.json` (with `case_id`, `status`, `sources`,
   `uncertain_items`, `change_record`).

The four problems from task.md §1 are addressed directly: 对得上
(sections follow the paper's headings and order), 留得住 (paper card
records question, data, method conditions, findings, limitations **and
premises**), 找得回 (anchor per key note), 用得上 (JSON + Markdown +
search index, fixed fields for cross-paper comparison).

## How to run it on a case (exact steps)

```bash
# 0. Discover the input — inspect /input/case.json, find the paper file,
#    record case_id. Never assume a path from a label.
cat /input/case.json
ls <directory the case points to>

# 1. Extract (work under /app/work)
python3 scripts/extract_text.py --input <paper.pdf|paper.txt|paper.md> \
  --out-text /app/work/paper.txt --out-pages /app/work/pages.json

# 2. Segment
python3 scripts/segment.py --pages /app/work/pages.json \
  --out /app/work/sections.json

# 3. Build the skeleton (save this partial deliverable immediately)
python3 scripts/build_notes.py --sections /app/work/sections.json \
  --case-id <case_id> --out-json /app/work/notes.json \
  --out-md /app/work/notes.md --out-index /app/work/index.json

# 4. Fill notes.json / notes.md by reading sections in order, with anchors
#    (see SKILL.md step 4 and templates/field-dictionary.md). Leave anything
#    unsupported as NOT_REPORTED.

# 5. Validate — must exit 0 before delivery
python3 scripts/validate_notes.py --notes /app/work/notes.json \
  --sections /app/work/sections.json

# 6. Deliver
mkdir -p /app/output
cp /app/work/notes.json /app/work/notes.md /app/work/index.json /app/output/
# write /app/output/result.json (case_id, status, paper_card, section_notes,
# knowledge_points, sources, uncertain_items, change_record)
```

All paths in `scripts/` are relative to the Skill directory; at evaluation
time the Skill is installed under `/skills/weekly-skill`, so invoke the
scripts by their installed path.

## Dependencies and fallbacks (verified on the build VM, 2026-11-26)

| Capability | On build VM | Evaluation image |
|---|---|---|
| Python 3 (scripts are stdlib-only) | 3.12.3 | expected; no third-party libs needed |
| `pdftotext` / `pdfinfo` (poppler) | 24.02.0, present | declared as `pdf-text-tool`; if absent, fall back to the harness tool, a supplied `.txt` copy, or record `partial` |
| Node | 24.22.1 | not used by this Skill |
| LibreOffice (preview rendering only) | 24.2.7.2 | optional; text/JSON outputs unaffected if absent |
| LaTeX (`pdflatex`/`xelatex`), pandoc, tesseract, ghostscript | **absent** | not required, not used |
| Python PDF libs (`PyPDF2`/`pdfplumber`/`fitz`) | **absent** | not required, not used |

No network, no `pip install`, no API keys. Scripts are deterministic:
same input → same skeleton and same validation result.

## Files in this submission

| File | Role |
|---|---|
| `SKILL.md` | Skill本体: frontmatter, when-to-use, 6-step workflow, fallbacks, failure handling, self-check |
| `README.md` | This usage/method doc |
| `scripts/extract_text.py` | Page-aware text extraction (PDF via pdftotext; .txt/.md direct) |
| `scripts/segment.py` | Heading detection (EN+ZH, numbered/unnumbered), paragraph ids + pages, figure/table mentions |
| `scripts/build_notes.py` | Notes skeleton, paper card, extractive + term candidates, search index |
| `scripts/validate_notes.py` | 9 error checks (E1–E9) + 2 warnings (W1–W2) on notes.json |
| `templates/paper-card.json` | JSON schema for notes.json / result.json (template, not an answer) |
| `templates/field-dictionary.md` | Field definitions, anchor format, dedup/merge rules, machine-vs-human checks |
| `examples/example-case.json` | Minimal call example input (labelled EXAMPLE, invented sample) |
| `examples/example-notes.md` | EXAMPLE output produced by the local test run (see below) |

## Local test (builder's own sample — NOT an official case)

Sample input: an invented 1-page paper written by the builder for
testing only, "SAMPLE: Starch-based hydrogel..." (see
`examples/example-case.json`; the paper text is embedded in the test run
below, not an official case file). It has an Abstract, Introduction,
Methods, Results, Discussion and Conclusion, one `Full Name (ABBR)`
definition, numbers with units, and a stated limitation — enough to
exercise heading detection, anchor assignment, term extraction and
validation.

Commands run (2026-11-26, this VM):

```bash
cd /tmp/litnotes-test
python3 <skill>/scripts/extract_text.py --input sample-paper.pdf \
  --out-text paper.txt --out-pages pages.json
python3 <skill>/scripts/segment.py --pages pages.json --out sections.json
python3 <skill>/scripts/build_notes.py --sections sections.json \
  --case-id SAMPLE-001 --out-json notes.json --out-md notes.md \
  --out-index index.json
python3 <skill>/scripts/validate_notes.py --notes notes.json \
  --sections sections.json
```

Outcome: PDF extraction via `pdftotext` succeeded (1 page, 2,069 chars);
segmentation found all 6 headed sections in order (plus a front-matter
section), with paragraph ids and pages; skeleton built
with 7 section notes, 1 term candidate (starch-based hydrogel / SH),
and an 8-entry index; validator passed on the skeleton (exit 0, warnings
only for NOT_REPORTED fields, as designed). The filled EXAMPLE output in
`examples/example-notes.md` was then produced by filling the skeleton
from the sample text with anchors and re-validating (exit 0, 0 errors).

## Limits (honest)

- Heading detection is rule-based: papers with no recognisable headings
  yield a single `unsectioned` section and chapter alignment cannot be
  verified (recorded, not hidden).
- Two-column PDFs can scramble reading order under `-layout`; the Skill
  flags the risk but does not repair column order automatically.
- Scanned-image PDFs yield almost no text; the Skill reports `partial`
  and hands over to OCR instead of inventing content.
- Extractive candidates are heuristic pointers (numbers / cue words);
  only the agent's paragraph-by-paragraph reading turns them into
  findings — the validator enforces the anchor, not the truth of the
  claim. Correctness of an anchor's *target* (does the cited paragraph
  really state the claim?) is a human/agent judgement, listed as such in
  the field dictionary.
- No `output_contract` fields were published in the challenge files, so
  `result.json` carries the §3 fields (input id, main result,
  evidence/anchors, status, uncertainty); if a case's `task.md` names
  extra fields, they are added verbatim.
- The Skill handles one paper per case, matching the 3 fixed cases; for
  multi-paper comparison, run it once per paper — the fixed paper-card
  fields make the cards comparable side by side.
