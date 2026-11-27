# Literature Structured Notes — Usage & Method (README)

Skill: `literature-structured-notes` (`SKILL.md`). Challenge:
product-arena-06-6d8cf72b — 文献总结与结构化笔记. Scoring: human review
only. Public repo: https://github.com/mekiann/literature-structured-notes
(`GITHUB_URL.txt` in the submission root, second line `SKILL.md`).
Version: v1.1 (see `CHANGELOG.md`).

## What it does

Turns one real research paper into chapter-aligned, verifiable, reusable
notes:

1. **Extract** the paper's text page by page (`scripts/extract_text.py`,
   `pdftotext`/`pdfinfo`; `--layout raw` fallback for two-column PDFs).
2. **Segment** the text into the paper's own sections, in its own order
   (`scripts/segment.py`) — no generic summary template is imposed.
3. **Build a skeleton** (`scripts/build_notes.py`): a fixed-field paper
   card, one section note per detected section, extractive candidates and
   term candidates, a figure/table register, plus a search index.
4. **Fill by reading**: the agent reads the sections in order and fills
   each slot only from the cited paragraph, attaching a source anchor
   (`section | paragraph id | page | figure/table`) to every key note.
   Unreported stays `NOT_REPORTED`; conflicts are recorded, never resolved
   silently. Figure/table values come from the citing text, never from
   the label.
5. **Audit** (new in v1.1): re-read each cited paragraph, check
   number/unit/sign and cross-field consistency
   (finding ↔ premises, limitation ↔ method/data), and record the
   outcome in `audit_record`; then measure the verifiability scorecard
   (`scripts/measure_gain.py` → `gain.json`).
6. **Validate** (`scripts/validate_notes.py`): rejects empty fields,
   unanchored filled claims, section-coverage mismatch, duplicate terms,
   anchors pointing at non-existent paragraphs/pages, and figure/table
   register errors (E10).
7. **Deliver** to `/app/output`: `notes.json`, `notes.md`, `index.json`,
   `gain.json`, `result.json` (with `case_id`, `status`, `sources`,
   `uncertain_items`, `gain_evidence`, `audit_record`,
   `change_record`).

The four problems from task.md §1 are addressed directly: 对得上
(sections follow the paper's headings and order), 留得住 (paper card
records question, data, method conditions, findings, limitations **and
premises**), 找得回 (anchor per key note), 用得上 (JSON + Markdown +
search index, fixed fields for cross-paper comparison).

## How to run it on a case (exact steps)

```bash
# 0. Pre-flight — verify the tools before reading the paper
python3 --version; which pdftotext pdfinfo
python3 scripts/segment.py --help

# 1. Extract (work under /app/work)
python3 scripts/extract_text.py --input <paper.pdf|paper.txt|paper.md> \
  --out-text /app/work/paper.txt --out-pages /app/work/pages.json
# two-column paper? re-extract with --layout raw and keep the coherent one

# 2. Segment
python3 scripts/segment.py --pages /app/work/pages.json \
  --out /app/work/sections.json

# 3. Build the skeleton (save this partial deliverable immediately)
python3 scripts/build_notes.py --sections /app/work/sections.json \
  --case-id <case_id> --out-json /app/work/notes.json \
  --out-md /app/work/notes.md --out-index /app/work/index.json

# 4. Fill notes.json / notes.md by reading sections in order, with anchors
#    (see SKILL.md step 4 and templates/field-dictionary.md). Leave anything
#    unsupported as NOT_REPORTED. Fill the figure/table register from the
#    citing text.

# 5. Audit (re-read each cited paragraph; check numbers, units, signs and
#    cross-field consistency) and measure the scorecard
python3 scripts/measure_gain.py --notes /app/work/notes.json \
  --sections /app/work/sections.json --out /app/work/gain.json

# 6. Validate — must exit 0 before delivery
python3 scripts/validate_notes.py --notes /app/work/notes.json \
  --sections /app/work/sections.json

# 7. Deliver
mkdir -p /app/output
cp /app/work/notes.json /app/work/notes.md /app/work/index.json \
   /app/work/gain.json /app/output/
# write /app/output/result.json (case_id, status, paper_card, section_notes,
# knowledge_points, sources, uncertain_items, gain_evidence, audit_record,
# change_record)
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
| `SKILL.md` | Skill本体: frontmatter, when-to-use, 7-step workflow, fallbacks, failure handling, self-check |
| `README.md` | This usage/method doc |
| `CHANGELOG.md` | Version history (v1.0 → v1.1 changes) |
| `scripts/extract_text.py` | Page-aware text extraction (PDF via pdftotext; .txt/.md direct; `--layout raw` two-column fallback) |
| `scripts/segment.py` | Heading detection (EN+ZH, numbered/unnumbered), paragraph ids + pages, figure/table mentions, two-column suspicion warning |
| `scripts/build_notes.py` | Notes skeleton, paper card, extractive + term candidates, figure/table register, search index |
| `scripts/validate_notes.py` | 10 error checks (E1–E10) + 3 warnings (W1–W3) on notes.json |
| `scripts/measure_gain.py` | Verifiability scorecard → `gain.json` (coverage, anchored-claim ratio, fill, figure/table resolution) |
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

## Local test — v1.1 re-run (2026-11-27, this VM)

The v1.0 sample files in `/tmp/litnotes-test` were lost in a VM restart,
so the same SAMPLE paper text was recreated from `examples/example-notes.md`
and re-run through the v1.1 scripts (same content, same case id
SAMPLE-001; PDF rebuilt with LibreOffice from the sample text):

```bash
cd /tmp/litnotes-test-v11
python3 <skill>/scripts/extract_text.py --input sample-paper.pdf \
  --out-text paper.txt --out-pages pages.json
