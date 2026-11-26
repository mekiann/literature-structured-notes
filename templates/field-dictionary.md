# Field dictionary and anchor format — 文献总结与结构化笔记

## Anchor format (every key note carries one)

`[§<section title> | <section_id>.<paragraph n> | p.<page> | <Figure/Table N if the claim comes from a figure or table>]`

Example: `[§Results | s4.p2 | p.7 | Figure 2]` — the claim can be checked by
opening page 7, section "Results", second paragraph, and Figure 2. An anchor
that names only the paper ("see the paper") is not an anchor and fails
validation (E5). If a claim spans paragraphs, cite the paragraph where the
claim is actually stated, not the section as a whole.

Paragraph ids come from `segment.py` (`s<order>.p<n>`); pages come from
`extract_text.py` (the page `pdftotext` read the text from). Never renumber
pages by hand: PDF page numbers printed on the page may differ from the
PDF's physical page count — record the physical page the extractor used,
and note a printed-page offset in `uncertain_items` if they differ.

## Paper-card fields

| Field | What counts as filled | What to do if absent |
|---|---|---|
| title | Title as printed (first front-matter paragraph) | NOT_REPORTED |
| research_question | The question / gap the paper states, in its own terms — not a paraphrase of the title | NOT_REPORTED + note where you looked (Abstract / Introduction) |
| data | Source, size/sample count, time span, selection criteria | NOT_REPORTED; never infer a dataset size |
| methods | Method/model/instrument + key conditions and parameter values | NOT_REPORTED |
| key_findings | Results with the numbers and units the paper gives; each number needs its own anchor | NOT_REPORTED |
| limitations | Limitations the paper states; add only ones verifiable from method/data | NOT_REPORTED |
| premises_for_conclusions | Conditions under which each conclusion holds (scope, parameter range, assumptions, controls). This is the field most often dropped by generic summaries — a conclusion without its premises must not be reused as a general claim. | NOT_REPORTED, and mark the conclusion itself as scope-limited in `uncertain_items` |

## Knowledge-point dedup / merge rules

1. **One canonical term per concept.** First occurrence's full form wins
   (e.g. "starch-based hydrogel (SH)" → canonical "starch-based hydrogel",
   abbreviation "SH"). Later bare "SH" uses map to the same entry.
2. **Variants, not duplicates.** Synonyms, spelling variants
   (British/American), singular/plural and abbreviation forms go in
   `variants[]` of the one entry; creating a second entry is a validation
   failure (E7).
3. **Abbreviation defined once.** `Full Name (ABBR)` at first use defines
   the pair. An abbreviation used before it is defined is flagged in
   `uncertain_items` with its paragraph.
4. **Contradiction rule.** If two passages define or value the same term
   differently, keep BOTH anchors in the entry, set status to
   `candidate`, and describe the conflict in `uncertain_items`. Never
   silently pick one.
5. **Merge record.** When two candidate terms are merged, keep the dropped
   form in `variants[]` and set the surviving entry's status to `merged`.

## Machine-checkable vs human-confirmed

- Machine-checkable: section coverage (E4), anchor existence and page
  match (E8), field presence / non-emptiness (E2), dedup (E7),
  placeholder leftovers (E9) — all enforced by `validate_notes.py`.
- Human-confirmed (agent must judge, validator cannot): whether an anchor
  points at the paragraph that *actually states* the claim (not just a
  paragraph in the same section); whether a number was copied with the
  right unit and sign; whether a "limitation" is really stated or merely
  plausible. For each filled claim, re-read the cited paragraph before
  writing it down — do not trust the extractive candidate sentence alone.
