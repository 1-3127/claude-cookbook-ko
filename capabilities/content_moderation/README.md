# Claude로 content policy 적용하기

문서로 작성한 content policy를 program이 적용할 수 있는 rule로 바꿉니다.

## 문제

Content moderation은 콘텐츠를 내보내기 전에 문서로 작성된 정책에 맞춰 확인한 뒤 게시, 거부, 사람 reviewer에게 전달 중 어떤 처리를 할지 결정하는 과정입니다. 콘텐츠는 어디에서나 올 수 있습니다. 사용자는 comment를 게시하고, 판매자는 listing을 만들고, 광고주는 creative를 제출하며, 자체 marketing team은 법무팀이 승인해야 하는 campaign을 작성합니다. 정책은 정책, 법무, brand team이 일상적인 영어로 작성한 문서입니다. 콘텐츠는 지속적으로 들어오며, 어떤 사람 team도 따라갈 수 없는 규모인 경우가 많습니다.

review에는 실제 제약이 있습니다. 결정은 일관되어야 합니다. 동일한 두 제출물에 다른 답이 나와서는 안 됩니다. 제출자가 이의를 제기하고 규제기관이 질문하므로 거부는 설명 가능해야 합니다. 정책은 계속 바뀌므로(새 주 규정, 새 사기 category), 이를 적용하는 것도 안전하게 바뀌어야 합니다.

## 일반적인 접근 방식

LLM으로 자연스럽게 처음 만드는 것은 전체 정책 문서를 prompt에 넣고 콘텐츠를 붙인 뒤 판정을 요청하는 것입니다. 괜찮은 prototype이며 demo에서 작동합니다. production 규모에서는 세 제약에 모두 부딪힙니다. 같은 콘텐츠가 실행마다 다른 판정을 받을 수 있습니다. 거부 설명은 model이 우연히 생성한 산문이며, reviewer가 줄마다 확인할 수 없습니다. 정책 변경은 단순한 prompt 수정입니다. review, diff, rollback할 것이 없고 과거의 모든 결정은 아무도 기록하지 않은 prompt version 아래에서 이루어졌습니다.

## 이 cookbook의 방식

Claude는 정확히 두 곳에서 실행되고 어느 쪽도 판정을 결정하지 않습니다.

![Architecture: 작성 시 정책 산문을 검증되고 version이 관리되는 ruleset으로 compile; runtime에 각 제출물에서 typed field를 추출하고 pure-function rule engine이 판정 생성](images/architecture.png)

- **compiler**는 각 정책 조항을 직접 정의한 field schema에 대한 rule로 바꿉니다. static validator가 모든 rule을 schema에 맞춰 확인하고 문제를 Claude에 돌려보내 수정합니다. 판단이 필요한 조항("25세 미만으로 보이는 사람이 없어야 한다")은 extraction에서 답하는 judged field가 됩니다. 전혀 확인할 수 없는 조항은 조용히 버리는 대신 uncompilable로 나열합니다.
- **extractor**는 각 제출물의 텍스트와 이미지를 한 번의 API 호출로 typed field로 읽습니다. 그 호출이 review마다 드는 비용의 전부입니다.
- **engine**은 model call 없는 일반 Python 약 200줄입니다. field에 rule을 적용하여 판정을 생성하고, 어떤 rule이 왜 발동했는지 보여주는 trace를 제공합니다. 언제나 같은 입력은 같은 판정을 냅니다. rule을 placement로 범위를 제한할 수 있고("New Jersey에서만"), model이 rule에 필요한 것을 판단하지 못했다면 제출물은 추측된 답을 받는 대신 사람 review로 갑니다. 다른 placement나 새 ruleset version으로 콘텐츠를 다시 확인하는 데는 비용이 들지 않습니다.

**[guide.ipynb](guide.ipynb)**부터 시작하세요. 완전히 실행된 상태이므로 아무것도 실행하지 않고 output을 읽을 수 있습니다.

## 포함된 것

이 패턴은 특정 콘텐츠 종류에 묶여 있지 않습니다. 콘텐츠를 문서로 작성된 정책에 맞춰 확인하는 모든 곳에 맞습니다. product listing, 광고 creative, comment와 review, 채용 게시물, 판매자 profile, video와 podcast metadata, 법무 또는 brand review를 받는 marketing 문구 등입니다. cookbook은 이 중 세 가지를 end-to-end로 다룹니다.

| Path | 내용 |
|---|---|
| `guide.ipynb` | Cookbook: schema, rule language, engine, compiler, LLM assertion, extraction, 일상적인 영어로 rule 추가, domain 변경, 평가 |
| `engine.py`, `pipeline.py` | Rule engine과 두 Claude stage; guide에서 import하고 관심 부분을 보여줌 |
| `data/ad_creatives/` | 실습 예제: schema, 정책 문서, 직접 작성한 참조 ruleset, label이 있는 sample, synthetic creative 이미지(`build_creatives.py`로 다시 생성) |
| `data/product_listings/` | 두 번째 domain: marketplace listing(위조, 의학적 주장, platform 밖 결제, seller-tier rule) |
| `data/ugc/` | 세 번째 domain: comment와 review(괴롭힘, PII, spam) |
| `evaluation/run_eval.py` | 세 domain의 label이 있는 sample에 대해 전체 pipeline 실행 |

데이터의 모든 회사와 brand는 만들어낸 것이고 creative 이미지는 Pillow로 생성하므로 ground-truth label은 구성 자체로 정확하며 여기의 어떤 것도 실제 광고주를 닮지 않습니다.

## 얼마나 잘 작동하는가

세 domain의 label이 있는 22개 sample에서 pipeline은 21개 결정을 맞힙니다. 유일한 오답은 실제로 경계선상의 comment(새 계정이 자신의 blog를 link: 홍보인가 아닌가?)이며, Notebook은 발생 이유와 수정 방법을 설명합니다. rule이나 engine이 아니라 schema의 field description 하나를 명확하게 합니다.

## 실행

```bash
# repo root에서(또는 standalone: pip install anthropic python-dotenv)
uv sync --all-extras
# capabilities/content_moderation/에서 전체 22개 sample 평가 실행:
python evaluation/run_eval.py
```

Notebook 자체의 평가 cell은 비용을 낮추기 위해 기본적으로 domain별 sample 2개를 실행합니다. 전체 표를 보려면 `RUN_FULL_EVAL=1`을 설정하세요. 기본 Notebook 실행은 약 10–15분이 걸리고 약 1달러가 듭니다.

## 사용할 때

정책을 직접 소유하고 자주 변경하며, 제출자나 auditor에게 판정을 설명해야 하고, 같은 콘텐츠를 여러 placement나 정책 version에 걸쳐 다시 확인하며, 정책 책임자가 engineer가 아닐 때 적합합니다.

CSAM이나 폭력과 같은 표준 단일 category 탐지에는 전용 classifier가 적합하므로 이 tool은 맞지 않습니다. 정책 변경 맥락이 없는 일회성 classification에는 단일 classification prompt가 일을 해결하므로 과도합니다.
