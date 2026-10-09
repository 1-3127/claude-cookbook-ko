---
allowed-tools: Bash(gh pr checkout:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(gh pr review:*), Bash(git diff:*), Bash(git log:*), Task, Read, Glob, Grep, AskUserQuestion
description: 열린 pull request를 검토하고 선택적으로 GitHub에 검토 결과 게시
---

## 인수

- `$ARGUMENTS`: 검토할 PR 번호 또는 URL

## 수행할 작업

지정된 pull request를 검토하고 피드백을 제공하세요.

### 1단계: PR checkout

먼저 다음을 사용하여 PR을 checkout하세요.
```
gh pr checkout $ARGUMENTS
```

### 2단계: PR 맥락 수집

PR 세부 정보를 가져오세요.
```
gh pr view $ARGUMENTS
gh pr diff $ARGUMENTS
```

### 3단계: 코드 변경 검토

`subagent_type: "code-reviewer"`로 Task 도구를 사용하여 변경 사항에 대한 철저한 코드 검토를 수행하세요. 분석을 위해 diff와 변경 파일을 agent에 전달하세요.

Code-reviewer agent는 다음을 분석합니다.
- 코드 품질과 모범 사례
- 잠재적인 버그 또는 문제
- 보안 우려 사항
- 성능 고려사항
- 문서와 주석

### 4단계: 검토 결과 제시

코드 검토가 완료되면 다음 형식으로 사용자에게 검토 결과를 제시하세요.

```
## PR 검토

**권고**: APPROVE | REQUEST_CHANGES | COMMENT

### 요약
[이 PR이 하는 일에 대한 1~2문장 개요]

### 실행 가능한 피드백(N개 항목)
- [ ] `file.py:42` - 문제 또는 필요한 변경 설명
- [ ] `notebook.ipynb` (`some_code = ...`가 있는 셀) - 설명

### 상세 검토

#### 코드 품질
[코드 패턴, 가독성, 유지보수성 분석]

#### 보안
[보안 고려사항]

#### 제안
[선택적 개선 사항]

#### 긍정적인 점
[잘한 점]
```

**가이드라인:**
- 작성자가 진행 상황을 추적할 수 있도록 실행 가능한 항목에는 체크박스를 사용하세요.
- Jupyter Notebook에서는 셀 번호 대신 코드 스니펫을 참조하세요.
- 가능한 경우 file:line 참조로 구체적으로 작성하세요.

### 5단계: 검토 결과 게시 여부 묻기

AskUserQuestion 도구를 사용하여 사용자에게 물어보세요.
- 이 검토 결과를 GitHub에 게시할지 여부
- 수행할 검토 조치: APPROVE, REQUEST_CHANGES 또는 COMMENT

### 6단계: 검토 결과 게시(승인된 경우)

사용자가 확인하면 다음을 사용하여 검토 결과를 게시하세요.
```
gh pr review $ARGUMENTS --body "YOUR_REVIEW_BODY" --approve|--request-changes|--comment
```

GitHub에 게시할 때 불필요한 내용을 줄이기 위해 상세 검토 섹션을 접을 수 있는 `<details>` tag로 감싸세요.

```markdown
## PR 검토

**권고**: APPROVE | REQUEST_CHANGES | COMMENT

### 요약
[요약]

<details>
<summary>실행 가능한 피드백(N개 항목)</summary>

- [ ] 항목...

</details>

<details>
<summary>상세 검토</summary>

[전체 검토 내용]

</details>
```

사용자의 선택에 따라 적절한 flag를 사용하세요.
- APPROVE에는 `--approve`
- REQUEST_CHANGES에는 `--request-changes`
- COMMENT만 하는 경우 `--comment`

**중요:** `gh pr review` 명령은 성공 시 아무것도 출력하지 않습니다. 이 명령은 한 번만 실행하세요. 출력이 없다면 성공을 의미하므로 재시도하지 마세요.
