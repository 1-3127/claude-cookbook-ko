# Gate, 비용 승인자

`CMA_gate_human_in_the_loop.py`가 사용하는 `policy.yaml`과 영수증 열두 개(`inbox/receipts.jsonl`)입니다. agent는 custom tool 두 개로 정책에 따라 각 영수증을 분류합니다. 명확한 승인과 거부에는 `decide()`, 모호한 모든 경우에는 `escalate()`입니다.

영수증 열두 개는 정책의 모든 분기를 거치도록 설계되었습니다. 명확히 자동 승인해야 하는 몇 개, 정책이 요구하는 영수증 image가 없는 하나, 관리자 승인 구간의 몇 개, 한도 초과 두 개, 금액과 관계없이 항상 escalation하는 출장 비용 하나, 의도적으로 모호한 category 하나입니다. 정상적인 실행은 `approve`, `reject`, `escalated` 결정을 혼합하여 만들며 결코 전부 하나의 경로만 나오지 않습니다.

