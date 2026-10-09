# 3단계 — Kubernetes(session별 pod)

> [Agent SDK hosting cookbook](../../07_Hosting_the_agent.ipynb)의 일부입니다.
> 아직 hosting 단계를 선택하지 않았다면 그 문서부터 시작하세요. Managed 방식이
> 더 적합한 경우와 이 방식이 실제로 필요한 경우를 다룹니다.

각 session에 자체 격리 pod를 제공하는 Kubernetes cluster에서 agent를 실행합니다.
Network 수준의 제어를 통해 agent pod가 Anthropic API에만 접근하도록 보장합니다.

```
                     ┌──────────────────────────────────────────────────┐
                     │                  Kubernetes                      │
                     │                                                  │
  curl / SDK ──────► Gateway (FastAPI)                                  │
                     │  ├─ K8s API로 agent pod 생성/삭제       │
                     │  ├─ /sessions/{id}/messages를 올바른 pod로 routing  │
                     │  └─ session → pod mapping을 Redis에 저장        │
                     │                                                  │
              ┌──────┴──────┐                                           │
              │             │                                           │
          Agent Pod    Agent Pod ──► Egress Proxy ──► api.anthropic.com │
          (session A)  (session B)      ▲                               │
              │             │            │                               │
              │     NetworkPolicy: pod는 egress-proxy에만 접근 가능     │
              │                                                         │
            Redis (session → pod-IP mapping)                            │
                     │                                                  │
                     └──────────────────────────────────────────────────┘
```

Agent image는 1단계에서 [`hosting/Dockerfile`](../Dockerfile)로 build하는 것과
**동일**합니다. Image는 같지만 운영 체계는 다릅니다. 단일 container나 Modal sandbox
대신 gateway가 각 session에 자체 pod를 제공하고, cluster가 pod의 접근 대상을 제한합니다.

> **Self-hosting 전에:** Infrastructure를 운영하지 않고 hosted agent만 원한다면
> Anthropic의 managed 방식을 사용하세요. [Hosting 개요](../README.md)를 참고하세요.
> 이 가이드는 자체 Kubernetes cluster에 agent가 필요한 팀(규제 환경, 기존 platform,
> custom networking)을 위한 것입니다.


## 각 구성 요소가 필요한 이유

**Gateway** — 각 사용자 session은 자체 agent pod를 갖습니다. 요청 시 해당 pod를
생성하고, 올바른 pod로 traffic을 routing하고, session이 idle 상태가 되면 정리할
구성 요소가 필요합니다. 그것이 gateway입니다. Kubernetes API와 통신하여 pod
lifecycle을 관리하며, Redis로 session과 pod IP의 대응 관계를 기억합니다.

**Egress proxy + NetworkPolicy** — Agent는 임의의 코드를 실행합니다. 이 조합은
agent pod가 `api.anthropic.com`에 접근하고 *그 외에는 아무 곳에도* 접근하지 못하게
보장합니다. NetworkPolicy는 egress proxy(port 443)와 DNS(port 53)를 제외한 모든
outbound traffic을 차단합니다. Egress proxy는 agent의 TLS를 종료한 뒤 Anthropic
API로 보내는 요청을 다시 암호화합니다. Internet, 다른 service 또는 다른 namespace에
접근하려는 모든 시도는 network 수준에서 drop됩니다.

**Redis** — Gateway는 어떤 pod가 어떤 session을 처리하는지 기억해야 합니다.
요청이 들어오면 Redis에서 session ID를 조회하여 pod IP를 찾고 traffic을 routing합니다.
Redis는 disk에 영속적으로 저장하므로 gateway를 재시작해도 mapping이 유지됩니다.

**Standby pool** — Pod 시작에는 10–30초가 걸립니다(image pull + container boot).
Gateway는 설정 가능한 수의 standby pod를 미리 준비하여 새로운 session이 기다리지
않고 즉시 하나를 할당받게 합니다. Pod가 할당되면 background에서 pool을 보충합니다.

## 사전 요구사항

