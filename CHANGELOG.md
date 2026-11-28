# Changelog — literature-structured-notes

## v1.3 — 2026-11-29 (improvement resubmission, deadline day)

Improvement over v1.2 (attempt 116476, scored 73.3333/100; leader
84.33, gap 11.0) along the challenge's scoring dimensions. No
official-case content is involved: all changes were verified on the
builder's own invented SAMPLE paper only (see README "Local test —
v1.3 re-run"), plus negative tests that prove the new checks fire.
Workflow stays 8 steps (step 3 gains condition candidates, step 5b
gains K6–K7, step 7 gains E12).

- **Actual effect — E12 anchor-content overlap (new, hard fail).**
  `validate_notes.py` gains check E12: a filled factual claim must
  share at least one content token (a Latin word of 4+ letters, minus
  generic stopwords) or one measured number with its anchor paragraph,
  or validation fails. E11 proves a number exists *somewhere* in the
  paper; E12 proves the *anchor paragraph* states something like the
  claim — it catches a drifted paraphrase and a wrong-paragraph anchor
  that E11 cannot see (proven: a drifted s5 result with no numbers
  fails E12; an s4 result anchored to the front-matter label paragraph
  fails E12). Applies to paper-card fields, section `result`/`method`
  slots, figure/table values and knowledge-point definitions;
  interpretive `purpose`/`conclusion`/`link_to_next_section` slots
  and claims with no checkable token are outside it by design (the
  step-5 audit covers them). Honest limit: E12 cannot catch an anchor
  swapped to another paragraph of the same paper that shares the same
  vocabulary — one shared token passes by design (documented in README
  "Limits").
- **Actual effect — condition candidates (new).** `build_notes.py`
  adds a per-section `condition_candidates` list (up to 2 sentences
  carrying a measured number with a unit: temperatures, doses,
  durations, concentrations) — the parameter values the `methods` and
  `premises_for_conclusions` fields are filled from, which result-cue
  scoring misses because bare conditions carry no result verb. On the
  SAMPLE paper it surfaces exactly the two Methods sentences the
  `methods`/`premises` fields are filled from (80 °C / 30 min and
  1% / 40 °C / 12 h). `templates/paper-card.json` documents the new
  field; SKILL.md step 4 tells the agent to use it as the premises
  source list.
- **Actual effect — empty-section and unresolved-figure checks (new).**
  `check_consistency.py` gains K6 (warn: a headed section note with
  every content slot NOT_REPORTED was segmented but never read;
  front-matter/unsectioned exempt) and K7 (warn: a section
  result/conclusion naming a Figure/Table whose register entry is
  still NOT_REPORTED cites it for a value the text never states).
  Both proven with negative tests (K6/K7 warn, exit 0). On SAMPLE-001
  both are silent (0 warnings), as every headed section is filled and
  all three register entries are resolved.
- **Use gain — filled values unchanged, gain is verification.**
  The v1.3 scorecard on SAMPLE-001 is identical to v1.2 (7/7 sections,
  anchored-claim ratio 0.963, 3/3 figures/tables resolved, 15
  NOT_REPORTED, 0 unreviewed candidates) — reported honestly rather
  than inflated. No `--baseline` delta is claimed for v1.3: the v1.2
  filled-notes file was lost in a VM restart, so no real v1.2 baseline
  file exists to compare against.
- `templates/field-dictionary.md` documents E12 and K6–K7;
  `templates/paper-card.json` documents `condition_candidates` and
  K1–K7; `SKILL.md` step 3/4/5b/7 and self-check updated accordingly.

## v1.2 — 2026-11-28 (improvement resubmission)

Improvement over v1.1 (attempt 114388, scored 73.3333/100) along the
challenge's scoring dimensions. No official-case content is involved:
all changes were verified on the builder's own invented SAMPLE paper
only (see README "Local test"), plus synthetic heading/docx/resilience
tests and negative tests that prove the new checks fire. Workflow is
now 8 steps (consistency check 5b, scorecard 6, validate 7, deliver 8).

- **Actual effect — E11 no-invented-numbers check (new).**
  `validate_notes.py` gains check E11 (hard fail): every measured
  number in a filled claim (unit/`%`, decimal, range, or bare integer
  ≥ 100 that is not a round multiple of 10) must occur in the
  extracted paper text. A fabricated number (tested: 78% → 79%)
  now fails validation instead of reaching delivery. W4 warns when a
  measured number is not in its cited paragraph (e.g. a premises value
  synthesised from another section) — the source section must then be
  named in `uncertain_items`.
- **Actual effect — cross-field consistency script (new).**
  `scripts/check_consistency.py` (K1–K5) machine-checks the step-5
  audit: findings without premises (K1, fail), a
  `link_to_next_section` naming the wrong next section (K2, fail),
  a `key_findings` number missing from every section result (K3,
  warn), a limitation with no traceable cue word (K4, warn), a
  knowledge-point definition anchored to a paragraph that never names
  the term (K5, fail). All five were proven with negative tests
  (K1/K2/K5 fail, K3/K4 warn). `result.json` gains
  `consistency_record`.
