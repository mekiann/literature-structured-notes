# Literature Structured Notes — Usage & Method (README)

Skill: `literature-structured-notes` (`SKILL.md`). Challenge:
product-arena-06-6d8cf72b — 文献总结与结构化笔记. Scoring: human review
only. Public repo: https://github.com/mekiann/literature-structured-notes
(`GITHUB_URL.txt` in the submission root, second line `SKILL.md`).
Version: v1.2 (see `CHANGELOG.md`).

## What it does

Turns one real research paper into chapter-aligned, verifiable, reusable
notes:

1. **Extract** the paper's text page by page (`scripts/extract_text.py`,
   `pdftotext`/`pdfinfo`; `--layout raw` fallback for two-column PDFs;
   `.docx` via LibreOffice; one failed page no longer aborts the run).
2. **Segment** the text into the paper's own sections, in its own order
   (`scripts/segment.py`) — no generic summary template is imposed.
3. **Build a skeleton** (`scripts/build_notes.py`): a fixed-field paper
   card, one section note per detected section, extractive candidates and
   limitation candidates, term candidates, a figure/table register, plus
   a search index.
4. **Fill by reading**: the agent reads the sections in order and fills
   each slot only from the cited paragraph, attaching a source anchor
   (`section | paragraph id | page | figure/table`) to every key note.
   Unreported stays `NOT_REPORTED`; conflicts are recorded, never resolved
   silently. Figure/table values come from the citing text, never from
   the label.
5. **Audit and consistency-check** (audit new in v1.1, consistency check
   new in v1.2): re-read each cited paragraph, check number/unit/sign
   and cross-field consistency (finding ↔ premises, limitation ↔
   method/data), and record the outcome in `audit_record`; then run
   `scripts/check_consistency.py` (K1–K5) and record its report as
   `consistency_record`.
6. **Measure the scorecard** (`scripts/measure_gain.py` → `gain.json`,
   with an optional `--baseline` delta against a real run of the same
   paper).
7. **Validate** (`scripts/validate_notes.py`): rejects empty fields,
   unanchored filled claims, section-coverage mismatch, duplicate terms,
   anchors pointing at non-existent paragraphs/pages, figure/table
   register errors (E10), and measured numbers that occur nowhere in
   the paper (E11); warns (W4) when a number is not in its cited
   paragraph.
8. **Deliver** to `/app/output`: `notes.json`, `notes.md`, `index.json`,
   `gain.json`, `consistency.json`, `result.json` (with `case_id`,
   `status`, `sources`, `uncertain_items`, `gain_evidence`,
   `audit_record`, `consistency_record`, `change_record`).

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
#    cross-field consistency) and consistency check (K1-K5)
python3 scripts/check_consistency.py --notes /app/work/notes.json \
  --sections /app/work/sections.json --out /app/work/consistency.json

# 6. Measure the scorecard
python3 scripts/measure_gain.py --notes /app/work/notes.json \
  --sections /app/work/sections.json --out /app/work/gain.json
#    optional fair-baseline delta (baseline = a real run's notes, same paper):
# python3 scripts/measure_gain.py --notes /app/work/notes.json \
#   --sections /app/work/sections.json \
#   --baseline /app/work/notes-baseline.json --out /app/work/gain.json

# 7. Validate — must exit 0 before delivery (E11 rejects numbers that
#    occur nowhere in the paper; W4 warns when a number is not in its
#    cited paragraph — name the source section in uncertain_items)
python3 scripts/validate_notes.py --notes /app/work/notes.json \
  --sections /app/work/sections.json

# 8. Deliver
mkdir -p /app/output
cp /app/work/notes.json /app/work/notes.md /app/work/index.json \
   /app/work/gain.json /app/work/consistency.json /app/output/
# write /app/output/result.json (case_id, status, paper_card, section_notes,
# knowledge_points, sources, uncertain_items, gain_evidence, audit_record,
# consistency_record, change_record)
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
| LibreOffice (preview rendering + `.docx` conversion) | 24.2.7.2 | optional for previews; required for `.docx` input (status `partial` if absent) |
| LaTeX (`pdflatex`/`xelatex`), pandoc, tesseract, ghostscript | **absent** | not required, not used |
| Python PDF libs (`PyPDF2`/`pdfplumber`/`fitz`) | **absent** | not required, not used |

No network, no `pip install`, no API keys. Scripts are deterministic:
same input → same skeleton and same validation result.

## Files in this submission

