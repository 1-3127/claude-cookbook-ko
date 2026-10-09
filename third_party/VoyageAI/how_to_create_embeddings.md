# Embedding
Text embedding은 텍스트 문자열의 수치 표현이며 floating point number의 vector로 나타냅니다. 두 text embedding 사이의 거리(일반적으로 cosine similarity)를 사용하여 두 텍스트가 서로 얼마나 관련되어 있는지 측정할 수 있으며, 거리가 작을수록 관련성이 높을 것으로 예측합니다.

문자열의 유사성을 비교하거나 서로 간의 거리에 따라 문자열을 clustering하면 **검색**(RAG architecture에서 널리 사용), **추천**, **이상 탐지** 등 다양한 애플리케이션을 구현할 수 있습니다.

## Anthropic으로 embedding 얻기
Anthropic은 자체 embedding 모델을 제공하지 않지만 text embedding의 선호 제공업체로 [Voyage AI](https://www.voyageai.com/?ref=anthropic)와 제휴했습니다. Voyage는 [최첨단](https://blog.voyageai.com/2023/10/29/voyage-embeddings/?ref=anthropic) embedding 모델을 만들며 금융 및 의료 같은 특정 산업 분야에 맞춘 모델과 회사에 맞게 fine-tuning할 수 있는 모델도 제공합니다.

Voyage embedding에 접근하려면 먼저 [Voyage AI 웹사이트](https://dash.voyageai.com/?ref=anthropic)에 가입하고 API key를 발급받은 뒤 편의를 위해 환경 변수로 설정하세요:

```bash
export VOYAGE_API_KEY="<your secret key>"
```

아래에 설명된 대로 공식 [`voyageai` Python package](https://github.com/voyage-ai/voyageai-python) 또는 HTTP 요청을 사용하여 embedding을 얻을 수 있습니다.

### Voyage Python Package

다음 명령으로 `voyageai` package를 설치할 수 있습니다:

```bash
pip install -U voyageai
```

그런 다음 client object를 생성하고 텍스트 embedding을 시작할 수 있습니다:

```python
import voyageai

vo = voyageai.Client()
# 환경 변수 VOYAGE_API_KEY를 자동으로 사용합니다.
# 또는 vo = voyageai.Client(api_key="<your secret key>")를 사용할 수 있습니다

texts = ["Sample text 1", "Sample text 2"]

result = vo.embed(texts, model="voyage-2", input_type="document")
print(result.embeddings[0])
print(result.embeddings[1])
```

`result.embeddings`는 각각 1024개의 floating-point number를 포함한 두 embedding vector의 목록입니다. 위 코드를 실행하면 두 embedding이 화면에 출력됩니다:

```
[0.02012746, 0.01957859, ...]  # "Sample text 1"의 embedding
[0.01429677, 0.03077182, ...]  # "Sample text 2"의 embedding
```

Embedding을 생성할 때 `embed()` 함수에 몇 가지 다른 argument를 지정할 수 있습니다. 명세는 다음과 같습니다:

> `voyageai.Client.embed(texts : List[str], model : str = "voyage-2", input_type : Optional[str] = None, truncation : Optional[bool] = None)`

- **texts** (List[str]) - `["I like cats", "I also like dogs"]`와 같은 문자열 목록 형태의 텍스트 목록. 현재 목록의 최대 길이는 128이며 목록의 총 token 수는 `voyage-2`의 경우 최대 320K, `voyage-code-2`의 경우 최대 120K입니다.
- **model** (str) - 모델 이름. 권장 옵션: `voyage-2`(기본값), `voyage-code-2`.
- **input_type** (str, 선택 사항, 기본값 `None`) - Input 텍스트 유형. 기본값은 `None`입니다. 다른 옵션: `query`, `document`.
    - input_type이 `None`이면 input 텍스트는 embedding 모델로 직접 인코딩됩니다. 또는 input이 문서나 query이면 사용자는 input_type을 각각 `document` 또는 `query`로 지정할 수 있습니다. 이 경우 Voyage는 input 텍스트 앞에 특수 prompt를 추가하고 확장된 input을 embedding 모델에 보냅니다.
    - Retrieval/search 사용 사례에서는 retrieval 품질을 높이기 위해 query 또는 문서를 인코딩할 때 이 argument를 지정하는 것을 권장합니다. input_type argument를 사용하거나 사용하지 않고 생성한 embedding은 서로 호환됩니다.

- **truncation** (bool, 선택 사항, 기본값 `None`) - Context length에 맞추기 위해 input 텍스트를 자를지 여부.
    - `True`이면 길이 제한을 초과하는 input 텍스트를 embedding 모델로 vector화하기 전에 context length에 맞추어 자릅니다.
    - `False`이면 주어진 텍스트가 context length를 초과할 경우 오류가 발생합니다.
    - 지정하지 않으면(기본값 `None`) input 텍스트가 context window length를 조금 초과할 경우 Voyage가 embedding 모델에 보내기 전에 자릅니다. Context window length를 크게 초과하면 오류가 발생합니다.

### Voyage HTTP API

Voyage HTTP API에 요청하여 embedding을 얻을 수도 있습니다. 예를 들어 terminal에서 `curl` 명령으로 HTTP 요청을 보낼 수 있습니다:

```bash
curl https://api.voyageai.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VOYAGE_API_KEY" \
  -d '{
    "input": ["Sample text 1", "Sample text 2"],
    "model": "voyage-2"
  }'
```

응답은 embedding과 token 사용량을 포함한 JSON object입니다:

```bash
{
  "object": "list",
  "data": [
    {
      "embedding": [0.02012746, 0.01957859, ...],
      "index": 0
    },
    {
      "embedding": [0.01429677, 0.03077182, ...],
      "index": 1
    }
  ],
  "model": "voyage-2",
  "usage": {
    "total_tokens": 10
  }
}
```

Voyage AI의 embedding endpoint는 `https://api.voyageai.com/v1/embeddings` (POST)입니다. Request header에 API key를 포함해야 합니다. Request body는 다음 argument를 포함한 JSON object입니다:

- **input** (str, List[str]) - 단일 텍스트 문자열 또는 문자열 목록 형태의 텍스트 목록. 현재 목록의 최대 길이는 128이며 목록의 총 token 수는 `voyage-2`의 경우 최대 320K, `voyage-code-2`의 경우 최대 120K입니다.
- **model** (str) - 모델 이름. 권장 옵션: `voyage-2`(기본값), `voyage-code-2`.
- **input_type** (str, 선택 사항, 기본값 `None`) - Input 텍스트 유형. 기본값은 `None`입니다. 다른 옵션: `query`, `document`.
- **truncation** (bool, 선택 사항, 기본값 `None`) - Context length에 맞추기 위해 input 텍스트를 자를지 여부.
    - `True`이면 길이 제한을 초과하는 input 텍스트를 embedding 모델로 vector화하기 전에 context length에 맞추어 자릅니다.
    - `False`이면 주어진 텍스트가 context length를 초과할 경우 오류가 발생합니다.
    - 지정하지 않으면(기본값 `None`) input 텍스트가 context window length를 조금 초과할 경우 Voyage가 embedding 모델에 보내기 전에 자릅니다. Context window length를 크게 초과하면 오류가 발생합니다.
- **encoding_format** (str, 선택 사항, 기본값 `None`) - Embedding 인코딩 형식. Voyage는 현재 두 옵션을 지원합니다:
    - 지정하지 않으면(기본값 `None`): embedding을 floating-point number 목록으로 표현;
    - `"base64"`: embedding을 [Base64](https://docs.python.org/3/library/base64.html) 인코딩으로 압축.


### AWS Marketplace

Voyage embedding은 [AWS Marketplace](https://aws.amazon.com/marketplace/seller-profile?id=seller-snt4gb6fd7ljg)에서 이용할 수 있습니다. AWS에서 Voyage에 접근하는 지침은 다음과 같습니다:

1. Model package 구독

    1. [Model package 목록 페이지](https://aws.amazon.com/marketplace/seller-profile?id=seller-snt4gb6fd7ljg)로 이동하여 배포할 모델을 선택하세요.
    1. *Continue to subscribe* 버튼을 클릭하세요.
    1. *Subscribe to this software* 페이지에서 세부 사항을 주의 깊게 검토하세요. 여러분과 조직이 표준 End-User License Agreement (EULA), 가격 및 지원 조건에 동의하면 "Accept Offer"를 클릭하세요.
    1. *Continue to configuration*을 선택하고 region을 고르면 Product Arn이 표시됩니다. 이는 Boto3로 배포 가능한 모델을 생성하는 데 필요한 model package ARN입니다. 선택한 region에 해당하는 ARN을 복사하여 다음 cell에서 사용하세요.

2. Model package 배포

    이제부터는 [Sagemaker Studio](https://aws.amazon.com/sagemaker/studio/)에서 제공된 [notebook](https://github.com/voyage-ai/voyageai-aws/blob/main/notebooks/deploy_voyage_code_2_sagemaker.ipynb)으로 계속 진행하는 것을 권장합니다. JupyterLab space를 생성하고 notebook을 업로드한 뒤 그곳에서 계속 진행하세요.


## 사용 가능한 모델

Voyage는 다음 embedding 모델 사용을 권장합니다:

|  모델 | Context Length | Embedding Dimension | 설명 |
| --- | --- | --- | --- |
| `voyage-2` | 4000 | 1024 | 최고의 retrieval 품질을 갖춘 최신 base (generalist) embedding 모델. 자세한 내용은 [blog 게시물](https://blog.voyageai.com/2023/10/29/voyage-embeddings/?ref=anthropic) 참조. |
| `voyage-code-2` | 16000 | 1536 | Code retrieval에 최적화(대안보다 17% 우수)되었으며 범용 corpus에서도 SoTA. 자세한 내용은 [blog 게시물](https://blog.voyageai.com/2024/01/23/voyage-code-2-elevate-your-code-retrieval/?ref=anthropic) 참조. |

`voyage-2`는 여러 분야에서 최첨단 성능을 달성하고 높은 효율을 유지하는 generalist embedding 모델입니다. `voyage-code-2`는 코드 애플리케이션에 최적화되었으며 latency가 약간 높지만 4배의 context length를 제공하여 더 유연하게 사용할 수 있습니다.

Voyage는 더 발전된 전문 모델을 적극적으로 개발하고 있으며 회사에 맞추어 embedding을 fine-tuning할 수 있습니다. Trial 접근이나 자체 데이터로 finetuning하려면 [contact@voyageai.com](mailto:contact@voyageai.com)으로 이메일을 보내세요!

- `voyage-finance-2`: 곧 출시
- `voyage-law-2`: 곧 출시
- `voyage-multilingual-2`: 곧 출시
- `voyage-healthcare-2`: 곧 출시

## 동기를 보여주는 예제
Embedding을 얻는 방법을 알았으므로 간단한 예제로 그 필요성을 살펴보겠습니다.

Retrieval할 문서 6개로 구성된 작은 corpus가 있다고 가정해 보겠습니다

```python
documents = [
    "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
    "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
    "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
    "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
    "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
    "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
]
```

먼저 Voyage로 각 문서를 embedding vector로 변환하겠습니다

```python
import voyageai

vo = voyageai.Client()

# 문서를 embedding
doc_embds = vo.embed(
    documents, model="voyage-2", input_type="document"
).embeddings
```

Embedding을 통해 vector space에서 semantic search/retrieval을 수행할 수 있습니다. 예제 query가 주어지면,

```python
query = "When is Apple's conference call scheduled?"
```

이를 embedding으로 변환하고 embedding space의 거리에 따라 가장 관련성 높은 문서를 찾기 위해 nearest neighbor search를 수행합니다.

```python
import numpy as np

# Query를 embedding
query_embd = vo.embed(
    [query], model="voyage-2", input_type="query"
).embeddings[0]

# 유사성 계산
# Voyage embedding은 길이 1로 정규화되므로 dot-product와
# cosine similarity는 같습니다.
similarities = np.dot(doc_embds, query_embd)

retrieved_id = np.argmax(similarities)
print(documents[retrieved_id])
```

문서와 query를 embedding할 때 각각 `input_type="document"`와 `input_type="query"`를 사용한다는 점에 유의하세요. 더 자세한 명세는 [여기](#voyage-python-package)에 있습니다.

Output은 실제로 query와 가장 관련성 높은 다섯 번째 문서입니다:

```
Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.
```

Vector database를 포함하여 embedding으로 RAG를 수행하는 방법에 대한 자세한 cookbook을 찾는다면 [RAG cookbook](https://github.com/anthropics/anthropic-cookbook/blob/main/third_party/Pinecone/rag_using_pinecone.ipynb)을 확인하세요.

## 자주 묻는 질문
### 두 embedding vector 사이의 거리는 어떻게 계산하나요?
Cosine similarity가 널리 사용되지만 대부분의 distance function도 잘 작동합니다. Voyage embedding은 길이 1로 정규화되므로 cosine similarity는 사실상 두 vector의 dot-product와 같습니다. 두 embedding vector 사이의 cosine similarity를 계산하는 데 사용할 수 있는 코드 snippet은 다음과 같습니다.

```python
import numpy

similarity = np.dot(embd1, embd2)
# Voyage embedding은 길이 1로 정규화되므로 cosine similarity는
# dot-product와 같습니다.
```

큰 corpus에서 가장 가까운 K개의 embedding vector를 찾으려면 대부분의 vector database에 내장된 기능 사용을 권장합니다.

### 문자열을 embedding하기 전에 token 수를 셀 수 있나요?
네! 다음 코드로 할 수 있습니다.

```python
import voyageai

vo = voyageai.Client()
total_tokens = vo.count_tokens(["Sample text"])
```

## 요금
요금 정보는 Voyage 웹사이트의 [요금 페이지](https://docs.voyageai.com/pricing/?ref=anthropic)에서 확인해야 합니다.

