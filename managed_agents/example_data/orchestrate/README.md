# Orchestrate, issue부터 merge된 PR까지 진행하기

`CMA_orchestrate_issue_to_pr.py`가 사용하는 자체 완결적인 maintainer workflow mock입니다. cookbook은 이 디렉터리를 zip으로 압축하여 agent에 건넵니다.

- `gh-mock`: 관련 `gh` subcommand를 흉내 내는 bash script. 상태는 `.gh-state/`에 보존됩니다.
- `issue_42.json`: Unicode bug report(`Café Culture` → `caf-culture`). agent가 코드를 읽어야 할 만큼 모호합니다.
- `src/url_utils.py` + `src/blog.py` + `tests/test_urls.py`: 버그가 있는 `slugify()`와 이를 잡는 실패하는 테스트입니다.

복구 지점 두 개를 넣었습니다. 불완전한 첫 수정은 pytest traceback과 함께 CI에 실패하며, 모의 reviewer bot은 `slugify()`에 docstring이 없으면 merge를 막습니다. 정상적인 실행은 `.gh-state/pr_101.json`에 `state: merged`, `ci/test: pass`, `APPROVED` review가 나타나는 상태로 끝납니다.

