---
allowed-tools: Bash(gh pr diff:*), Bash(gh pr view:*), Bash(gh pr review:*), Bash(git diff:*), Bash(git log:*), Task, Read, Glob, Grep
description: Pull request를 검토하고 GitHub에 검토 결과 게시(CI/자동화용)
---

## 인수

- `$ARGUMENTS`: 검토할 PR 번호

## 수행할 작업

지정된 pull request를 검토하고 GitHub에 검토 결과를 게시하세요. 이 명령은 CI/자동화 환경을 위해 설계되었습니다.

### 1단계: PR 맥락 수집

PR 세부 정보와 diff를 가져오세요.
```
gh pr view $ARGUMENTS
gh pr diff $ARGUMENTS
```

### 2단계: 코드 변경 검토

`subagent_type: "code-reviewer"`로 Task 도구를 사용하여 변경 사항에 대한 철저한 코드 검토를 수행하세요. 분석을 위해 diff와 변경 파일을 agent에 전달하세요.

Code-reviewer agent는 다음을 분석합니다.
- 코드 품질과 모범 사례
- 잠재적인 버그 또는 문제
- 보안 우려 사항
- 성능 고려사항
- 문서와 주석

### 3단계: 검토 결과 결정

코드 검토 발견 사항을 바탕으로 적절한 검토 조치를 결정하세요.
- **APPROVE** (`--approve`): 코드가 좋아 보이며 중요한 문제가 발견되지 않음
- **REQUEST_CHANGES** (`--request-changes`): Merge 전에 반드시 수정해야 하는 중대한 문제
- **COMMENT** (`--comment`): Merge를 차단하지 않는 제안 또는 사소한 문제

### 4단계: 검토 결과 게시

다음을 사용하여 GitHub에 검토 결과를 게시하세요.
```
gh pr review $ARGUMENTS --body "YOUR_REVIEW_BODY" --approve|--request-changes|--comment
```

접을 수 있는 섹션이 포함된 다음 template을 사용하여 검토 본문을 작성하세요.

```markdown
## PR 검토

**권고**: APPROVE | REQUEST_CHANGES | COMMENT

### 요약
[이 PR이 하는 일에 대한 1~2문장 개요]

<details>
<summary>실행 가능한 피드백(N개 항목)</summary>

주의가 필요한 구체적인 항목을 나열하세요. 추적 가능한 항목에는 체크박스를 사용하세요.

- [ ] `file.py:42` - 문제 또는 필요한 변경 설명
- [ ] `notebook.ipynb` (`some_code = ...`가 있는 셀) - 설명
- [ ] 일반: 특정 파일에 국한되지 않는 피드백 설명

</details>

<details>
<summary>상세 검토</summary>

### 코드 품질
[코드 패턴, 가독성, 유지보수성 분석]

### 보안
[보안 고려사항 또는 우려 사항]

### 제안
[차단하지 않는 선택적 개선 사항]

### 긍정적인 점
[잘한 점을 구체적으로 작성]

</details>
```

**가이드라인:**
- 요약과 실행 가능한 피드백은 보이도록 유지하세요(접힌 섹션 밖).
- 불필요한 내용을 줄이기 위해 상세 분석은 접힌 "상세 검토" 섹션에 넣으세요.
- 작성자가 처리한 내용을 추적할 수 있도록 실행 가능한 피드백에는 체크박스를 사용하세요.
- Jupyter Notebook에서는 셀 번호 대신 코드 스니펫을 참조하세요(예: "`data = pd.read_csv(...)`가 있는 셀").

**중요:** `gh pr review` 명령은 성공 시 아무것도 출력하지 않습니다. 이 명령은 한 번만 실행하세요. 출력이 없다면 성공을 의미하므로 재시도하지 마세요.
