---
name: literature-structured-notes
description: Turn a real research paper into chapter-aligned structured notes — section summaries in the paper's own order, a fixed-field paper card (research question, data, methods, key findings, limitations, premises), deduplicated knowledge points, and a source anchor (section/paragraph/page/figure) on every key note — with a validator that rejects empty fields and unanchored claims. Use when given a paper (PDF or text) and asked to summarise it, take structured notes, extract key points, or produce reusable, verifiable reading notes.
---

# Literature Summarization & Structured Notes

## When to use

A case gives you a real paper (usually a PDF, sometimes text) and asks for
reading notes that can be checked and reused — not a free-form summary.
Use this Skill when the deliverable must be **对得上** (skeleton follows
the paper's own chapters and argument order), **留得住** (question, data,
method conditions, findings, limitations *and the premises that make the
conclusions hold* are all recorded), **找得回** (every key note anchors to
a specific section, paragraph, page or figure), and **用得上** (notes are
JSON + Markdown + a searchable index, and paper cards share fixed fields
so papers can be compared side by side).

Do **not** use this Skill to write a generic abstract-style summary, to
answer questions the paper does not address, or to produce a literature
review across papers you have not read — those are different tasks.

## Inputs (discover, don't assume)

1. Read `/input/case.json` first. Record `case_id` and find the paper:
   inspect every key; the paper path may be under `material`, `files`,
   `paper`, `input_files`, `attachments`, or a relative path. List the
   directory the case points to (`ls`) and read the actual files — never
   assume content from a filename or a domain label.
2. Read `task.md` in the case directory for any case-specific instructions;
   they override nothing here except output filenames the case names.
3. If no paper file is present, stop: write `result.json` with
   `status: "unable-to-judge"`, `uncertain_items: ["no paper file found in
   the case; looked in: <paths checked>"]`, and no invented notes.

## Workflow (8 steps, save partial deliverables early)

Work under `/app/work`; final outputs under `/app/output`. Save
`notes.json`/`notes.md` after step 3 already (skeleton), and again after
each step — a crash must never lose the skeleton.

### Step 0 — Pre-flight (30 seconds, saves failed runs)

```bash
python3 --version            # 3.10+ (scripts are stdlib only)
which pdftotext pdfinfo      # page-aware PDF extraction
python3 scripts/segment.py --help   # scripts run at all
```

If `pdftotext` is absent, do not start step 1 on a PDF: use the harness
`pdf-text-tool` if provided, a supplied `.txt`/`.md` copy, or record
`status: partial` with the missing tool named. A run that fails at step 1
after the paper was read wastes the whole budget.

### Step 1 — Extract text, page-aware (script: `scripts/extract_text.py`)

```bash
python3 scripts/extract_text.py --input <paper.pdf|paper.docx|paper.txt|paper.md> \
  --out-text /app/work/paper.txt --out-pages /app/work/pages.json
```

- PDF: uses `pdftotext` (poppler, declared resource `pdf-text-tool`),
  page by page with `-layout`; `pdfinfo` gives the page count. Every
  paragraph keeps the page it came from — this is what makes anchors
  verifiable later.
- Word (`.docx`): converted to text with LibreOffice (`soffice`,
  declared resource `office-renderer`) when present; if LibreOffice is
  absent the script exits 2 — record `status: partial` with the missing
  tool named, never guess content.
- If one PDF page fails to extract, the run continues with the remaining
  pages; the failed page is marked in `pages.json`
  (`extraction_failed: true`) and must be listed in `uncertain_items`,
  with `status: partial` if key content may live on that page.
- If the PDF is encrypted, the script exits with reason `encrypted_pdf`:
  record `status: partial`, do not guess content, note the human handover.
- If fewer than 200 characters come out, the paper is probably a scanned
  image (needs `ocr-tool`) or figure-heavy: record the low-text warning,
  status `partial`, and continue only with what was actually extracted.
