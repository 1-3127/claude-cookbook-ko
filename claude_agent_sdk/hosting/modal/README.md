# 2단계 — Modal

`modal.Sandbox`를 통해 [Modal](https://modal.com)에서 **동일한**
`hosting/Dockerfile` image를 실행합니다. Public HTTPS URL과 scale-to-zero를 제공하며,
관리할 infrastructure가 없습니다.

## 사전 요구사항

```bash
pip install modal
modal setup            # 인증을 위해 browser를 엽니다
modal secret create anthropic ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
```

## 배포

```bash
cd claude_agent_sdk/
python hosting/modal/modal_app.py
```

Modal에서 Dockerfile을 원격 build하고(build context = `claude_agent_sdk/`,
로컬과 동일), `serve`를 실행하는 sandbox를 시작한 뒤 tunnel URL을 출력합니다.

## 요청 보내기

배포 script가 `url:` 줄과 `token:` 줄을 출력합니다. Tunnel URL은 public이므로
server는 messages endpoint에서 bearer token을 요구합니다(공개된 것은
`/health`뿐입니다):

```bash
curl -N -X POST "$MODAL_URL/sessions/demo-1/messages" \
  -H "Authorization: Bearer $MODAL_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What are the latest AI agent trends?"}'
```

## 영속성

기본적으로 `modal_app.py`는 `modal.Volume`을 `/data`에 mount합니다. 이는
1단계와 같은 `CLAUDE_CONFIG_DIR` 활용 방식입니다. Sandbox를 재시작해도
session transcript가 유지됩니다.

> **참고:** `modal.Volume`에는 명시적인 commit semantics가 있습니다. Workload에서
> 많은 sandbox가 여러 session에 동시에 쓰고, 쓰기 내용이 유실된다면
> Modal `Dict`나 외부 store를 기반으로 하는
> [`SessionStore`](https://code.claude.com/docs/en/agent-sdk/session-storage)로 전환하세요. 3단계에서도 이를 사용합니다.

## Liveness

Modal은 `Sandbox.create`에 전달한 `timeout=`이 만료될 때까지 sandbox를
실행하며, `GET /health`를 probe하지 않습니다. 내부 server가 종료되면 timeout으로
sandbox가 정리될 때까지 sandbox는 계속 실행되고 요청은 실패합니다. Demo보다
오래 사용하는 경우 자체 모니터링을 `/health`로 지정하고 응답이 중단되면
sandbox를 다시 생성하세요.

## 정리

```bash
python hosting/modal/teardown.py
```

Sandbox를 중지하고 volume을 삭제하여 idle resource에 과금되지 않도록 합니다.
