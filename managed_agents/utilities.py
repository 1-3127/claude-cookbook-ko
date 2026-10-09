"""cookbook notebook의 공유 helper.

Notebook 00은 세션 출력을 소비하는 두 방법을 소개합니다.
사후 `events.list` polling과 `events.stream`의 실시간 event streaming입니다.
처음 접할 때 실제 API 형태를 볼 수 있도록 두 루프 모두 00 안에 작성되어 있습니다.

소개가 끝나면 다른 모든 notebook은 루프를 반복하지 않고 이 module에서
`stream_until_end_turn`을 import합니다. helper는 notebook 00의 streaming 패턴을
그대로 가져와 `agent.message` text를 출력하고 각 `agent.tool_use`를 표시하며,
`stop_reason.type == "end_turn"`인 `session.status_idle`이 도착하면 종료합니다.

helper는 의도적으로 `requires_action`을 처리하지 않습니다. custom tool notebook
(01 Part A와 05)은 turn 도중 tool 호출에 응답해야 하므로 stream을 직접 진행하며
루프를 내부에 유지합니다.
"""

import io
import textwrap
import time
import zipfile

from anthropic import Anthropic


def wait_for_idle_status(client: Anthropic, session_id: str, max_wait: float = 5.0) -> None:
    """세션의 서버 측 status 필드가 `idle`이 될 때까지 polling합니다.

    SSE stream의 `session.status_idle` event는 `sessions.retrieve`가
    `status == "idle"`을 보고하기 조금 전에 도착할 수 있어, stream 종료 직후
    `archive()` 호출이 "cannot be archived while its status is running."과 함께
    400을 반환할 수 있습니다. 이 helper는 짧은 polling으로 race를 처리합니다.
    `stream_until_end_turn` 후(또는 내부 stream 루프 종료 후),
    `archive()` 전에 호출하세요.
    """
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        if client.beta.sessions.retrieve(session_id).status == "idle":
            return
        time.sleep(0.25)


def stream_until_end_turn(client: Anthropic, session_id: str) -> None:
    """세션 event를 streaming하고 agent가 turn을 완료할 때까지 출력합니다.

    Notebook 00의 streaming 패턴을 helper로 분리하여 이후 notebook에서
    반복하지 않게 합니다. 세션은 turn 종료 및 custom tool 응답이 필요할 때
    모두 입력을 기다리는 동안 `session.status_idle`을 내보내므로
    `stop_reason.type`으로 구분하여 `end_turn`에서만 종료합니다.

    stream이 종료한 뒤에도 서버 측 status가 안정될 때까지 기다려
    즉시 `archive()`를 호출해도 state machine과 race가 발생하지 않게 합니다.
    """
    with client.beta.sessions.events.stream(session_id) as stream:
        for ev in stream:
            match ev.type:
                case "agent.message":
                    for block in ev.content:
                        if block.type == "text":
                            print(block.text, end="")
                case "agent.tool_use":
                    print(f"\n[{ev.name}]")
                case "session.status_idle" if ev.stop_reason and ev.stop_reason.type == "end_turn":
                    break
                case "session.status_terminated":
                    return
    wait_for_idle_status(client, session_id)


# Notebook 04는 `example_data/`에 파일을 commit하는 대신
# 아래 helper로 repo fixture를 메모리에 만듭니다.
# repo가 충분히 작아 helper가 stub 파일 디렉터리보다
# 읽기 쉽습니다.


def make_unfamiliar_repo_zip() -> io.BytesIO:
    """오래된 문서가 있는 작은 repository의 ZIP을 메모리에 만듭니다.

    repo에는 `services/` 아래 microservices로 배치된 약 37개 파일이 있지만
    `ARCHITECTURE.md`는 여전히 이전 monolithic 구조를 설명합니다.
    grounding notebook은 실제 코드와 대조하지 않고 문서를 믿는 agent가
    확신에 찬 틀린 답을 만드는 것을 보여 주는 데 사용합니다.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "ARCHITECTURE.md",
            textwrap.dedent("""\
            # Architecture (STALE, do not trust)

            The app is a monolith with three layers:
            - api/ for REST handlers
            - core/ for business logic
            - db/ for database access

            [Out of date. The real structure is microservices under
            services/. An agent that trusts this without reading the
            code will answer wrong.]
        """),
        )
        zf.writestr(
            "README.md",
            "# Widget Service\n\nSee ARCHITECTURE.md (possibly outdated).\n",
        )
        for svc in ["auth", "billing", "notifications", "widgets"]:
            zf.writestr(
                f"services/{svc}/main.py",
                f"# {svc} service entrypoint\ndef handle(): ...\n",
            )
            zf.writestr(f"services/{svc}/models.py", f"class {svc.title()}: ...\n")
            for i in range(6):
                zf.writestr(f"services/{svc}/util_{i}.py", f"def helper_{i}(): ...\n")
        for legacy in ["api", "core", "db"]:
            zf.writestr(f"{legacy}/.gitkeep", "")
    buf.seek(0)
    return buf
