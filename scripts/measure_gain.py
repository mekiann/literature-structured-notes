#!/usr/bin/env python3
"""Measure the verifiability scorecard of a completed notes.json.

Usage:
  python3 measure_gain.py --notes /app/work/notes.json
                          --sections /app/work/sections.json
                          [--out /app/work/gain.json]
                          [--baseline /app/work/notes-baseline.json]

What it does (deterministic, stdlib only -- it measures, it does not judge):
  Counts what the notes actually deliver, so the gain of using this Skill
  over a free-form summary can be stated with numbers instead of adjectives:
    - section coverage (one note per detected section, in order)
    - share of filled claims that carry a real anchor (paragraph + page)
    - share of paper-card fields filled (not NOT_REPORTED)
    - knowledge points verified vs still candidate
    - figure/table register entries resolved vs still NOT_REPORTED
    - NOT_REPORTED slots remaining (honest gaps, listed in uncertain_items)
    - extractive candidates still unreviewed

  With --baseline, the same scorecard is computed for a second notes.json
  (a real run of the same paper through a base agent without the Skill,
  or an earlier version of this Skill on the same paper) and a delta
  block is added. The baseline file must be a real run's output -- never
  an invented number. The delta is evidence for the "gain" fields of
  result.json (quality gain / gain verifiability in task.md SS2).

The scorecard is evidence for the "gain" fields of result.json
(quality gain / gain verifiability in task.md SS2). It compares the
notes against the paper's own structure -- it does NOT invent a baseline
score. A fair baseline comparison is documented in SKILL.md step 7:
run the same paper through a base agent without the Skill, score both
outputs with this script, and record both scorecards in result.json.

Exit 0 always (a low score is a finding, not a crash); the JSON it
writes is the record. Never edit the numbers by hand.
"""
import argparse
import json
import sys

CARD_FIELDS = ["title", "research_question", "data", "methods",
               "key_findings", "limitations", "premises_for_conclusions"]
SECTION_SLOTS = ["purpose", "method", "result", "conclusion",
                 "link_to_next_section"]
NOT_REPORTED = "NOT_REPORTED"


def is_filled(v):
    return isinstance(v, str) and v.strip() not in ("", NOT_REPORTED)


def has_real_anchor(a):
    return (isinstance(a, dict) and a.get("paragraph_id")
            and a.get("page") is not None)


