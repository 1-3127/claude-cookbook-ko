from typing import Any

import numpy as np
from rouge_score import rouge_scorer


def rouge_eval(summary, ground_truth, threshold=0.3) -> float:
    """
    ROUGE score로 요약을 평가합니다.

    Args:
    summary (str): 평가할 요약.
    ground_truth (str): ground_truth 요약.
    threshold (float): ROUGE score의 threshold(기본값: 0.3).

    Returns:
    bool: 평균 ROUGE score가 threshold보다 높으면 True, 그렇지 않으면 False.
    """
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(summary, ground_truth)

    # 평균 ROUGE score 계산
    avg_rouge = np.mean(
        [scores["rouge1"].fmeasure, scores["rouge2"].fmeasure, scores["rougeL"].fmeasure]
    )

    return float(avg_rouge)


def get_assert(output: str, context, threshold=0.3) -> bool | float | dict[str, Any]:
    ground_truth = context["vars"]["ground_truth"]
    score = rouge_eval(output, ground_truth)

    if score >= threshold:
        return {"pass": True, "score": score, "reason": "Average score is above threshold"}
    else:
        return {"pass": False, "score": score, "reason": "Average score is below threshold"}
