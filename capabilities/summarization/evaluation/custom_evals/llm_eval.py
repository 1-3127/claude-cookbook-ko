import json
import os
from typing import Any

import anthropic


def llm_eval(summary, input):
    """
    LLM (Claude)으로 요약을 평가합니다.

    Args:
    summary (str): 평가할 요약.
    input (str): 요약된 원본 텍스트.

    Returns:
    bool: 평균 score가 threshold보다 높으면 True, 그렇지 않으면 False.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # 여기에도 예제를 포함하면 성능을 더 개선할 수 있습니다!
    prompt = f"""Evaluate the following summary based on these criteria:
    1. Conciseness (1-5)
    2. Accuracy (1-5)
    3. Completeness (1-5)
    4. Clarity (1-5)
    5. Explanation - a general description of the way the summary is evaluatied

    Here are some things to think about as you go about grading.

    1. Does the summary accurately capture the key provisions of the legal document?
    2. Does the summary omit any important details from the legal document?
    3. Does the summary contain any inaccuracies or misrepresentations of the legal document?
    4. Does the summary fairly represent the legal document as a whole, or does it unduly emphasize certain provisions over others?
    5. Does the summary accurately reflect the language and tone of the legal document?
    6. Does the summary capture the key concepts and principles embodied in the legal document?
    7. Does the summary omit any important ideas that should be captured to make decisions using the document?

    Provide a score for each criterion in JSON format. Here is the format you should follow always:

    <json>
    {{
    "conciseness": <number>,
    "accuracy": <number>,
    "completeness": <number>,
    "clarity": <number>,
    "explanation": <string>,
    }}
    </json>

    Original Text: {input}

    Summary to Evaluate: {summary}

    Evaluation (JSON format):"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}, {"role": "assistant", "content": "<json>"}],
        stop_sequences=["</json>"],
    )

    evaluation = json.loads(response.content[0].text)
    # 숫자가 아닌 값을 걸러내고 평균 계산
    numeric_values = [value for key, value in evaluation.items() if isinstance(value, (int, float))]
    avg_score = sum(numeric_values) / len(numeric_values)
    return avg_score, evaluation["explanation"]


def get_assert(output: str, context, threshold=0.5) -> bool | float | dict[str, Any]:
    input = context["vars"]["input"]
    score, evaluation = llm_eval(output, input)

    # 성능을 측정하는 서로 다른 4개 차원
    normalized_score = score / 4

    if normalized_score >= threshold:
        return {"pass": True, "score": score, "reason": evaluation}
    else:
        return {"pass": False, "score": score, "reason": evaluation}
