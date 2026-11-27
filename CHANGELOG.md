# Changelog — literature-structured-notes

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
