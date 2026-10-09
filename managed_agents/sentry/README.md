# Sentry × Claude Managed Agents가 이전되었습니다

이 예제는 이제 Claude Quickstarts repo에 있습니다.

**[claude-quickstarts/managed-agents/sentry](https://github.com/anthropics/claude-quickstarts/tree/main/managed-agents/sentry)**

notebook 대신 실행 가능한 앱이며 실행 가능한 앱은 [claude-quickstarts](https://github.com/anthropics/claude-quickstarts)에 속합니다. 이 repo는 notebook demo를 보관합니다, [`sre_incident_responder.ipynb`](../sre_incident_responder.ipynb)도 포함됩니다.

## 이전 version을 설정했다면

예약된 triage는 같은 방식으로 실행됩니다. 이전하면서 두 가지가 바뀌었습니다.

- vault, environment, agent는 `agents/sentry-triage/*.yaml`에 정의하고 `./agents/setup.sh`와 [`ant` CLI](https://platform.claude.com/docs/en/cli-sdks-libraries/cli/quickstart)로 생성합니다. `setup_agent.py`, `update_agent.py`, `agent_config.py`는 없어졌습니다. agent를 변경하려면 YAML을 편집하고 `./agents/setup.sh`를 다시 실행하세요. deployment도 새 version으로 다시 고정합니다.
- `COOKBOOK_MODEL` override는 없어졌습니다. `agents/sentry-triage/agent.yaml`에서 `model`을 설정하세요.

여기에 있던 코드의 마지막 version은 [`a97b9a2`](https://github.com/anthropics/claude-cookbooks/tree/a97b9a2dc300635f0c26b5e05d0b54bbe0279ee5/managed_agents/sentry)에 있습니다.

