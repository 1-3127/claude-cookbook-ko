# Claude Agent SDK로 강력한 agent 구축하기

[Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)로 agent를 구축하는 recipe를 소개합니다. SDK의 핵심 기초부터 multi-agent orchestration과 production 배포까지 다룹니다.

## 시작하기

#### 1. 아직 설치하지 않았다면 uv, [node](https://nodejs.org/en/download/), Claude Code CLI 설치하기

```curl -LsSf https://astral.sh/uv/install.sh | sh```

```npm install -g @anthropic-ai/claude-code```

Notebook 자체의 사전 요구사항에 별도 CLI 설치가 명시되어 있지 않다면 `npm` 단계는 선택 사항입니다. `claude-agent-sdk` package에 CLI가 포함되어 있습니다.

#### 2. 프로젝트 clone 및 설정하기

```git clone https://github.com/anthropics/claude-cookbooks.git```

```cd claude-cookbooks/claude_agent_sdk```

```uv sync```

uv 환경은 모든 Notebook을 실행할 하나의 kernel을 제공합니다. 첫 cell에서 자체 요구사항을 설치하는 Notebook은 다른 kernel에서도 실행됩니다.

#### 3. Notebook에서 사용할 수 있도록 venv를 Jupyter kernel로 등록하기

```uv run python -m ipykernel install --user --name="cc-sdk-tutorial" --display-name "Python (cc-sdk-tutorial)"```

