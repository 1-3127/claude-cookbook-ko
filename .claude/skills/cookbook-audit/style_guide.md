# 1. 도입부

목적: 구축하는 장치가 아니라 해결할 문제와 제공할 가치를 중심으로 Notebook을 구성합니다.

### 구조

문제로 관심 끌기(1~2문장)
중요한 이유(1~2문장)
할 수 있게 될 일(학습 목표로 2~4개 bullet point)
선택 사항: 이를 통해 가능해지는 일(더 넓은 활용 가능성에 대한 1문장)
문제나 가치로 시작할 수 있지만 장치로 시작해서는 안 됩니다. Terminal Learning Objective (TLO)와 Enabling Learning Objective (ELO)를 처음에 나열하고, 결론에서 다시 연결하세요. 이는 사용자와 학습 계약을 맺는 것입니다.

좋은 예: 
엔지니어링 팀의 GitHub Actions workflow는 수십 가지 이유로 실패합니다. Flaky test, dependency 충돌, 인프라 문제 또는 실제 버그 때문입니다. 

즉시 주의가 필요한 실패와 기다려도 되는 실패를 수동으로 triage하느라 매주 senior engineer의 시간이 몇 시간씩 낭비됩니다. 

AI observability agent는 CI/CD pipeline을 연중무휴로 모니터링하고, signal과 noise를 구분하며, 중요한 것만 escalate할 수 있습니다. 중대한 실패를 절대로 놓치지 않으면서 수동 triage 시간을 60~80% 줄입니다. 

나쁜 예:
이 Notebook에서는 research agent를 만들겠습니다. Research agent는 인터넷을 검색하고 정보를 분석할 수 있어 유용합니다. Claude Code SDK를 사용하여 WebSearch 도구가 있는 agent를 만들겠습니다.

다음 방법을 배웁니다.
- `query()` 함수 사용
- `ClaudeSDKClient` 설정
- WebSearch 도구 활성화
- Multi-turn 대화 처리

### Template

```
## 도입부

[2~3문장: 어떤 문제인가요? 왜 어렵거나 중요한가요?]

[1~2문장: 이 문제의 해결이 중요한 이유 / 이를 통해 얻는 가치]

**이 cookbook을 마치면 다음을 할 수 있습니다.**
- [동작을 나타내는 동사] [구체적인 기능] [맥락/제약]
- [동작을 나타내는 동사] [구체적인 기능] [맥락/제약]
- [동작을 나타내는 동사] [구체적인 기능] [맥락/제약]
- [고급 결과를 위한 선택적 4번째 항목]

[1~2문장: 이 패턴이 다른 사용 사례로 확장되는 방법]
```

# 2. 사전 준비와 설정
사용자가 이 프로젝트를 성공적으로 진행하는 데 필요한 일반적인 요구사항을 마련하세요. Software 요구사항(예: python >= 3.11, anthropic>=0.71)과 software 외 요구사항(Python 실무 지식, RAG architecture에 대한 이해)을 모두 포함합니다. 

Pip으로 설치할 때 %%capture를 사용하여 Jupyter stdout에 pip install 출력이 나타나지 않도록 하세요(매우 장황할 수 있습니다).

```markdown
## 사전 준비

이 가이드를 따르기 전에 다음을 갖추었는지 확인하세요.

* [필수 지식/도구 - 없으면 cookbook이 작동하지 않음]


## 설정

[설명이 있는 단계별 지침]
[`os.setenv`보다 `dotenv` 선호]
```

좋은 예:
```markdown
%%capture
%pip install -U anthropic scikit-learn voyageai

--- 

import anthropic
import dotenv

# 좋은 습관을 가르침
dotenv.load_dotenv()

# Model 이름을 상수로 두면 변경하기 쉬움 
MODEL = "claude-haiku-4-5"

client = anthropic.Anthropic()
```

나쁜 예:

```markdown
%pip install anthropic
%pip install foo
%pip install bar
%pip install baz
%pip install this
%pip install that

--

# 나쁜 습관을 가르침
os.environ["ANTHROPIC_API_KEY"] = "YOUR_ANTHROPIC_API_KEY"

# 불필요한 중복
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')
```

### Template

```markdown
## 사전 준비

이 가이드를 따르기 전에 다음을 갖추었는지 확인하세요.

**필수 지식:**
- Python 기초 - 함수, 반복문, 기본 자료구조를 편하게 다룰 수 있음
- API와 JSON에 대한 기본적인 이해

**필수 도구:**
- Python 3.11 이상
- Anthropic API key ([여기서 발급](https://console.anthropic.com))

**권장 사항:**
- Python async/await 패턴에 대한 이해
- RAG architecture 개념에 대한 기본 지식

## 설정

먼저 필요한 dependency를 설치합니다.

~~~python
%%capture
%pip install -U anthropic scikit-learn numpy python-dotenv
~~~


**참고:** `.env` 파일에 다음이 포함되어 있는지 확인하세요.
ANTHROPIC_API_KEY=your_key_here


환경 변수를 불러오고 client를 설정합니다.

~~~python
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"

client = anthropic.Anthropic()
~~~
```


# 3. Cookbook 핵심 섹션
각 기능/개념은 문서화가 아닌 시연을 통해 가르치는 별도 섹션을 갖습니다.

Architecture 개요를 포함하거나, 전체 프로젝트를 보여주거나, 더 큰 프로젝트를 향해 단계적으로 구축할 수 있습니다. 긴 내용을 나누는 데 도움이 되도록 시각 자료를 자유롭게 포함하세요. 외부 콘텐츠로 연결하기보다 본문 내 이미지를 선호하세요. 

기능 나열, 명백한 내용에 대한 과도한 설명, 맥락 없는 코드를 피하세요. 

코드 블록을 소개하기 전에 무엇을 할 것인지 설명하고, 실행한 뒤에는 방금 배운 내용을 설명해야 합니다.

4. 결론
결론은 학습 목표에 다시 연결되어야 하며, 독자에게 다른 읽을거리, 링크 또는 이어서 탐구할 아이디어를 안내해야 합니다. 

좋은 예:
```
## 이 가이드에서 한 일 되짚기

이 가이드에서는 SDK를 통해 programmatic하게 호출할 수 있는 MCP 도구를 만드는 방법을 살펴보며, 확장 가능하고 fault-tolerant한 workflow를 구현했습니다. 다음을 다뤘습니다.

* MCP Server 설정
* 최적화되지 않은 예제
* 더 나은 예제
* Production 사용 사례를 위한 고려사항 

배운 내용을 실제 프로젝트에도 적용할 수 있습니다. 다음을 고려하세요.

1. X와 Y를 통한 추가 observability 제공
2. 이 문제를 대규모로 다룰 때의 성능 특성 고려

등등..
```
나쁜 예:


독자가 배운 내용을 자신의 구체적인 맥락에 적용하는 방법에 대한 강조가 부족합니다.
```
Claude Code SDK로 정교한 multi-agent 시스템을 구축할 수 있다는 것을 보여주었습니다.
```


