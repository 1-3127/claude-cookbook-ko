"""guide.ipynb가 사용하는 compiler와 extractor.

Compiler:  policies.md + schema.json + context.json --Claude--> {derived_fields, rules, uncompilable}
           validate_document() retry loop 사용(static error를 model에 다시 전달).
Extractor: content(텍스트 + 선택적 이미지) --Claude--> typed fields dict, output schema는
           schema.json ∪ derived_fields이며 structured output으로 강제.

이후 engine(engine.py)이 deterministic하게 평가. Claude는 판정을 결정하지 않음."""

from __future__ import annotations

import base64
import copy
import json
import pathlib
from typing import Any

import anthropic
from engine import validate_document

# Compilation은 정책 변경마다 한 번 실행하므로 가장 강력한 model 사용.
# Extraction은 콘텐츠마다 한 번 실행하므로 더 저렴하고 빠른 model 사용.
COMPILER_MODEL = "claude-opus-5"
EXTRACTOR_MODEL = "claude-sonnet-5"
MODEL = COMPILER_MODEL  # 하위 호환 alias

client: anthropic.Anthropic | None = None


def _client() -> anthropic.Anthropic:
    """호출자가 credential을 로드한 뒤 최초 사용 시 API client 생성."""
    global client
    if client is None:
        client = anthropic.Anthropic()
    return client


# ---------------------------------------------------------------------------
# Compiler: 자연어 정책 -> rule document
# ---------------------------------------------------------------------------

RULE_FORMAT_SPEC = """\
Emit a single JSON object with exactly these top-level keys:

{
  "derived_fields": {
    "<snake_case_name>": {
      "type": ["boolean", "null"],
      "judge": "<precise yes/no instruction for a vision+text model looking at the content. \
State when to answer null (cannot be determined / not applicable).>",
      "source_policy": "<clause number>"
    }
  },
  "rules": [
    {
      "id": "<clause>_<short_slug>",            // unique, e.g. "1.1a_alcohol_targeting_21"
      "policy_ref": "<clause number>",
      "policy_text": "<the clause, verbatim or lightly trimmed>",
      "action": "block" | "flag",               // block = reject outright; flag = human review
      "uses_llm_fields": <true iff 'when' references a derived field>,
      "scope": <condition>,                     // OPTIONAL: where the rule applies.
                                                // May reference CONTEXT keys and extracted fields.
                                                // Omit entirely if the rule applies everywhere.
      "when": <condition>                       // The VIOLATION over extracted fields (incl. derived).
                                                // Rule fires => policy breached.
    }
  ],
  "uncompilable": [
    {"policy_ref": "...", "policy_text": "...",
     "reason": "<why no field or judgment can decide this — e.g. requires external data>"}
  ]
}

<condition> grammar (same for scope and when):
  {"all": [<condition>, ...]}   |   {"any": [<condition>, ...]}   |   {"not": <condition>}
  {"field": "<name>", "op": "<op>", "value": <literal>}

Operators: eq, neq, gt, gte, lt, lte, in, not_in, contains, not_contains, regex, exists
- "exists" takes no value; {"not": {"field": f, "op": "exists"}} means "f is missing/null".
- "contains" on an array field checks membership; on a string field, case-insensitive substring.
- "regex" is case-insensitive.

Compilation rules:
1. Prefer operators over existing schema fields. If a clause cannot be expressed with
   operators, define a derived boolean field with a "judge" instruction and reference it.
   Only if a clause needs information available in NEITHER the content NOR the context
   (e.g. an external registry lookup), list it under "uncompilable" — never invent fields.
2. Split applicability from violation: "Alcohol ads must X" => scope: category==alcohol,
   when: NOT X. A clause with no applicability condition gets no "scope" key.
3. One clause listing several regions/categories compiles to ONE rule using the "in"
   operator — never duplicate a rule per value.
4. A clause with several independent requirements compiles to several rules (suffix ids
   a/b/c) so each violation is reported separately.
5. Missing-value semantics are handled by the engine (null => needs human review); do not
   add null-checks beyond what the policy asks for. To require a value is set, use "exists".
6. "when" may only reference extracted/derived fields. "scope" may also reference context keys.
"""


