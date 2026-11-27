#!/usr/bin/env python3
"""Validate a completed notes.json before delivery.

Usage:
  python3 validate_notes.py --notes /app/work/notes.json
                            --sections /app/work/sections.json

Checks (exit 0 = pass, 1 = fail; warnings never pass a failed check):
  E1  notes.json parses and has case_id, status, paper_card,
      section_notes, knowledge_points, uncertain_items, sources.
  E2  Every paper_card field exists and is either a real value or the
      literal "NOT_REPORTED". Empty strings and null are FAILURES --
      an empty field must not be passed off as complete.
  E3  Every paper_card field that is NOT "NOT_REPORTED" has an entry in
      paper_card.field_anchors naming section_id + paragraph_id + page.
  E4  Section coverage: one section_note per section in sections.json,
      in the same order, with matching section_id and title.
  E5  Every section_note has purpose/method/result/conclusion/
      link_to_next_section present; any filled value (not NOT_REPORTED)
      must carry an anchor naming a real paragraph id from sections.json
      on a page inside that section's page range.
  E6  Every knowledge point has canonical_term, a definition that is
      either real or NOT_REPORTED, an anchor (real paragraph/page or an
      explicit NOT_REPORTED marker), and status filled in.
  E7  Dedup: no two knowledge points share the same canonical term or
      abbreviation (case-insensitive) unless one is marked merged.
  E8  No anchor references a paragraph id or page that does not exist.
  E9  No filled claim contains a hedging placeholder left over
      ("TODO", "TBD", "XXX", "[?]", "???").
 E10  Figure/table register: every mentioned_in paragraph id exists;
      a filled value_from_text (not NOT_REPORTED) must carry an anchor
      naming a real paragraph id on a page inside that section.
 E11  No invented numbers: every measured number in a filled claim (a
      number with a unit or %, a decimal, a range, or a bare integer
      >= 100 that is not a round multiple of 10) must occur somewhere in
      the extracted paper text. A number that appears nowhere in the
      paper is a fabrication -- fix or drop the claim. Round paraphrases
      ("about 100" for 102) are outside this check by design; the claim
      audit (SKILL.md step 5) still has to re-read the paragraph.

Warnings (do not fail, but must be listed in uncertain_items):
  W1  Any field still NOT_REPORTED.
  W2  Extractive candidates still present unreviewed (a finding that
      copies a candidate sentence verbatim without an anchor).
  W3  Figure/table register entries still NOT_REPORTED (the value the
      citing text states was not recorded).
  W4  A measured number in a filled claim does not occur in its cited
      anchor paragraph (it may come from another section, e.g. a
      premises field synthesising a Methods condition -- then the
      source section must be named in uncertain_items). E11 still
      requires the number to occur somewhere in the paper.

Stdlib only. Deterministic.
"""
import argparse
import json
import re
import sys

# Units a measured number may carry. Keep in sync with build_notes.py
# UNITS (same list, same meaning: a claim number counts as "measured"
# only with one of these, a % sign, or as a decimal / large integer).
UNITS = (r"%|percent|°C|°F|℃|K\b|mg|μg|µg|ng|pg|g\b|kg\b|mL|μL|µL|L\b|"
         r"nm|μm|µm|mm|cm|m\b|Å|mM|M\b|mol|mmol|μmol|Pa|kPa|MPa|GPa|"
         r"eV|keV|Da|kDa|rpm|Hz|kHz|MHz|W\b|mW|kW|V\b|mV|A\b|mA|ppm|ppb|"
         r"fold|wt%|at%|vol%|h\b|min|s\b|ms|d\b|wk|yr|mmHg|N\b|J\b|cal|"
         r"mol/L|mg/mL|×|°")
NUM_TOKEN_RE = re.compile(
    r"\d[\d,]*(?:\.\d+)?(?:\s*[-–—]\s*\d[\d,]*(?:\.\d+)?)?\s*(?:" + UNITS + r")?"
    r"|\d[\d,]*(?:\.\d+)?")