- If `pdftotext` is absent in the evaluation image, fall back in this
  order: (a) the harness `pdf-text-tool` if provided; (b) a `.txt`/`.md`
  version of the paper if the case supplies one; (c) record
  `status: partial` with `uncertain_items: ["pdftotext unavailable; no
  text layer extracted"]`. Never fabricate text from a filename.
- Two-column papers: if `segment.py` (step 2) warns of a possible
  two-column layout, re-extract with `--layout raw` and compare the two
  texts; keep the layout whose sentences read coherently, record which
  one was kept in `sources`, and note the discarded one in
  `uncertain_items`. Never mix pages from both extractions.

### Step 2 — Segment into the paper's OWN sections (script: `scripts/segment.py`)

```bash
python3 scripts/segment.py --pages /app/work/pages.json --out /app/work/sections.json
```

- Detects headings in English and Chinese, numbered (`1 Introduction`,
  `3.2 Methods`, `2: Methods`) and unnumbered (`Abstract`, `摘要`,
  `结果与讨论`, `Experimental Setup`, `Data Availability Statement`,
  `Author Contributions`, `Future Work`). A trailing full stop on a
  short known heading (`Introduction.`) is tolerated; a body sentence
  such as `3.5 g of sample was added.` is never promoted to a heading.
  Sections exist only where a heading line is actually found; text before
  the first heading is `front-matter`. No generic template sections are
  ever imposed — if the paper has no "Methods" heading, there is no
  Methods section note, and that is recorded as a limit, not papered over.
- Every paragraph gets an id `s<order>.p<n>` and its page; figure/table
  mentions (`Figure 2`, `表 3`) are recorded per paragraph.
- Read `sections.json` warnings: no headings found, duplicate titles, a
  possible two-column layout, or an empty extraction each change what
  you may claim later. A two-column warning means step 1's `--layout raw`
  comparison (above) before you fill anything.
- Long papers: process sections in order in batches, saving `notes.json`
  after each section; never skip a section silently — list skipped
  sections in `uncertain_items`.

### Step 3 — Build the skeleton (script: `scripts/build_notes.py`)

```bash
python3 scripts/build_notes.py --sections /app/work/sections.json \
  --case-id <case_id> --out-json /app/work/notes.json \
  --out-md /app/work/notes.md --out-index /app/work/index.json
```

This produces, mechanically and deterministically:
- a **paper card** with fixed fields (`title`, `research_question`,
  `data`, `methods`, `key_findings`, `limitations`,
  `premises_for_conclusions`) — all `NOT_REPORTED` except the title,
  which is taken from the first front-matter paragraph;
- one **section note per detected section, in the paper's own order**,
  each with `purpose / method / result / conclusion /
  link_to_next_section` slots (all `NOT_REPORTED`);
- **extractive candidates**: up to 3 sentences per section containing a
  number, percent, or result cue word, labelled `candidate` — these are
  pointers for you to verify, never findings;
- **limitation candidates**: up to 2 sentences per section carrying a
  limitation cue (`only`, `limited`, `however`, `仅`, `局限` ...) —
  pointers for the `limitations` field, which result-cue scoring
  misses; verify each one against its paragraph before promoting it;
- **condition candidates**: up to 2 sentences per section carrying a
  measured number with a unit — parameter values and measurement
  conditions (temperatures, doses, durations, concentrations) that
  the `methods` and `premises_for_conclusions` fields are filled
  from; verify each one against its paragraph before promoting it;
- **term candidates**: abbreviation definitions `Full Name (ABBR)`,
  `Full Name, also known as Short` / `hereafter Short` forms, and
  repeated capitalised phrases (2+ occurrences), grouped as canonical
  term + variants;
- a **figure/table register** per section: every Figure/Table the
  section's paragraphs mention, with the mentioning paragraph ids —
  the value each one carries is filled in step 4 from the citing text,
  never from the label;
- a **search index** (`index.json`) of sections and terms.
Save these files now — this is the honest partial deliverable.

