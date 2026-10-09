"""
Agent session의 Kubernetes pod lifecycle 관리.

K8s API로 session별 agent pod를 생성, 모니터링, 삭제합니다. 새 session이
cold pod의 image pull 및 boot를 30-60초 기다리지 않고 즉시 시작하도록
pre-warmed pod의 standby pool을 유지합니다.

K8s 입문자를 위한 핵심 개념:
- "Pod"는 K8s의 최소 배포 단위이며, 하나 이상의 container를 감싸는 wrapper로
  생각하세요(여기서는 pod당 container 하나 사용).
- "Label"은 K8s 객체의 key/value tag입니다. Standby 및 active pod와
  pod를 소유한 session을 추적하는 데 사용합니다.
- K8s API는 synchronous/blocking이므로 async event loop를 block하지 않도록
  모든 호출을 `asyncio.to_thread()`로 감쌉니다.
"""

import asyncio
import logging
import os
import uuid

import kubernetes
from kubernetes import client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module 수준 K8s 구성
# ---------------------------------------------------------------------------
# load_incluster_config()는 K8s가 모든 pod의
# /var/run/secrets/kubernetes.io/에 자동 mount하는 service-account token을 읽습니다.
# 이 코드가 K8s cluster 내부에서 실행될 때만 작동합니다.
# 로컬 실행(test, 개발 server 등)에서는 실패합니다. 이를 catch하고 flag를
# 전환하여 나머지 gateway가 여전히 이 module을 import할 수 있게 합니다.
_k8s_available = True

try:
    kubernetes.config.load_incluster_config()
except kubernetes.config.ConfigException:
    logger.warning(
        "Failed to load in-cluster K8s config — running outside Kubernetes. "
        "Pod management functions will be unavailable."
    )
    _k8s_available = False

# AGENT_IMAGE는 agent pod의 container image입니다(예: "us-docker.pkg.dev/…/agent:latest").
# K8s가 있으면 필수이며, 그렇지 않으면 무시됩니다. Import 시가 아닌 시작 시
# (initialize_standby_pool) 검증하므로 잘못 구성한 gateway가 import에서
# crash-loop하는 대신 readiness probe를 실패하게 합니다.
AGENT_IMAGE = os.environ.get("AGENT_IMAGE", "")

# Agent pod를 생성하는 namespace. Namespace는 K8s가 resource를
# 분할하는 방식이며 cluster 객체를 위한 폴더와 같습니다.
AGENT_NAMESPACE = os.getenv("AGENT_NAMESPACE", "claude-agent")

# 준비 상태로 유지할 pre-warmed "standby" pod 수. 사용자가 session을
# 시작하면 처음부터 pod를 만드는 대신 이 중 하나를 할당합니다.
STANDBY_POOL_SIZE = int(os.getenv("STANDBY_POOL_SIZE", "2"))

# Standby pool을 보충하는 background asyncio task의 handle.
_replenish_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Pod manifest builder
# ---------------------------------------------------------------------------