def compiler_prompt(policies: str, schema: dict, context_schema: dict) -> str:
    return f"""You are a policy compiler for a content-review system. Convert the natural-language
policy document below into machine-checkable rules over the extraction schema.

<extraction_schema>
Fields extracted from each piece of content by an extraction model:
{json.dumps(schema, indent=2)}
</extraction_schema>

<context_schema>
Facts supplied by the caller at evaluation time (NOT extracted from content).
Only "scope" conditions may reference these keys:
{json.dumps(context_schema, indent=2)}
</context_schema>

<rule_format>
{RULE_FORMAT_SPEC}
</rule_format>

<policy_document>
{policies}
</policy_document>

Compile every clause. Respond with the JSON object only — no prose, no markdown fences."""


def _parse_json_reply(text: str) -> dict:
    """JSON 주위에 실수로 붙은 markdown fence 허용."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1]
        t = t.rsplit("```", 1)[0]
    return json.loads(t)


def compile_policies(
    policies: str, schema: dict, context_schema: dict, max_repair_rounds: int = 3
) -> tuple[dict, list[dict]]:
    """정책 산문을 rule document로 compile하고 re-prompting으로 static error 수정.

    (document, transcript_of_attempts) 반환; transcript는 Notebook 독자에게
    validator가 무엇을 잡았고 model이 어떻게 수정했는지 보여줌."""
    messages: list[dict] = [
        {"role": "user", "content": compiler_prompt(policies, schema, context_schema)}
    ]
    attempts: list[dict] = []

    for round_no in range(max_repair_rounds + 1):
        with _client().messages.stream(
            model=COMPILER_MODEL,
            max_tokens=32000,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise RuntimeError("model response contained no text block")
        try:
            doc = _parse_json_reply(text)
            problems = validate_document(doc, schema, context_schema)
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            doc, problems = None, {"<parse>": [f"response was not valid JSON: {e}"]}

        attempts.append({"round": round_no, "problems": problems})
        if not problems:
            return doc, attempts

        messages.append({"role": "assistant", "content": text})
        messages.append(
            {
                "role": "user",
                "content": "Your compiled document has problems found by static validation against the schema. "
                "Fix ONLY these problems and respond with the full corrected JSON object:\n\n"
                + json.dumps(problems, indent=2),
            }
        )

    raise RuntimeError(
        f"compiler failed static validation after {max_repair_rounds} repairs: {problems}"
    )


def compile_single_rule(
    description: str, doc: dict, schema: dict, context_schema: dict, max_repair_rounds: int = 2
) -> dict:
    """일상적인 영어로 된 rule description 하나를 기존 ruleset에 맞춰 compile.

    추가 사항만 담긴 {"rules": [...], "derived_fields": {...}} 반환;
    적합한 기존 derived field를 재사용하고 반환 전 validate."""
    prompt = f"""You are a policy compiler for a content-review system. A reviewer wants to add ONE new
rule to an existing ruleset, described in natural language.

<extraction_schema>
{json.dumps(schema, indent=2)}
</extraction_schema>

<context_schema>
Caller-supplied placement facts. Only "scope" conditions may reference these keys:
{json.dumps(context_schema, indent=2)}
</context_schema>

<existing_derived_fields>
Reuse these when they fit instead of defining near-duplicates:
{json.dumps(doc.get("derived_fields", {}), indent=2)}
</existing_derived_fields>

<existing_rule_ids>
{json.dumps([r["id"] for r in doc["rules"]])}
</existing_rule_ids>

<rule_format>
{RULE_FORMAT_SPEC}
</rule_format>

<new_rule_description>
{description}
</new_rule_description>

