"""guide.ipynb가 사용하는 deterministic rule engine.

Compiled artifact(compiler가 생성하는 것)
-------------------------------------------
{
  "derived_fields": {                      # compiler에 필요한 LLM-judged boolean; runtime에
    "<name>": {"type": ["boolean","null"], # extraction schema로 병합(여전히 Claude 호출은 한 번)
               "judge": "<instruction>", "source_policy": "1.1"}
  },
  "rules": [
    {
      "id": "nj_gambling_helpline",
      "policy_ref": "5.1",
      "policy_text": "In New Jersey, gambling creatives must display the 1-800-GAMBLER helpline.",
      "action": "block" | "flag",
      "scope": <condition>,                # 선택 사항. rule 적용 대상. context ∪ fields에
                                           # 대해 평가(이름 충돌 시 context 우선).
                                           # scope 없음 = 모든 곳에 적용.
      "when": <condition>                  # 위반. 추출된 field(derived 포함)에 대해 평가.
                                           # rule 발동 => 정책 위반.
    }
  ],
  "uncompilable": [                        # schema field와 LLM judgment 어느 쪽에도
    {"policy_ref": "...", "policy_text": "...", "reason": "..."}   # 대응하지 않는 조항(예: 외부 데이터 필요)
  ]
}

<condition> grammar(scope와 when에 동일):
  {"all": [...]} | {"any": [...]} | {"not": <condition>}
  {"field": "<name>", "op": "<operator>", "value": <literal>}

Operator: eq, neq, gt, gte, lt, lte, in, not_in, contains, not_contains, regex, exists

Three-valued logic
------------------
Extraction은 null("이미지에서 알 수 없음")을 반환할 수 있고 context는 key를 생략할 수 있음.
누락/null 값에 대한 assertion은 UNKNOWN(None)으로 평가되어 Kleene 방식으로 전파됨.
  scope=False        -> out_of_scope(건너뛰지만 log에는 기록)
  scope=True/absent  -> when: True->fired, False->clear, None->unknown
  scope=None         -> when: False->clear, else->unknown   (fail-safe, fail-open 아님)
결과에 영향을 줄 수 있는 unknown은 확신에 찬 판정 대신 "needs_review" 결정을 만듦."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

OPS = {
    "eq": lambda a, v: a == v,
    "neq": lambda a, v: a != v,
    "gt": lambda a, v: a > v,
    "gte": lambda a, v: a >= v,
    "lt": lambda a, v: a < v,
    "lte": lambda a, v: a <= v,
    "in": lambda a, v: a in v,
    "not_in": lambda a, v: a not in v,
    "contains": lambda a, v: (v.lower() in a.lower()) if isinstance(a, str) else (v in a),
    "not_contains": lambda a, v: (
        (v.lower() not in a.lower()) if isinstance(a, str) else (v not in a)
    ),
    "regex": lambda a, v: re.search(v, str(a), re.IGNORECASE) is not None,
    "exists": lambda a, v: True,  # 아래에서 별도 처리; a가 None이 아닐 때만 도달
}


@dataclass
class Step:
    """audit trail의 한 줄: leaf assertion 또는 all/any/not connective."""

    field: str
    op: str
    expected: Any
    actual: Any
    result: bool | None
    depth: int = 0
    group: bool = False  # True = 이 줄은 leaf가 아닌 all/any/not connective


@dataclass
class RuleResult:
    rule_id: str
    action: str
    outcome: str  # "fired" | "clear" | "unknown" | "out_of_scope"
    scope_trace: list[Step] = field(default_factory=list)
    trace: list[Step] = field(default_factory=list)
    scope_result: bool | None = True  # True = scope 안 / scope 조항 없음


@dataclass
class Verdict:
    decision: str  # "block" | "flag" | "needs_review" | "approve"
    fired: list[RuleResult]
    unknown: list[RuleResult]
    clear: list[RuleResult]
    out_of_scope: list[RuleResult]

    @staticmethod
    def _fmt(steps: list[Step], indent: str) -> list[str]:
        out = []
        for s in steps:
            mark = {True: "T", False: "F", None: "?"}[s.result]
            pad = indent + "  " * s.depth
            if s.group:
                out.append(f"{pad}{mark}  {s.op}:")
            else:
                rhs = "" if s.op == "exists" else f" {s.expected!r}"
                out.append(f"{pad}{mark}  {s.field} {s.op}{rhs}  (actual: {s.actual!r})")
        return out

    def explain(self) -> str:
        lines = [f"DECISION: {self.decision.upper()}"]
        for r in self.fired:
            lines.append(f"  ✗ [{r.action}] {r.rule_id}")
            if r.scope_trace:
                lines.append("      scope:")
                lines += self._fmt(r.scope_trace, "        ")
            lines += self._fmt(r.trace, "      ")
        for r in self.unknown:
            missing = sorted(
                {s.field for s in r.scope_trace + r.trace if s.result is None and not s.group}
            )
            why = "scope indeterminate" if r.scope_result is None else "could not determine"
            lines.append(f"  ? [{r.action}] {r.rule_id}  — {why}: {', '.join(missing)}")
        if self.out_of_scope:
            lines.append(f"  – out of scope: {', '.join(r.rule_id for r in self.out_of_scope)}")
        if not self.fired and not self.unknown:
            lines.append(f"  ✓ all {len(self.clear)} applicable rules clear")
        return "\n".join(lines)


def _eval(cond: dict, values: dict, trace: list[Step], depth: int = 0) -> bool | None:
    for connective in ("all", "any", "not"):
        if connective in cond:
            header = Step("", connective, None, None, None, depth, group=True)
            trace.append(header)
            children = cond[connective] if connective != "not" else [cond[connective]]
            results = [_eval(c, values, trace, depth + 1) for c in children]
            if connective == "all":
                out = (
                    False
                    if any(r is False for r in results)
                    else (None if any(r is None for r in results) else True)
                )
            elif connective == "any":
                out = (
                    True
                    if any(r is True for r in results)
                    else (None if any(r is None for r in results) else False)
                )
            else:
                out = None if results[0] is None else (not results[0])
            header.result = out
            return out

    name, op, expected = cond["field"], cond["op"], cond.get("value")
    actual = values.get(name)
    if op == "exists":
        result: bool | None = actual is not None
    elif actual is None:
        result = None
    else:
        try:
            result = bool(OPS[op](actual, expected))
        except (TypeError, re.error):
            result = None
    trace.append(Step(name, op, expected, actual, result, depth))
    return result


def evaluate_rule(rule: dict, fields: dict, context: dict | None = None) -> RuleResult:
    context = context or {}
    rr = RuleResult(rule["id"], rule.get("action", "flag"), "clear")

    if "scope" in rule:
        # 충돌 시 context 우선; scope는 추출 field(예: ad_category)를 기준으로 삼을 수도 있음
        rr.scope_result = _eval(rule["scope"], {**fields, **context}, rr.scope_trace)
        if rr.scope_result is False:
            rr.outcome = "out_of_scope"
            return rr

    w = _eval(rule["when"], fields, rr.trace)
    if rr.scope_result is None:  # 적용 여부를 확인할 수 없음: 확실한 통과만 안전함
        rr.outcome = "clear" if w is False else "unknown"
    else:
        rr.outcome = "fired" if w is True else "clear" if w is False else "unknown"
    return rr


def evaluate(rules: list[dict], fields: dict, context: dict | None = None) -> Verdict:
    results = [evaluate_rule(r, fields, context) for r in rules]
    fired = [r for r in results if r.outcome == "fired"]
    unknown = [r for r in results if r.outcome == "unknown"]
    clear = [r for r in results if r.outcome == "clear"]
    oos = [r for r in results if r.outcome == "out_of_scope"]
    if any(r.action == "block" for r in fired):
        decision = "block"
    elif fired:
        decision = "flag"
    elif unknown:
        decision = "needs_review"
    else:
        decision = "approve"
    return Verdict(decision, fired, unknown, clear, oos)


# ---------------------------------------------------------------------------
# compiled document의 static validation. 실행 전에 compiler가 존재하지 않는
# field를 참조하거나, 선언하지 않은 context key로 scope를 정하거나, enum을
# 집합 밖의 값과 비교하는 등의 문제를 잡아냄. compiler의 retry loop는
# 이를 Claude에 다시 전달.
# ---------------------------------------------------------------------------

NUMERIC_OPS = {"gt", "gte", "lt", "lte"}
LIST_OPS = {"in", "not_in"}


def _check_condition(cond: Any, props: dict, path: str, problems: list[str]) -> None:
    if not isinstance(cond, dict):
        problems.append(f"{path}: condition must be an object")
        return
    keys = [k for k in ("all", "any", "not", "field") if k in cond]
    if len(keys) != 1:
        problems.append(f"{path}: must have exactly one of all/any/not/field, got {list(cond)}")
        return
    k = keys[0]
    if k in ("all", "any"):
        if not isinstance(cond[k], list) or not cond[k]:
            problems.append(f"{path}.{k}: must be a non-empty list")
            return
        for i, c in enumerate(cond[k]):
            _check_condition(c, props, f"{path}.{k}[{i}]", problems)
        return
    if k == "not":
        _check_condition(cond["not"], props, f"{path}.not", problems)
        return

    name, op = cond.get("field"), cond.get("op")
    if name not in props:
        problems.append(f"{path}: unknown field {name!r} (available: {sorted(props)})")
        return
    if op not in OPS:
        problems.append(f"{path}: unknown op {op!r}")
        return
    spec = props[name]
    ftype = spec.get("type")
    types = set(ftype) if isinstance(ftype, list) else {ftype}
    types.discard("null")
    val = cond.get("value")
    if op in NUMERIC_OPS and not types & {"number", "integer"}:
        problems.append(f"{path}: op {op!r} needs a numeric field, {name!r} is {ftype}")
    if op in LIST_OPS and not isinstance(val, list):
        problems.append(f"{path}: op {op!r} needs a list value")
    if "enum" in spec and op in ("eq", "neq") and val not in spec["enum"]:
        problems.append(f"{path}: {val!r} not in enum for {name!r}: {spec['enum']}")
    if "enum" in spec and op in LIST_OPS and isinstance(val, list):
        bad = [v for v in val if v not in spec["enum"]]
        if bad:
            problems.append(f"{path}: {bad!r} not in enum for {name!r}: {spec['enum']}")
    if op == "regex":
        try:
            re.compile(str(val))
        except re.error as e:
            problems.append(f"{path}: invalid regex {val!r}: {e}")


def validate_document(
    doc: dict, schema: dict, context_schema: dict | None = None
) -> dict[str, list[str]]:
    """전체 compiled artifact {derived_fields, rules, uncompilable} 검증.

    {rule_id_or_section: [problems]} 반환; 빈 dict는 형식이 올바름을 뜻함.
    - 'when'은 schema field + derived field를 참조할 수 있음.
    - 'scope'는 context key + schema field + derived field를 참조할 수 있음."""
    out: dict[str, list[str]] = {}
    derived = doc.get("derived_fields", {})

    dprobs: list[str] = []
    for name, spec in derived.items():
        if name in schema.get("properties", {}):
            dprobs.append(f"derived field {name!r} collides with schema field")
        if not spec.get("judge"):
            dprobs.append(f"derived field {name!r} missing 'judge' instruction")
    if dprobs:
        out["derived_fields"] = dprobs

    field_props = {**schema.get("properties", {}), **derived}
    scope_props = {**field_props, **(context_schema or {}).get("properties", {})}

    seen: set[str] = set()
    for r in doc.get("rules", []):
        rid = r.get("id", "<missing id>")
        probs: list[str] = []
        for key in ("id", "when"):
            if key not in r:
                probs.append(f"rule missing '{key}'")
        if r.get("action") not in (None, "block", "flag"):
            probs.append(f"action must be 'block' or 'flag', got {r.get('action')!r}")
        if rid in seen:
            probs.append(f"duplicate rule id {rid!r}")
        seen.add(rid)
        if "scope" in r:
            _check_condition(r["scope"], scope_props, f"{rid}.scope", probs)
        if "when" in r:
            _check_condition(r["when"], field_props, f"{rid}.when", probs)
        if probs:
            out.setdefault(rid, []).extend(probs)
    return out