def scorecard(notes, seg):
    section_ids = [s["id"] for s in seg["sections"]]

    card = notes.get("paper_card", {})
    anchors = card.get("field_anchors", {})
    card_filled = sum(1 for fld in CARD_FIELDS if is_filled(card.get(fld)))
    card_anchored = sum(1 for fld in CARD_FIELDS
                        if is_filled(card.get(fld))
                        and has_real_anchor(anchors.get(fld)))

    sn_list = notes.get("section_notes", [])
    coverage = ([s.get("section_id") for s in sn_list] == section_ids)
    slots_filled = slots_anchored = 0
    ft_total = ft_resolved = 0
    unreviewed = 0
    for sn in sn_list:
        slot_anchors = sn.get("anchors", {})
        for slot in SECTION_SLOTS:
            if is_filled(sn.get(slot)):
                slots_filled += 1
                if has_real_anchor(slot_anchors.get(slot)):
                    slots_anchored += 1
        for ft in sn.get("figures_tables", []):
            ft_total += 1
            if is_filled(ft.get("value_from_text")):
                ft_resolved += 1
        for c in sn.get("extractive_candidates", []):
            if str(c.get("status", "")).startswith("candidate"):
                unreviewed += 1

    kps = notes.get("knowledge_points", [])
    kp_verified = sum(1 for kp in kps if kp.get("status") == "verified")
    kp_candidate = sum(1 for kp in kps
                       if str(kp.get("status", "")).startswith("candidate"))
    kp_merged = sum(1 for kp in kps if kp.get("status") == "merged")

    not_reported = (len(CARD_FIELDS) - card_filled)
    for sn in sn_list:
        not_reported += sum(1 for slot in SECTION_SLOTS
                            if not is_filled(sn.get(slot)))
        not_reported += sum(1 for ft in sn.get("figures_tables", [])
                            if not is_filled(ft.get("value_from_text")))
    not_reported += sum(1 for kp in kps
                        if not is_filled(kp.get("definition")))

    total_filled = card_filled + slots_filled
    total_anchored = card_anchored + slots_anchored
    ratio = (total_anchored / total_filled) if total_filled else 1.0

    return {
        "case_id": notes.get("case_id"),
        "section_coverage": {"covered": len(sn_list),
                             "detected": len(section_ids),
                             "in_order": coverage},
        "paper_card": {"filled": card_filled, "of": len(CARD_FIELDS),
                       "anchored": card_anchored},
        "section_slots": {"filled": slots_filled,
                          "anchored": slots_anchored},
        "anchored_claim_ratio": round(ratio, 3),
        "knowledge_points": {"total": len(kps), "verified": kp_verified,
                             "candidate": kp_candidate, "merged": kp_merged},
        "figures_tables": {"total": ft_total, "resolved": ft_resolved},
        "not_reported_remaining": not_reported,
        "unreviewed_extractive_candidates": unreviewed,
        "uncertain_items": len(notes.get("uncertain_items", [])),
        "note": "Scorecard measures this run only. For a baseline "
                "comparison, run the same paper without the Skill, "
                "score both with this script, and record both scorecards "
                "in result.json gain_evidence; never invent a baseline.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True)
    ap.add_argument("--sections", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--baseline", default=None,
                    help="a second notes.json (same paper, base agent "
                         "without the Skill, or an earlier Skill version) "
                         "to compare against; adds a delta block")
    args = ap.parse_args()
    with open(args.notes, encoding="utf-8") as f:
        notes = json.load(f)
    with open(args.sections, encoding="utf-8") as f:
        seg = json.load(f)
    card = scorecard(notes, seg)
    if args.baseline:
        with open(args.baseline, encoding="utf-8") as f:
            base_notes = json.load(f)
        base = scorecard(base_notes, seg)
        card["baseline"] = base
        card["delta_vs_baseline"] = {
            "anchored_claim_ratio":
                round(card["anchored_claim_ratio"]
                      - base["anchored_claim_ratio"], 3),
            "paper_card_filled":
                card["paper_card"]["filled"]
                - base["paper_card"]["filled"],
            "section_slots_filled":
                card["section_slots"]["filled"]
                - base["section_slots"]["filled"],
            "knowledge_points_verified":
                card["knowledge_points"]["verified"]
                - base["knowledge_points"]["verified"],
            "figures_tables_resolved":
                card["figures_tables"]["resolved"]
                - base["figures_tables"]["resolved"],
            "not_reported_remaining":
                card["not_reported_remaining"]
                - base["not_reported_remaining"],
            "unreviewed_extractive_candidates":
                card["unreviewed_extractive_candidates"]
                - base["unreviewed_extractive_candidates"],
            "note": "Positive delta = this run delivers more than the "
                    "baseline on the same paper and sections; a zero "
                    "delta is a finding, not a failure to hide.",
        }
    print(f"gain scorecard for {notes.get('case_id')}: "
          f"sections {card['section_coverage']['covered']}/"
          f"{card['section_coverage']['detected']} "
          f"(in order: {card['section_coverage']['in_order']}), "
          f"paper card {card['paper_card']['filled']}/"
          f"{card['paper_card']['of']} filled "
          f"({card['paper_card']['anchored']} anchored), "
          f"slots {card['section_slots']['filled']} filled "
          f"({card['section_slots']['anchored']} anchored), "
          f"anchored-claim ratio {card['anchored_claim_ratio']:.3f}, "
          f"knowledge points {card['knowledge_points']['verified']} "
          f"verified / {card['knowledge_points']['total']}, "
          f"figures/tables {card['figures_tables']['resolved']}/"
          f"{card['figures_tables']['total']} resolved, "
          f"{card['not_reported_remaining']} NOT_REPORTED remaining, "
          f"{card['unreviewed_extractive_candidates']} unreviewed "
          f"candidate(s)")
    if args.baseline:
        d = card["delta_vs_baseline"]
        print(f"delta vs baseline: anchored-claim ratio "
              f"{d['anchored_claim_ratio']:+.3f}, paper card filled "
              f"{d['paper_card_filled']:+d}, slots filled "
              f"{d['section_slots_filled']:+d}, knowledge points verified "
              f"{d['knowledge_points_verified']:+d}, figures/tables "
              f"resolved {d['figures_tables_resolved']:+d}, "
              f"NOT_REPORTED remaining {d['not_reported_remaining']:+d}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
