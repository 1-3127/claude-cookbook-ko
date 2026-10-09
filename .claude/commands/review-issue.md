---
allowed-tools: Bash(gh issue view:*), Bash(gh issue list:*), Bash(gh issue comment:*), Bash(gh issue edit:*), Bash(gh issue close:*), Read, Glob, Grep, AskUserQuestion
description: GitHub issue 검토 및 응답
---

## 인수

- `$ARGUMENTS`: 검토할 issue 번호

## 수행할 작업

지정된 GitHub issue를 검토하고 커뮤니티 가이드라인에 따라 적절한 응답 초안 작성을 도우세요.

### 1단계: Issue 맥락 수집

Comment를 포함한 issue 세부 정보를 가져오세요.
```bash
gh issue view $ARGUMENTS --repo anthropics/claude-cookbooks --json number,title,body,author,labels,state,comments,createdAt
```

### 2단계: Issue 분류

내용을 바탕으로 issue 유형을 판단하세요.

1. **Spam/Noise**: 의미 없는 말, 테스트 게시물, 주제와 무관한 내용 또는 악의적인 의도
2. **버그 보고**: Cookbook에서 작동하지 않는 코드, 깨진 링크 또는 잘못된 정보 보고
3. **Cookbook 제안**: 새로운 콘텐츠 또는 상당한 추가 내용 제안
4. **질문**: 사용법이나 API 동작에 관한 질문 또는 명확한 설명 요청
5. **커뮤니티 자료**: 외부 프로젝트 또는 자료 공유(Discord로 안내)
6. **중복**: 이미 존재하거나 처리된 issue

### 3단계: 관련 맥락 확인

Issue에서 특정 파일이나 Notebook을 참조한다면:
- 참조된 파일을 읽어 맥락 이해
- Issue가 유효한지 확인(예: 깨진 링크가 실제로 존재하는지)
- 이를 해결할 수 있는 관련 issue 또는 PR 검색

### 4단계: 응답 초안 작성

Issue 유형에 따라 다음 가이드라인을 준수하여 적절한 응답 초안을 작성하세요.

#### Spam/Noise의 경우:
- Comment 없이 닫기 권장
- 보안 우려 사항 표시

#### 버그 보고의 경우:
- 보고를 확인하고 보고자에게 감사 전달
- 가능한 경우 문제 확인(참조된 파일/코드 검사)
- 유효하고 간단하다면: Signed commit을 사용한 PR 제출 요청
- 유효하고 복잡하다면: 문제를 확인하고 주시하고 있음을 안내
- 이미 수정되었다면: 수정 내용(PR/commit) 참조
- 예: "보고해 주셔서 감사합니다! 이를 수정하는 PR을 제출해 주실 수 있을까요? 제출하신다면 반드시 [signed commit](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)을 사용해 주세요."

#### Cookbook 제안의 경우:
- 제안에 감사 전달
- 다음 기준으로 평가:
  - Claude API/SDK 기능에 직접 초점을 맞추고 있나요?
  - 실용적이며 명확한 교육적 가치가 있나요?
  - 기존 콘텐츠와 차별화되어 있나요?
- 유망하다면: 관심을 표현하고 필요하면 명확히 하기 위한 질문
- 적합하지 않다면: 이유를 정중히 설명하고 적절한 자료로 안내
- 안내 예: "[topic]은 흥미롭지만, 저희는 Claude의 native API 기능을 보여주는 데 초점을 맞추고 있습니다. 외부 framework의 패턴을 옮기기보다는 어떤 구체적인 Claude 기능을 보여주고 싶은지 생각해 보시기를 권합니다."

#### 질문의 경우:
- 가능한 경우 유용하고 직접적인 답변 제공
- 관련 문서 링크 제공: https://docs.claude.com
- 해당하는 경우 구체적인 cookbook 예제 참조
- 이어지는 논의를 위해 Discord 제안: https://anthropic.com/discord
- API 버그라면: 적절한 채널에 보고하도록 안내