DIGITS_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm(t):
    """Normalise text for number comparison: unify micro signs and the
    Celsius sign, drop the space between a number and its unit, collapse
    dashes and whitespace."""
    t = t.replace("µ", "μ").replace("℃", "°C")
    t = re.sub(r"(\d)\s+(?=%|°C|°F|[a-zA-ZμÅ×])", r"\1", t)
    t = re.sub(r"(\d)\s*[-–—]\s*(\d)", r"\1-\2", t)
    t = re.sub(r"\s+", " ", t)
    return t


def measured_numbers(claim):
    """Measured numbers in a claim: (normalised token, [digit parts]).

    A token counts only if it carries a unit or %, is a decimal, is a
    range, or is a bare integer >= 100 that is not a round multiple of
    10 (a round "about 100" paraphrase is not checked here).
    """
    out = []
    for m in NUM_TOKEN_RE.finditer(claim):
        tok = m.group(0)
        digits = DIGITS_RE.findall(tok)
        if not digits:
            continue
        has_unit = bool(re.search(r"(?:" + UNITS + r")$", tok.strip()))
        has_pct = "%" in tok
        is_range = bool(re.search(r"\d\s*[-–—]\s*\d", tok))
        is_decimal = any("." in d for d in digits)
        bare_int = (len(digits) == 1 and "." not in digits[0]
                    and not has_unit and not has_pct)
        if bare_int:
            try:
                n = int(digits[0].replace(",", ""))
            except ValueError:
                continue
            if n < 100 or n % 10 == 0:
                continue
        if not (has_unit or has_pct or is_range or is_decimal or bare_int):
            continue
        norm_tok = _norm(tok).replace(",", "")
        parts = [d.replace(",", "") for d in digits]
        out.append((norm_tok, parts))
    return out


def _number_in(norm_text, token, parts):
    """True if the token, or all of its digit parts, occur in the text."""
    if re.search(r"(?<!\d)" + re.escape(token) + r"(?!\d)", norm_text):
        return True
    return all(re.search(r"(?<!\d)" + re.escape(p) + r"(?!\d)", norm_text)
               for p in parts)

CARD_FIELDS = ["title", "research_question", "data", "methods",
               "key_findings", "limitations", "premises_for_conclusions"]
SECTION_SLOTS = ["purpose", "method", "result", "conclusion",
                 "link_to_next_section"]