- **Actual effect — limitation candidates (new).**
  `build_notes.py` adds a per-section `limitation_candidates` list
  (sentences with a limitation cue: `only`, `limited`, `however`,
  `仅`, `局限` ...) so the `limitations` field is filled from the
  paper instead of from plausibility. On the SAMPLE paper it surfaces
  exactly the two Discussion sentences the limitations field is filled
  from. Term candidates now also catch `also known as` / `hereafter`
  definitions and repeated capitalised phrases from 2 occurrences
  (was 3); the number-unit list grew (µm, mM, Pa, eV, ppm, wt%, …).
- **Actual effect — heading coverage (improved).** `segment.py`
  recognises more real headings (`Experimental Setup`, `Sample
  Preparation`, `Data Availability Statement`, `Author
  Contributions`, `Future Work`, …), `N:` colon numbering and a
  trailing full stop on short known headings, while still refusing
  body sentences such as `3.5 g of sample was added.` (proven on a
  synthetic headings test: 8 headings found, 0 false positives).
- **Use gain — baseline delta (new).** `measure_gain.py` gains
  `--baseline`: given a real run's notes for the same paper it emits
  a `delta_vs_baseline` block (anchored-claim ratio, fill, figure
  resolution, NOT_REPORTED). v1.2 vs v1.1 on SAMPLE-001: delta 0 on
  every count — the filled values are unchanged; the gain is in
  stricter verification, reported honestly rather than inflated.
- **Reliability — extraction resilience (improved).**
  `extract_text.py` no longer aborts the whole paper when one page
  fails: it continues with the remaining pages and marks the failed
  page (`extraction_failed: true`, listed in `uncertain_items`;
  proven with a stubbed-pdftotext unit test). `.docx` input is now
  supported via LibreOffice conversion (proven on the SAMPLE paper
  converted to .docx: same 1,758 chars extracted).
- `result.json` gains `consistency_record`; `gain.json` may carry a
  `delta_vs_baseline` block. `templates/field-dictionary.md`
  documents E11 and K1–K5; `templates/paper-card.json` gains the
  `consistency_record` field.

## v1.1 — 2026-11-27 (improvement resubmission)

Improvement over v1.0 (attempt 112268, scored 63/100) along the
challenge's scoring dimensions. No official-case content is involved:
all changes were verified on the builder's own invented SAMPLE paper
only (see README "Local test").

- **Actual effect — figure/table register (new).** `build_notes.py`
  now lists every Figure/Table a section mentions, with the citing
  paragraph ids; `validate_notes.py` gains check E10 (mentioned ids
  exist; a filled value needs a real anchor) and warning W3. The agent
  records the value the citing text states, or leaves the entry
  NOT_REPORTED — a finding may no longer cite a figure for a number
  the text never states. (v1.0's own example notes admitted figure
  contents were not extracted.)
- **Actual effect — claim audit (new step 5).** Before validation the
  agent re-reads each cited paragraph and checks number/unit/sign,
  checks the same number wherever else it appears, and checks
  cross-field consistency (finding ↔ premises, limitation ↔
  method/data, link_to_next_section names a real handover). Rules in
  `templates/field-dictionary.md`; the outcome is recorded in
  `result.json` `audit_record`.
- **Use gain — verifiability scorecard (new).**
  `scripts/measure_gain.py` counts section coverage, anchored-claim
  ratio, paper-card fill, verified knowledge points, resolved
  figure/table entries and NOT_REPORTED remaining, and writes
  `gain.json`, copied into `result.json` `gain_evidence`. SKILL.md
  documents the fair baseline comparison (same paper, same extraction,
  same budget; both scorecards recorded, never an invented baseline).
- **Reliability — two-column handling (improved).**
  `segment.py` now flags pages whose lines are mostly short fragments
  as possible two-column layouts; `extract_text.py` gains
  `--layout raw` so the agent can re-extract and keep the coherent
  layout, recorded in `sources`. Step 0 pre-flight check added
  (Python, pdftotext, scripts run) so a missing tool is found before
  the paper is read. Long-paper batching (save after each section) is
  now explicit in step 2.
- **Ecology — GitHub link fixed.** v1.0's SKILL.md self-check and
  README said no GitHub account was available and skipped the bonus;
  the public repo https://github.com/mekiann/literature-structured-notes
  now exists, `GITHUB_URL.txt` is in the submission root, and the
  self-check requires the submitted Skill to match the repo version.
- `result.json` gains `gain_evidence` and `audit_record`; `sources`
  gains the extraction layout used. Workflow is now 7 steps
  (pre-flight 0, audit 5, validate 6, deliver 7).

## v1.0 — 2026-11-26 (first submission, attempt 112268)

Initial Skill: page-aware extraction, own-section segmentation,
skeleton builder, validator (E1–E9, W1–W2), field dictionary,
paper-card schema, worked SAMPLE example. Scored 63/100 (final).