#### 커뮤니티 자료의 경우:
- 공유에 감사하고 더 적절한 장소로 안내
- 이 리포지토리는 cookbook issue를 위한 곳이며 커뮤니티 작업 소개를 위한 곳이 아님
- 안내 후 issue 닫기
- 예: "프로젝트를 공유해 주셔서 감사합니다! 커뮤니티 자료를 GitHub issue로 추적하지는 않지만, 작업을 공유하기 좋은 곳이 있습니다. [Discord](https://anthropic.com/discord)의 **#share-your-project** 채널이나 Reddit의 [r/ClaudeAI](https://reddit.com/r/ClaudeAI) 커뮤니티를 이용해 주세요."

#### 중복의 경우:
- 원래 issue/PR 참조
- 적절하다면 중복으로 닫기

### 5단계: Label 제안

Issue 유형에 따라 적절한 label을 권장하세요.
- `bug` - 버그 보고
- `enhancement` - 기능 요청 또는 제안
- `question` - 질문
- `documentation` - 문서 개선
- `duplicate` - 이미 존재함
- `wontfix` - 처리하지 않을 예정
- `good first issue` - 새로운 기여자를 위한 간단한 수정

### 6단계: 검토 결과 제시

사용자에게 발견 사항을 제시하세요.

1. **Issue 요약**: Issue 내용에 대한 간단한 설명
2. **분류**: Issue 유형
3. **유효성 확인**: Issue가 유효하며 실행 가능한지 여부(확인한 경우)
4. **제안 응답**: 게시할 comment 초안
5. **제안 label**: 추가할 label
6. **제안 조치**: Comment, 닫기 또는 다른 조치 여부

### 7단계: 사용자 승인받기

AskUserQuestion을 사용하여 다음을 물어보세요.
- 작성한 응답 초안 게시 여부
- 제안한 label 추가 여부
- Issue 닫기 여부(적절한 경우)

### 8단계: 조치 수행(승인된 경우)

사용자 승인에 따라:

**Comment 게시:**
```bash
gh issue comment $ARGUMENTS --repo anthropics/claude-cookbooks --body "YOUR_RESPONSE"
```

**Label 추가:**
```bash
gh issue edit $ARGUMENTS --repo anthropics/claude-cookbooks --add-label "label1,label2"
```

**Issue 닫기:**
```bash
gh issue close $ARGUMENTS --repo anthropics/claude-cookbooks --reason "not planned"
```
또는 comment와 함께:
```bash
gh issue close $ARGUMENTS --repo anthropics/claude-cookbooks --comment "Closing because..."
```

## 응답 어조 가이드라인

- 전문적이고 친절하며 간결하게 작성
- 기여자의 참여에 감사 전달
- 제안을 거절할 때 직접적으로 말하되 무시하는 태도는 피하기
- 가능한 경우 실행 가능한 다음 단계 제공
- 모든 내용을 본문에서 설명하기보다 자료 링크 제공
- 지나치게 설명하거나 과도하게 사과하지 않기

## 응답 예시

**버그 보고 응답:**
```
안녕하세요 @username, 자세히 보고해 주셔서 감사합니다!

링크가 깨진 것을 확인했습니다. 이를 수정하는 PR을 제출해 주실 수 있을까요? 제출하신다면 반드시 [signed commit](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)을 사용해 주세요.

PR을 제출하지 않으셔도 괜찮습니다. 저희가 수정하겠습니다.
```

**질문 응답:**
```
안녕하세요 @username!

`cache_control` parameter가 필요한 이유는... [설명]

자세한 내용은 [prompt caching 문서](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)를 확인하세요.

추가 질문이 있으시면 [Discord](https://anthropic.com/discord)에서 논의하기 좋습니다!
```

**제안 거절 응답:**
```
안녕하세요 @username, 자세히 제안해 주셔서 감사합니다!

개념은 흥미롭지만, 저희 cookbook은 Claude의 native API 기능을 직접 보여주는 데 초점을 맞추고 있습니다. 다음을 고려해 보시기를 권합니다.

- 어떤 구체적인 Claude API 기능을 보여주고 있나요?
- 기존 문서와 어떻게 차별화되나요?
- 사용자가 외부 dependency 없이 독립적으로 실행할 수 있나요?

이 질문들을 중심으로 제안을 재구성해 주신다면 기꺼이 다시 검토하겠습니다. SDK에 관심을 갖고 참여해 주셔서 감사합니다!
```
