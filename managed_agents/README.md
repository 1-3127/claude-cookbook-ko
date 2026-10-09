# Claude Managed Agents cookbook

Claude Managed Agents는 stateful하고 tool을 사용하는 agent를 위한 Anthropic의 hosted runtime입니다. agent와 sandbox environment를 한 번 정의한 뒤 파일, tool 상태, 대화를 turn 사이에 유지하는 세션에서 실행합니다. 이 tutorial들은 전체 과정을 보여 줍니다.

## Managed Agents의 MongoDB

retrieval, graph traversal, system of record를 위한 실제 database를 agent에 제공하고 싶나요?
**[`CMA_with_mongodb_atlas.ipynb`](CMA_with_mongodb_atlas.ipynb)**은 통합 cookbook입니다. CMA agent에 MongoDB를 연결하는 세 방식(각 경로에서 credential이 있는 곳), 가져올 수 있는 구성 요소인 네 retrieval 패턴(vector / full-text / hybrid / graph), Atlas를 system of record와 audit 기반으로 사용하는 전체 human-in-the-loop 사기 검토 agent를 다룹니다.

## 응용 cookbook

- **[data_analyst_agent.ipynb](data_analyst_agent.ipynb)**는 pandas와 plotly로 CSV를 서술형 HTML 보고서로 바꾸는 분석 agent를 만듭니다. environment와 agent를 설정하고, dataset을 mount하고, 실행을 streaming하고, 생성된 artifact를 가져옵니다.
- **[slack_data_bot.ipynb](slack_data_bot.ipynb)**는 해당 agent를 Slack bot으로 감쌉니다. CSV와 함께 mention하면 thread에서 보고서를 받으며 reply는 같은 세션을 이어갑니다.
- **[sre_incident_responder.ipynb](sre_incident_responder.ipynb)**는 Managed Agents를 on-call 과정에 넣습니다. 알림이 세션을 시작하고, agent가 조사하여 PR을 연 뒤 merge 전에 사람 승인을 기다립니다. alert webhook을 연결하고, Skill과 custom tool을 연결하고, Console에서 전체 실행을 검토합니다.

## 안내 tutorial

현실적인 workflow로 Managed Agents API 인터페이스를 가르치는 전체 과정 tutorial입니다. 엄격한 읽기 순서는 없지만 `CMA_iterate_fix_failing_tests.ipynb`이 좋은 시작점입니다. 다른 모든 notebook의 기반이 되는 API 형태를 소개합니다.

