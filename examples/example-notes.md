# EXAMPLE output — structured notes for SAMPLE-001

> **EXAMPLE ONLY.** Produced by the builder's local test run on an
> invented SAMPLE paper ("Starch-Based Hydrogel for Controlled Release:
> A Laboratory Study", 1 page, written by the builder for testing).
> This is **not** an official case, not a real paper, and not a result.
> It shows the output format only. Every claim below was checked
> against the sample text paragraph cited in its anchor.

## Paper card

- **Title:** Starch-Based Hydrogel for Controlled Release: A Laboratory Study
- **Research question:** Whether a starch-based hydrogel can release a model dye in a controlled way. [§Introduction | s2.p1 | p.1]
- **Data:** Model dye; starch (5 g) in water (100 mL); three repeats, reported values are means. [§Methods | s3.p1 | p.1]
- **Methods:** Starch mixed with water, heated to 80 °C for 30 min; crosslinker 1% by weight; cast into moulds; dried at 40 °C for 12 h; release measured in water at 37 °C, samples every 2 h. [§Methods | s3.p1 | p.1]
- **Key findings:** 78% of the dye released within 24 h; doubling the crosslinker dose reduced release to 52% in the same period; dried samples kept their shape with no visible cracking. [§Results | s4.p1 | p.1 | Figure 2]
- **Limitations:** Only one model dye was tested; tests lasted 24 h only. [§Discussion | s5.p1 | p.1]
- **Premises for conclusions:** Conclusions hold for one model dye, in water at 37 °C, over 24 h, at the crosslinker doses tested; wider use for other molecules or longer times is not shown. [§Discussion | s5.p1 | p.1]

## Section notes (paper's own order)

### Abstract (s1, p.1)
- purpose: State what was prepared, what was measured, and the headline result.
- method: A starch-based hydrogel (SH) was prepared to test controlled release of a model dye.
- result: 78% released within 24 h at 37 °C; release slowed when the crosslinker dose was doubled.
- conclusion: The method is simple and cheap, but tested on one dye only.
- link to next: the question and headline result stated here are developed in the Introduction (s2).

### 1 Introduction (s2, p.1)
- purpose: Motivate the study — controlled release matters, existing hydrogels are expensive or hard to make, starch is cheap and available.
- conclusion: The paper asks whether a starch-based hydrogel can release a model dye in a controlled way.
- link to next: the question posed here is answered by the method in s3; Figure 1 shows the release setup used in all later tests.
- method / result: NOT_REPORTED (the Introduction states no method or result).

### 2 Methods (s3, p.1)
- purpose: Describe preparation and measurement so the experiment can be repeated.
- method: Starch (5 g) in water (100 mL), heated to 80 °C for 30 min; crosslinker 1% by weight; cast, dried at 40 °C for 12 h; release measured in water at 37 °C, samples every 2 h; three repeats, means reported.
- link to next: the procedure here produces the release values reported in s4.
- result / conclusion: NOT_REPORTED (the Methods section reports no result).

### 3 Results (s4, p.1)
- purpose: Report the measured release values.
- result: 78% released within 24 h (Figure 2); doubling the crosslinker dose reduced release to 52%; values per dose are in Table 1; samples kept their shape with no visible cracking.
- link to next: these values are interpreted in the Discussion (s5), including the diffusion-model match and the single-dye limit.
- method / conclusion: NOT_REPORTED.

### 4 Discussion (s5, p.1)
- purpose: Interpret the results and state what they do and do not show.
- result: Crosslinker dose controls release speed; the pattern matches a simple diffusion model.
- conclusion: The main claim is supported within the tested scope; it may not hold for other molecules, and longer tests are needed.
- link to next: the scoped conclusion here becomes the Conclusion (s6).

### 5 Conclusion (s6, p.1)
- purpose: Give the final, scoped answer to the research question.
- conclusion: A starch-based hydrogel can release a model dye in a controlled way, with release speed set by crosslinker dose; the method is cheap and simple; wider use needs tests on other molecules and over longer times.
- method / result / link to next: NOT_REPORTED (final section).

## Knowledge points

- **starch-based hydrogel (SH)** — a hydrogel made from starch, prepared here to test controlled release of a model dye. [§Abstract | s1.p1 | p.1] — status: verified.

## Uncertain / limits

- Front-matter section (s0) is the builder's SAMPLE label line and the paper title, not paper content; its slots are left NOT_REPORTED.
- Printed page numbers are not shown in the sample PDF; anchors use the physical PDF page (p.1).
- Figure 1, Figure 2 and Table 1 are cited in the text but their contents were not extracted (text-only sample); findings cite the text statements, not the figure contents.

## Validation

`validate_notes.py` on the filled notes: **PASS, exit 0** (0 errors;
15 warnings, all honest NOT_REPORTED slots listed above). The full
filled JSON is the file the validator checked; this Markdown is its
readable rendering.
