#!/usr/bin/env python3
"""Build the chapter-aligned notes skeleton from segmented paper text.

Usage:
  python3 build_notes.py --sections /app/work/sections.json
                         --case-id <id from /input/case.json>
                         --out-json /app/work/notes.json
                         --out-md   /app/work/notes.md
                         --out-index /app/work/index.json

What it does (deterministic, mechanical extraction only -- it does NOT
write interpretive claims):
  1. Paper card skeleton: title taken from the first non-heading paragraph
     of front-matter (or "NOT_REPORTED"); every other field starts as
     "NOT_REPORTED" for the agent to fill from the source with an anchor.
     Nothing is guessed from the title or from field names.
  2. One section note per detected section, in the paper's own order, each
     with purpose/method/result/conclusion/link slots (NOT_REPORTED until
     the agent fills them) and the section's paragraph anchors.
  3. Extractive candidates: for each section, up to 3 sentences that
     contain a number, a percent, or a result cue word -- labelled
     "candidate" so the agent verifies each one against the paragraph
     before promoting it to a finding. Candidates are never presented as
     findings by this script.
  3b. Figure/table register: every Figure/Table mentioned in the
     section's paragraphs, with the paragraph(s) that mention it.
     Values are NOT extracted from the figure/table itself (a text
     extractor cannot read a chart) -- the agent records the value the
     surrounding text states, with an anchor, or leaves it
     NOT_REPORTED. A finding that cites a figure without a value from
     the text is not a verified finding.
  4. Term candidates: abbreviation definitions "Full Name (ABBR)" found in
     the text, and repeated capitalised phrases; grouped under a canonical
     term with variants, for the agent to confirm/merge per the dedup
     rules in SKILL.md. Unconfirmed terms stay status="candidate".
  5. Search index (index.json): every section, candidate term and anchor,
     so notes are retrievable by keyword without re-reading the paper.

The agent's job after this script: read the sections in order, fill the
NOT_REPORTED slots with claims copied/checked against the cited
paragraph, attach an anchor to every filled claim, then run
validate_notes.py. Any slot the agent cannot support from the text stays
NOT_REPORTED -- it is never filled with a plausible invention.
"""
import argparse
import json
import re
import sys
from collections import Counter

SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")
ABBR_RE = re.compile(r"([A-Za-z][A-Za-z\-]+(?:\s+[a-z][A-Za-z\-]+){0,4})"
                      r"\s*\(([A-Z]{2,10})\)")
NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|percent|mg|g|mL|nm|°C|K|h|min|s\b)")
RESULT_CUES = re.compile(
    r"\b(show|shows|showed|demonstrat|increas|decreas|reduc|improv|significan|"
    r"achiev|obtain|found|reveal|conclude|表明|提高|降低|增加|减少|证明|发现|结果)\w*",
    re.IGNORECASE)
CAP_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")


