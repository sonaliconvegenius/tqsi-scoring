# Evaluator report

Always return a clickable HTML artifact and companion JSON for the actual assessment. The header prominently shows final overall decision score, decision, Critical/Major/Minor counts, raw mean and whether the 59 cap reduced the score. Repeat per target language. Never label the raw mean as the final result.

Include assessment name, Program Name, PoD Name, subject, grade/education level, languages, version; unknown values stay unrecorded. Preserve exact evidence, item scores, quality ratings, suggested corrections, discarded findings and coverage. Missing units remain visible. Do not present unscored terminology or sentence-construction concerns as clean language.

Metadata JSON uses assessment_name, program_name, pod_name, subject, grade, document_version, coverage. Suggestions map IDs to arrays of {test,field,suggested_correction}. Provide rewrites for quality findings.

Offer upload of Document Version2 then3, compare remaining/resolved/new/uncertain findings. The HTML file selector prepares a chat handoff only; it cannot execute evaluation. Release approval remains the programme owner's responsibility. Historical demo artifacts must be labelled as examples, never scores for a new upload.

Completion requires scripts/complete_assessment.py and delivery-manifest.json with ARTIFACTS VERIFIED. Final chat must link the generated HTML and JSON. Plain text, a table, or a POC document alone does not satisfy delivery. Identify version1.0.1 in acceptance checks.