def _build_pod_manifest(
    *,
    pod_name: str,
    labels: dict[str, str],
) -> client.V1Pod:
    """Agent pod의 V1Pod manifest를 구성합니다.

    V1Pod는 Kubernetes Pod spec의 Python 표현입니다. 두 가지 주 section이
    있습니다:
      - metadata: name, namespace, label(query/filtering용 tag)
      - spec: 실제 workload 정의 — container, volume 등

    V1Container는 실행할 Docker container를 설명합니다. 중요 field:
      - image: Pull할 container image
      - env: Container에 주입할 환경 변수
      - volume_mounts: Container에 mapping되는 K8s Volume의 디렉터리
      - resources: CPU/memory request(scheduling hint) 및 limit(엄격한 상한)
      - ports: Container가 listen할 port

    Volume은 pod에 연결되는 storage 단위입니다. 여기서는 K8s Secret을 읽기 전용
    디렉터리로 mount하여 image에 넣지 않고도 container가 TLS certificate에
    접근할 수 있게 합니다.
    """

    # --- Container 정의 ---
    container = client.V1Container(
        name="agent",
        image=AGENT_IMAGE,
        # Kind에 load한 image가 작동하도록 IfNotPresent 사용. :latest tag는 기본적으로
        # imagePullPolicy=Always를 의미하여 registry에서 pull하려 하고
        # kind가 node에 이미 load한 image는 무시하게 됩니다.
        image_pull_policy="IfNotPresent",
        # Cookbook image의 entrypoint는 기본적으로 일회성 실행이며, "serve"를
        # 전달하면 장기 실행 FastAPI server(hosting/server.py)를 시작합니다.
        args=["serve"],
        env=[
            # K8s Secret에서 API key를 가져옵니다. Secret은 민감한 data(password,
            # token)를 저장하며 저장 시 base64로 encoding됩니다. secretKeyRef를
            # 사용하면 pod spec 자체에 값이 나타나지 않고 pod 시작 시
            # 주입됩니다.
            client.V1EnvVar(
                name="ANTHROPIC_API_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name="anthropic-api-key",
                        key="ANTHROPIC_API_KEY",
                    ),
                ),
            ),
            # Egress proxy(TLS 종료 및 outbound 접근 제어를 처리하는 sidecar service)를
            # 통해 API traffic을 routing합니다.
            client.V1EnvVar(
                name="ANTHROPIC_BASE_URL",
                value="https://egress-proxy",
            ),
            # Node.js(및 다른 tool)가 egress proxy의 self-signed CA certificate를
            # 신뢰하도록 알려 줍니다.
            client.V1EnvVar(
                name="NODE_EXTRA_CA_CERTS",
                value="/certs/ca.crt",
            ),
            # Pod 내부에서 agent의 HTTP/WS server가 listen하는 port.
            client.V1EnvVar(
                name="PORT",
                value="8000",
            ),
            # SDK가 session transcript를 작성하는 위치. 기본적으로 emptyDir로
            # mount됩니다. README의 영속성 절을 참고하세요.
            client.V1EnvVar(
                name="CLAUDE_CONFIG_DIR",
                value="/data",
            ),
        ],
        # Agent가 proxy를 통한 HTTPS connection을 검증할 수 있도록 egress proxy의
        # TLS certificate를 /certs에 mount합니다.
        volume_mounts=[
            client.V1VolumeMount(
                name="egress-proxy-tls",
                mount_path="/certs",
                read_only=True,
            ),
        ],
        # Resource request 및 limit:
        # - "requests"는 K8s scheduler에 확보할 용량을 알려 줍니다.
        #   이를 충족하지 못하는 node에는 pod가 배치되지 않습니다.
        # - "limits"는 kernel이 cgroup으로 적용하는 엄격한 상한입니다.
        #   Container가 memory limit를 초과하면 OOM-kill됩니다.
        resources=client.V1ResourceRequirements(
            requests={"cpu": "250m", "memory": "512Mi"},
            limits={"cpu": "1", "memory": "2Gi"},
        ),
        # Container가 port 8000에서 listen한다고 선언합니다. 주로 문서용이며
        # K8s는 이를 강제하지 않지만, tool과 다른 개발자가 pod의
        # network interface를 이해하는 데 도움이 됩니다.
        ports=[client.V1ContainerPort(container_port=8000)],
        # Readiness: Uvicorn이 아직 SDK를 import하고 port 8000을 bind하기 전에도
        # pod는 phase=Running일 수 있습니다. Gateway는 container가 Ready라고
        # 보고하는 pod만 할당/routing하므로 이 probe가 그 간극을
        # 해소합니다. (Kubelet probe는 pod가 아닌 node에서 오므로
        # NetworkPolicy가 차단하지 않습니다.)
        readiness_probe=client.V1Probe(
            http_get=client.V1HTTPGetAction(path="/health", port=8000),
            initial_delay_seconds=2,
            period_seconds=2,
            failure_threshold=15,
        ),
        # Model이 지시한 코드를 실행하는 container에 대한 pod 수준 hardening:
        # Privilege escalation 및 Linux capability 없음, 기본 seccomp filter
        # (1단계에서 Docker가 적용하는 것과 동일).
        # runAsNonRoot는 의도적으로 설정하지 않습니다. 공유하는 1단계 image는
        # root로 실행되며, non-root 사용자로 전환하는 것은 manifest가 아닌
        # image 변경입니다.
        security_context=client.V1SecurityContext(
            allow_privilege_escalation=False,
            capabilities=client.V1Capabilities(drop=["ALL"]),
            seccomp_profile=client.V1SeccompProfile(type="RuntimeDefault"),
        ),
    )

    # --- Pod 정의 ---
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            namespace=AGENT_NAMESPACE,
            # Label은 pod에 붙이는 임의의 key/value 쌍입니다.
            # 다음에 사용합니다:
            #   - "app": 이 application에 속하는 pod 식별
            #   - "role": Agent pod와 gateway/proxy pod 구별
            #   - "pool-status": Standby와 active의 lifecycle state 추적
            #   - "session-id": Pod를 소유한 사용자 session에 연결
            labels=labels,
        ),
        spec=client.V1PodSpec(
            # ServiceAccount는 pod의 K8s API permission을 제어합니다.
            # "agent-sa"에는 최소 RBAC를 구성해야 합니다(pod는 K8s API와
            # 전혀 통신할 필요가 없습니다).
            service_account_name="agent-sa",
            # Agent는 K8s API를 호출하지 않으므로 service-account token도
            # mount하지 마세요. Model이 지시한 코드를 실행하는 pod 내부의
            # credential을 하나 줄입니다.
            automount_service_account_token=False,
            containers=[container],
            volumes=[
                # "egress-proxy-tls" Secret을 volume으로 제공합니다.
                # Secret의 data key는 mount 경로의 파일이 됩니다.
                client.V1Volume(
                    name="egress-proxy-tls",
                    secret=client.V1SecretVolumeSource(
                        secret_name="egress-proxy-tls",  # noqa: S106 — credential이 아닌 k8s Secret 이름
                    ),
                ),
            ],
            # "Never"는 container가 종료되어도 K8s가 재시작하지 않음을 뜻합니다.
            # Agent pod는 ephemeral이며 session당 하나이고 완료 시 삭제됩니다.
            restart_policy="Never",
            # Uvicorn은 SIGTERM에서 빠르게 종료하지 않으므로 기본 30초 grace
            # period는 정리를 지연시킬 뿐입니다. Agent pod에는 drain할 가치가 있는
            # state가 없으므로 5초면 충분합니다.
            termination_grace_period_seconds=5,
        ),
    )
    return pod


