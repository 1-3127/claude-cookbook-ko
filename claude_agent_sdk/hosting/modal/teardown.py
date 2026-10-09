"""이 app의 모든 sandbox를 중지하고 session volume을 삭제합니다.

Idle resource에 과금되지 않도록 cookbook을 마치면 실행하세요::

    python hosting/modal/teardown.py
"""

from __future__ import annotations

import modal

# Teardown이 import 시 부작용으로 image build를 일으키지 않도록
# modal_app에서 import하지 않고 inline으로 정의합니다.
APP_NAME = "research-agent-hosting"
VOLUME_NAME = "research-agent-sessions"


def main() -> None:
    app = modal.App.lookup(APP_NAME, create_if_missing=False)
    for sandbox in modal.Sandbox.list(app_id=app.app_id):
        print(f"terminating sandbox {sandbox.object_id}")
        sandbox.terminate()

    modal.Volume.objects.delete(VOLUME_NAME, allow_missing=True)
    print(f"deleted volume {VOLUME_NAME}")


if __name__ == "__main__":
    main()
