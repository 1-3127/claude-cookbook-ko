"""Client와 agent pod 사이의 투명한 SSE relay.

Gateway는 agent의 event stream을 이해하지 않으며 byte를 그대로 전달합니다.
Pod 안의 ``hosting/server.py``는 ``POST /sessions/{id}/messages``에서
Server-Sent Events를 사용합니다. 해당 요청을 열어 parsing 없이 raw SSE byte를
호출자에게 전달합니다. Agent의 wire format이 바뀌어도 이 파일은 영향을 받지 않습니다.
"""

import json
import logging
from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

AGENT_PORT = 8000

# 죽은 pod IP가 빠르게 실패하도록 connect/write/pool은 제한하고 read는 무제한.
# Agent turn은 정상적으로도 몇 분 동안 streaming할 수 있기 때문입니다.
_TIMEOUT = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0)


async def relay_sse(
    pod_ip: str,
    session_id: str,
    body: dict,
) -> AsyncIterator[bytes]:
    """Agent pod에 request body를 POST하고 raw-SSE byte stream을 반환합니다.

    이 coroutine이 반환되기 전에 upstream connection을 수립하므로, 죽거나
    접근 불가능한 pod는 stream 도중 connection 중단(client에서는 ``curl (18)``)
    대신 호출자에게 명확한 502로 나타납니다. 호출자는 coroutine을 await하고
    반환한 iterator를 ``media_type="text/event-stream"``의 ``StreamingResponse``로
    감쌉니다.

    ``aiter_lines()``가 아닌 ``aiter_raw()``가 여러 줄의 ``data:`` payload 및
    빈 줄 event delimiter를 정확히 보존합니다. Re-framing하지 않습니다.
    """
    url = f"http://{pod_ip}:{AGENT_PORT}/sessions/{session_id}/messages"
    # 의도적으로 async with가 아님 — client는 send(..., stream=True)보다 오래 유지돼야 함.
    client = httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        req = client.build_request("POST", url, json=body)
        upstream = await client.send(req, stream=True)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail=f"agent pod {pod_ip} unreachable: {exc}",
        ) from exc

    if upstream.status_code >= 400:
        body_bytes = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail=f"agent pod returned {upstream.status_code}: "
            f"{body_bytes.decode(errors='replace')[:200]}",
        )

    async def _stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        except httpx.HTTPError as exc:
            # Stream 중간에 pod가 종료됨(OOM-kill, eviction). HTTP status를 이미
            # 보냈으므로 502를 반환할 수 없습니다. Connection을 끊는 대신 contract의
            # ``event: error`` frame을 내보냅니다.
            logger.warning(f"Upstream stream from {pod_ip} aborted: {exc!r}")
            payload = json.dumps({"message": f"agent pod stream aborted: {exc}"})
            yield f"event: error\ndata: {payload}\n\n".encode()
        finally:
            await upstream.aclose()
            await client.aclose()

    return _stream()
