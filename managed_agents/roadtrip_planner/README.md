# 자동차 여행 계획 도구가 이전되었습니다

이 예제는 이제 Claude Quickstarts repo에 있습니다.

**[claude-quickstarts/managed-agents/roadtrip-planner](https://github.com/anthropics/claude-quickstarts/tree/main/managed-agents/roadtrip-planner)**

notebook 대신 실행 가능한 앱이며 실행 가능한 앱은 [claude-quickstarts](https://github.com/anthropics/claude-quickstarts)에 속합니다. 이 repo는 notebook demo를 보관합니다, 같은 `multiagent` 및 `event_deltas` 기능을 notebook 형태로 다루는 [`CMA_coordinate_specialist_team.ipynb`](../CMA_coordinate_specialist_team.ipynb)과 [`CMA_watch_subagents_live.ipynb`](../CMA_watch_subagents_live.ipynb)도 포함됩니다.

## 이전 version을 설정했다면

앱은 같은 네 기능을 보여 줍니다. 이전하면서 세 가지가 바뀌었습니다.

- agent 두 개, environment, vault는 `agents/` 아래 YAML에 정의하고 `./agents/setup.sh`와 [`ant` CLI](https://platform.claude.com/docs/en/cli-sdks-libraries/cli/quickstart)로 생성합니다. `npm run setup`과 `npm run teardown`은 없어졌습니다. 정리는 `./agents/teardown.sh`입니다.
- config는 `.env.local` 대신 `.env`에서 읽으며 resource ID 이름은 `ROADTRIP_PLANNER_*` 대신 `CLAUDE_*`(`CLAUDE_VAULT_ID`, `CLAUDE_AGENT_ID`)입니다.
- 디렉터리는 hyphen이 있는 `roadtrip-planner`입니다.

여기에 있던 코드의 마지막 version은 [`a97b9a2`](https://github.com/anthropics/claude-cookbooks/tree/a97b9a2dc300635f0c26b5e05d0b54bbe0279ee5/managed_agents/roadtrip_planner)에 있습니다.