python3 <skill>/scripts/segment.py --pages pages.json --out sections.json
python3 <skill>/scripts/build_notes.py --sections sections.json \
  --case-id SAMPLE-001 --out-json notes.json --out-md notes.md \
  --out-index index.json
# fill the skeleton from the sample text (same values as example-notes.md)
python3 <skill>/scripts/measure_gain.py --notes notes.json \
  --sections sections.json --out gain.json
python3 <skill>/scripts/validate_notes.py --notes notes.json \
  --sections sections.json
```

Outcome: extraction 1 page; segmentation found the same 6 headed sections
in order; skeleton now also carries the figure/table register (Figure 1,
Figure 2, Table 1, each with its citing paragraph); the filled notes
pass validation (exit 0, 0 errors, 15 warnings — all honest NOT_REPORTED
slots, same count as v1.0); `measure_gain.py` reports the scorecard:
section coverage 7/7 in order, paper card 7/7 filled (6 anchored — the
title carries no anchor by design), 20 section slots filled (20
anchored), anchored-claim ratio 0.963, knowledge points 1/1 verified,
figure/table register 3/3 resolved from the citing text (e.g. "78%
released within 24 h" for Figure 2), 15 NOT_REPORTED remaining,
0 unreviewed candidates. The two-column warning was checked separately
on a synthetic two-column-style page and fired as designed.

## Limits (honest)

- Heading detection is rule-based: papers with no recognisable headings
  yield a single `unsectioned` section and chapter alignment cannot be
  verified (recorded, not hidden).
- Two-column PDFs can scramble reading order under `-layout`; v1.1 flags
  suspect pages in `segment.py` and offers a `--layout raw` re-extraction
  to compare, but it does not repair column order automatically — the
  agent still verifies against a rendered page where possible.
- Scanned-image PDFs yield almost no text; the Skill reports `partial`
  and hands over to OCR instead of inventing content.
- Figure/table values come from the text that cites them, not from the
  figure image: a value that only exists inside a chart is recorded as
  read-from-rendered-figure with its citing paragraph, or left
  NOT_REPORTED.
- Extractive candidates are heuristic pointers (numbers / cue words);
  only the agent's paragraph-by-paragraph reading turns them into
  findings — the validator enforces the anchor, not the truth of the
  claim. Correctness of an anchor's *target* (does the cited paragraph
  really state the claim?) is a human/agent judgement, enforced by the
  step-5 claim audit and listed as such in the field dictionary.
- No `output_contract` fields were published in the challenge files, so
  `result.json` carries the §3 fields (input id, main result,
  evidence/anchors, status, uncertainty); if a case's `task.md` names
  extra fields, they are added verbatim.
- The Skill handles one paper per case, matching the 3 fixed cases; for
  multi-paper comparison, run it once per paper — the fixed paper-card
  fields make the cards comparable side by side.
