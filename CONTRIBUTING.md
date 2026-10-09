# Claude Cookbooks에 기여하기

Claude Cookbooks 기여에 관심을 가져 주셔서 감사합니다! 이 가이드는 개발을 시작하고 기여 내용이 품질 기준을 충족하도록 돕습니다.

## 개발 환경 설정

### 사전 준비

- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/) package manager(권장) 또는 pip

### 빠른 시작

1. **uv 설치**(권장 package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   
   또는 Homebrew로 설치합니다.
   ```bash
   brew install uv
   ```

2. **리포지토리 clone**:
   ```bash
   git clone https://github.com/anthropics/claude-cookbooks.git
   cd claude-cookbooks
   ```

3. **개발 환경 설정**:
   ```bash
   # Virtual environment 생성 및 dependency 설치
   uv sync --all-extras
   
   # 또는 pip 사용:
   pip install -e ".[dev]"
   ```

4. **Pre-commit hook 설치**:
   ```bash
   uv run pre-commit install
   # 또는: pre-commit install
   ```

5. **API key 설정**:
   ```bash
   cp .env.example .env
   # .env를 편집하여 Claude API key를 추가
   ```

## 품질 기준

이 리포지토리는 코드 품질을 유지하기 위해 자동화 도구를 사용합니다.

### Notebook 검증 도구 구성

- **[nbconvert](https://nbconvert.readthedocs.io/)**: 테스트를 위한 Notebook 실행
- **[ruff](https://docs.astral.sh/ruff/)**: Jupyter를 기본 지원하는 빠른 Python linter와 formatter
- **Claude AI Review**: Claude를 사용한 지능형 코드 검토

**참고**: 사용자가 예상 결과를 확인할 수 있도록 Notebook 출력은 의도적으로 이 리포지토리에 유지합니다.

### Claude Code Slash Command

이 리포지토리에는 Claude Code(로컬 개발용)와 GitHub Actions CI에서 모두 작동하는 slash command가 포함되어 있습니다. Claude Code로 이 리포지토리에서 작업할 때 자동으로 사용할 수 있습니다.

**사용 가능한 명령**:
- `/link-review` - Markdown과 Notebook의 링크 검증
- `/model-check` - Claude model 사용이 최신 상태인지 확인
- `/notebook-review` - 종합적인 Notebook 품질 검사

**Claude Code에서 사용하기**:
```bash
# CI에서 실행하는 것과 같은 검증 실행
/notebook-review skills/my-notebook.ipynb
/model-check
/link-review README.md
```

이 명령들은 CI pipeline과 정확히 같은 검증 로직을 사용하므로 push 전에 문제를 발견하는 데 도움이 됩니다. 명령 정의는 로컬과 CI에서 모두 사용할 수 있도록 `.claude/commands/`에 저장되어 있습니다.

### Commit 전

1. **품질 검사 실행**:
   ```bash
   uv run ruff check skills/ --fix
   uv run ruff format skills/
   
   uv run python scripts/validate_notebooks.py
   ```

2. **Notebook 실행 테스트**(선택 사항, API key 필요):
   ```bash
   uv run jupyter nbconvert --to notebook \
     --execute skills/classification/guide.ipynb \
     --ExecutePreprocessor.kernel_name=python3 \
     --output test_output.ipynb
   ```

### Pre-commit Hook

Pre-commit hook은 코드 품질을 보장하기 위해 각 commit 전에 자동으로 실행됩니다.

- Ruff로 코드 포맷팅
- Notebook 구조 검증

Hook이 실패하면 문제를 수정한 후 다시 commit하세요.

## 기여 가이드라인

### Notebook 모범 사례

1. **API key에 환경 변수 사용**:
   ```python
   import os
   api_key = os.environ.get("ANTHROPIC_API_KEY")
   ```

2. **현재 Claude model 사용**:
   - 가능한 경우 유지보수가 용이하도록 model alias를 사용하세요.
   - 최신 Haiku model: `claude-haiku-4-5` (Haiku 4.5)
   - 현재 model 확인: https://docs.claude.com/en/docs/about-claude/models/overview
   - Claude가 PR 검토에서 model 사용을 자동으로 검증합니다.

3. **Notebook의 초점 유지**:
   - Notebook 하나당 개념 하나
   - 명확한 설명과 주석
   - 예상 출력을 Markdown 셀로 포함

4. **Notebook 테스트**:
   - 처음부터 끝까지 오류 없이 실행되는지 확인하세요.
   - 예제 API 호출에는 최소한의 token을 사용하세요.
   - 오류 처리를 포함하세요.

5. **Managed Agent에 cookbook 이름으로 tag 지정**:
   ```python
   agent = client.beta.agents.create(
       name="cookbook-data-analyst",
       metadata={"anthropic_cookbook": "claude-cookbooks/data-analyst-agent"},
       ...
   )
   ```
   - 사람들이 어떤 cookbook을 실행하는지 알 수 있도록 모든 `agents.create` 호출에 이를 전달하세요.
   - 값은 `claude-cookbooks/`와 kebab-case로 된 Notebook 파일명의 조합입니다(`data_analyst_agent.ipynb`는 `data-analyst-agent`가 됩니다).
   - 소문자, 숫자, 하이픈만 사용하세요. 다른 형식의 값은 attribution에서 무시되며, 이를 알리는 오류도 발생하지 않습니다.
   - Session은 agent의 tag를 상속하므로 `sessions.create`에는 아무것도 필요하지 않습니다.

### Git Workflow

1. **Feature branch 생성**:
   ```bash
   git checkout -b <your-name>/<feature-description>
   # 예: git checkout -b alice/add-rag-example
   ```

2. **Conventional commit 사용**:
   ```bash
   # 형식: <type>(<scope>): <subject>
   
   # 유형:
   feat     # 새로운 기능
   fix      # 버그 수정
   docs     # 문서
   style    # 포맷팅
   refactor # 코드 구조 변경
   test     # 테스트
   chore    # 유지보수
   ci       # CI/CD 변경
   
   # 예:
   git commit -m "feat(skills): add text-to-sql notebook"
   git commit -m "fix(api): use environment variable for API key"
   git commit -m "docs(readme): update installation instructions"
   ```

3. **Commit을 atomic하게 유지**:
   - Commit 하나당 논리적 변경 하나
   - 명확하고 내용을 잘 설명하는 메시지 작성
   - 해당하는 경우 issue 참조

4. **Push 및 PR 생성**:
   ```bash
   git push -u origin your-branch-name
   gh pr create  # 또는 GitHub 웹 인터페이스 사용
   ```

### Pull Request 가이드라인

1. **PR 제목**: Conventional commit 형식을 사용하세요.
2. **설명**: 다음을 포함하세요.
   - 변경한 내용
   - 변경한 이유
   - 테스트 방법
   - 관련 issue 번호
3. **PR의 초점 유지**: PR 하나당 기능/수정 하나
4. **피드백에 응답**: 검토 의견에 신속하게 대응하세요.

## 테스트

### 로컬 테스트

검증 모음을 실행합니다.

```bash
# 모든 Notebook 검사
uv run python scripts/validate_notebooks.py

# 모든 파일에 pre-commit 실행
uv run pre-commit run --all-files
```

### CI/CD

GitHub Actions workflow는 다음을 자동으로 수행합니다.

- Notebook 구조 검증
- Ruff로 코드 lint
- Notebook 실행 테스트(maintainer용)
- 링크 검사
- Claude가 코드와 model 사용 검토

자원을 절약하기 위해 외부 기여자에게는 제한된 API 테스트가 제공됩니다.

## 도움받기

- **Issue**: [GitHub Issues](https://github.com/anthropics/claude-cookbooks/issues)
- **Discord**: [Anthropic Discord](https://www.anthropic.com/discord)

## 보안

- API key나 secret을 절대로 commit하지 마세요.
- 민감한 데이터에는 환경 변수를 사용하세요.
- 보안 문제는 security@anthropic.com으로 비공개 보고하세요.

## License

기여하면 자신의 기여 내용에 프로젝트와 동일한 license(MIT License)가 적용된다는 데 동의하는 것입니다.
