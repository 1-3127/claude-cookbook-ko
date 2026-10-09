---
allowed-tools: Read,Glob,Grep,Edit
description: registry.yaml에 새로운 Notebook 추가
---

위 prompt에서 지정한 Notebook에 대한 새로운 항목을 `registry.yaml`에 추가하세요.

## 지침

1. 지정된 경로의 **Notebook을 읽어** 내용을 이해하세요.
2. `authors.yaml`에 **작성자가 있는지 확인**하세요.
   - 사용자에게 Notebook 작성자의 GitHub username을 물어보세요.
   - `authors.yaml`을 읽고 해당 username이 key로 존재하는지 확인하세요.
   - 작성자가 없다면 사용자에게 세부 정보를 물어보고 `authors.yaml`에 추가하세요.
     - **name**: 전체 표시 이름
     - **website**: GitHub profile URL 또는 개인 웹사이트
     - **avatar**: 기본값으로 `https://github.com/<username>.png` 사용
3. 다음 필드로 **Registry 항목을 생성**하세요.

### 필수 필드
- **title**: Notebook의 첫 heading에서 추출하거나 간결하고 내용을 잘 설명하는 제목 생성
- **description**: Notebook에서 가르치는 내용을 요약하는 짧은 1~2문장 설명 작성
- **path**: 리포지토리 루트 기준 Notebook 상대 경로
- **authors**: 2단계의 GitHub username 사용
- **date**: 오늘 날짜를 YYYY-MM-DD 형식으로 사용
- **categories**: 다음 목록에서 적절한 category 1~2개 선택:
  - Agent Patterns
  - Claude Agent SDK
  - Cybersecurity
  - Evals
  - Fine-Tuning
  - Multimodal
  - Integrations
  - Observability
  - RAG & Retrieval
  - Responses
  - Skills
  - Thinking
  - Tools

### 스타일 가이드라인
- 제목은 간결하면서도 내용을 잘 설명해야 합니다(기존 항목의 예시 참고).
- 설명은 사용자가 무엇을 배우거나 만들게 될지에 초점을 맞춰 약 15~20단어로 작성해야 합니다.
- Notebook의 주요 초점에 가장 잘 맞는 category를 선택하세요.

## 출력

1. 작성자가 새로 추가된다면 제안하는 `authors.yaml` 항목을 검토용으로 보여주고 승인 후 추가하세요.
2. 제안하는 `registry.yaml` 항목을 사용자에게 검토용으로 보여주세요.
3. 사용자 승인 후 Edit 도구로 `registry.yaml`에 항목을 덧붙이세요.
4. 파일 내에서 path 기준 알파벳순을 유지하거나, 확실하지 않으면 끝에 덧붙이세요.

## 항목 형식 예시

### authors.yaml (새로운 작성자인 경우에만)
```yaml
github-username:
  name: Full Name
  website: https://github.com/github-username
  avatar: https://github.com/github-username.png
```

### registry.yaml
```yaml
- title: Example Notebook Title
  description: 이 notebook이 다루는 내용과 사용자에게 가르치는 내용을 간단히 설명.
  path: category/notebook_name.ipynb
  authors:
  - github-username
  date: 'YYYY-MM-DD'
  categories:
  - Category Name
```
