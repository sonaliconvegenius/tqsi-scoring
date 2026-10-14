# Evaluator output — V2.0

Applies to the latest Claude `tqsi-scoring` v0.2.0 tool built from the 14 October policy and subsequent user scope decisions. Never enable the older Codex package's validation gate or R2/R3 checks when reporting this tool's output.

## Required delivery

Every evaluation produces a clickable **HTML evaluator artifact** and its companion JSON, not just a score or a raw scorer dump. Use `scripts/render_output.py`; keep the scorer's values unchanged. Provide exact evidence and a proposed correction per error where the source supports one. Quality findings require rewrites. Do not auto-apply changes to the original document.

The evaluator sees:

1. Assessment name, Program Name, PoD Name, Subject, Grade/Education level, source/target languages and Document Version. Unknown metadata is “Not recorded”, never invented.
2. Overview for each target language: scored/unresolved counts, mean error score, bands, quality counts including not rated/n/a, flags and coverage. Error scores and quality ratings stay separate.
3. An actionable table: item ID, target language, error score, quality rating, finding and next action. Expandable details show source text, current translation, exact evidence and suggested correction.
4. A revision handoff for Document Version 2, then Version 3 if needed. The evaluator attaches the revised bilingual, trilingual or multilingual document in the plugin chat; the local report's file picker only prepares the request and never claims to run AI evaluation.
5. A fresh assessment and comparison: resolved, remaining, new candidates, uncertain, added/removed items, source/settings changes, separated by language. Stable finding IDs are preferable; textual changes alone are not proof of a new or resolved defect. Missing assessments, changed source/settings, or discarded evidence cannot establish resolution.
6. Final submitted results with outstanding actions and run record. “Final submitted” is not release approval.

## V2 coverage

Use R1/Annex C and the current scorer checks. E6, N4, P1, REF, R2, R3 and R3 suggestions are explicitly outside this build; their absence causes no score deduction and no NC flag. §8 validation is deferred to the team: report its pending status, without blocking or modifying scores. The ten-item test is limited positive-case evidence; it does not establish full gold-set validation.

The product intake design covers any subject, KG–12/Higher Ed and multiple target languages. The present scorer's operational policy is English→Hindi/Telugu with Hindi grade rules 1–10. Disclose that boundary rather than silently claiming other subjects/languages/levels have been validated. Word/PDF/Excel extraction is handled by the host assistant's supported readers; the local renderer accepts JSON.

## Generate the artifact

After the existing scoring command:

```
python scripts/render_output.py report.json items.json --metadata metadata.json --suggestions suggestions.json --out evaluator-output.html --json-out evaluator-output.json
```

Metadata includes assessment_name, program_name, pod_name, subject, grade, document_version and coverage. Suggestions map item IDs to arrays of `{test, field, suggested_correction}`. Do not use test labels to generate blind findings; add corrections only after findings are frozen when running a benchmark.

For reassessment, add `--previous-report previous-report.json --previous-items previous-items.json`. Supply both previous files so source changes can be verified. Display actual confirmed uncertainty and incomplete coverage; never add a second judge pass just to obtain a higher score.