# ---------------------------------------------------------------------------
# Standby pool 관리
# ---------------------------------------------------------------------------


async def _create_standby_pod() -> str:
    """Standby pod 하나를 생성하고 이름을 반환합니다.

    Standby pod는 pre-warmed 상태입니다. Image를 pull하고 container를 시작한 뒤
    session에 할당될 때까지 idle 상태로 기다립니다. 사용자는 연결할 때
    image pull + container 시작을 기다릴 필요가 없습니다.
    """
    v1 = client.CoreV1Api()
    pod_name = f"agent-standby-{uuid.uuid4().hex[:8]}"
    labels = {
        "app": "claude-agent",
        "role": "agent",
        "pool-status": "standby",  # 아직 session에 할당되지 않음
    }
    pod_manifest = _build_pod_manifest(pod_name=pod_name, labels=labels)

    logger.info(f"Creating standby pod {pod_name}")
    # asyncio.to_thread()는 blocking K8s client 호출을 thread-pool worker에서
    # 실행하여 async event loop를 block하지 않게 합니다.
    await asyncio.to_thread(
        v1.create_namespaced_pod,
        namespace=AGENT_NAMESPACE,
        body=pod_manifest,
    )
    return pod_name


def _pod_is_ready(pod) -> bool:
    """Pod가 Running이고 IP가 있으며 모든 container가 Ready이면 True입니다.

    "Running"은 container process가 시작되었다는 뜻일 뿐입니다. Readiness probe
    (/health의 HTTP GET)가 uvicorn이 실제로 listen 중인지 알려 줍니다.
    """
    return bool(
        pod.status.phase == "Running"
        and pod.status.pod_ip
        and pod.metadata.deletion_timestamp is None
        and all(cs.ready for cs in (pod.status.container_statuses or []))
    )


