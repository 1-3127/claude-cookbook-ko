from typing import Any

import nltk
import numpy as np
from nltk.tokenize import word_tokenize
from nltk.translate.bleu_score import sentence_bleu

# 필요한 NLTK 데이터 다운로드
nltk.download("punkt", quiet=True)


def nltk_bleu_eval(output, ground_truth) -> float:
    """
    NLTK로 BLEU score를 계산하고 threshold에 대해 평가합니다.

    Args:
    output (str): 평가할 output.
    ground_truth (str): ground_truth output.
    threshold (float): BLEU score의 threshold(기본값: 0.5).

    Returns:
    tuple: (float, bool) - BLEU score 및 threshold 통과 여부.
    """
    # 요약 tokenize
    output_tokens = word_tokenize(output.lower())
    ground_truth_tokens = word_tokenize(ground_truth.lower())

    try:
        # BLEU score 계산
        # 참고: sentence_bleu는 reference 목록을 받으므로 reference_tokens를 목록으로 감쌉니다
        bleu_score = sentence_bleu(
            [ground_truth_tokens], output_tokens, weights=(0.25, 0.25, 0.25, 0.25)
        )

        # bleu_score가 float인지 확인
        if isinstance(bleu_score, (int, float)):
            bleu_score_float = float(bleu_score)
        elif isinstance(bleu_score, (list, np.ndarray)):
            # List나 array이면 평균 사용
            bleu_score_float = float(np.mean(bleu_score))
        else:
            # 숫자도 list도 아니면 기본값 0
            print(f"Warning: Unexpected BLEU score type: {type(bleu_score)}. Defaulting to 0.")
            bleu_score_float = 0.0
    except Exception as e:
        print(f"Error calculating BLEU score: {e}. Defaulting to 0.")
        bleu_score_float = 0.0

    # BLEU score 및 threshold 통과 여부 모두 반환
    return bleu_score_float


def get_assert(output: str, context, threshold=0.3) -> bool | float | dict[str, Any]:
    ground_truth = context["vars"]["ground_truth"]
    score = nltk_bleu_eval(output, ground_truth)

    if score >= threshold:
        return {"pass": True, "score": score, "reason": "Average score is above threshold"}
    else:
        return {"pass": False, "score": score, "reason": "Average score is below threshold"}