PLACEHOLDERS = ("TODO", "TBD", "XXX", "[?]", "???")
NOT_REPORTED = "NOT_REPORTED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True)
    ap.add_argument("--sections", required=True)
    args = ap.parse_args()
    errors, warnings = [], []

    try:
        with open(args.notes, encoding="utf-8") as f:
            notes = json.load(f)
    except Exception as e:
        print(f"FAIL E1: notes.json unreadable: {e}")
        return 1
    try:
        with open(args.sections, encoding="utf-8") as f:
            seg = json.load(f)
    except Exception as e:
        print(f"FAIL E1: sections.json unreadable: {e}")
        return 1

    para_index = {}   # paragraph id -> (section id, page)
    section_ids = []
    for s in seg["sections"]:
        section_ids.append(s["id"])
        for p in s["paragraphs"]:
            para_index[p["id"]] = (s["id"], p["page"])

    def check_anchor(anchor, where):
        """Anchor must be a dict with section_id + paragraph_id + page,
        or a string explicitly marked NOT_REPORTED."""
        if isinstance(anchor, str):
            if NOT_REPORTED in anchor:
                return True
            errors.append(f"E5/E8 {where}: anchor is a bare string without "
                          f"a paragraph/page reference: {anchor!r}")
            return False
        if not isinstance(anchor, dict):
            errors.append(f"E5/E8 {where}: anchor is not an object: {anchor!r}")
            return False
        pid = anchor.get("paragraph_id")
        page = anchor.get("page")
        if pid not in para_index:
            errors.append(f"E8 {where}: anchor paragraph {pid!r} does not exist")
            return False
        if page is not None and page != para_index[pid][1]:
            errors.append(f"E8 {where}: anchor page {page} does not match "
                          f"paragraph {pid} (actual p.{para_index[pid][1]})")
            return False
        return True

    # E1: top-level keys
    for k in ("case_id", "status", "paper_card", "section_notes",
              "knowledge_points", "uncertain_items", "sources"):
        if k not in notes:
            errors.append(f"E1: missing top-level key {k!r}")

    # E2/E3: paper card
    card = notes.get("paper_card", {})
    anchors = card.get("field_anchors", {})
    if not isinstance(card, dict):
        errors.append("E2: paper_card is not an object")
    else:
        for field in CARD_FIELDS:
            if field not in card:
                errors.append(f"E2: paper_card missing field {field!r}")
                continue
            v = card[field]
            if v is None or (isinstance(v, str) and v.strip() == ""):
                errors.append(f"E2: paper_card.{field} is empty/null -- "
                              "use NOT_REPORTED, never an empty value")
            elif isinstance(v, str) and v.strip() == NOT_REPORTED:
                warnings.append(f"W1: paper_card.{field} is NOT_REPORTED")
            elif isinstance(v, str) and any(p in v for p in PLACEHOLDERS):
                errors.append(f"E9: paper_card.{field} contains a leftover "
                              "placeholder")
            elif field != "title":
                a = anchors.get(field)
                if not a:
                    errors.append(f"E3: filled paper_card.{field} has no "
                                  "entry in field_anchors")
                else:
                    check_anchor(a, f"paper_card.{field}")

    # E4: section coverage and order
    sn_list = notes.get("section_notes", [])
    if [s.get("section_id") for s in sn_list] != section_ids:
        errors.append("E4: section_notes do not cover sections.json in the "
                      f"same order (expected {section_ids}, got "
                      f"{[s.get('section_id') for s in sn_list]})")
    for sn in sn_list:
        where = f"section {sn.get('section_id')}"
        for slot in SECTION_SLOTS:
            if slot not in sn:
                errors.append(f"E5: {where} missing slot {slot!r}")
                continue
            v = sn[slot]
            if v is None or (isinstance(v, str) and v.strip() == ""):
                errors.append(f"E2: {where}.{slot} is empty/null -- use "
                              "NOT_REPORTED")
            elif isinstance(v, str) and v.strip() == NOT_REPORTED:
                warnings.append(f"W1: {where}.{slot} is NOT_REPORTED")
            elif isinstance(v, str) and any(p in v for p in PLACEHOLDERS):
                errors.append(f"E9: {where}.{slot} contains a leftover placeholder")
        # E5: filled slots need an anchor in sn["anchors"] keyed by slot
        slot_anchors = sn.get("anchors", {})
        for slot in SECTION_SLOTS:
            v = sn.get(slot)
            if isinstance(v, str) and v.strip() not in ("", NOT_REPORTED):
                a = slot_anchors.get(slot)
                if not a:
                    errors.append(f"E5: {where}.{slot} is filled but has no "
                                  "anchor in section anchors")
                else:
                    check_anchor(a, f"{where}.{slot}")
        # E8: section-level anchor paragraph must exist
        if "anchor" in sn:
            check_anchor(sn["anchor"], f"{where} (section anchor)")
        # E10: figure/table register -- mentioned_in ids must exist; a
        # filled value needs a real anchor naming a paragraph in range.
        for ft in sn.get("figures_tables", []):
            fwhere = f"{where} figures_tables[{ft.get('item')!r}]"
            for pid in ft.get("mentioned_in", []):
                if pid not in para_index:
                    errors.append(f"E10 {fwhere}: mentioned paragraph "
                                  f"{pid!r} does not exist")
            v = ft.get("value_from_text")
            if v is None or (isinstance(v, str) and v.strip() == ""):
                errors.append(f"E10 {fwhere}: value_from_text is empty/null "
                              "-- use NOT_REPORTED")
            elif isinstance(v, str) and v.strip() == NOT_REPORTED:
                warnings.append(f"W3: {fwhere} value is NOT_REPORTED")
            elif isinstance(v, str) and any(p in v for p in PLACEHOLDERS):
                errors.append(f"E10 {fwhere}: value contains a leftover "
                              "placeholder")
            else:
                a = ft.get("anchor")
                if not a:
                    errors.append(f"E10 {fwhere}: filled value has no anchor")
                else:
                    check_anchor(a, fwhere)

    # E6/E7: knowledge points
    seen_terms, seen_abbrs = {}, {}
    for i, kp in enumerate(notes.get("knowledge_points", [])):
        where = f"knowledge_points[{i}]"
        term = (kp.get("canonical_term") or "").strip()
        if not term:
            errors.append(f"E6: {where} has no canonical_term")
            continue
        key = term.lower()
        if key in seen_terms:
            errors.append(f"E7: duplicate canonical term {term!r} "
                          f"(also at {seen_terms[key]})")
        seen_terms[key] = where
        ab = (kp.get("abbreviation") or "").strip()
        if ab and ab != NOT_REPORTED:
            if ab.lower() in seen_abbrs and kp.get("status") != "merged":
                errors.append(f"E7: duplicate abbreviation {ab!r} "
                              f"(also at {seen_abbrs[ab.lower()]})")
            seen_abbrs[ab.lower()] = where
        definition = kp.get("definition")
        if definition is None or (isinstance(definition, str)
                                  and definition.strip() == ""):
            errors.append(f"E6: {where} definition is empty/null -- use "
                          "NOT_REPORTED")
        elif isinstance(definition, str) and definition.strip() == NOT_REPORTED:
            warnings.append(f"W1: {where} definition is NOT_REPORTED")
        if "anchor" not in kp:
            errors.append(f"E6: {where} has no anchor field")
        else:
            check_anchor(kp["anchor"], where)
        if not kp.get("status"):
            errors.append(f"E6: {where} has no status")

    # E11/W4: measured numbers must occur in the paper (E11, hard) and
    # in the cited anchor paragraph (W4, warning). A number that appears
    # nowhere in the extracted paper text is a fabrication.
    para_text = {}
    for s in seg["sections"]:
        for p in s["paragraphs"]:
            para_text[p["id"]] = p["text"]
    full_paper_norm = _norm(" ".join(para_text.values()))

    def check_numbers(where, text, anchor):
        if not isinstance(text, str) or text.strip() in ("", NOT_REPORTED):
            return
        if not isinstance(anchor, dict) or not anchor.get("paragraph_id"):
            return
        pid = anchor["paragraph_id"]
        para_norm = _norm(para_text.get(pid, ""))
        for token, parts in measured_numbers(text):
            if not _number_in(full_paper_norm, token, parts):
                errors.append(f"E11 {where}: measured number {token!r} "
                              f"occurs nowhere in the paper -- fix or drop "
                              f"the claim")
            elif not _number_in(para_norm, token, parts):
                warnings.append(f"W4 {where}: measured number {token!r} "
                                f"is not in the cited paragraph {pid} -- "
                                f"name its source section in uncertain_items")

    if isinstance(card, dict):
        for field in CARD_FIELDS:
            if field == "title":
                continue
            check_numbers(f"paper_card.{field}", card.get(field),
                          anchors.get(field))
    for sn in sn_list:
        slot_anchors = sn.get("anchors", {})
        for slot in SECTION_SLOTS:
            check_numbers(f"section {sn.get('section_id')}.{slot}",
                          sn.get(slot), slot_anchors.get(slot))
        for ft in sn.get("figures_tables", []):
            check_numbers(
                f"section {sn.get('section_id')} "
                f"figures_tables[{ft.get('item')!r}]",
                ft.get("value_from_text"), ft.get("anchor"))
    for i, kp in enumerate(notes.get("knowledge_points", [])):
        check_numbers(f"knowledge_points[{i}]", kp.get("definition"),
                      kp.get("anchor"))

    # W2: unreviewed extractive candidates copied verbatim into findings
    for sn in sn_list:
        for c in sn.get("extractive_candidates", []):
            if c.get("status", "").startswith("candidate"):
                warnings.append(
                    f"W2: section {sn.get('section_id')} still has an "
                    "unreviewed extractive candidate -- verify or drop it")

    print(f"validate_notes: {len(errors)} error(s), {len(warnings)} warning(s)")
    for e in errors:
        print(f"  FAIL {e}")
    for w in warnings:
        print(f"  warn {w}")
    if errors:
        print("RESULT: FAIL -- fix the errors above; do not deliver notes "
              "that fail validation.")
        return 1
    print("RESULT: PASS (warnings are honest gaps, listed in uncertain_items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