async def _wait_for_pod_running(pod_name: str, timeout: int = 120) -> str:
    """Running이면서 Ready가 될 때까지 pod를 poll합니다. Pod IP를 반환합니다.

    K8s pod phase: Pending -> Running -> Succeeded/Failed.
    Pod가 Running이고 cluster network에서 IP address를 할당받으며 readiness
    probe가 agent server의 connection 수락을 확인하기 전에는 사용할 수 없으므로
    기다려야 합니다.

    Pod가 실패하면 RuntimeError, `timeout`초 안에 시작하지 않으면
    TimeoutError를 발생시킵니다.
    """
    v1 = client.CoreV1Api()
    interval = 2
    elapsed = 0

    while elapsed < timeout:
        pod = await asyncio.to_thread(
            v1.read_namespaced_pod,
            name=pod_name,
            namespace=AGENT_NAMESPACE,
        )
        phase = pod.status.phase
        logger.debug(f"Pod {pod_name} phase: {phase}")

        if _pod_is_ready(pod):
            logger.info(f"Pod {pod_name} ready at {pod.status.pod_ip}")
            return pod.status.pod_ip

        if phase in ("Failed", "Unknown"):
            raise RuntimeError(f"Pod {pod_name} entered {phase} state")

        await asyncio.sleep(interval)
        elapsed += interval

    raise TimeoutError(f"Pod {pod_name} did not become Ready within {timeout}s")


async def _get_standby_pods() -> list[str]:
    """Session을 처리할 준비가 된 standby pod의 이름을 반환합니다.

    K8s label selector로 filtering합니다. API server가 모든 pod를 반환하는
    대신 server-side filtering하므로 효율적입니다.

    두 상태는 의도적으로 제외합니다. Terminating pod(deletionTimestamp 설정 —
    할당하면 곧 종료할 container로 session을 routing)와 아직 Ready가 아닌
    pod(uvicorn 시작 중 — 할당하면 connection 오류 발생)입니다.
    """
    v1 = client.CoreV1Api()
    pods = await asyncio.to_thread(
        v1.list_namespaced_pod,
        namespace=AGENT_NAMESPACE,
        label_selector="role=agent,pool-status=standby",
    )
    return [p.metadata.name for p in pods.items if _pod_is_ready(p)]


async def _count_standby_pods() -> int:
    """존재하거나 생성 중인 standby pod 수를 계산합니다(Pending 또는 Running).

    추가 생성 여부를 결정할 때 사용합니다. 할당 가능한 pod만 반환하는
    ``_get_standby_pods``와 달리 Pending pod도 계산합니다. Cold cluster에서는
    아직 image를 pull 중이며, 이를 세지 않으면 replenisher가 과잉 생성합니다.
    """
    v1 = client.CoreV1Api()
    pods = await asyncio.to_thread(
        v1.list_namespaced_pod,
        namespace=AGENT_NAMESPACE,
        label_selector="role=agent,pool-status=standby",
    )
    return sum(
        1
        for p in pods.items
        if p.status.phase in ("Pending", "Running") and p.metadata.deletion_timestamp is None
    )


async def _delete_pod_by_name(pod_name: str) -> None:
    """이름으로 pod 하나를 삭제하며 404는 무시합니다."""
    v1 = client.CoreV1Api()
    try:
        await asyncio.to_thread(
            v1.delete_namespaced_pod,
            name=pod_name,
            namespace=AGENT_NAMESPACE,
        )
    except kubernetes.client.exceptions.ApiException as e:
        if e.status != 404:
            raise