| Tool | 용도 |
|------|---------------|
| [kind](https://kind.sigs.k8s.io/) | Docker 내 로컬 Kubernetes cluster |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | Manifest 적용, cluster 점검 |
| [docker](https://docs.docker.com/get-docker/) | Container image build |
| `openssl` | Egress proxy의 TLS certificate 생성 |
| `ANTHROPIC_API_KEY` | 환경 변수로 설정 |

## Quickstart(로컬, kind 사용)

```bash
cd hosting/kubernetes
export ANTHROPIC_API_KEY=sk-ant-...
./kind-quickstart.sh
```

세 image를 build하고 로컬 `kind` cluster에 load한 뒤, 모든 manifest를 적용하고
gateway를 `localhost:8080`으로 port-forward합니다. 두 demo tenant(`alice`, `bob`)의
bearer token도 생성하여 마지막에 출력합니다. 사용하려는 token을 export하세요:

```bash
export ALICE_TOKEN=...   # kind-quickstart.sh가 출력함
export BOB_TOKEN=...
```

## 요청 보내기

경로와 형식은 1/2단계와 동일합니다. Base URL이 바뀌고, 이제 gateway는 호출
tenant를 식별하는 bearer token을 요구합니다:

```bash
curl -N -X POST http://localhost:8080/sessions/demo/messages \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "What tools do you have?"}'
```

새 `session_id`의 첫 요청은 standby pod를 할당받습니다(pool이 비었으면 새로 생성).
이후 같은 `session_id`의 요청은 같은 pod로 routing되므로 agent는 연속적인 대화를
보게 됩니다.

이제 session은 `alice`에 속합니다. Gateway는 session을 생성한 tenant를 Redis에
기록하고 이후 모든 요청에서 확인합니다. 같은 호출을 `$BOB_TOKEN`으로 보내면
`403 {"detail":"session belongs to another tenant"}`를 반환하고, token이 전혀 없으면
`401`을 반환합니다. Tenant map은 `gateway-tenants` secret의 정적인
`token:tenant,token:tenant` 문자열입니다. 실제 credential에서 tenant를 도출하려면
[`gateway/main.py`](./gateway/main.py)의 `authenticate()` stub을 자체 IdP로 교체하세요.

운영 체계가 동작하는 모습을 확인하세요:

```bash
kubectl -n claude-agent get pods -w
# agent-standby-* pod가 나타나고, curl하면 하나가 active로 바뀝니다
```

Session을 종료하려면 gateway를 통해 Redis mapping도 정리되도록 합니다
(다른 모든 session 작업과 마찬가지로 owner만 가능):

```bash
curl -X DELETE http://localhost:8080/sessions/demo \
  -H "Authorization: Bearer $ALICE_TOKEN"
```

(`kubectl delete pod`도 작동하지만, 해당 session의 다음 요청이 502를 반환할 때까지
Redis에 오래된 `session → pod-IP` 항목이 남습니다.)

## Egress 제한 검증하기

Agent는 model이 실행하기로 결정한 코드를 실행합니다. Egress proxy + NetworkPolicy가
있으면 prompt injection을 당한 agent도 임의의 host에 접근할 수 없습니다. 이를 검증하세요:

> Kind의 기본 CNI(kindnet)는 NetworkPolicy를 적용하지 않으므로
> `kind-quickstart.sh`는 Calico를 설치합니다. GKE/EKS/AKS 또는 Calico/Cilium cluster는
> 기본적으로 이를 적용하며, 이 절의 내용을 그대로 사용할 수 있습니다.

```bash
AGENT_POD=$(kubectl -n claude-agent get pods -l role=agent \
  -o jsonpath='{.items[0].metadata.name}')

# 실패해야 합니다 — Calico는 egress-proxy 외의 모든 경로를 drop합니다.
# (Agent image는 slim이며 curl이 없으므로 Python socket을 사용합니다.)
kubectl -n claude-agent exec "$AGENT_POD" -- python3 -c \
  "import socket; socket.setdefaulttimeout(5); socket.create_connection(('example.com',443)); print('REACHED — policy NOT enforcing')"
```

예상 결과는 `OSError: [Errno 101] Network is unreachable`(또는 timeout)과
non-zero 종료입니다. Egress-proxy 경로가 *열려 있다*는 positive control은 위의
curl이 model 출력을 반환하면서 이미 입증되었습니다.

## Standby pool

`STANDBY_POOL_SIZE`(`agent-config` ConfigMap 내부)는 gateway가 준비 상태로
유지하는 warm pod 수를 제어합니다. 현재 상태를 확인하세요(유효한 tenant token이면 가능):

```bash
curl http://localhost:8080/api/pool -H "Authorization: Bearer $ALICE_TOKEN"
```

## 영속성

`server.py`는 transcript(및 caller-ID → SDK-ID map)를
`CLAUDE_CONFIG_DIR=/data`에 영속적으로 저장합니다. 이 단계에서는 pod의 ephemeral
filesystem이므로:

- **Pod가 살아 있는 동안**(idle-timeout 기간 내), 후속 message는
  1/2단계와 정확히 같은 방식으로 대화를 resume합니다.
- **Pod가 정리된 후**에는 `/data`가 사라집니다. 해당 `session_id`의
  다음 message는 기록이 없는 새 pod를 받습니다.

Cookbook demo에서는 괜찮습니다. Session은 curl보다 오래 유지되지만 cluster보다
오래 유지되지는 않습니다. Production에서는 pod가 재생성되어도 유지되는 durable
storage가 필요합니다. 두 가지 선택지가 있습니다:

1. Pod의 로컬 disk 대신 `/data`에 **PersistentVolumeClaim을 mount**하고,
   session이 돌아오면 gateway가 같은 PVC를 다시 연결하게 합니다. `server.py`를
   그대로 사용할 수 있지만 각 session이 하나의 zone에 있는 volume과 결합됩니다.
2. SDK의 [`SessionStore`](https://code.claude.com/docs/en/agent-sdk/session-storage)로
   **`/data`를 외부 storage에 mirror**합니다. 로컬 disk 쓰기가 여전히 먼저 발생하고,
   store는 mirror이며, `mirror_error`는 치명적이지 않습니다. 이는 Notebook의
   *Production에 사용할 수 있도록 만들기* 절에서 설명하는 방식입니다.
   Cookbook에는 아직 없는 작은 hook을 `server.py`에 추가해야 합니다.

## 자체 cluster에 배포하기

`kind`는 topology를 검증하며, manifest는 특정 cloud에 의존하지 않습니다. EKS,
AKS, GKE, OpenShift 또는 bare metal에서 실행하려면 image registry와 외부 진입점을 교체하세요:

```bash
REG=your.registry.example.com/claude-agent     # ECR, ACR, GHCR, Artifact Registry, ...

# 1. 세 image build 및 push
docker build -t $REG/agent:latest -f ../Dockerfile ..
docker build -t $REG/gateway:latest ./gateway
docker build -t $REG/egress-proxy:latest ./egress-proxy
docker push $REG/agent:latest $REG/gateway:latest $REG/egress-proxy:latest

# 2. Egress proxy용 TLS certificate
./generate-certs.sh

# 3. Namespace + secret + config
kubectl apply -f manifests/namespace.yaml
kubectl -n claude-agent create secret generic anthropic-api-key \
    --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
kubectl -n claude-agent create secret generic gateway-tenants \
    --from-literal=GATEWAY_TENANTS="$(openssl rand -hex 16):tenant-a,$(openssl rand -hex 16):tenant-b"
kubectl -n claude-agent create secret generic egress-proxy-tls \
    --from-file=ca.crt=certs/ca.crt \
    --from-file=proxy.crt=certs/proxy.crt \
    --from-file=proxy.key=certs/proxy.key
kubectl -n claude-agent create configmap agent-config \
    --from-literal=AGENT_IMAGE=$REG/agent:latest \
    --from-literal=STANDBY_POOL_SIZE=2

# 4. Registry를 교체하여 manifest 적용
for f in manifests/*.yaml; do
  sed "s|REGISTRY_URL|$REG|g" "$f" | kubectl apply -f -
done
```

> 나중에 `$REG`를 변경하면 `agent-config` ConfigMap도 다시 생성하세요.
> Gateway는 agent pod를 생성할 때 여기에서 `AGENT_IMAGE`를 읽으므로,
> manifest에 `sed`만 다시 실행해서는 pod의 image 대상이 바뀌지 않습니다.

그런 다음 cluster가 ingress에 사용하는 방식(cloud LoadBalancer, Ingress controller,
service mesh gateway)을 통해 `gateway` Service를 노출합니다. 환경마다 달라지는
세 가지 사항이 있습니다:

- **Registry 인증** — Node에는 `$REG`의 pull credential이 필요합니다
  (`imagePullSecrets`, IRSA/Workload Identity 또는 public registry).
- **NetworkPolicy 적용** — Egress 제한은 CNI가 `NetworkPolicy`를 적용할 때만
  작동합니다(Cilium, Calico, GKE Dataplane V2, VPC CNI policy add-on이 있는 EKS).
  이를 무시하는 CNI에서는 agent pod가 internet에 접근할 수 있습니다.
- **Gateway 앞의 TLS + 인증** — 정적인 `GATEWAY_TENANTS` token map은
  실제 credential의 임시 대안입니다. Public으로 노출하기 전에 IdP / API gateway를
  앞에 배치하세요.

## 이 구성이 제공하지 않는 것

- 실제 identity provider. Gateway는 tenant별 session 소유권을 *확실히* 적용합니다.
  `GATEWAY_TENANTS`의 각 bearer token은 tenant에 대응하고, 생성 tenant가 session을
  소유하며, 다른 tenant는 403을 받습니다. 하지만 token 자체는 발급, rotation,
  revocation 또는 tenant별 RBAC가 없는 정적인 map입니다. `authenticate()`를 IdP로
  교체하세요. 소유권 검사는 바뀌지 않습니다.
- Durable session storage([영속성](#persistence) 참고)
- Gateway autoscaling 또는 multi-region routing
- DNS 수준 egress 제어 — Node-local DNS cache가 계속 작동하도록 port 53은 모든
  resolver에 열려 있으며, 이로 인해 DNS tunneling이 잔여 exfiltration 경로로 남습니다.
  Cluster가 kube-dns/CoreDNS와 직접 통신하는 경우 이를 강화하는 방법은
  [`manifests/network-policy.yaml`](./manifests/network-policy.yaml)의 참고 내용을 보세요.
- 보안이 강화된 지원 service — Gateway, Redis, nginx는 기본 image의 기본(root)
  사용자로 실행됩니다. Hardening에 쓸 자원은 model이 지시하는 코드를 실행하는
  agent pod에 투입했습니다. Production 전에 나머지도 조직의 baseline에 맞춰 제한하세요.
- [`OTEL_EXPORTER_OTLP_ENDPOINT`](https://code.claude.com/docs/en/agent-sdk/observability)가
  기본 제공하는 범위를 넘어선 observability

## 정리

```bash
./teardown.sh        # kind cluster 삭제 + certs/ 삭제
```

## 구조

```
kubernetes/
├── README.md
├── kind-quickstart.sh         # kind에서 로컬 end-to-end 실행
├── teardown.sh
├── generate-certs.sh          # egress-proxy용 self-signed CA + proxy certificate
├── gateway/
│   ├── main.py                # FastAPI: routing + 정리
│   ├── k8s.py                 # pod lifecycle + standby pool
│   ├── proxy.py               # SSE relay
│   ├── requirements.txt
│   └── Dockerfile
├── egress-proxy/
│   ├── nginx.conf
│   └── Dockerfile
└── manifests/
    ├── namespace.yaml
    ├── redis.yaml
    ├── egress-proxy.yaml
    ├── gateway.yaml           # SA + RBAC + Deployment + Service
    └── network-policy.yaml
```
