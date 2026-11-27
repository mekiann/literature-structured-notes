#!/usr/bin/env python3
"""Check cross-field consistency of a filled notes.json (step 5b).

Usage:
  python3 check_consistency.py --notes /app/work/notes.json
                               --sections /app/work/sections.json
                               [--out /app/work/consistency.json]

The claim audit (SKILL.md step 5) is a reading task -- the agent re-reads
each cited paragraph. These five checks are the machine-checkable part of
that audit, run before validation so a structural inconsistency is caught
with a named check instead of slipping into the delivered notes:

  K1  FAIL: key_findings is filled but premises_for_conclusions is not.
      A finding without its premises must not be reused as a general
      claim (see templates/field-dictionary.md).
  K2  FAIL: a link_to_next_section that names a section id (sN) names a
      section other than the one that actually follows. A link that
      names no section id is a warning (a generic handover is not a
      real handover).
  K3  WARN: a measured number in key_findings does not appear in any
      section note's result/conclusion -- the card and the sections
      disagree about what was found.
  K4  WARN: a limitations item whose anchor paragraph contains no
      limitation cue word ("only", "limited", "not", "however", "仅",
      "局限", "不足", "然而" ...) and whose anchor section is not
      Discussion / Conclusion / Limitations may be invented from
      plausibility rather than stated -- re-read the paragraph.
  K5  FAIL: a knowledge point's definition anchor paragraph does not
      contain the canonical term (case-insensitive, hyphens ignored) --
      the definition is anchored to a paragraph that never names it.

Exit 0 = no failures (warnings are reported, not hidden); exit 1 = at
least one FAIL. The JSON report is copied into result.json as
consistency_record. Stdlib only. Deterministic.
"""
import argparse
import json
import re
import sys

NOT_REPORTED = "NOT_REPORTED"
SECTION_ID_RE = re.compile(r"\bs(\d+)\b")
LIMIT_CUES = re.compile(
    r"\b(only|limited|limitation|not|however|fail|despite|although|"
    r"remains unclear|further work)\b|仅|局限|不足|然而|未|没有|但是|尽管|有待",
    re.IGNORECASE)
# Measured numbers: same rule as validate_notes.py E11 (unit/%, decimal,
# range, or bare integer >= 100 not a round multiple of 10).
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
    t = t.replace("µ", "μ").replace("℃", "°C")
    t = re.sub(r"(\d)\s+(?=%|°C|°F|[a-zA-ZμÅ×])", r"\1", t)
    t = re.sub(r"(\d)\s*[-–—]\s*(\d)", r"\1-\2", t)
    return re.sub(r"\s+", " ", t)


def measured_numbers(claim):
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
        out.append((_norm(tok).replace(",", ""),
                    [d.replace(",", "") for d in digits]))
    return out


def _number_in(norm_text, token, parts):
    if re.search(r"(?<!\d)" + re.escape(token) + r"(?!\d)", norm_text):
        return True
    return all(re.search(r"(?<!\d)" + re.escape(p) + r"(?!\d)", norm_text)
               for p in parts)


def is_filled(v):
    return isinstance(v, str) and v.strip() not in ("", NOT_REPORTED)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True)
    ap.add_argument("--sections", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(args.notes, encoding="utf-8") as f:
        notes = json.load(f)
    with open(args.sections, encoding="utf-8") as f:
        seg = json.load(f)

    failures, warnings = [], []
    card = notes.get("paper_card", {})
    anchors = card.get("field_anchors", {})
    sn_list = notes.get("section_notes", [])
    sections = seg["sections"]
    para_text = {}
    para_section = {}
    for s in sections:
        for p in s["paragraphs"]:
            para_text[p["id"]] = p["text"]
            para_section[p["id"]] = s["id"]

    # K1: findings need premises.
    if is_filled(card.get("key_findings")) and not is_filled(
            card.get("premises_for_conclusions")):
        failures.append("K1: key_findings is filled but "
                        "premises_for_conclusions is NOT_REPORTED -- a "
                        "finding without its premises must not be reused "
                        "as a general claim")

    # K2: link_to_next_section must name the section that actually follows.
    for i, sn in enumerate(sn_list):
        link = sn.get("link_to_next_section")
        if not is_filled(link):
            continue
        nxt = sn_list[i + 1]["section_id"] if i + 1 < len(sn_list) else None
        named = [f"s{n}" for n in SECTION_ID_RE.findall(link)]
        if not named:
            warnings.append(f"K2: section {sn.get('section_id')} "
                            f"link_to_next_section names no section id -- "
                            f"a generic handover is not a real handover")
        elif nxt is None:
            warnings.append(f"K2: section {sn.get('section_id')} is the "
                            f"last section but its link names {named}")
        else:
            for nid in named:
                if nid != nxt:
                    failures.append(
                        f"K2: section {sn.get('section_id')} "
                        f"link_to_next_section names {nid} but the next "
                        f"section is {nxt}")

    # K3: numbers in key_findings must also appear in a section result.
    section_results = " ".join(
        _norm(" ".join(sn.get(slot) or "" for slot in ("result", "conclusion")))
        for sn in sn_list)
    if is_filled(card.get("key_findings")):
        for token, parts in measured_numbers(card["key_findings"]):
            if not _number_in(section_results, token, parts):
                warnings.append(
                    f"K3: key_findings number {token!r} appears in no "
                    f"section result/conclusion -- card and sections "
                    f"disagree about what was found")

    # K4: limitations must trace to a limitation cue or a Discussion-like
    # section, not to plausibility.
    if is_filled(card.get("limitations")):
        a = anchors.get("limitations")
        if isinstance(a, dict) and a.get("paragraph_id"):
            pid = a["paragraph_id"]
            ptext = para_text.get(pid, "")
            sec = next((s for s in sections
                        if s["id"] == para_section.get(pid)), None)
            sec_title = (sec or {}).get("title", "").lower()
            in_discussion = any(
                k in sec_title for k in ("discussion", "conclusion",
                                         "limitation", "讨论", "结论", "局限"))
            if not in_discussion and not LIMIT_CUES.search(ptext):
                warnings.append(
                    f"K4: limitations anchor {pid} contains no limitation "
                    f"cue word and is not in a Discussion/Conclusion "
                    f"section -- re-read the paragraph; the limitation "
                    f"may be invented from plausibility")

    # K5: a knowledge point's definition anchor must name the term.
    for i, kp in enumerate(notes.get("knowledge_points", [])):
        term = (kp.get("canonical_term") or "").strip()
        a = kp.get("anchor")
        if not term or not isinstance(a, dict) or not a.get("paragraph_id"):
            continue
        ptext = para_text.get(a["paragraph_id"], "")
        folded = re.sub(r"[-‐]", " ", ptext.lower())
        folded_term = re.sub(r"[-‐]", " ", term.lower())
        if folded_term not in folded:
            failures.append(
                f"K5: knowledge_points[{i}] {term!r} is not named in its "
                f"anchor paragraph {a['paragraph_id']} -- the definition "
                f"is anchored to a paragraph that never names it")

    report = {"case_id": notes.get("case_id"),
              "failures": failures, "warnings": warnings,
              "checks_run": ["K1", "K2", "K3", "K4", "K5"],
              "result": "FAIL" if failures else "PASS"}
    print(f"check_consistency: {len(failures)} failure(s), "
          f"{len(warnings)} warning(s)")
    for f in failures:
        print(f"  FAIL {f}")
    for w in warnings:
        print(f"  warn {w}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"wrote {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