| File | Role |
|---|---|
| `SKILL.md` | Skill本体: frontmatter, when-to-use, 8-step workflow, fallbacks, failure handling, self-check |
| `README.md` | This usage/method doc |
| `CHANGELOG.md` | Version history (v1.0 → v1.1 → v1.2 changes) |
| `scripts/extract_text.py` | Page-aware text extraction (PDF via pdftotext; .docx via LibreOffice; `--layout raw` two-column fallback; one failed page no longer aborts the run) |
| `scripts/segment.py` | Heading detection (EN+ZH, numbered/unnumbered, more heading types, trailing-stop tolerance), paragraph ids + pages, figure/table mentions, two-column suspicion warning |
| `scripts/build_notes.py` | Notes skeleton, paper card, extractive + limitation + term candidates, figure/table register, search index |
| `scripts/check_consistency.py` | Cross-field consistency checks K1–K5 → `consistency.json` (new in v1.2) |
| `scripts/validate_notes.py` | 11 error checks (E1–E11) + 4 warnings (W1–W4) on notes.json |
| `scripts/measure_gain.py` | Verifiability scorecard → `gain.json` (coverage, anchored-claim ratio, fill, figure/table resolution; `--baseline` delta in v1.2) |
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

## Local test — v1.2 re-run (2026-11-28, this VM)

The same SAMPLE paper (recreated from `examples/example-notes.md`,
same content, same case id SAMPLE-001; PDF rebuilt with LibreOffice
from the sample text) was re-run through the v1.2 scripts:

```bash
cd /tmp/litnotes-test-v12
python3 <skill>/scripts/extract_text.py --input sample-paper.pdf \
  --out-text paper.txt --out-pages pages.json
python3 <skill>/scripts/segment.py --pages pages.json --out sections.json
python3 <skill>/scripts/build_notes.py --sections sections.json \
  --case-id SAMPLE-001 --out-json notes.json --out-md notes.md \
  --out-index index.json
# fill the skeleton from the sample text (same values as example-notes.md)
python3 <skill>/scripts/check_consistency.py --notes notes.json \
  --sections sections.json --out consistency.json
python3 <skill>/scripts/measure_gain.py --notes notes.json \
  --sections sections.json --baseline notes-v11-filled.json --out gain.json
python3 <skill>/scripts/validate_notes.py --notes notes.json \
  --sections sections.json
```

Outcome: extraction 1 page, 1,758 chars; segmentation found the same
6 headed sections in order; the skeleton now also carries
`limitation_candidates` (Abstract: "The method is simple and cheap,
but it was tested on one dye only."; Discussion: the two sentences
the limitations field is filled from); the filled notes pass
`check_consistency.py` (0 failures, 0 warnings) and validation
(exit 0, 0 errors, 16 warnings — 15 honest NOT_REPORTED slots plus
one W4: the premises field's 37 °C comes from Methods s3.p1, not
from its anchor paragraph s5.p1, now explained in
`uncertain_items`); `measure_gain.py --baseline` against the v1.1
filled notes reports delta 0 on every count (same filled values —
the gain is in stricter verification, not in the sample score).

Negative tests (all run, all behave as designed):
- E11: changing 78% to 79% in `key_findings` fails validation
  (exit 1, `E11 ... occurs nowhere in the paper`).
- K1: dropping `premises_for_conclusions` fails consistency (exit 1).
- K2: a `link_to_next_section` naming s5 from s2 fails (exit 1).
- K5: a knowledge point anchored to a paragraph that never names the
  term fails (exit 1).
- K3 + K4: removing 52% from every section result and moving the
  limitations anchor to Methods warns (exit 0, 2 warnings).

Other v1.2 tests (all run on this VM):
- Headings: a synthetic text file with `ABSTRACT`, `1. Introduction.`,
  `2: Experimental Setup`, `2.1 Sample Preparation`, `Data Availability
  Statement`, `Author Contributions`, `REFERENCES` and the trap
  sentence `3.5 g of sample was added.` segmented into 9 sections
  with 8 heading lines and 0 false positives.
- `.docx`: the SAMPLE paper converted to .docx extracted the same
  1,758 chars (78% and Abstract present).
- Page resilience: with `pdftotext` stubbed to fail on page 2 of a
  3-page PDF, extraction returned 0, kept pages 1 and 3, and marked
  page 2 `extraction_failed: true`.

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
  findings — the validator enforces the anchor, and E11 enforces that
  every measured number occurs in the paper, but whether an anchor's
  *target* paragraph really states the claim is a human/agent
  judgement, enforced by the step-5 claim audit and the K1–K5
  consistency check and listed as such in the field dictionary.
  E11 deliberately does not check round paraphrases ("about 100" for
  102) or bare integers below 100 — those stay the audit's job.
- No `output_contract` fields were published in the challenge files, so
  `result.json` carries the §3 fields (input id, main result,
  evidence/anchors, status, uncertainty); if a case's `task.md` names
  extra fields, they are added verbatim.
- The Skill handles one paper per case, matching the 3 fixed cases; for
  multi-paper comparison, run it once per paper — the fixed paper-card
  fields make the cards comparable side by side.