### Step 4 — Fill the notes by reading, in section order

Read the sections **in the order in `sections.json`**, not in template
order. For each section note, fill the slots only from paragraphs in
that section; write the `link_to_next_section` as the actual handover
(e.g. "the gap identified here motivates the method in s3") — if there
is no visible handover, write `NOT_REPORTED`, not a generic sentence.

For the paper card, follow `templates/field-dictionary.md`:
- `research_question`, `data`, `methods`, `key_findings`,
  `limitations`, `premises_for_conclusions` — each value copied or
  checked against its cited paragraph, with the anchor recorded in
  `paper_card.field_anchors`.
- `premises_for_conclusions` is mandatory to attempt: the sample scope,
  parameter range, assumptions and controls under which each conclusion
  holds. Use the `condition_candidates` of the Methods/Results
  sections (sentences carrying a measured number with a unit) as the
  source list — a condition synthesised from another section must name
  its source section in `uncertain_items` (validator W4). A conclusion
  recorded without its premises must be flagged in
  `uncertain_items` as scope-limited.
- Numbers keep the paper's units and sign; a number whose unit you
  cannot find is `NOT_REPORTED`, not a bare number. A measured number
  you write must occur in the paper's extracted text — the validator's
  E11 check rejects numbers that appear nowhere in the paper, and its
  W4 warning flags numbers that are not in the cited paragraph (e.g. a
  premises value synthesised from another section: name the source
  section in `uncertain_items`).
- Fill `limitations` from the paper, not from plausibility: use the
  `limitation_candidates` of the Discussion/Conclusion sections and
  check each one against its paragraph; a limitation with no cue word
  in its anchor paragraph is flagged by the step-5 consistency check
  (K4) — re-read the paragraph or drop it.

Knowledge points: confirm each candidate term against the text, merge
synonyms/abbreviations/spelling variants into one entry per the dedup
rules in `templates/field-dictionary.md`, give each a definition in the
paper's own terms and an anchor. If two passages define the same term
differently, keep both anchors, set status `candidate`, and describe
the conflict in `uncertain_items` — never silently pick one.

Figures and tables: for each entry in the section's figure/table
register, record `value_from_text` — the value the citing paragraph
states about that figure/table, with an anchor to that paragraph. A
text extractor cannot read a chart image: if a value was read off a
rendered figure, say so in `uncertain_items` and still anchor the
paragraph that discusses it. If the citing text states no value, the
entry stays `NOT_REPORTED` and no finding may cite that figure/table
as evidence for a number — see `templates/field-dictionary.md`.

Rules for every filled claim:
- Re-read the cited paragraph before writing the claim down. The
  extractive candidate sentence alone is not evidence.
- **Never write what the paper does not say.** Unreported = `NOT_REPORTED`;
  conflicting = both sides + anchors in `uncertain_items`; uncertain =
  say so with where you looked. Empty strings and null are forbidden —
  the validator rejects them.
- Do not copy a generic summary template over the paper's structure, and
  do not use the paper's field labels (or any domain label in the case)
  to invent data the text does not contain.

### Step 5 — Claim audit & consistency check

Before validation, audit the filled notes once against their own
anchors, following the claim-audit rules in
`templates/field-dictionary.md`: re-read each cited paragraph and
check number, unit and sign; check the same number wherever else it
appears in the paper; check cross-field consistency (every finding has
its premises; every limitation traces to a method/data condition or a
sentence the paper states; every `link_to_next_section` names a real
handover); check the figure/table register. Correct or drop every
claim that fails the audit — never leave a drifted paraphrase in place.
Record the audit in `result.json` `audit_record`: claims checked,
claims corrected, claims dropped, conflicts kept. An audit with 0
corrections still records "0 corrections".

Then run the machine-checkable part of that audit:

```bash
python3 scripts/check_consistency.py --notes /app/work/notes.json \
  --sections /app/work/sections.json --out /app/work/consistency.json
```