| Notebook | 가르치는 내용 |
| --- | --- |
| [`CMA_iterate_fix_failing_tests.ipynb`](CMA_iterate_fix_failing_tests.ipynb) | 실패하는 test suite의 실행 → 관찰 → 수정 루프. 시작점 notebook입니다. 버그가 있는 package를 통과시키는 관점으로 agent / environment / session, 파일 mount, streaming event 루프를 소개합니다. |
| [`CMA_orchestrate_issue_to_pr.ipynb`](CMA_orchestrate_issue_to_pr.ipynb) | 모의 `gh` CLI의 issue → 수정 → PR → CI → review → merge. Multi-turn 진행, 체인 도중 CI 실패와 review comment에서 복구하기. 보충 설명은 파일 mount 대신 실제 repo의 `github_repository` resource를 사용하는 법을 보여 줍니다. |
| [`CMA_explore_unfamiliar_codebase.ipynb`](CMA_explore_unfamiliar_codebase.ipynb) | 오래된 문서 함정이 있는 익숙하지 않은 codebase에서 grounding하기. 보충 설명은 `sessions.resources.add`로 실행 중인 세션에 resource를 추가하는 법을 보여 줍니다. |
| [`CMA_gate_human_in_the_loop.ipynb`](CMA_gate_human_in_the_loop.ipynb) | custom tool `decide()` / `escalate()`로 human-in-the-loop 비용 승인하기. custom tool 왕복 패턴, `requires_action`에 의한 idle 전환, 병렬 tool 호출 중복 제거를 다룹니다. |
| [`CMA_with_mongodb_atlas.ipynb`](CMA_with_mongodb_atlas.ipynb) | **MongoDB Atlas** 전체 과정: 세 연결 경로(host 측 custom tool, self-hosted sandbox, self-hosted MCP), 네 retrieval 패턴(vector / full-text / RRF hybrid / `$graphLookup`), 같은 cluster에 결정과 append-only audit trail을 기록하는 human-in-the-loop 사기 검토 agent. 위험한 사례에서 `requires_action` gate로 일시 정지하고 CI용 자동 처리 gate와 production용 webhook 인계를 보여 줍니다. |
| [`CMA_prompt_versioning_and_rollback.ipynb`](CMA_prompt_versioning_and_rollback.ipynb) | 서버 측 prompt versioning: v1 생성, labelled test set 평가, v2 출시, regression 감지, 세션을 version 1에 고정하여 rollback. `agents.update`, `sessions.create`의 version 고정, prompt가 코드가 아닐 때 review gate가 옮겨지는 곳을 다룹니다. |
| [`CMA_operate_in_production.ipynb`](CMA_operate_in_production.ipynb) | Production 설정: MCP toolset, 최종 사용자별 credential용 vault, 장시간 연결 없이 HITL과 비용 감독을 수행하는 `session.status_idled` 및 `session.budget_reached` webhook 패턴, residency용 `inference_geo` 고정, resource lifecycle CRUD 동작. |
| [`CMA_remember_user_preferences.ipynb`](CMA_remember_user_preferences.ipynb) | Memory store: 한 세션에서 고객 선호를 배우고 다음 세션에서 기억해 내는 쇼핑 agent. `memory_stores.create`, 연결별 `instructions`가 있는 `resources` 연결, 자체 애플리케이션에서 memory 살펴보기와 미리 넣기, 고객별 읽기·쓰기 store와 브랜드 전체 읽기 전용 store 결합을 다룹니다. |
| [`CMA_coordinate_specialist_team.ipynb`](CMA_coordinate_specialist_team.ipynb) | `multiagent` coordinator 설정의 서로 다른 역할 팀: coordinator가 범위를 지정한 toolset을 가진 specialist 세 명(web search researcher, 파일 읽기 librarian, 규칙 기반 가격 담당자)을 실행하여 판매 제안서를 구성합니다. `multiagent` 필드, `thread_created` / `thread_message_received` event 타입, 역할별 tool 범위 지정의 중요성, 작성 전 자문하는 `advisor` roster 항목을 다룹니다. |
| [`CMA_watch_subagents_live.ipynb`](CMA_watch_subagents_live.ipynb) | 실시간으로 관찰할 수 있는 교육과정 계획 팀. subagent text를 실시간 streaming하는 thread별 `event_deltas`, 세션 생성의 `initial_events`, 비용 조절 수단인 agent별 model `effort`, version 없는 `agents.update`를 다룹니다. coordinate-specialist-team의 형태를 기반으로 합니다. |
| [`CMA_plan_big_execute_small.ipynb`](CMA_plan_big_execute_small.ipynb) | Coordinator 패턴의 경제성: frontier coordinator가 token을 많이 사용하는 web 읽기를 저렴한 병렬 worker에 위임합니다. thread별 `usage.list_cost` 측정과 작업 분기 제한 장치인 세션 `budget`을 사용하여 엄밀성이 같은 단독 frontier 대조 실행과 비교합니다. |
| [`CMA_verify_with_outcome_grader.ipynb`](CMA_verify_with_outcome_grader.ipynb) | Outcomes로 평가·수정 루프 만들기: writer가 출처가 있는 조사 보고서를 작성하고, stateless grader가 모든 URL을 fetch하여 rubric에 따라 모든 인용문을 확인하며, feedback이 보고서 통과까지 수정을 이끕니다. `user.define_outcome`, `span.outcome_evaluation_*` event, grader가 실행할 수 있는 rubric 작성법을 다룹니다. |
| [`CMA_consult_an_advisor.ipynb`](CMA_consult_an_advisor.ipynb) | `advisor` roster 항목으로 turn 도중 더 강력한 model에 자문하는 중간 등급 작업 agent. `multiagent.agents`의 `{"type": "advisor"}` 항목, primary stream의 `anthropic.advisor` thread lifecycle, advisor thread `usage`의 자문별 비용, redacted 전달 방식을 다룹니다. |
| [`CMA_cap_session_spend.ipynb`](CMA_cap_session_spend.ipynb) | 한 세션에 강제로 적용하는 지출 상한. `sessions.create`의 `budget` 필드, `session.usage` snapshot event와 `usage.list_cost`, `budget_reached` 일시 정지, `sessions.update`로 상한 올리기·내리기·제거하기를 다룹니다. |
| [`CMA_use_skills_from_a_repo.ipynb`](CMA_use_skills_from_a_repo.ipynb) | agent의 `skills` 필드 없이 세션 시작 시 mount한 repository 루트의 `.claude/skills/`에서 발견되는 skill. scanner가 기대하는 구조, 먼저 읽고 따르는 protocol, lifecycle 규칙(skill 상한, 단일 scan, 필요할 때 중첩 발견)을 다룹니다. |
| [`CMA_pin_inference_geo.ipynb`](CMA_pin_inference_geo.ipynb) | agent 정의의 data residency: `model.inference_geo` 고정, 적용 위치, workspace `allowed_inference_geos` 정책과의 관계, `agent_with_overrides`로 세션 하나의 지역 덮어쓰기. |

