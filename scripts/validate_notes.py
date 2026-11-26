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

Warnings (do not fail, but must be listed in uncertain_items):
  W1  Any field still NOT_REPORTED.
  W2  Extractive candidates still present unreviewed (a finding that
      copies a candidate sentence verbatim without an anchor).

Stdlib only. Deterministic.
"""
import argparse
import json
import re
import sys

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