async def _claim_standby_pod(session_id: str) -> str | None:
    """Session에 standby pod를 atomic하게 할당하는 것을 시도합니다. Pod IP 또는 None 반환.

    Label patch로 atomic하게 할당합니다. 두 gateway가 같은 pod의 할당을 경쟁하면
    하나의 PATCH는 성공하고 다른 하나는 conflict 오류로 실패하며, 실패한 쪽은
    다음 standby pod로 넘어갑니다. K8s patch는 객체 수준에서 atomic하므로
    외부 locking 없이 안전합니다.
    """
    v1 = client.CoreV1Api()
    standby_pods = await _get_standby_pods()

    for pod_name in standby_pods:
        try:
            # Pod label을 patch하여 "active"로 표시하고 이 session에 연결합니다.
            # 이는 K8s API의 atomic operation입니다.
            body = {
                "metadata": {
                    "labels": {
                        "pool-status": "active",
                        "session-id": str(session_id),
                    },
                },
            }
            patched = await asyncio.to_thread(
                v1.patch_namespaced_pod,
                name=pod_name,
                namespace=AGENT_NAMESPACE,
                body=body,
            )
            pod_ip = patched.status.pod_ip
            logger.info(f"Claimed standby pod {pod_name} for session {session_id} at {pod_ip}")
            return pod_ip
        except kubernetes.client.exceptions.ApiException as e:
            # 다른 gateway instance가 먼저 이 pod를 할당받았거나 삭제되었을 수
            # 있습니다. 다음 pod로 넘어갑니다.
            logger.warning(f"Failed to claim pod {pod_name}: {e.status}")
            continue

    return None


async def _replenish_pool() -> None:
    """Standby pool을 STANDBY_POOL_SIZE까지 보충합니다.

    Pod가 할당되거나 삭제된 후 호출됩니다. Pod를 하나씩 생성하고 매번 전에
    pool 수를 다시 계산하여, 보충 중 발생한 할당을 다음 trigger까지 기다리지
    않고 이번 실행에서 반영합니다. Pending pod도 계산하므로 느린 image pull로
    인한 과잉 생성을 방지합니다.

    계속 실패하는 image(잘못된 tag, 누락된 secret)가 무한 반복하지 않도록
    loop에 한도가 있습니다. 첫 실패 pod를 정리한 뒤 중단합니다.
    """
    for _ in range(STANDBY_POOL_SIZE * 2):
        current_count = await _count_standby_pods()
        if current_count >= STANDBY_POOL_SIZE:
            logger.debug(
                f"Standby pool has {current_count}/{STANDBY_POOL_SIZE} pods, "
                "no replenishment needed"
            )
            return

        logger.info(
            f"Replenishing standby pool: {current_count}/{STANDBY_POOL_SIZE}, creating 1 pod"
        )
        pod_name = None
        try:
            pod_name = await _create_standby_pod()
            # 준비됐다고 계산하기 전에 pod가 Running이 될 때까지 대기
            await _wait_for_pod_running(pod_name)
        except Exception:
            logger.exception("Failed to create standby pod")
            if pod_name:
                # Failed/멈춘 pod를 "standby" label로 남기지 마세요.
                # Pool 수에 포함되지만 session은 처리하지 못합니다.
                try:
                    await _delete_pod_by_name(pod_name)
                except Exception:
                    logger.exception(f"Could not clean up failed standby pod {pod_name}")
            return