streaming event 루프는 iterate notebook에서 한 줄씩 설명한 뒤 `utilities.stream_until_end_turn`으로 분리하여 다른 notebook이 `match ev.type:` block을 반복하는 대신 import할 수 있게 합니다. gate notebook과 MongoDB cookbook은 예외입니다. custom tool agent는 helper가 다루지 않는 `requires_action`에 의한 idle 전환을 `end_turn`과 함께 처리해야 하므로 루프를 내부에 유지합니다.

## 시작하기

environment에 `ANTHROPIC_API_KEY`를 설정한 뒤 Jupyter에서 `data_analyst_agent.ipynb`을 열어 위에서 아래로 셀을 실행하세요. 각 notebook은 자체 dependency를 설치하고 필요한 credential을 입력받습니다. `CMA_orchestrate_issue_to_pr.ipynb`의 orchestrate-to-PR 보충 설명, `CMA_operate_in_production.ipynb`의 vault 기반 MCP 예제, `CMA_use_skills_from_a_repo.ipynb`에는 `GITHUB_TOKEN`도 필요합니다(공개 repo 읽기 권한의 fine-grained PAT면 충분). `CMA_with_mongodb_atlas.ipynb`의 MongoDB cookbook에는 Atlas SRV connection string인 `MONGO_URI`도 필요합니다(M0 무료 cluster 사용 가능). provider key인 `MDB_ATLAS_API_KEY` 또는 `VOYAGE_API_KEY`는 선택 사항이며 실시간 embedding과 reranker 경로만 활성화합니다.

모든 cookbook fixture 데이터 — 응용 cookbook의 입력 CSV와 보조 자료, 안내 tutorial이 읽는 함정 fixture — 는 `example_data/`에 있습니다. 디렉터리 구성은 [`example_data/OVERVIEW.md`](example_data/OVERVIEW.md)를 참고하세요.

## 실행 가능한 앱

이 디렉터리는 notebook을 보관합니다. Slack 및 Linear bot, Sentry triage agent, 자동차 여행 계획 도구, 이전에 여기에 있던 MCP server 같은 Managed Agents 기반 전체 앱은 [claude-quickstarts/managed-agents](https://github.com/anthropics/claude-quickstarts/tree/main/managed-agents)에 있습니다.

