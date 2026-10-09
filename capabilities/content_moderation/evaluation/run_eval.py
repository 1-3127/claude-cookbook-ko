"""모든 domain에 걸친 end-to-end 평가.

../data/ 아래 각 domain에 대해:
  1. rule 가져오기. ad_creatives는 직접 작성한 golden ruleset 사용; 다른 domain은
     Claude가 policies.md에서 compile(./compiled/<domain>.json에 cache;
     새 compile을 강제하려면 cache 삭제).
  2. samples.jsonl의 모든 sample에서 field 추출(각각 Claude 호출 한 번;
     sample에 이미지가 있으면 vision 사용).
  3. deterministic하게 평가하고 결정을 sample의 기대 label과 비교.

results.json을 기록하고 domain별 표 출력.

capabilities/content_moderation/에서 실행:   python evaluation/run_eval.py
ANTHROPIC_API_KEY의 Anthropic API key 필요(이 script 옆의 .env 파일도 가능)."""

import json
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv()

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from engine import evaluate, validate_document  # noqa: E402
from pipeline import compile_policies, extract_fields  # noqa: E402

COMPILED = HERE / "compiled"
COMPILED.mkdir(exist_ok=True)

DOMAINS = ["ad_creatives", "product_listings", "ugc"]


def load_domain(name: str) -> dict:
    d = ROOT / "data" / name
    return {
        "dir": d,
        "schema": json.loads((d / "schema.json").read_text()),
        "context": json.loads((d / "context.json").read_text()),
        "policies": (d / "policies.md").read_text(),
        "samples": [
            json.loads(line)
            for line in (d / "samples.jsonl").read_text().splitlines()
            if line.strip()
        ],
    }


def rules_for(name: str, dom: dict) -> dict:
    if name == "ad_creatives":
        return json.loads((dom["dir"] / "rules.golden.json").read_text())
    cache = COMPILED / f"{name}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    print(f"  compiling {name} policies with Claude…")
    doc, attempts = compile_policies(dom["policies"], dom["schema"], dom["context"])
    print(
        f"  compiled in {len(attempts)} round(s): {len(doc['rules'])} rules, "
        f"{len(doc.get('derived_fields', {}))} derived, {len(doc.get('uncompilable', []))} uncompilable"
    )
    cache.write_text(json.dumps(doc, indent=2))
    return doc


def main() -> None:
    results = {"domains": {}, "totals": {"correct": 0, "n": 0}}
    for name in DOMAINS:
        dom = load_domain(name)
        doc = rules_for(name, dom)
        problems = validate_document(doc, dom["schema"], dom["context"])
        if problems:
            raise ValueError(f"{name}: ruleset fails static validation: {problems}")

        print(f"\n═══ {name} — {len(doc['rules'])} rules, {len(dom['samples'])} samples")
        rows = []
        for s in dom["samples"]:
            image = dom["dir"] / s["image"] if s.get("image") else None
            fields = extract_fields(
                s["submission"], dom["schema"], doc.get("derived_fields", {}), image_path=image
            )
            verdict = evaluate(doc["rules"], fields, s["context"])
            ok = verdict.decision == s["expected"]
            rows.append(
                {
                    "name": s["name"],
                    "expected": s["expected"],
                    "got": verdict.decision,
                    "ok": ok,
                    "fired": [r.rule_id for r in verdict.fired],
                    "unknown": [r.rule_id for r in verdict.unknown],
                }
            )
            mark = "✓" if ok else "✗"
            print(
                f"  {mark} {s['name']:<38} expected {s['expected']:<12} got {verdict.decision:<12} "
                f"fired: {', '.join(r.rule_id for r in verdict.fired) or '—'}"
            )
        correct = sum(r["ok"] for r in rows)
        results["domains"][name] = {"rows": rows, "correct": correct, "n": len(rows)}
        results["totals"]["correct"] += correct
        results["totals"]["n"] += len(rows)
        print(f"  → {correct}/{len(rows)} decisions correct")

    t = results["totals"]
    print(
        f"\n═══ TOTAL: {t['correct']}/{t['n']} decisions correct "
        f"({100 * t['correct'] / t['n']:.0f}%)"
    )
    (HERE / "results.json").write_text(json.dumps(results, indent=2))
    print(f"results written to {HERE / 'results.json'}")


if __name__ == "__main__":
    main()
