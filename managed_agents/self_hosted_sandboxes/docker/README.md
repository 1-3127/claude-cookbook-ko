# Docker demo — Self-Hosted Sandbox

Host는 `ant beta:worker poll`을 직접 실행합니다. Claim한 work item마다 `--on-work` 스크립트(`on-work.sh`)가 `docker run`으로 entrypoint가 `ant beta:worker run`인 session별 container를 실행합니다. 각 container에는 session별 Docker volume이 뒷받침하는 `/workspace`(agent의 working tree이며, skill이 여기에 다운로드됨)가 제공되므로 한 session의 여러 container에 걸쳐 tree와 skill이 유지됩니다.

이는 `../cf/`의 cloud 없는 variant입니다(`../cf/`는 동일한 `ant beta:worker run` entrypoint를 Cloudflare Containers에서 실행). 동일한 CLI와 동일한 환경 변수 contract를 사용하며, 직접 제어하는 host에서 일반 Docker만 사용합니다.

- **`Dockerfile`** — session별 image: 고정된 `ant` CLI, `WORKDIR
  /workspace`, `ENTRYPOINT ["ant","beta:worker","run", …]`. CLI가 heartbeat, backlog reconcile, SSE, `bash`/`read`/`write`/`edit`/`glob`/
  `grep` toolset, 종료 시 work item force-stop을 담당합니다.
- **`on-work.sh`** — poller가 work item마다 호출합니다. Poller가 설정한 `ANTHROPIC_{WORK_ID,ENVIRONMENT_ID,SESSION_ID,ENVIRONMENT_KEY}`를 읽고, stdin의 work JSON을 비우고, `--rm` session별 container를 **foreground**에서 `exec`합니다(idempotent: 실행 중인 session의 중복 item은 no-op). Container가 종료할 때까지 block합니다. 반드시 그래야 합니다. `ant beta:worker poll`은 `--on-work` 스크립트가 반환하는 즉시 work item에 stop을 게시하기 때문입니다(CLI opt-out 없음). Detached `docker run -d`는 container가 work를 claim하기 전에 poller가 중지하도록 하므로 `bash` tool call이 실행되지 않습니다.
- **`start.sh`** — image를 build하고 `--on-work on-work.sh`로 host poller를 exec합니다.

Idle policy는 SDK 기본값입니다. 각 container는 `stop_reason: end_turn`인 `session.status_idle` 이후 60초에 종료하며, 다른 모든 event는 clock을 초기화합니다. 이후 `--rm`이 container를 제거하며, session별 volume은 해당 session의 다음 메시지를 위해 유지됩니다.

어디에도 org API key가 없습니다. 유일한 credential은 **environment key**입니다. Poller는 이를 사용하여 work를 claim합니다. 각 container에는 `ANTHROPIC_ENVIRONMENT_KEY`(session별 호출 — event stream, lease heartbeat, force-stop)**와** `ANTHROPIC_AUTH_TOKEN`으로 전달됩니다(CLI의 skill-download client는 `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`만 해석하고 `ANTHROPIC_ENVIRONMENT_KEY`는 해석하지 않으므로, 이것이 없으면 skill 다운로드가 조용히 실패합니다).

## Sandbox에서 MongoDB에 query하기

이 image에는 `python3` + `pymongo`가 포함되어 있으며, `on-work.sh`는 선택적인 `MONGO_URI`를 각 session별 container에 전달하므로 agent가 `bash` 도구에서 MongoDB에 직접 query할 수 있습니다.

```sh
python3 -c 'import os; from pymongo import MongoClient; \
c = MongoClient(os.environ["MONGO_URI"]); \
print(list(c["mydb"]["mycoll"].find({}, {"_id": 0}).limit(5)))'
```

`./start.sh` 전에 host 쪽에서 설정하세요(poller → `on-work.sh` → container로 전달).

```sh
export MONGO_URI="mongodb+srv://<user>:<password>@<cluster>/"
```

`MONGO_URI`는 Anthropic의 secret이 아니라 **여러분의** secret입니다. 직접 build하고 실행하는 container이므로 control plane이나 session event history에 전달되지 않는 일반 환경 변수입니다. 이것이 self-hosted의 장점입니다. (*Cloud* sandbox에는 database secret용 환경 변수나 vault 채널이 없으므로, 그곳에서는 credential을 host 쪽의 custom tool 뒤에 보관합니다. 세 연결 경로를 모두 살펴보는 [MongoDB-on-CMA 랜딩 페이지](../../mongodb_on_cma/README.md)와 [cookbook](../../CMA_with_mongodb_atlas.ipynb)의 1절을 참고하세요.)

Agent의 `bash`는 이 container 안에서 실행되므로 `MONGO_URI`를 읽을 수 있습니다. 작업을 신뢰한다면 괜찮습니다. Least privilege를 위해 내장 toolset을 raw URI 대신 좁은 `mongo_query(...)`를 제공하는 자체 worker tool로 바꾸세요. MongoDB shell을 선호하시나요? Image에 `mongosh`를 추가하고(MongoDB의 apt repo) `mongosh "$MONGO_URI" --eval '…'`를 호출하세요.

## 사전 준비

- Docker
- Host의 PATH에 있는 `ant`, `Dockerfile`에 고정된 것과 **동일한 build**
  (`ARG ANT_VERSION`). 설치:

  ```sh
  VERSION=1.10.0   # Dockerfile의 ANT_VERSION과 일치해야 함
  OS=$(uname -s | tr '[:upper:]' '[:lower:]')
  ARCH=$(uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/')
  curl -fsSL "https://github.com/anthropics/anthropic-cli/releases/download/v${VERSION}/ant_${VERSION}_${OS}_${ARCH}.tar.gz" \
    | sudo tar -xz -C /usr/local/bin ant
  ant --version
  ```

## 실행

```sh
export ANTHROPIC_ENVIRONMENT_ID=env_...
export ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat...
./start.sh
```

그런 다음 해당 `ANTHROPIC_ENVIRONMENT_ID`를 가리키는 session을 만들고 메시지를 보내세요. 순서대로 다음이 보여야 합니다.

```
[start] polling env=env_... base=https://api.anthropic.com
[on-work] session=sesn_... work=work_... container=... (started)
```

Container log(`docker logs cma-sesn_...`)에는 `ant beta:worker run` JSON이 표시됩니다. `downloaded skill …`, `executing tool …` 등입니다. Container는 idle timeout 후 자신을 제거하며, `cma-ws-<session_id>` volume은 해당 session의 다음 메시지를 위해 유지됩니다(버리려면 `docker volume rm`).

Webhook 기반 demo(Modal/Daytona/Vercel/Cloudflare)와 달리 여기에는 webhook이 없습니다. `ant beta:worker poll`이 environment를 직접 long-poll하므로 인터넷에 아무것도 노출할 필요가 없습니다.
