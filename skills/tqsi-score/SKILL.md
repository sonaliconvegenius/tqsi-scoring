---
name: tqsi-score
description: Score translated PAL questions (English to Hindi or Telugu) with the T-QSI Policy v1.0 assessment tool. Use when asked to score, check or rate translated questions, produce T-QSI error scores or quality ratings, or review a translation file against the T-QSI policy.
---

# T-QSI scoring

Each question gets two separate results: an **error score** (0–100) and a **quality rating** (Good / Fair / Poor), plus flags. Never combine the two.

The source of truth is the T-QSI Policy v1.0 (14 October 2026). This tool implements its checks: E1–E5, E7, E8, E9, N1–N3, C1–C3, with R1 (Annex C) for E8.

## Not evaluated in this tool

- E6 (wrong glossary term), N4 and P1 (style list checks).
- The REF flag, and the R2 glossary and R3 style list. They are not used.
- Suggested additions to R3.

Section 8 validation has not been run, so results are not validated. Say so when reporting.

## Split of work

- **You (the AI)** judge each question once, following `JUDGING_INSTRUCTIONS.md` in this skill folder. Write `judgements.json`.
- **`scripts/tqsi_tool.py`** runs the code checks, verifies every quote against its part, and computes the score, bands, rating, flags and report. Do not compute scores yourself.

## Inputs

An items file (JSON array), one object per question:

```json
{
  "item_id": "45-HI",
  "lang": "hi",
  "grade": 4,
  "image": false,
  "source": { "question": "...", "options": ["...", "..."], "key": "..." },
  "target": { "question": "...", "options": ["...", "..."], "key": "..." }
}
```

- `lang` is `hi` or `te`.
- `grade` is an integer 1–10. It sets the Annex C band for Hindi. Without it, E8 cannot be checked and is reported as undecidable.
- `image` is `true` when the English question has a picture (IMG).
- Questions with empty question text are not scored.
- Ask for the file path if it was not given. Do not invent items.

## Steps

1. **Precheck (code).**
   ```bash
   python "<plugin folder>/scripts/tqsi_tool.py" precheck items.json > precheck.json
   ```
   Gives option and blank counts, numbers, maths-expression differences, script and display checks, and English letters in the target with their R1 status. This is evidence for the judge.

2. **Judge (AI).** Follow `skills/tqsi-score/JUDGING_INSTRUCTIONS.md`. One judgement per item, in the form it specifies. Use the precheck as evidence. Quote exact words. Give a rewrite for every quality finding.

3. **Score (code).**
   ```bash
   python "<plugin folder>/scripts/tqsi_tool.py" score items.json judgements.json --precheck precheck.json --model "<model>" --prompt-version "<version>" > report.json
   ```
   Verifies each quote (NFC, exact match in its part), discards any finding that fails, applies R1 to E8, and computes the results. One line per item goes to stderr: `item · error score · rating · flags`.

4. **Record the input hash** if needed:
   ```bash
   python "<plugin folder>/scripts/tqsi_tool.py" hash items.json
   ```

5. **Report artifact.** Read `OUTPUT_CONTRACT.md` in this skill folder. Generate an HTML evaluator report and companion JSON using `scripts/render_output.py`. Show the clickable artifact, per-target overview, exact findings, proposed corrections, coverage, next actions and discarded evidence. Offer Document Version 2, then Version 3 if needed, and compare fresh assessments. Keep the current scorer values unchanged.

## Rules that are easy to get wrong

- Error score = 100 − 25 × Major − 5 × Minor, floor 0. Any Critical finding makes it 0.
- Bands: 100, 75–99, 1–74, 0.
- Quality is rated only when the error score is above 0. A zero score reads `0 · not rated`.
- Rating: no failing quality question = Good; one = Fair; two or three = Poor. Count questions, not findings.
- E3 applies only when the English key is correct. A wrong English key is outside this policy.
- E8 follows Annex C for the item's band. English that Annex C allows is not reported, and the tool discards such findings.
- Roman numerals (i, ii, iii) are allowed in every band in Annex C, as written. Annex C says this is not yet confirmed by the Translation lead.
- Flags: IMG (English has a picture), SEN (adds gender, caste, religion, class or stereotype content; Content Governance reviews it), UND (a check could not be decided).


## Output V2.0

The agreed evaluator output is defined in [OUTPUT_CONTRACT.md](OUTPUT_CONTRACT.md). Always provide the evaluator artifact when assessing content. Open `assets/evaluator-output-v2.html` for a worked ten-question example, clearly labelled as a past test rather than results for a newly uploaded file. New evaluations must render their own scorer report. Section 8 validation remains deferred; do not turn it or dropped R2/R3 checks into a scoring gate.
