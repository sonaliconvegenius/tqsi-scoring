"""T-QSI assessment tool, built from T-QSI Policy v1.0 (14 October 2026).

Scope (per the plan approved for this build):
  - Checks: E1-E5, E7, E8, E9 (errors); N1-N3, C1-C3 (quality).
  - Not evaluated: E6, N4, P1. Flags REF is not raised. R2 and R3 are not used.
  - E8 is checked against R1 (Annex C, r1_rules.json), by language and grade band.
  - Section 8 validation is deferred. No flag NC is added for validation.

Subcommands:
  precheck items.json [--r1 r1_rules.json]          code evidence per item (policy 2.2)
  score items.json judgements.json [--precheck f]   verify quotes, score, report (policy 2.4, 3.4, 4.5, 5, 6)
  hash items.json                                   SHA-256 of the input file (policy 2.6)

Stdlib only. The AI judges; this script verifies and scores.
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Policy 3.3: severity of each error check. E6 is not evaluated.
ERROR_SEVERITY = {
    "E1": "Critical", "E2": "Critical", "E3": "Critical", "E4": "Critical", "E5": "Critical",
    "E7": "Major", "E8": "Major",
    "E9": "Minor",
}
# Policy 4.3: quality question of each check. N4 and P1 are not evaluated.
QUALITY_QUESTION = {"N1": "Q1", "N2": "Q1", "N3": "Q1", "C1": "Q3", "C2": "Q3", "C3": "Q3"}
EVALUATED = set(ERROR_SEVERITY) | set(QUALITY_QUESTION)
REMOVED = {"E6": "not evaluated", "N4": "not evaluated", "P1": "not evaluated"}

SCRIPT_RANGES = {"hi": (0x0900, 0x097F), "te": (0x0C00, 0x0C7F)}  # policy 2.2: script check
DIGIT_MAP = {
    **{ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")},
    **{ord(c): str(i) for i, c in enumerate("౦౧౨౩౪౫౬౭౮౯")},
}
BLANK_RE = re.compile(r"_{2,}")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
LATIN_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]+(?:\.[A-Za-z]+)*\.?(?![A-Za-z])")
MATHS_RE = re.compile(r"\\\((.*?)\\\)|\$(.*?)\$", re.S)
# Policy 5.1 IMG: a picture in the English question or any option. Markers as they appear in the question bank.
IMAGE_RE = re.compile(r"\[image\]|<img|/uploads/|\.(?:png|jpe?g|gif|svg)\b", re.I)


def nfc(text):
    return unicodedata.normalize("NFC", text or "")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fields_of(side):
    """Map each part name (policy 'Part' definition) to its text: question, option n, key."""
    out = {"question": side.get("question", "")}
    for i, opt in enumerate(side.get("options", []), start=1):
        out[f"option {i}"] = opt
    out["key"] = side.get("key", "")
    return out


def has_image(item):
    """Policy 5.1: IMG when the English question or any English option has a picture."""
    if item.get("image"):
        return True
    return any(IMAGE_RE.search(t or "") for t in fields_of(item["source"]).values())


def band_for(item, r1):
    """Annex C band for an item: hi_1_5, hi_6_10 or te. None when the grade is missing."""
    if item.get("lang") == "te":
        return "te"
    grade = item.get("grade")
    if not isinstance(grade, int) or not 1 <= grade <= 10:
        return None
    return "hi_1_5" if grade <= 5 else "hi_6_10"


def r1_status(token_rules, band):
    """Return (translate_tokens, keep_tokens) for a band from the R1 rules."""
    translate, keep = set(), set()
    for rule in token_rules:
        bucket = translate if rule.get(band) == "translate" else keep
        bucket.update(rule["tokens"])
    return translate, keep


def present(token, text):
    return re.search(r"(?<![A-Za-z])" + re.escape(token) + r"(?![A-Za-z])", text) is not None


def maths_segments(text):
    return sorted({re.sub(r"\s+", "", a or b) for a, b in MATHS_RE.findall(text or "")})


def precheck_item(item, token_rules):
    src, tgt, lang = item["source"], item["target"], item.get("lang", "hi")
    sf, tf = fields_of(src), fields_of(tgt)
    out = {"item_id": item["item_id"], "lang": lang, "grade": item.get("grade"), "image": has_image(item)}

    # Policy 2.2: counts. Matching pairs and answer steps are not counted by code.
    out["option_count"] = {"source": len(src.get("options", [])), "target": len(tgt.get("options", []))}
    out["blank_count"] = {"source": len(BLANK_RE.findall(sf["question"])),
                          "target": len(BLANK_RE.findall(tf["question"]))}

    # Policy 2.2: numbers and maths expressions (evidence only; X3 allows format change).
    out["numbers"] = {
        "source": sorted(set(NUMBER_RE.findall(sf["question"].translate(DIGIT_MAP)))),
        "target": sorted(set(NUMBER_RE.findall(tf["question"].translate(DIGIT_MAP)))),
    }
    out["maths_differs"] = [name for name in sf if maths_segments(sf[name]) != maths_segments(tf.get(name, ""))]

    # Policy 2.2: script and display. Fields identical in both languages are not translated; skip them.
    script_issues, display_issues = [], []
    lo, hi = SCRIPT_RANGES.get(lang, (None, None))
    for name, text in tf.items():
        if sf.get(name) == text:
            continue
        if lo is not None and text.strip() and not any(lo <= ord(c) <= hi for c in text):
            script_issues.append({"part": name, "issue": "no target-script characters"})
        if text.count("\\(") != text.count("\\)") or text.count("$") % 2:
            display_issues.append({"part": name, "issue": "unclosed maths delimiter"})
    out["script_issues"] = script_issues
    out["display_issues"] = display_issues

    # Policy 2.2 and 7.3: English letters in the target. Evidence for E8 and X4; the AI decides.
    band = band_for(item, None)
    src_text = " ".join(sf.values())
    tgt_text = " ".join(tf.values())
    if band is None:
        out["r1_band"] = None
        out["r1_note"] = "R1 band cannot be set (grade missing or outside 1-10): E8 evidence not computed"
        out["english_in_target"] = sorted(set(LATIN_RE.findall(tgt_text)))
        return out
    out["r1_band"] = band
    translate, keep = r1_status(token_rules, band)
    src_latin = set(LATIN_RE.findall(src_text))
    tgt_latin = set(LATIN_RE.findall(tgt_text))
    # Annex C "translate": English is not allowed in the target for this band, even if copied from the source.
    out["r1_translate_found"] = sorted(t for t in translate if present(t, tgt_text))
    # 7.3: English not allowed by R1 counts as E8. Copied maths letters are X4 and are left to the AI.
    out["english_not_in_source_or_allowed"] = sorted(t for t in tgt_latin if t not in src_latin and t not in keep)
    out["english_in_target"] = sorted(tgt_latin)
    return out


def excerpt_ok(excerpt, field_text, is_target):
    """Policy 2.4: the quoted words must appear in that part after NFC normalisation."""
    if is_target and excerpt == "<absent>":
        return True
    return bool(excerpt) and nfc(excerpt) in nfc(field_text)


def score_item(item_id, findings, undecidable, image, sen):
    """Policy 3.4, 3.5, 4.1, 4.5, 5.1 and 6.1 for one item."""
    tests = [f["test"] for f in findings]
    und = {u["test"] for u in undecidable}
    error_tests = [t for t in tests if t in ERROR_SEVERITY]
    quality_tests = [t for t in tests if t in QUALITY_QUESTION]

    flags = set()
    if image:
        flags.add("IMG")
    if sen:
        flags.add("SEN")
    if und:
        flags.add("UND")

    if und & set(ERROR_SEVERITY):
        error_out, band = "n/a", None
    else:
        severities = [ERROR_SEVERITY[t] for t in error_tests]
        if "Critical" in severities:
            error_score = 0
        else:
            error_score = max(0, 100 - 25 * severities.count("Major") - 5 * severities.count("Minor"))
        error_out = error_score
        band = ("100" if error_score == 100 else "75-99" if error_score >= 75
                else "1-74" if error_score >= 1 else "0")

    if error_out == "n/a":
        rating = "n/a"
    elif error_out == 0:
        rating = "not rated"
    elif {QUALITY_QUESTION[t] for t in und if t in QUALITY_QUESTION}:
        rating = "n/a"
        flags.add("UND")
    else:
        failing = {QUALITY_QUESTION[t] for t in quality_tests}
        rating = "Good" if not failing else "Fair" if len(failing) == 1 else "Poor"

    flag_text = " ".join(sorted(flags))
    line = f"{item_id} · {error_out} · {rating}" + (f" · {flag_text}" if flag_text else "")
    return {"item_id": item_id, "error_score": error_out, "band": band, "rating": rating,
            "flags": sorted(flags), "line": line}


def set_report(scored):
    numeric = [s for s in scored if s["error_score"] != "n/a"]
    rated = [s for s in scored if s["rating"] in ("Good", "Fair", "Poor")]
    report = {
        "items_scored": len(numeric),
        "items_n_a": len(scored) - len(numeric),
        "bands": {b: sum(1 for s in numeric if s["band"] == b) for b in ("100", "75-99", "1-74", "0")},
        "ratings": {r: sum(1 for s in rated if s["rating"] == r) for r in ("Good", "Fair", "Poor")},
        "flags": {f: sum(1 for s in scored if f in s["flags"]) for f in ("IMG", "SEN", "UND")},
    }
    if numeric:
        report["mean_error_score"] = round(sum(s["error_score"] for s in numeric) / len(numeric), 2)
    return report


def cmd_precheck(args):
    items = load_json(args.items)
    r1 = load_json(args.r1 or HERE / "r1_rules.json")
    out = []
    for item in items:
        if not (item.get("source", {}).get("question") and item.get("target", {}).get("question")):
            out.append({"item_id": item.get("item_id"), "skipped": "not scorable: question text is empty"})
            continue
        out.append(precheck_item(item, r1["rules"]))
    json.dump({"r1_version": r1.get("version", "none"), "items": out},
              sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_score(args):
    items = {i["item_id"]: i for i in load_json(args.items)}
    judgements = load_json(args.judgements)
    r1_rules = load_json(args.r1 or HERE / "r1_rules.json")["rules"]
    pre_doc = load_json(args.precheck) if args.precheck else {}
    pre_map = {p["item_id"]: p for p in pre_doc.get("items", [])}

    scored, discarded, report_items = [], [], []
    for j in judgements:
        item_id = j["item_id"]
        item = items.get(item_id)
        if item is None:
            discarded.append({"item_id": item_id, "reason": "no matching item in items file"})
            continue
        sf, tf = fields_of(item["source"]), fields_of(item["target"])
        kept = []
        for f in j.get("findings", []):
            test, field = f.get("test"), f.get("field", "")
            if test in REMOVED:
                discarded.append({"item_id": item_id, "test": test, "reason": f"check {test} {REMOVED[test]} in this tool"})
                continue
            if test not in EVALUATED:
                discarded.append({"item_id": item_id, "test": test, "reason": "unknown check code"})
                continue
            if test == "E8":
                band = band_for(item, None)
                if band is None:
                    discarded.append({"item_id": item_id, "test": test, "reason": "R1 band not set: E8 cannot be checked (7.3)"})
                    continue
                _, keep = r1_status(r1_rules, band)
                if f.get("target_excerpt", "").strip() in keep:
                    discarded.append({"item_id": item_id, "test": test, "reason": f"English allowed by R1 for this band (Annex C, 7.3)"})
                    continue
            if test in QUALITY_QUESTION and not f.get("rewrite"):
                discarded.append({"item_id": item_id, "test": test, "reason": "quality finding without a better wording (4.3)"})
                continue
            if field not in sf:
                discarded.append({"item_id": item_id, "test": test, "reason": f"unknown part '{field}'"})
                continue
            if not excerpt_ok(f.get("source_excerpt", ""), sf[field], False):
                discarded.append({"item_id": item_id, "test": test, "reason": "English quote not found in its part (2.4)"})
                continue
            if not excerpt_ok(f.get("target_excerpt", ""), tf.get(field, ""), True):
                discarded.append({"item_id": item_id, "test": test, "reason": "translated quote not found in its part (2.4)"})
                continue
            kept.append({**f, "verified": True})

        if any(f['test'] == 'E1' for f in kept):
            kept = [f for f in kept if f['test'] == 'E1']
        scored_item = score_item(item_id, kept, j.get("undecidable", []),
                                 has_image(item), j.get("sen_flag", False))
        scored_item["findings"] = kept
        report_items.append(scored_item)
        scored.append(scored_item)

    report = {
        "items": [{k: v for k, v in s.items() if k != "line"} for s in report_items],
        "set_report": set_report(scored),
        "discarded_findings": discarded,
        "run_record": {
            "r1_version": pre_doc.get("r1_version", "not recorded"),
            "ai_model": args.model or "not recorded",
            "ai_instructions_version": args.prompt_version or "not recorded",
            "input_hash_sha256": hashlib.sha256(Path(args.items).read_bytes()).hexdigest(),
        },
    }
    from calculate_batch import calculate_batch
    report['batch_calculation'] = calculate_batch(report, list(items.values()))
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()
    for s in report_items:
        print(s["line"], file=sys.stderr)


def cmd_hash(args):
    print(hashlib.sha256(Path(args.items).read_bytes()).hexdigest())


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="T-QSI assessment tool (T-QSI Policy v1.0)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("precheck")
    pc.add_argument("items")
    pc.add_argument("--r1", help="R1 rules file (default: r1_rules.json beside this script)")
    pc.set_defaults(func=cmd_precheck)

    ps = sub.add_parser("score")
    ps.add_argument("items")
    ps.add_argument("judgements")
    ps.add_argument("--precheck")
    ps.add_argument("--r1", help="R1 rules file (default: r1_rules.json beside this script)")
    ps.add_argument("--model", help="AI model used for judgement (recorded, policy 2.6)")
    ps.add_argument("--prompt-version", help="AI instructions version (recorded, policy 2.6)")
    ps.set_defaults(func=cmd_score)

    ph = sub.add_parser("hash")
    ph.add_argument("items")
    ph.set_defaults(func=cmd_hash)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
