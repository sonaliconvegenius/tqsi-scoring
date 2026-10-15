# T-QSI judging instructions (AI judge)

Source: T-QSI Policy v1.0 (14 October 2026), T-QSI Policy v1.0.docx. Read §2, §3, §4, §5 and Annex C before judging. Where this file and the policy differ, the policy wins.

## Your task

Judge one item at a time against its English source. Make one judgement per item. Write the result to `judgements.json` in the form in section 4.

## Checks you evaluate

Errors (policy §3):
- E1 Structure (Critical): different number of options, blanks, matching pairs or answer steps; or one language has a picture where the other has text.
- E2 Display (Critical): a part will not display properly (unclosed maths or formatting, whole part in the wrong script, characters that show as boxes).
- E3 Answer (Critical): the option marked correct is wrong in the translation, or another option is also correct, while the English marked option is correct. If the English answer is wrong too, it is outside this policy (§1.4). Do not report it.
- E4 Task (Critical): different operation, different number of answers, "not" added or removed, or direction reversed.
- E5 Cannot be answered (Critical): an option or the key is in English (other than X4 or X5), or needed information is missing.
- E7 Meaning (Major): an object, number, condition word, comparison or name differs, or information is added or left out; the task and answer still work.
- E8 English left in (Major): any other English word in the translation, other than X4 or X5. One finding per distinct word or phrase per item. Apply Annex C: English that R1 does not allow for the item's band counts as E8. Do not report English that Annex C allows for that band.
- E9 Spelling and grammar (Minor): misspelling, wrong ending or gender/number match, wrong punctuation, stray character. One finding per word.

Quality (policy §4):
- N1 Repeated "one" (a / an translated word for word before each of two or more things).
- N2 Long "used for" phrase where a shorter phrase says the same.
- N3 "Which / that" clause where a shorter sentence without it says the same.
- C1 Incomplete sentence (no main verb where English has one).
- C2 Option does not fit the blank.
- C3 Unclear "this / it" (could refer to two things in the translation, one in the English).

Every quality finding must include a better wording (`rewrite`). A quality finding without one is discarded.

## Not evaluated (do not report)

- E6 (wrong glossary term). Not evaluated in this tool.
- N4 and P1 (style list checks). Not evaluated in this tool.
- REF flag. Not raised.
- Suggested additions to R3. Not produced.

## Pictures (policy §1.4, §5.1)

What a picture shows is outside this policy. Judge the text only. Do not mark a check undecidable only because a picture, figure or image option cannot be seen. The tool adds flag IMG when the English question or an option has a picture.

## Exclusions (policy §3.2): these are not errors

X1 different wording with the same objects, numbers, conditions and task; X2 grammar the language needs; X3 number written the local way; X4 letters kept on purpose (maths letters and labels, maths expressions, English allowed by R1); X5 English maths term in brackets right after the translated term; X6 accepted spelling or double space; X7 correct but awkward (judged under Part 2, not Part 1).

## Rules

- Record each problem once, under the first check it matches (§3.3). If E1 is found, no other check runs on that item. After E2 to E5, the other error checks still run.
- Quote exact words: `source_excerpt` from the English part, `target_excerpt` from the translated part. Use `<absent>` in `target_excerpt` when the whole part is missing. The tool checks every quote and discards any it cannot find (§2.4).
- For each check, answer clear, problem found, or cannot decide. Give a reason when you cannot decide. Put that check in `undecidable`.
- Set `sen_flag` true only when the translation adds gender, caste, religion, class or stereotype content the English does not have. Gender that grammar requires does not count.
- Use the `grade` and `lang` in the item for Annex C. If the grade is missing, E8 cannot be checked; report E8 as undecidable.

## 4. Output format (`judgements.json`)

A JSON array with one object per item:

```json
{
  "item_id": "45-HI",
  "findings": [
    {
      "test": "E7",
      "field": "question",
      "source_excerpt": "exact English words",
      "target_excerpt": "exact translated words, or <absent>",
      "defect": "one sentence saying what is wrong",
      "rewrite": null
    }
  ],
  "undecidable": [{"test": "N1", "reason": "..."}],
  "sen_flag": false
}
```

- `field` is `question`, `option N` (N counts from 1), or `key`.
- `rewrite` is required for N and C findings; use `null` for error findings.
- Do not include `verified` or `r3_candidate`.
