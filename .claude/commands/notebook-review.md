---
allowed-tools: Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(echo:*),Read,Glob,Grep,WebFetch
description: Jupyter Notebook과 Python 스크립트 종합 검토
---

**중요**: 위 prompt에 명시적으로 나열된 파일만 검토하세요. 추가 파일을 검색하거나 검토하지 마세요.

Notebook review skill을 사용하여 지정된 Jupyter Notebook과 Python 스크립트를 검토하세요.

다음 내용을 포함한 명확한 요약을 제공하세요.
- ✅ 잘된 점
- ⚠️ 개선 제안
- ❌ 반드시 수정해야 하는 중대한 문제

**중요: 다음 명령을 사용하여 검토 내용을 pull request의 comment로 게시하세요: `gh pr comment $PR_NUMBER --body "your review"`**
