# 평가

세 domain의 label이 있는 sample(`data/<domain>/samples.jsonl`)에 대해 전체 pipeline을 실행하고 각 결정을 기대 label과 비교합니다. cookbook 폴더의 `engine.py`와 `pipeline.py`를 사용하며, 이는 guide가 import하는 것과 같은 module입니다.

```bash
pip install anthropic python-dotenv
# capabilities/content_moderation/에서(ANTHROPIC_API_KEY 필요):
python evaluation/run_eval.py
```

ad_creatives domain은 `data/ad_creatives/rules.golden.json`의 직접 작성한 ruleset을 사용합니다. 나머지 두 domain은 최초 실행 시 Claude가 compile하고 `evaluation/compiled/`에 cache합니다. 결과는 `evaluation/results.json`에 기록됩니다.