#### 4. Claude API Key
1. [platform.claude.com](https://platform.claude.com/dashboard)에 방문합니다.
2. 계정을 만들거나 로그인합니다.
3. "Get API keys"를 클릭합니다.
4. Key를 복사하여 `.env` 파일에 ```ANTHROPIC_API_KEY=``` 형식으로 붙여 넣습니다.

#### 5. Recipe 02용 GitHub Token
Recipe 02인 Observability Agent를 진행할 계획이라면:
1. [여기](https://github.com/settings/personal-access-tokens/new)에서 GitHub Personal Access Token을 발급받습니다.
2. 기본 옵션(public repo, account permission 없음)으로 "Fine-grained" token을 선택합니다.
3. `.env` 파일에 `GITHUB_TOKEN="<token>"` 형식으로 추가합니다.
4. 컴퓨터에서 [Docker](https://www.docker.com/products/docker-desktop/)가 실행 중인지 확인합니다.

#### 6. 선택 사항: 함께 제공되는 agent module import하기
기초 recipe의 동반 코드를 Notebook 외부에서 사용하려면 `claude_agent_sdk/` 디렉터리에서 Python을 실행하여 동반 package를 import할 수 있도록 합니다.

## 배우게 될 내용

기초 과정을 통해 다음을 접하게 됩니다:
- Python SDK의 `query()`, `ClaudeSDKClient`, `ClaudeAgentOptions` interface를 사용하는 **SDK 핵심 기초**
- 기본 WebSearch부터 복잡한 MCP server 통합까지의 **tool 사용 pattern**
- 전문 subagent와 조정을 활용한 **multi-agent orchestration**
- Compliance 추적 및 audit trail용 hook을 활용하는 **enterprise 기능**
- Model Context Protocol(MCP)을 통한 **외부 system 통합**

참고: 이 recipe는 Claude Code에 어느 정도 익숙하다고 가정합니다. Claude Code를 사용해 coding 작업의 효율을 높이고 있으며 그 본연의 agentic 능력을 Software Engineering 이외의 작업에도 활용하려는 경우, 이 recipe가 시작하는 데 도움이 될 것입니다.

## 기초 과정

기초 과정은 기본 agent 구현부터 현실의 복잡성을 처리할 수 있는 정교한 multi-agent system까지 안내합니다. 각 recipe는 이전 recipe를 바탕으로 새로운 개념과 기능을 소개하며, 실용적이고 production에 사용할 수 있는 구현을 유지합니다.

### [00: 한 줄짜리 Research Agent](00_The_one_liner_research_agent.ipynb)

단 몇 줄의 코드로 구축한 단순하면서도 강력한 research agent로 시작하세요. 이 Notebook은 SDK 핵심 개념을 소개하고 Claude Agent SDK가 자율적인 정보 수집과 종합을 어떻게 가능하게 하는지 보여 줍니다.

**핵심 개념:**
- `query()` 및 async iteration을 사용하는 기본 agent loop
- 자율적인 조사를 위한 WebSearch tool
- Read tool을 활용한 multimodal 기능
- `ClaudeSDKClient`를 사용하는 대화 context 관리
- Agent 전문화를 위한 system prompt

**동반 코드:** [`research_agent/`](research_agent/)

### [01: Chief of Staff Agent](01_The_chief_of_staff_agent.ipynb)

Startup CEO를 위한 종합적인 AI Chief of Staff를 구축하며 production 환경용 고급 SDK 기능을 살펴봅니다. 이 Notebook은 governance, compliance, 전문 지식을 갖춘 정교한 agent architecture를 만드는 방법을 보여 줍니다.

**살펴볼 핵심 기능:**
- **Memory 및 Context:** CLAUDE.md 파일을 통한 영속적인 지침
- **Output Styles:** 대상에 맞춘 소통
- **Plan Mode:** 복잡한 작업을 실행하지 않고 전략적으로 계획하기
- **Custom Slash Commands:** 일반적인 작업을 위한 사용하기 쉬운 shortcut
- **Hooks:** 자동화된 compliance 추적 및 audit trail
- **Subagent Orchestration:** 분야별 전문성을 위한 전문 agent 조정
- **Bash Tool 통합:** 절차적 지식 및 복잡한 계산을 위한 Python script 실행

**동반 코드:** [`chief_of_staff_agent/`](chief_of_staff_agent/)

### [02: Observability Agent](02_The_observability_agent.ipynb)

Model Context Protocol을 통해 agent를 외부 system에 연결하여 로컬 기능을 넘어 확장합니다. Agent를 수동적인 관찰자에서 DevOps workflow의 능동적인 참여자로 전환합니다.

**고급 기능:**
- **Git MCP Server:** Repository 분석 및 version control용 tool 13개 이상
- **GitHub MCP Server:** GitHub platform 전체 통합용 tool 100개 이상
- **실시간 모니터링:** CI/CD pipeline 분석 및 장애 감지
- **지능적인 incident 대응:** 자동화된 근본 원인 분석
- **Production workflow 자동화:** 모니터링부터 실행 가능한 insight까지

**동반 코드:** [`observability_agent/`](observability_agent/)

### [03: Site Reliability Agent](03_The_site_reliability_agent.ipynb)

읽기 전용 관찰에서 읽기 및 쓰기를 통한 문제 해결로 나아갑니다. Production incident를 조사하고, 근본 원인을 진단하고, 수정 사항을 적용하고, 결과를 문서화하는 SRE incident 대응 agent를 구축합니다. 이 모든 작업을 자율적으로 수행합니다.

**핵심 기능:**
- **MCP Tool Server:** JSON-RPC subprocess를 통해 metrics, infrastructure, diagnostics, documentation용 tool 12개 이상 제공
- **Prometheus 통합:** Error rate, latency, DB connection 모니터링을 위한 PromQL query
- **읽기 및 쓰기를 통한 문제 해결:** 설정 파일 수정, Docker service 재시작, 수정 사항 검증
- **Safety Hooks:** 쓰기 작업을 검증하는 PreToolUse hook(pool size 범위, config sanity check)
- **전체 incident lifecycle:** 감지부터 문제 해결, post-mortem 문서화까지
- **Production 확장:** 조건부 MCP tool 등록을 통한 선택적인 PagerDuty 및 Confluence 통합

**동반 코드:** [`site_reliability_agent/`](site_reliability_agent/)

### [04: OpenAI Agents SDK에서 migration하기](04_migrating_from_openai_agents_sdk.ipynb)

기존 OpenAI Agents SDK application을 Claude Agent SDK로 port합니다. 두 SDK를 실제로 실행하면서 하나의 비용 승인 agent 예제를 통해 각 primitive를 대응시킵니다.

**핵심 개념:**
- **Primitive 대응:** `@function_tool`, guardrail, `Runner.run`을 Claude의 대응 기능에 연결
- **단일 agent port:** Custom tool, input/output guardrail, multi-turn session, 영속적인 resume
- **Client와 `query()` 비교:** Stateful `ClaudeSDKClient`와 stateless `query()`의 사용 시점
- **Observability:** SDK의 OpenTelemetry export를 기존 stack에 연결

### [05: Session Browser 구축하기](05_Building_a_session_browser.ipynb)

Parser를 작성하는 대신 SDK가 disk에 저장한 session transcript를 읽어, 사용자가 agent 제품에서 기대하는 대화 기록 sidebar를 구축합니다.

**핵심 개념:**
- **Session 목록 조회:** Branch, title, 마지막 수정 metadata가 포함된 pagination 방식의 session 목록
- **Transcript 읽기:** Agent를 시작하지 않고 저장된 session의 message 재생
- **기록 정리:** Session 이름 변경, tag 지정, filtering
- **Fork:** 어느 지점에서든 session을 분기하고 fork를 실제 `query()` 호출로 resume

**동반 코드:** [`session_browser_demo/`](session_browser_demo/)

### [06: Vulnerability Detection Agent](06_The_vulnerability_detection_agent.ipynb)

C 대상을 threat modeling하고, 내장 file tool로 memory-safety bug를 찾으며, 발견 사항을 검토자가 조치할 수 있는 보고서로 triage하는 취약점 발견 agent를 구축합니다.

**핵심 개념:**
- **Threat Modeling:** 초기 설정 후 인터뷰를 진행하고 `THREAT_MODEL.md`를 작성하는 `ClaudeSDKClient` session
- **Agentic 탐색 loop:** 직접 만든 파일 접근 기능 대신 내장 `Read`/`Grep`/`Glob` tool 사용
- **연결된 단계:** Schema를 준수하는 JSON을 출력하는 별도의 탐색, triage, 보고 `query()` 호출

**동반 코드:** [`vulnerability_detection_agent/`](vulnerability_detection_agent/)

### [07: Agent hosting하기](07_Hosting_the_agent.ipynb)

Recipe 00의 research agent를 세 단계의 운영 성숙도에 맞춰 배포합니다. 모든 단계에서 동일한 container image와 HTTP interface를 사용합니다.

**핵심 개념:**
- **Docker:** 개발 반복 과정과 내부 tool을 위한 로컬 및 단일 VM hosting
- **Modal:** URL과 scale-to-zero를 제공하는 managed serverless
- **Kubernetes:** 자체 cluster의 multi-tenant 배포
- **이식 가능한 interface:** 세 단계 모두 동일한 agent 코드, image, HTTP interface 사용

**동반 코드:** [`hosting/`](hosting/)

### [08: Dynamic Workflow로 대규모 subagent orchestration하기](08_Dynamic_workflows.ipynb)

하나의 context window가 조정할 수 있는 규모를 넘어 확장합니다. Agent SDK에서 dynamic workflow를 시작하세요. Claude가 작업에 맞는 JavaScript orchestration script를 작성하면, runtime이 background에서 병렬 subagent 집단 전체에 걸쳐 실행합니다.

**핵심 개념:**
- **Subagent와 Workflow 비교:** 계획을 보유하는 주체가 model의 context인지 deterministic script인지
- **SDK에서 Workflow 시작:** `Workflow` tool, `allowed_tools`, streaming 방식의 실행 진행 상황
- **Fan-Out + Adversarial Verification:** 주장마다 verifier 하나를 병렬 실행하며, 각 verifier는 판단이 인정되기 전에 skeptic agent의 반박을 받음
- **생성된 Script 읽기:** `agent()`, `parallel()`, `pipeline()`, phase, structured output schema

## 독립적인 Recipe

작업에 맞춰 구성된 독립적인 recipe입니다. 각 recipe는 Notebook과 지원 파일을 포함하는 자체 디렉터리에 있습니다.

### [예약 실행하는 Repository Reviewer 구축하기](scheduled_repository_reviewer/scheduled_repository_reviewer.ipynb)

반복적인 검토 업무를 직접 관리하는 무인 작업으로 전환합니다. Repository를 일정에 따라 검토하고 실행 간에 session을 resume하여, 한 번의 전체 baseline 검토 이후에는 짧은 후속 검토를 수행하는 읽기 전용 review agent를 구축합니다. 이전 검토의 id와 발견 사항을 다시 제시하는 schema 검증 field로 그 연속성을 증명합니다. Notebook은 첫 두 cycle을 수동으로 실행한 뒤, 동반 script인 [`scheduled_review.py`](scheduled_repository_reviewer/scheduled_review.py)를 통해 reviewer를 예약 실행하도록 설정하며 마무리합니다.

**핵심 개념:**
- **읽기 전용 Agent:** `tools`는 존재하는 내장 tool을, `allowed_tools`는 질문 없이 실행되는 tool을 결정하며, 둘 다 `Read`, `Glob`, `Grep`로 제한하면 agent에는 쓰기 tool이 없음
- **무인 Permission Mode:** 사전 승인한 tool과 `permission_mode="dontAsk"` 사용, 그리고 실행에서 소비할 turn 수와 비용을 제한하는 `max_turns` 및 `max_budget_usd`
- **연속성을 위한 Resume 가능한 Session:** `ResultMessage`에서 `session_id`를 가져와 호출 간에 저장하고 다음 실행에 `resume`으로 전달
- **Schema로 검증되는 연속성:** 후속 검토의 `output_format` schema가 응답에 이전 검토의 id와 finding id를 다시 제시하도록 요구하므로 resume 연결을 assert할 수 있는 field로 확인
- **Typed 실패 경로 및 검색하기 쉬운 출력:** `VERDICT:` 줄은 structured reply 자체의 field에서 출력되며, 완료 줄은 성공 검증 후에만 출력됨. 좁은 범위의 `ResultError` catch는 한도를 초과한 실행이 `REVIEW-RUN-INCOMPLETE`와 함께 non-zero로 종료되게 함

## 배경
### Claude Agent SDK의 발전

Claude Code는 Anthropic의 가장 성공적인 제품 중 하나가 되었으며, 이는 SOTA coding 능력 때문만은 아닙니다. 진정한 돌파구는 더 근본적인 데 있습니다. **Claude는 agentic 작업에 탁월합니다.**

Claude Code를 특별하게 만드는 것은 코드 이해뿐 아니라 다음 능력입니다:
- 복잡한 작업을 처리할 수 있는 단계로 자율적으로 분해하기
- Tool을 효과적으로 사용하고, 어떤 tool을 언제 사용할지 지능적으로 판단하기
- 오래 실행되는 작업에서 context와 memory 유지하기
- 오류에서 원활하게 복구하고 필요할 때 접근 방식 조정하기
- 설명을 요청할 때와 합리적인 가정으로 진행할 때를 구별하기

이러한 능력 덕분에 Claude Code는 Claude 본연의 agentic 능력에 대한 "bare metal" harness에 가장 가까운 존재가 되었습니다. 가능한 한 적은 overhead로 model의 능력을 발휘하게 하는, 최소한이지만 완전하고 정교한 interface입니다.

### Coding을 넘어: Agent 구축자를 위한 Toolkit

SDK는 원래 Anthropic engineer가 개발 workflow를 가속하기 위해 만든 내부 tool이었지만, 공개 출시를 통해 예상하지 못한 가능성이 드러났습니다. Claude Agent SDK와 GitHub 통합이 출시된 후, 개발자들은 coding을 훨씬 넘어서는 작업에 사용하기 시작했습니다:

- 여러 출처에서 정보를 수집하고 종합하는 **research agent**
- Dataset을 탐색하고 insight를 생성하는 **data analysis agent**
- 반복적인 업무 process를 처리하는 **workflow automation agent**
- System을 관찰하고 문제에 대응하는 **monitoring 및 observability agent**
- 다양한 종류의 콘텐츠를 만들고 다듬는 **content generation agent**

Pattern은 명확했습니다. SDK는 의도치 않게 효과적인 agent 구축 framework가 되었습니다. Software 개발의 복잡성을 처리하도록 설계한 architecture가 범용 agent 생성에도 매우 적합함이 입증되었습니다.

이 recipe series는 단순한 자동화부터 복잡한 enterprise system까지, 어떤 분야나 사용 사례에서도 효율이 매우 높은 agent를 구축하기 위해 Claude Agent SDK를 활용하는 방법을 보여 줍니다.

## 기여하기

문제를 발견했거나 제안이 있으신가요? Issue를 열거나 pull request를 제출해 주세요!
