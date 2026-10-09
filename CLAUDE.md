# Claude Cookbooks

Claude API로 개발하기 위한 Jupyter Notebook과 Python 예제 모음입니다.

## 빠른 시작

```bash
# Dependency 설치
uv sync --all-extras

# Pre-commit hook 설치
uv run pre-commit install

# API key 설정
cp .env.example .env
# .env를 편집하여 ANTHROPIC_API_KEY를 추가
```

## 개발 명령

```bash
make format        # Ruff로 코드 포맷팅
make lint          # Lint 실행
make check         # Format-check + lint 실행
make fix           # 문제 자동 수정 + 포맷팅
make test          # Pytest 실행
```

또는 uv로 직접 실행합니다.

```bash
uv run ruff format .           # 포맷팅
uv run ruff check .            # Lint
uv run ruff check --fix .      # 자동 수정
uv run pre-commit run --all-files
```

## 코드 스타일

- **줄 길이:** 100자
- **따옴표:** 큰따옴표
- **Formatter:** Ruff

Notebook에서는 파일 중간의 import (E402), 재정의 (F811), 변수 네이밍 (N803, N806)에 대한 규칙이 완화되어 있습니다.

## Git Workflow

**Branch 네이밍:** `<username>/<feature-description>`

**Commit 형식 (conventional commits):**
```
feat(scope): add new feature
fix(scope): fix bug
docs(scope): update documentation
style: lint/format
```

## 주요 규칙

1. **API Key:** `.env` 파일을 절대로 commit하지 마세요. `dotenv.load_dotenv()`를 사용한 뒤 `os.environ` 또는 `os.getenv()`로 key에 접근하세요.

2. **Dependency:** `uv add <package>` 또는 `uv add --dev <package>`를 사용하세요. pyproject.toml을 직접 편집하지 마세요.

3. **Model:** 현재 Claude model을 사용하세요. 최신 버전은 docs.anthropic.com에서 확인하세요.
   - Sonnet: `claude-sonnet-5`
   - Haiku: `claude-haiku-4-5`
   - Opus: `claude-opus-4-8`
   - **날짜가 들어간 model ID는 절대 사용하지 마세요** (예: `claude-sonnet-4-6-20250514`). 항상 날짜 없는 alias를 사용하세요.
   - **Bedrock model ID**는 다른 형식을 따릅니다. 문서의 기본 Bedrock model ID를 사용하세요.
     - Opus 4.8: `anthropic.claude-opus-4-8`
     - Sonnet 5: `anthropic.claude-sonnet-5`
     - Haiku 4.5: `anthropic.claude-haiku-4-5-20251001-v1:0`
     - Global endpoint에는 `global.`을 앞에 붙이세요(권장): `global.anthropic.claude-opus-4-8`
     - 참고: 이전 Bedrock model은 날짜가 들어간 `-YYYYMMDD-v1:0` 접미사를 사용합니다(예: 위의 Haiku 4.5). 최신 model은 접미사 없는 `anthropic.claude-<model>` 형식을 사용합니다.

4. **Notebook:**
   - Notebook의 출력을 유지하세요(시연을 위한 의도적인 선택입니다).
   - Notebook 하나당 개념 하나를 다루세요.
   - Notebook이 처음부터 끝까지 오류 없이 실행되는지 테스트하세요.

5. **품질 검사:** Commit 전에 `make check`를 실행하세요. Pre-commit hook이 포맷팅과 Notebook 구조를 검증합니다.

## Slash Command

다음 명령은 Claude Code와 CI에서 사용할 수 있습니다.

- `/notebook-review` - Notebook 품질 검토
- `/model-check` - Claude model 참조 검증
- `/link-review` - 변경된 파일의 링크 검사

## 프로젝트 구조

```
capabilities/      # Claude 핵심 기능 (RAG, classification 등)
evals/             # Model evaluation 패턴과 benchmark
skills/            # 고급 skill 기반 Notebook
tool_use/          # Tool use와 통합 패턴
multimodal/        # Vision과 이미지 처리
misc/              # Batch processing, caching, 유틸리티
third_party/       # Pinecone, Voyage, Wikipedia 통합
extended_thinking/ # Extended reasoning 패턴
scripts/           # 검증 스크립트
.claude/           # Claude Code 명령과 skill
```

## 새로운 Cookbook 추가하기

1. 적절한 디렉터리에 Notebook을 만듭니다.
2. `registry.yaml`에 title, description, path, authors, categories 항목을 추가합니다.
3. 새로운 기여자라면 `authors.yaml`에 작성자 정보를 추가합니다.
4. 품질 검사를 실행하고 PR을 제출합니다.
