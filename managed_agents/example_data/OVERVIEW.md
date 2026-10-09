# 예제 데이터

이 디렉터리는 cookbook notebook이 읽는 작고 독립적인 입력을 보관합니다. 여기의 모든 것은 commit되어 있어 database를 세우거나 API에 가입하거나 `ANTHROPIC_API_KEY` 외의 credential을 연결하지 않고 cookbook 전체를 실행할 수 있습니다. 각 하위 디렉터리는 notebook 하나와 연결되며 그 notebook만 접근합니다.

fixture는 의도적으로 작습니다. 사람이 몇 분 안에 읽을 수 있고 직접 파일을 열어 agent가 추론하는 내용을 따라갈 만큼 작지만 실제로 알아낼 무언가가 있을 만큼 큽니다. 각 fixture에는 작은 함정이나 까다로운 요소가 적어도 하나 있습니다. 두 버그의 의존 관계, 코드와 일치하지 않는 오래된 문서, 승인 한도의 경계에 놓인 영수증입니다. 목적은 항상 첫 시도에 성공하는 장난감 대신 agent가 실제로 씨름할 대상을 주는 것입니다.

| 디렉터리 | 사용하는 곳 | Notebook의 핵심 | 내용 | 대략적인 실행 시간 |
|-----------|---------|----------------|---------------|-----------------|
| `iterate/` | `CMA_iterate_fix_failing_tests.py` | 실패하는 test suite의 실행 → 관찰 → 수정 루프 | 버그 세 개를 넣은 작은 `calc.py` package와 관련 테스트 파일. 실패 하나가 다른 실패의 결과이므로 신중한 agent는 근본 원인을 수정하고 두 번째 테스트가 스스로 통과하는 것을 봅니다. | 약 2분 |
| `orchestrate/` | `CMA_orchestrate_issue_to_pr.py` | 모의 `gh` CLI로 issue부터 merge된 PR까지 진행하기 | `.gh-state/`에 상태를 저장하는 모의 `gh` script, 모호한 Unicode 버그를 설명하는 `issue_42.json`, 버그를 심은 작은 `src/` + `tests/` repo. 체인은 agent가 진행 도중 CI 실패에서 복구하고 merge 전에 review bot의 사소한 docstring 지적을 처리하게 합니다. | 약 5분 |
| `gate/` | `CMA_gate_human_in_the_loop.py` | custom tool을 사용하는 human-in-the-loop 승인 경로 | 승인 규칙을 설명하는 `policy.yaml`과 정책의 모든 분기를 실행하는 영수증 열두 개. 명확한 승인, 명확한 거부, 추측하는 대신 escalation해야 하는 실제로 모호한 몇 가지 사례입니다. | 약 3분 |
| `mongodb_on_cma/` | `CMA_with_mongodb_atlas.ipynb` | MongoDB Atlas retrieval로 사기 검토 agent의 근거 갖추기 | `seed_transactions.jsonl`: 사전 계산한 1024차원 embedding을 가진 사기 검토 transaction 20개, 한 줄당 하나. 다섯 경로(명확한 승인, 명확한 거부, structuring, 고액, fraud ring)로 hybrid retrieval과 graph traversal이 각각 실제로 드러낼 대상을 가지며, agent가 자동 결정 대신 escalation해야 할 경계 사례도 있습니다. | 약 4분 |

네 번째 notebook인 `CMA_explore_unfamiliar_codebase.py`도 fixture 데이터로 실행하지만 repository fixture가 충분히 작아 commit하는 대신 `utilities.make_unfamiliar_repo_zip()`로 메모리에 생성합니다. helper는 stub 파일 디렉터리보다 짧고 읽기 쉬우며 함정(실제 microservices 코드와 더 이상 일치하지 않는 이전 monolithic 구조를 설명하는 오래된 `ARCHITECTURE.md`)을 한곳에 분명하게 유지합니다.

이 디렉터리의 모든 것은 offline으로 실행됩니다. 모의 CLI는 네트워크 호출 대신 로컬 JSON을 읽고 쓰며 test runner는 `python3 -c` 호출일 뿐이고 여기의 어떤 것도 외부로 통신하지 않습니다.

