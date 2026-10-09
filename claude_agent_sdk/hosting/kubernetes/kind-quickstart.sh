#!/bin/bash
# =============================================================================
# kind-quickstart.sh — 로컬 kind cluster에서 전체 3단계 topology 실행
# =============================================================================
#
# kind("Kubernetes in Docker")는 노트북 컴퓨터의 Docker container 내부에서
# 실제 Kubernetes API server를 시작합니다. Cloud 계정이 필요하지 않습니다.
# 여기서 적용하는 manifest는 production cluster에 적용하는 것과 같으며,
# image registry만 다릅니다.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOSTING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"      # → claude_agent_sdk/hosting/ (Dockerfile, server.py)
SDK_ROOT="$(cd "$HOSTING_ROOT/.." && pwd)"        # → claude_agent_sdk/ (build context — image에 research_agent/, utils/ 필요)
cd "$SCRIPT_DIR"

CLUSTER=claude-agent
REG=local                                     # Kind에 load한 image의 tag 접두사

info() { printf '\033[0;32m[INFO]\033[0m %s\n' "$1"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$1"; exit 1; }

for cmd in kind kubectl docker openssl jq; do
    command -v "$cmd" >/dev/null || error "$cmd is required but not installed"
done
: "${ANTHROPIC_API_KEY:?Must set ANTHROPIC_API_KEY (get one at https://console.anthropic.com/settings/keys)}"
# Preflight: Key를 중심으로 cluster를 만들기 전에 실제로 작동하는지 검증합니다.
# 환경 변수의 오래되거나 취소된 key는 전체 stack이 가동되고 첫 curl을
# 보낸 후에야 혼란스러운 "Invalid API key" 오류를 일으킵니다.
info "Verifying ANTHROPIC_API_KEY against api.anthropic.com..."
_preflight=$(curl -sS https://api.anthropic.com/v1/models \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01") || error "Could not reach api.anthropic.com"
if echo "$_preflight" | jq -e 'has("error")' >/dev/null; then
    error "ANTHROPIC_API_KEY rejected by API: $_preflight
       Mint a fresh key at https://console.anthropic.com/settings/keys and re-export."
fi

# 1. Cluster ────────────────────────────────────────────────────────────────
# Kind의 기본 CNI(kindnet)는 NetworkPolicy를 적용하지 않습니다. 이를 비활성화하고
# Calico를 설치하여 아래 egress 제한 demo가 실제 cluster와 같은 방식으로
# traffic을 실제로 차단하게 합니다.
if ! kind get clusters | grep -qx "$CLUSTER"; then
    info "Creating kind cluster '$CLUSTER' (default CNI disabled, Calico will provide NetworkPolicy)..."
    cat <<EOF | kind create cluster --name "$CLUSTER" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true
  podSubnet: "192.168.0.0/16"
EOF
    info "Installing Calico CNI..."
    kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.5/manifests/calico.yaml
    info "Waiting for Calico to be ready..."
    # Workload 객체는 apply 직후 존재하므로 이를 기다립니다. Label로 pod를 기다리면
    # DaemonSet이 아직 scheduling하지 않았을 수 있어 race가 발생합니다.
    kubectl -n kube-system rollout status daemonset/calico-node --timeout=180s
    kubectl -n kube-system rollout status deployment/calico-kube-controllers --timeout=180s
    # 이제 node에 CNI가 있으며, image build 전에 Ready로 바뀌기를 기다립니다.
    kubectl wait --for=condition=ready node --all --timeout=120s
else
    info "kind cluster '$CLUSTER' already exists — reusing"
    REUSING_CLUSTER=1
fi

# 2. Image ─────────────────────────────────────────────────────────────────
# Agent image는 1단계(docker/)에서 build하는 것과 같습니다. Dockerfile 하나에
# 주변 운영 체계만 다릅니다.
info "Building agent image..."
docker build -t "${REG}/agent:latest" -f "$HOSTING_ROOT/Dockerfile" "$SDK_ROOT"

info "Building gateway image..."
docker build -t "${REG}/gateway:latest" "$SCRIPT_DIR/gateway"

info "Building egress-proxy image..."
docker build -t "${REG}/egress-proxy:latest" "$SCRIPT_DIR/egress-proxy"

info "Loading images into kind..."
kind load docker-image "${REG}/agent:latest" "${REG}/gateway:latest" \
    "${REG}/egress-proxy:latest" --name "$CLUSTER"

# 3. Certificate ───────────────────────────────────────────────────────────
info "Generating TLS certificates for the egress proxy..."
bash generate-certs.sh

# 4. Namespace, secret, config ─────────────────────────────────────────────
info "Applying namespace..."
kubectl apply -f manifests/namespace.yaml

info "Creating secrets..."
kubectl -n claude-agent create secret generic anthropic-api-key \
    --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

# Gateway가 session 소유권을 적용하는 것을 볼 수 있도록 demo tenant 두 개 사용:
# Alice는 자신의 session을 읽기/이어가기/삭제할 수 있고 bob은 403을 받습니다.
# Gateway는 pod 시작 시 secret을 읽으므로 재실행에서는 manifest 적용 후
# 아래 deployment를 재시작합니다.
ALICE_TOKEN=$(openssl rand -hex 16)
BOB_TOKEN=$(openssl rand -hex 16)
kubectl -n claude-agent create secret generic gateway-tenants \
    --from-literal=GATEWAY_TENANTS="${ALICE_TOKEN}:alice,${BOB_TOKEN}:bob" \
    --dry-run=client -o yaml | kubectl apply -f -

kubectl -n claude-agent create secret generic egress-proxy-tls \
    --from-file=ca.crt=certs/ca.crt \
    --from-file=proxy.crt=certs/proxy.crt \
    --from-file=proxy.key=certs/proxy.key \
    --dry-run=client -o yaml | kubectl apply -f -

info "Creating agent-config ConfigMap..."
kubectl -n claude-agent create configmap agent-config \
    --from-literal=AGENT_IMAGE="${REG}/agent:latest" \
    --from-literal=STANDBY_POOL_SIZE=2 \
    --dry-run=client -o yaml | kubectl apply -f -

# 5. Manifest ──────────────────────────────────────────────────────────────
info "Applying manifests..."
for f in manifests/*.yaml; do
    sed "s|REGISTRY_URL|${REG}|g" "$f" | kubectl apply -f -
done

# 재실행 시 gateway pod는 새로 재생성한 GATEWAY_TENANTS secret보다 오래된 상태입니다.
# 새 token이 적용되도록 재시작합니다.
if [[ -n "${REUSING_CLUSTER:-}" ]]; then
    info "Restarting gateway to pick up regenerated tenant tokens..."
    kubectl -n claude-agent rollout restart deploy/gateway
    kubectl -n claude-agent rollout status deploy/gateway --timeout=300s
fi

# 6. 대기 ───────────────────────────────────────────────────────────────────
info "Waiting for gateway to be ready (this can take a minute on first run)..."
kubectl -n claude-agent wait --for=condition=available deploy/redis --timeout=180s
kubectl -n claude-agent wait --for=condition=available deploy/egress-proxy --timeout=180s
kubectl -n claude-agent wait --for=condition=available deploy/gateway --timeout=300s

# 7. 완료 ───────────────────────────────────────────────────────────────────
info "Ready. Port-forwarding gateway to http://localhost:8080 ..."
kubectl -n claude-agent port-forward svc/gateway 8080:8080 &
PF_PID=$!
# Script와 함께 port-forward도 종료되도록 합니다(Ctrl-C 또는 오류 종료).
# 그렇지 않으면 남아 있어서 다음 실행이 "address already in use"로 실패합니다.
trap 'kill "$PF_PID" 2>/dev/null || true' EXIT INT TERM
sleep 2

cat <<EOF

  Two demo tenants are configured. Sessions belong to whichever tenant
  creates them:

    alice  $ALICE_TOKEN
    bob    $BOB_TOKEN

  Try it as alice:

    curl -N -X POST http://localhost:8080/sessions/demo/messages \\
      -H 'Authorization: Bearer $ALICE_TOKEN' \\
      -H 'Content-Type: application/json' \\
      -d '{"prompt": "Hello from Tier 3"}'

  Now hit alice's session with bob's token — the gateway returns 403:

    curl -X POST http://localhost:8080/sessions/demo/messages \\
      -H 'Authorization: Bearer $BOB_TOKEN' \\
      -H 'Content-Type: application/json' \\
      -d '{"prompt": "let me in"}'

  Watch pods come and go:

    kubectl -n claude-agent get pods -w

  Stop the port-forward with Ctrl-C, or run ./teardown.sh to delete the cluster.

EOF

wait $PF_PID
