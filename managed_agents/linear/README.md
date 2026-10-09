# Linear × Claude Managed Agents가 이전되었습니다

이 예제는 이제 Claude Quickstarts repo에 있습니다.

**[claude-quickstarts/managed-agents/linear](https://github.com/anthropics/claude-quickstarts/tree/main/managed-agents/linear)**

notebook 대신 실행 가능한 앱이며 실행 가능한 앱은 [claude-quickstarts](https://github.com/anthropics/claude-quickstarts)에 속합니다. 이 repo는 notebook demo를 보관합니다.

## 이전 version을 설정했다면

bridge는 같은 방식으로 작동합니다. 이전하면서 네 가지가 바뀌었습니다.

- agent와 environment는 `agents/linear-assistant/*.yaml`에 정의하고 `./agents/setup.sh`와 [`ant` CLI](https://platform.claude.com/docs/en/cli-sdks-libraries/cli/quickstart)로 생성합니다. `bun run setup`은 없어졌습니다.
- Anthropic webhook route는 `/cma-webhook`이 아니라 `/managed-agents/webhook`입니다. Claude Console → Manage → Webhooks에서 endpoint URL을 update하세요.
- config는 `.env.local` 대신 `.env`에서 읽습니다.
- 처음 agent를 설치한 Linear workspace가 bridge를 소유합니다. `LINEAR_ALLOWED_ORG_IDS`에 나열하지 않으면 다른 workspace의 설치는 거부됩니다. 이전 version은 server에 접근할 수 있는 모든 workspace가 설치할 수 있었습니다.

여기에 있던 코드의 마지막 version은 [`a97b9a2`](https://github.com/anthropics/claude-cookbooks/tree/a97b9a2dc300635f0c26b5e05d0b54bbe0279ee5/managed_agents/linear)에 있습니다.

