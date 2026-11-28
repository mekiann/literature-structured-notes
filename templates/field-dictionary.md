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

## Figure / table register (one entry per mention)

`build_notes.py` lists every Figure/Table a section's paragraphs mention,
with the paragraph(s) that mention it. For each entry:

- `value_from_text`: the value the **citing text** states about that
  figure/table (e.g. "78% released within 24 h, Figure 2"), copied with
  its unit and anchored to the citing paragraph. A text extractor cannot
  read a chart image, so a value read off a rendered figure must say so
  in `uncertain_items` ("read from rendered Figure 2, not from extracted
  text") and still carry the paragraph anchor of the text that discusses it.
- If the text mentions a figure/table but states no value for it, the
  entry stays `NOT_REPORTED` and the finding must not cite that
  figure/table as evidence for a number.
- A finding that cites "Figure 2" while the register entry is
  NOT_REPORTED is an unanchored claim: fix the finding or resolve the
  register entry, never leave both.

## Claim audit (re-read before delivery)

After filling and before validation, audit every filled claim once
against its own anchor paragraph:

1. Re-read the cited paragraph in full. Does it actually state the
   claim, with the same number, unit and sign? A paraphrase that drifts
   (e.g. "most" for "78%", or a reversed comparison) is rewritten or
   dropped — never left in place.
2. Check the number against the same number anywhere else it appears
   (Abstract vs Results vs Conclusion). If the paper gives different
   values in different places, record both with anchors in
   `uncertain_items`; do not pick the rounder one.
3. Check cross-field consistency:
   - every `key_findings` item has its scope in
     `premises_for_conclusions` (sample, parameter range, controls);
     a finding without premises is flagged scope-limited;
   - every `limitations` item traces to a method/data condition in
     `methods`/`data` or to a sentence the paper itself states;
     a limitation invented from plausibility is removed;
   - `link_to_next_section` names a real handover (a question, gap or
     result the next section actually picks up), not a generic
     "this leads to the next section".
4. Check the figure/table register: each resolved entry's value matches
   the citing paragraph; each unresolved entry is listed in
   `uncertain_items` with the reason (text states no value / figure
   content not extractable).

Record the audit in `result.json` `audit_record`: how many claims were
checked, how many were corrected or dropped, and any conflicts kept.
An audit that changed nothing still records "0 corrections" — a missing
audit record is a gap, not a pass.

## E11 — no invented numbers (validator, hard check)

Every measured number in a filled claim must occur somewhere in the
extracted paper text, or the validator fails the notes (E11). A
"measured number" is a number with a unit or `%` sign, a decimal, a
range, or a bare integer ≥ 100 that is not a round multiple of 10
("about 100" for 102 is a paraphrase and is outside this check; the
claim audit above still has to re-read the paragraph). Numbers are
compared after normalising units (`37 °C` = `37°C`, `µ` = `μ`).

A measured number that is not in its cited anchor paragraph is a W4
warning, not a failure: it is legitimate when a field synthesises
conditions from across the paper (e.g. `premises_for_conclusions`
citing a temperature stated in Methods while anchored to Discussion)
— but then the source section must be named in `uncertain_items`.

## Cross-field consistency checks K1–K7 (script: check_consistency.py)

The machine-checkable part of the claim audit, run as step 5b before
validation. Exit 1 on any FAIL; the report is `result.json`
`consistency_record`.

| Check | Rule | Severity |
|-|-|-|
| K1 | `key_findings` filled ⇒ `premises_for_conclusions` filled | FAIL |
| K2 | A `link_to_next_section` naming a section id (`sN`) must name the section that actually follows; a link naming no section id is a generic handover | FAIL / warn |
| K3 | A measured number in `key_findings` must also appear in some section note's `result`/`conclusion` | warn |
| K4 | A `limitations` item whose anchor paragraph has no limitation cue word (`only`, `limited`, `not`, `however`, `仅`, `局限`, `不足`, `然而` ...) and is not in a Discussion/Conclusion/Limitations section may be invented from plausibility | warn |
| K5 | A knowledge point's definition anchor paragraph must contain the canonical term (case-insensitive, hyphens ignored) | FAIL |
| K6 | A headed section note (not front-matter / unsectioned) with all four content slots (`purpose`/`method`/`result`/`conclusion`) NOT_REPORTED was segmented but never read | warn |
| K7 | A section `result`/`conclusion` naming a Figure/Table whose register entry is still NOT_REPORTED cites it for a value the citing text never states | warn |

## E12 — anchor-content overlap (validator, hard check)

A filled factual claim must share at least one content token (a Latin
word of 4+ letters, excluding generic stopwords such as "paper",
"study", "result") or one measured number with its anchor paragraph,
or the validator fails the notes (E12). E11 proves a number exists
*somewhere* in the paper; E12 proves the *anchor paragraph* states
something like the claim — it catches a drifted paraphrase ("most" for
"78%", a reversed comparison) and an anchor pasted onto the wrong
paragraph, which E11 cannot see. Applies to the paper-card fields, the
section `result`/`method` slots, figure/table values and knowledge-point
definitions. `purpose`, `conclusion` and `link_to_next_section` are
interpretive / structural handovers, not factual claims, so they are
outside E12 (the claim audit and K2 cover them). A claim with no
checkable Latin token and no measured number (e.g. a purely Chinese
paraphrase) is outside E12; the claim audit above still has to re-read
the paragraph.

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
  placeholder leftovers (E9), measured numbers occurring in the paper
  (E11), anchor-content overlap for factual claims (E12),
  findings-with-premises / link targets / term anchors (K1, K2, K5),
  empty section notes and findings citing unresolved figures (K6, K7)
  — all enforced by `validate_notes.py` and `check_consistency.py`.
- Human-confirmed (agent must judge, validator cannot): whether an anchor
  points at the paragraph that *actually states* the claim (not just a
  paragraph in the same section); whether a number was copied with the
  right unit and sign; whether a "limitation" is really stated or merely
  plausible. For each filled claim, re-read the cited paragraph before
  writing it down — do not trust the extractive candidate sentence alone.