Checks K1–K7 (see `templates/field-dictionary.md`): findings without
premises (K1, fail), a `link_to_next_section` naming the wrong next
section (K2, fail), a `key_findings` number missing from every section
result (K3, warn), a limitation with no traceable cue (K4, warn), a
knowledge-point definition anchored to a paragraph that never names
the term (K5, fail), a headed section note left entirely NOT_REPORTED
(K6, warn), and a result/conclusion citing a Figure/Table whose
register entry is still NOT_REPORTED (K7, warn). Exit 1 = fix every
`FAIL` line before continuing.
Copy `consistency.json` into `result.json` as `consistency_record`.

### Step 6 — Verifiability scorecard

Measure what the notes actually deliver:

```bash
python3 scripts/measure_gain.py --notes /app/work/notes.json \
  --sections /app/work/sections.json --out /app/work/gain.json
```

`gain.json` is the verifiability scorecard (section coverage,
anchored-claim ratio, paper-card fill, knowledge points verified,
figure/table entries resolved, NOT_REPORTED remaining). Copy it into
`result.json` as `gain_evidence`. For a fair baseline comparison, run
the same paper through a base agent without the Skill and pass its
notes with `--baseline`:

```bash
python3 scripts/measure_gain.py --notes /app/work/notes.json \
  --sections /app/work/sections.json --baseline /app/work/notes-baseline.json \
  --out /app/work/gain.json
```

The `--baseline` file must be a real run's output on the same paper —
never an invented number. The scorecard measures this run only; a low
score is a finding to report, not a failure to hide.

### Step 7 — Validate (script: `scripts/validate_notes.py`)

```bash
python3 scripts/validate_notes.py --notes /app/work/notes.json \
  --sections /app/work/sections.json
```

Exit 0 = pass (warnings are honest gaps, and must appear in
`uncertain_items`). Exit 1 = fail: fix every `FAIL` line — missing
anchors, empty fields, section-coverage mismatch, duplicate terms,
anchors pointing at non-existent paragraphs/pages, leftover
`TODO/TBD/XXX` placeholders, **E11: a measured number that occurs
nowhere in the paper**, and **E12: a filled factual claim that shares
no content token or number with its anchor paragraph** (the paragraph
does not state the claim — fix the anchor or reword the claim; E12
does not apply to the interpretive `purpose` / `conclusion` /
`link_to_next_section` slots or to claims with no checkable token).
W4 warns when a measured number is not in its cited paragraph — name
the source section in `uncertain_items`.
Re-run until it passes. **Never deliver notes that fail validation,
and never weaken the validator to make them pass.**

### Step 8 — Deliver to `/app/output`

Copy the validated files and write `result.json`:

- `notes.json` — the full structured notes (schema:
  `templates/paper-card.json`).
- `notes.md` — the same notes as readable Markdown (regenerate from
  `notes.json` after filling; keep the two in sync).
- `index.json` — search index (sections + terms + anchors).
- `gain.json` — the verifiability scorecard from step 6.
- `consistency.json` — the step-5 consistency report (K1–K7).
- `result.json` — `case_id`, `status` (`success` | `partial` |
  `unable-to-judge`, with a reason), `paper_card`,
  `section_notes`, `knowledge_points`, `sources` (paper filename,
  extraction tool actually used, extraction layout used, sections detected), `uncertain_items`,
  `gain_evidence` (the step-6 scorecard, plus a baseline scorecard if
  one was run), `audit_record` (step-5 audit outcome),
  `consistency_record` (step-5 K1–K7 outcome),
  and a `change_record` (what was filled, what stayed NOT_REPORTED,
  validator result). No output_contract fields were published in the
  challenge files for this task, so `result.json` carries the §3 fields
  above (input id, main result, evidence/anchors, status, uncertainty);
  if the case's `task.md` names additional required fields, add them
  verbatim and note the addition in `change_record`.
