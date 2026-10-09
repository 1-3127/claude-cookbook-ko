---
allowed-tools: Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)
description: 현재 공개 model을 기준으로 Claude model 사용 검증
---

**중요**: 위 prompt에 명시적으로 나열된 파일만 검토하세요. 추가 파일을 검색하거나 검토하지 마세요.

지정된 변경 파일의 Claude model 사용을 검토하세요.

먼저 다음 주소에서 현재 허용되는 model 목록을 가져오세요.
https://docs.claude.com/en/docs/about-claude/models/overview.md

그런 다음 확인하세요.
1. 모든 model 참조가 현재 공개 model 목록에 속하는지 확인
2. Deprecated model(이전 Sonnet 3.5, Opus 3 버전) 표시
3. 내부/비공개 model 이름 표시
4. 유지보수가 용이하도록 -latest로 끝나는 alias 사용 제안

발견된 문제에 대해 명확하고 실행 가능한 피드백을 제공하세요.

**중요: 다음 명령을 사용하여 발견 사항을 pull request의 comment로 게시하세요: `gh pr comment $PR_NUMBER --body "your findings"`**
