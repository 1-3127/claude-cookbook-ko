#!/bin/bash
# =============================================================================
# generate-certs.sh — Self-signed CA 및 proxy certificate 생성
# =============================================================================
#
# SELF-SIGNED CA란?
#     Certificate Authority(CA)는 TLS certificate에 서명하는 주체입니다.
#     보통 browser와 app은 잘 알려진 CA(Let's Encrypt 등)를 신뢰합니다.
#     "Self-signed" CA는 직접 만드는 것으로 기본적으로 신뢰되지 않지만
#     application이 명시적으로 신뢰하도록 구성할 수 있습니다.
#
# 필요한 이유:
#     Egress proxy는 agent pod와 api.anthropic.com 사이에 있습니다. Agent pod는
#     HTTPS로 proxy에 연결하므로 proxy에 TLS certificate가 필요합니다.
#     Proxy는 public website가 아닌 내부 service이므로 public CA에서
#     certificate를 받을 수 없습니다. 자체 CA를 만들어 그것으로
#     proxy certificate에 서명합니다.
#
#     그런 다음 NODE_EXTRA_CA_CERTS 환경 변수로 agent pod가
#     CA certificate를 신뢰하게 구성합니다. 이는 Node.js(및 Node.js에서
#     실행하는 Claude Code 같은 tool)에 자체 CA가 서명한 TLS certificate를
#     수락하도록 알려 줍니다.
#
# 이 SCRIPT가 생성하는 것:
#     certs/ca.key     — CA private key(비밀로 유지)
#     certs/ca.crt     — CA certificate(agent pod와 공유하여
#                                             proxy를 신뢰하도록 함)
#     certs/proxy.key  — Proxy private key(proxy pod에 mount)
#     certs/proxy.crt  — 자체 CA가 서명한 proxy certificate
#                                             (proxy pod에 mount)
# =============================================================================

set -euo pipefail

CERTS_DIR="$(dirname "$0")/certs"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "Generating CA certificate..."
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt \
    -subj "/CN=Demo CA/O=Agent SDK Demo"

echo "Generating proxy certificate..."
openssl genrsa -out proxy.key 2048

# Egress-proxy hostname용 SAN을 포함한 CSR 생성
cat > proxy.cnf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = egress-proxy

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = egress-proxy
DNS.2 = egress-proxy.claude-agent.svc.cluster.local
DNS.3 = localhost
EOF

openssl req -new -key proxy.key -out proxy.csr -config proxy.cnf

# CA로 서명
openssl x509 -req -in proxy.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out proxy.crt -days 365 -sha256 -extensions req_ext -extfile proxy.cnf

# CSR 및 config 정리
rm -f proxy.csr proxy.cnf ca.srl

echo ""
echo "Certificates generated:"
ls -la .
echo ""
echo "CA certificate:    ca.crt"
echo "Proxy certificate: proxy.crt"
echo "Proxy key:         proxy.key"