A description with several distinct behaviors (e.g. flag generally but block outright in
one state) compiles to several rules; do not collapse or drop any part. Respond with a
JSON object only, no prose, no fences:
{{
  "rules": [ ... 1-4 rules; ids NOT in existing_rule_ids; policy_ref "custom" ... ],
  "derived_fields": {{ ... ONLY newly needed judged fields (empty object if none) ... }}
}}"""
    messages = [{"role": "user", "content": prompt}]
    for _ in range(max_repair_rounds + 1):
        response = _client().messages.create(
            model=COMPILER_MODEL, max_tokens=8000, messages=messages
        )
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise RuntimeError("model response contained no text block")
        out = _parse_json_reply(text)
        candidate = {
            "derived_fields": {**doc.get("derived_fields", {}), **out.get("derived_fields", {})},
            "rules": doc["rules"] + out.get("rules", []),
        }
        problems = validate_document(candidate, schema, context_schema)
        if not problems:
            return out
        messages += [
            {"role": "assistant", "content": text},
            {
                "role": "user",
                "content": "Static validation found problems. Fix ONLY these and "
                "respond with the full corrected JSON object:\n\n" + json.dumps(problems, indent=2),
            },
        ]
    raise RuntimeError(f"single-rule compile failed validation after retries: {problems}")


# ---------------------------------------------------------------------------
# Extractor: 콘텐츠 -> typed field(schema ∪ derived_fields, structured output)
# ---------------------------------------------------------------------------


def build_extraction_schema(schema: dict, derived_fields: dict) -> dict:
    """병합된 structured-outputs 호환 schema: 모든 property가 required이고,
    additionalProperties는 false이며 derived judge 텍스트는 description으로 전달."""
    out = copy.deepcopy(schema)
    out.pop("$comment", None)
    for name, spec in derived_fields.items():
        out["properties"][name] = {
            "type": spec.get("type", ["boolean", "null"]),
            "description": "JUDGMENT: " + spec["judge"],
        }
    for spec in out["properties"].values():
        spec.pop("$comment", None)
    out["required"] = sorted(out["properties"].keys())
    out["additionalProperties"] = False
    return out


EXTRACTOR_SYSTEM = """You are a content-analysis extractor for a policy-review pipeline.
You are given one content submission (text metadata, and an image when the content has one)
and a set of fields to extract. Fill every field.

Rules:
- Answer strictly from what is present in the submission. Do not guess.
- Where a field's type allows null, use null when the value genuinely cannot be determined
  from the submission — a downstream system routes those to human review. Never use null
  as a lazy default when the evidence is there.
- Fields whose description starts with "JUDGMENT:" require your judgment call on the stated
  question; apply the instruction literally.
- You decide nothing about policy. You only report what you observe."""


def extract_fields(
    submission: dict,
    schema: dict,
    derived_fields: dict,
    image_path: str | pathlib.Path | None = None,
) -> dict:
    """제출물 하나에서 typed field 추출. fields dict 반환."""
    content: list[dict[str, Any]] = []
    if image_path is not None:
        p = pathlib.Path(image_path)
        media_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }
        ext = p.suffix.lstrip(".").lower()
        if ext not in media_types:
            raise ValueError(f"unsupported image type: {p.suffix} (expected png, jpg, or webp)")
        media_type = media_types[ext]
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(p.read_bytes()).decode(),
                },
            }
        )
    content.append(
        {
            "type": "text",
            "text": "Submission metadata:\n"
            + json.dumps(submission, indent=2)
            + "\n\nExtract all fields.",
        }
    )

    response = _client().messages.create(
        model=EXTRACTOR_MODEL,
        max_tokens=4096,
        system=EXTRACTOR_SYSTEM,
        output_config={
            "format": {
                "type": "json_schema",
                "schema": build_extraction_schema(schema, derived_fields),
            }
        },
        messages=[{"role": "user", "content": content}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("model response contained no text block")
    return json.loads(text)