- If the case asks for an editable Office/slide/diagram output, also
  render a PDF/PNG preview for inspection (declared resource
  `office-renderer` / LibreOffice when available); this Skill's core
  deliverables are text/JSON and need no rendering.

## Dependencies and fallbacks (verified on the build VM)

| Capability | Preferred | Fallback | If absent |
|---|---|---|---|
| PDF text, page-aware | `pdftotext`/`pdfinfo` 24.02.0 (poppler) | harness `pdf-text-tool`; `.txt` copy if supplied | status `partial`, no invented text |
| Word input | LibreOffice 24.2.7.2 (`soffice`, converts `.docx` to text) | — | status `partial`, missing tool named |
| One PDF page fails to extract | per-page resilience in `extract_text.py` (other pages still extracted; failed page marked) | — | failed page in `uncertain_items`, status `partial` if key content may live there |
| Section/term extraction, validation | Python 3.12 stdlib scripts in `scripts/` | — (no third-party libs needed) | — |
| Cross-field consistency | `scripts/check_consistency.py` (K1–K7, stdlib) | — | audit falls back to the manual step-5 reading check; `consistency_record` records why |
| Verifiability scorecard | `scripts/measure_gain.py` (stdlib, `--baseline` delta) | — | scorecard skipped; `gain_evidence` records why |
| Scanned-image PDF | `ocr-tool` (declared) | — | low-text warning, status `partial` |
| Rendering previews | LibreOffice 24.2.7.2 | skip preview, note it | text/JSON outputs unaffected |
| LaTeX / pandoc / tesseract / ghostscript | not required | not required | not used by this Skill |

All scripts are Python 3 stdlib only; no `pip install`, no network, no
API keys. Deterministic: same input → same skeleton, same validation
result. The interpretive filling (step 4) is the agent's reading work;
re-running it should converge on the same anchors, which is why anchors
cite paragraph ids, not free text.

## Failure handling

| Situation | Response |
|---|---|
| No paper file in the case | `status: unable-to-judge`, list paths checked, no notes |
| Encrypted / permission-restricted PDF | `status: partial`, reason `encrypted_pdf`, human handover note |
| Scanned image, <200 chars extracted | `status: partial`, low-text warning, OCR handover |
| One PDF page fails to extract | continue with the other pages; failed page marked in `pages.json` and listed in `uncertain_items`; `status: partial` if key content may live there |
| `.docx` input, LibreOffice absent | `status: partial`, missing tool named, no guessed text |
| No headings detected | single `unsectioned` section; chapter alignment marked as a limit |
| Two-column reading-order errors suspected | flag in `uncertain_items`; re-extract with `--layout raw` and keep the coherent layout (step 1); check a rendered page if `pdf-render-tool` is available |
| Very long paper / token budget pressure | summarise per section in order, save after each section; never skip a section silently — list skipped sections in `uncertain_items` |
| Validator fails | fix the notes, never the validator; deliver only after exit 0 |
| Audit finds a drifted claim | correct or drop the claim; record it in `audit_record` |

## Self-check (before reporting done)

1. `validate_notes.py` exits 0 on the final `notes.json`.
2. Every section in `sections.json` has a section note, in order.
3. Every filled paper-card field has a `field_anchors` entry whose
   paragraph exists on the stated page.
4. `result.json` has `case_id`, `status`, `sources`,
   `uncertain_items`, `gain_evidence`, `audit_record`,
   `consistency_record`, and `change_record`; `status` is honest
   (`partial` if anything is NOT_REPORTED).
5. `check_consistency.py` exits 0 (K1–K7) on the final `notes.json`,
   and every W4 warning is explained in `uncertain_items`.
6. The public GitHub repo for this Skill is
   https://github.com/mekiann/literature-structured-notes and
   `GITHUB_URL.txt` (first line: the repo URL, second line: `SKILL.md`)
   is in the submission root; the submitted Skill matches the repo
   version.
7. No number, claim, score or log appears that was not read from the
   paper or produced by a script run in this session.
