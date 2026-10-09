# Managed Agents MCP server가 이전되었습니다

이 예제는 이제 Claude Quickstarts repo에 있습니다.

**[claude-quickstarts/managed-agents/mcp-server-typescript](https://github.com/anthropics/claude-quickstarts/tree/main/managed-agents/mcp-server-typescript)**

notebook 대신 실행 가능한 앱이며 실행 가능한 앱은 [claude-quickstarts](https://github.com/anthropics/claude-quickstarts)에 속합니다. 이 repo는 notebook demo를 보관합니다.

## 이전 version을 설정했다면

tool 아홉 개와 두 transport는 같은 방식으로 작동합니다. 이전하면서 다섯 가지가 바뀌었습니다.

- 디렉터리는 `cma-mcp`가 아니라 `mcp-server-typescript`입니다. stdio server를 절대 경로로 등록했다면 새 위치에서 다시 등록하세요.
- bearer token variable은 `CMA_MCP_TOKEN`이 아니라 `MANAGED_AGENTS_MCP_TOKEN`입니다. 최소 32자여야 하며 그렇지 않으면 HTTP server가 시작을 거부합니다.
- HTTP server는 기본적으로 `127.0.0.1`에 bind합니다. 이전에는 모든 interface에서 수신했습니다. 다른 주소로 제공하려면 `HOST`를 설정하고 `ALLOWED_HOSTS`에 공개 hostname을 나열하세요. 다른 `Host` header의 요청은 거부됩니다.
- `ALLOWED_AGENT_IDS`가 새로 생겼습니다. 설정하지 않으면 이전처럼 token이 workspace의 모든 agent에 접근합니다. 쉼표로 구분한 목록을 설정하면 server를 해당 agent로 제한합니다.
- environment는 `environment.yaml`에 정의하고 [`ant` CLI](https://platform.claude.com/docs/en/cli-sdks-libraries/cli/quickstart)로 생성합니다. inline `--config` 명령은 없어졌습니다.

여기에 있던 코드의 마지막 version은 [`6b671ef`](https://github.com/anthropics/claude-cookbooks/tree/6b671ef60ada2a8d3b0c07cadb424172da5135f5/managed_agents/cma-mcp)에 있습니다.