def split_sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def candidates(paras, limit=3):
    scored = []
    for p in paras:
        for s in split_sentences(p["text"]):
            score = 0
            if NUM_RE.search(s):
                score += 2
            if RESULT_CUES.search(s):
                score += 1
            if len(s) > 40:
                score += 1
            if score >= 2:
                scored.append((score, len(s), s, p["id"], p["page"]))
    scored.sort(key=lambda t: (-t[0], t[1]))
    out, seen = [], set()
    for _, _, s, pid, page in scored:
        if s in seen:
            continue
        seen.add(s)
        out.append({"sentence": s, "paragraph_id": pid, "page": page,
                    "status": "candidate -- verify against the paragraph "
                              "before using as a finding"})
        if len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", required=True)
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-index", required=True)
    args = ap.parse_args()
    with open(args.sections, encoding="utf-8") as f:
        seg = json.load(f)
    sections = seg["sections"]

    title = "NOT_REPORTED"
    for s in sections:
        if s["title"] == "front-matter" and s["paragraphs"]:
            first = s["paragraphs"][0]["text"]
            if len(first) < 300:
                title = first
            break
    if title == "NOT_REPORTED":
        for s in sections:
            if s["paragraphs"]:
                title = s["paragraphs"][0]["text"][:200]
                break

    # Abbreviation definitions and repeated capitalised phrases.
    # Abbreviations are searched per paragraph (never across paragraph
    # boundaries) so a title line cannot glue itself onto a definition.
    abbrs = {}
    for s in sections:
        for p in s["paragraphs"]:
            for full, ab in ABBR_RE.findall(p["text"]):
                full = re.sub(r"^(A|An|The)\s+", "", full.strip())
                # A real definition has at least one lowercase word; this
                # rejects all-caps fragments and heading debris.
                if any(w and w[0].islower() for w in full.split()):
                    abbrs.setdefault(ab, set()).add(full)
    full_text = " ".join(p["text"] for s in sections for p in s["paragraphs"])
    cap_counts = Counter(CAP_PHRASE_RE.findall(full_text))
    terms = []
    for ab, fulls in sorted(abbrs.items()):
        terms.append({"canonical": sorted(fulls)[0], "abbreviation": ab,
                      "variants": sorted(fulls),
                      "status": "candidate -- confirm the definition in the text"})
    for phrase, n in cap_counts.most_common(20):
        if n >= 3 and phrase not in [t["canonical"] for t in terms]:
            terms.append({"canonical": phrase, "abbreviation": "NOT_REPORTED",
                          "variants": [phrase], "occurrences": n,
                          "status": "candidate -- confirm it is a real term, "
                                    "not a heading fragment"})

    section_notes = []
    index_entries = []
    for s in sections:
        first = s["paragraphs"][0] if s["paragraphs"] else None
        anchor = {"section": s["title"], "section_id": s["id"],
                  "page_start": s["page_start"], "page_end": s["page_end"]}
        if first is not None:
            # Point the section anchor at its first real paragraph so the
            # anchor always names a paragraph that exists (validator E8).
            anchor["paragraph_id"] = first["id"]
            anchor["page"] = first["page"]
        # Figure/table register for this section: one entry per distinct
        # Figure/Table mentioned in its paragraphs (mechanical only --
        # values come from the agent reading the citing text, never
        # guessed from the label).
        ft_register = {}
        for p in s["paragraphs"]:
            for item in list(p.get("figures", [])) + list(p.get("tables", [])):
                ft_register.setdefault(item, {"item": item,
                                              "mentioned_in": [],
                                              "value_from_text": "NOT_REPORTED",
                                              "anchor": "NOT_REPORTED -- attach section/paragraph/page after verifying",
                                              "status": "candidate -- record the value the citing text states, or leave NOT_REPORTED"})
                if p["id"] not in ft_register[item]["mentioned_in"]:
                    ft_register[item]["mentioned_in"].append(p["id"])
        section_notes.append({
            "section_id": s["id"], "section_title": s["title"],
            "page_start": s["page_start"], "page_end": s["page_end"],
            "paragraph_ids": [p["id"] for p in s["paragraphs"]],
            "purpose": "NOT_REPORTED", "method": "NOT_REPORTED",
            "result": "NOT_REPORTED", "conclusion": "NOT_REPORTED",
            "link_to_next_section": "NOT_REPORTED",
            "anchor": anchor,
            "figures_tables": sorted(ft_register.values(),
                                     key=lambda e: e["item"]),
            "extractive_candidates": candidates(s["paragraphs"]),
        })
        index_entries.append({"kind": "section", "term": s["title"],
                              "note_id": s["id"], "anchor": anchor})
    for t in terms:
        index_entries.append({"kind": "term", "term": t["canonical"],
                              "note_id": None, "anchor": None,
                              "status": t["status"]})

    notes = {
        "case_id": args.case_id,
        "status": "partial -- skeleton built by script; interpretive fields "
                  "NOT_REPORTED until the agent fills them with anchors",
        "paper_card": {
            "title": title,
            "research_question": "NOT_REPORTED",
            "data": "NOT_REPORTED",
            "methods": "NOT_REPORTED",
            "key_findings": "NOT_REPORTED",
            "limitations": "NOT_REPORTED",
            "premises_for_conclusions": "NOT_REPORTED",
            "field_anchors": {},
        },
        "section_notes": section_notes,
        "knowledge_points": [
            {"canonical_term": t["canonical"],
             "abbreviation": t["abbreviation"],
             "variants": t["variants"],
             "definition": "NOT_REPORTED",
             "anchor": "NOT_REPORTED -- attach section/paragraph/page after verifying",
             "status": t["status"]} for t in terms],
        "uncertain_items": list(seg.get("warnings", [])),
        "sources": {"extraction": "extract_text.py + segment.py (this run)",
                    "sections_detected": len(sections)},
    }
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(f"# Structured notes (SKELETON) -- case {args.case_id}\n\n")
        f.write("> Skeleton built mechanically by build_notes.py. Every "
                "NOT_REPORTED slot must be filled by the agent from the "
                "cited paragraph, or left NOT_REPORTED. Nothing here is a "
                "verified finding yet.\n\n")
        f.write(f"## Paper card\n\n- Title: {title}\n")
        for k in ("research_question", "data", "methods", "key_findings",
                  "limitations", "premises_for_conclusions"):
            f.write(f"- {k}: NOT_REPORTED\n")
        for sn in section_notes:
            f.write(f"\n## {sn['section_title']} "
                    f"(pp. {sn['page_start']}-{sn['page_end']}, {sn['section_id']})\n\n")
            for k in ("purpose", "method", "result", "conclusion",
                      "link_to_next_section"):
                f.write(f"- {k}: NOT_REPORTED\n")
            if sn["extractive_candidates"]:
                f.write("- Extractive candidates (verify before use):\n")
                for c in sn["extractive_candidates"]:
                    f.write(f"  - \"{c['sentence']}\" "
                            f"[{c['paragraph_id']}, p.{c['page']}]\n")
            if sn["figures_tables"]:
                f.write("- Figures/tables mentioned (record the value the "
                        "citing text states, or leave NOT_REPORTED):\n")
                for ft in sn["figures_tables"]:
                    f.write(f"  - {ft['item']}: mentioned in "
                            f"{', '.join(ft['mentioned_in'])}; value: "
                            f"NOT_REPORTED\n")
        f.write("\n## Knowledge points (candidates)\n\n")
        for t in notes["knowledge_points"]:
            f.write(f"- {t['canonical_term']} ({t['abbreviation']}): "
                    f"definition NOT_REPORTED; status: {t['status']}\n")
        f.write("\n## Uncertain / limits\n\n")
        for u in notes["uncertain_items"]:
            f.write(f"- {u}\n")
        if not notes["uncertain_items"]:
            f.write("- None recorded by the scripts.\n")

    with open(args.out_index, "w", encoding="utf-8") as f:
        json.dump({"case_id": args.case_id, "entries": index_entries},
                  f, ensure_ascii=False, indent=2)
    print(f"built skeleton: {len(sections)} section note(s), "
          f"{len(terms)} term candidate(s), {len(index_entries)} index entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