def _schedule_replenish() -> None:
    """Background asyncio task로 pool 보충을 시작합니다.

    Fire-and-forget 방식이며 호출자는 보충 완료를 기다리지 않습니다. 이미
    보충 중이면 중복 작업을 피하도록 no-op입니다.
    """
    global _replenish_task
    if _replenish_task and not _replenish_task.done():
        return  # 이미 보충 중
    try:
        loop = asyncio.get_running_loop()
        _replenish_task = loop.create_task(_replenish_pool())
    except RuntimeError:
        logger.warning("No running event loop, skipping replenishment")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def initialize_standby_pool() -> None:
    """Gateway 시작 시 standby pool을 pre-warm합니다.

    Application boot 중 한 번 호출합니다. K8s를 사용할 수 없으면
    (예: 로컬 개발) no-op입니다.
    """
    if not _k8s_available:
        logger.info("K8s unavailable — skipping standby pool initialization")
        return
    if not AGENT_IMAGE:
        raise RuntimeError("AGENT_IMAGE env var is required when running inside Kubernetes")
    logger.info(f"Initializing standby pool with {STANDBY_POOL_SIZE} pods")
    await _replenish_pool()


async def create_agent_pod(session_id: str) -> str:
    """Session의 실행 중인 agent pod를 가져옵니다. Pod IP address를 반환합니다.

    전략:
    1. Pre-warmed standby pod 할당 시도(즉시).
    2. 없으면 on-demand pod 생성(image pull이 필요하므로 느림).

    어느 방식이든 이후 background에서 pool을 보충하여 다음 session이
    (가능하면) standby pod를 받게 합니다.
    """
    # 먼저 pre-warmed standby pod 할당 시도
    pod_ip = await _claim_standby_pod(session_id)
    if pod_ip:
        _schedule_replenish()
        return pod_ip

    # Standby pod가 없으면 on-demand 생성으로 fallback
    logger.warning(f"No standby pods available for session {session_id}, creating on-demand")
    pod_name = f"agent-session-{session_id}"
    labels = {
        "app": "claude-agent",
        "role": "agent",
        "pool-status": "active",
        "session-id": str(session_id),
    }
    pod_manifest = _build_pod_manifest(pod_name=pod_name, labels=labels)

    v1 = client.CoreV1Api()
    await asyncio.to_thread(
        v1.create_namespaced_pod,
        namespace=AGENT_NAMESPACE,
        body=pod_manifest,
    )

    pod_ip = await _wait_for_pod_running(pod_name)
    _schedule_replenish()
    return pod_ip


async def delete_agent_pod(session_id: str) -> None:
    """Session의 agent pod를 삭제합니다.

    먼저 label로 검색하고(할당된 standby와 on-demand 모두 가능),
    안전망으로 기존 이름 방식에 fallback합니다.
    """
    v1 = client.CoreV1Api()

    # Session-id label로 pod 찾기(할당한 standby와 on-demand pod 모두
    # session-id label을 받으므로 둘 다 작동).
    pods = await asyncio.to_thread(
        v1.list_namespaced_pod,
        namespace=AGENT_NAMESPACE,
        label_selector=f"role=agent,session-id={session_id}",
    )

    if not pods.items:
        # Fallback: On-demand pod의 deterministic 이름 시도
        pod_name = f"agent-session-{session_id}"
        try:
            await asyncio.to_thread(
                v1.delete_namespaced_pod,
                name=pod_name,
                namespace=AGENT_NAMESPACE,
            )
            logger.info(f"Deleted pod {pod_name}")
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                logger.debug(f"No pod found for session {session_id}")
            else:
                raise
        return

    for pod in pods.items:
        pod_name = pod.metadata.name
        try:
            await asyncio.to_thread(
                v1.delete_namespaced_pod,
                name=pod_name,
                namespace=AGENT_NAMESPACE,
            )
            logger.info(f"Deleted pod {pod_name} for session {session_id}")
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                logger.debug(f"Pod {pod_name} already gone")
            else:
                raise

    # Slot을 비운 후 pool 보충
    _schedule_replenish()


async def get_pool_status() -> dict:
    """Standby pool의 현재 state를 반환합니다.

    Health check 및 debugging에 유용하며, 준비된 standby pod 수와
    목표 pool 크기를 알려 줍니다.
    """
    standby_pods = await _get_standby_pods()
    return {
        "target_size": STANDBY_POOL_SIZE,
        "ready_count": len(standby_pods),
        "standby_pods": standby_pods,
    }
