# Promptfoo로 평가하기

### 사전 준비 
Promptfoo를 사용하려면 시스템에 node.js 및 npm이 설치되어 있어야 합니다. 자세한 내용은 [이 가이드](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)를 따르세요  

npm으로 promptfoo를 설치하거나 npx로 직접 실행할 수 있습니다. 이 가이드에서는 npx를 사용합니다.  

*참고: 이 예제에서는 디렉터리에 이미 초기화된 `promptfooconfig.yaml` 파일이 있으므로 `npx promptfoo@latest init`을 실행할 필요가 없습니다*  

[여기](https://www.promptfoo.dev/docs/getting-started)에서 공식 문서를 확인하세요  


### 시작하기
평가는 `promptfooconfig...` `.yaml` 파일이 orchestrate합니다. 애플리케이션에서는 retrieval 시스템 평가용 `promptfooconfig_retrieval.yaml`과 end-to-end 성능 평가용 `promptfooconfig_end_to_end.yaml`로 평가 logic을 나눕니다. 각 파일에서 다음 절을 정의합니다

### Retrieval 평가

- Prompt
    - Promptfoo는 다양한 형식의 prompt를 import할 수 있습니다. 자세한 내용은 [여기](https://www.promptfoo.dev/docs/configuration/parameters)에서 읽을 수 있습니다.
    - 이 사례에서는 매번 새 prompt를 제공하지 않고 평가를 위해 각 retrieval 'provider'에 `{{query}}`를 그대로 전달합니다
- Provider
    - 표준 LLM provider 대신 `guide.ipynb`의 각 retrieval 방법에 custom provider를 작성했습니다
- 테스트
    - `guide.ipynb`에서 사용한 같은 데이터를 사용합니다. `end_to_end_dataset.csv`와 `retrieval_dataset.csv`로 나누고 각 dataset에 `__expected` column을 추가하여 행마다 자동으로 assertion을 실행할 수 있게 했습니다
    - Retrieval 평가 logic은 `eval_end_to_end.py`에서 찾을 수 있습니다

### End-to-End 평가

- Prompt
    - Promptfoo는 다양한 형식의 prompt를 import할 수 있습니다. 자세한 내용은 [여기](https://www.promptfoo.dev/docs/configuration/parameters)에서 읽을 수 있습니다.
    - End-to-end 평가 config에는 사용한 방법에 각각 대응하는 prompt 3개가 있습니다
        - 함수는 Claude API를 호출하는 대신 prompt만 반환한다는 점 외에는 `guide.ipynb`의 함수와 같습니다. Promptfoo가 API 호출 및 결과 저장을 orchestrate합니다.
        - Prompt 함수에 대한 자세한 내용은 [여기](https://www.promptfoo.dev/docs/configuration/parameters#prompt-functions)에서 읽을 수 있습니다. Python을 사용하면 RAG에 필요한 VectorDB class를 재사용할 수 있으며, 이는 `vectordb.py`에 정의되어 있습니다.
- Provider
    - Promptfoo로 여러 platform의 다양한 LLM에 연결할 수 있습니다. [자세한 내용은 여기](https://www.promptfoo.dev/docs/providers)를 참조하세요. `guide.ipynb`에서는 기본 temperature 0.0으로 Haiku를 사용했습니다. Promptfoo로 다양한 모델을 실험하겠습니다.
- 테스트
    - `guide.ipynb`에서 사용한 같은 데이터를 사용합니다. `end_to_end_dataset.csv`와 `retrieval_dataset.csv`로 나누고 각 dataset에 `__expected` column을 추가하여 행마다 자동으로 assertion을 실행할 수 있게 했습니다
    - Promptfoo에는 [여기](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic)에서 확인할 수 있는 다양한 built-in 테스트가 있습니다.
    - Retrieval 시스템의 테스트 logic은 `eval_retrieval.py`, end-to-end 시스템의 테스트 logic은 `eval_end_to_end.py`에서 찾을 수 있습니다
- Output
    - Output 파일 경로를 정의합니다. Promptfoo는 여러 형식으로 결과를 출력할 수 있습니다. [여기](https://www.promptfoo.dev/docs/configuration/parameters/#output-file)를 참조하세요. 또는 Promptfoo web UI를 사용할 수 있습니다. [여기](https://www.promptfoo.dev/docs/usage/web-ui)를 참조하세요.


### 평가 실행

Promptfoo를 시작하려면 terminal을 열고 이 디렉터리(`./evaluation`)로 이동하세요.

평가를 실행하기 전에 다음 환경 변수를 정의해야 합니다:

`export ANTHROPIC_API_KEY=YOUR_API_KEY`  
`export VOYAGE_API_KEY=YOUR_API_KEY`

`evaluation` 디렉터리에서 다음 명령 중 하나를 실행하세요.  

- End-to-end 시스템 성능 평가: `npx promptfoo@latest eval -c promptfooconfig_end_to_end.yaml --output ../data/end_to_end_results.json`

- Retrieval 시스템 성능을 독립적으로 평가: `npx promptfoo@latest eval -c promptfooconfig_retrieval.yaml --output ../data/retrieval_results.json`

평가가 완료되면 terminal에서 dataset의 각 행 결과를 출력합니다. `npx promptfoo@latest view`를 실행하여 promptfoo UI viewer에서 output을 볼 수도 있습니다.