# Promptfoo를 이용한 Evaluation

### 사전 준비
Promptfoo를 사용하려면 system에 node.js와 npm이 설치되어 있어야 합니다. 자세한 내용은 [이 guide](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)를 따르세요.

npm으로 promptfoo를 설치하거나 npx로 직접 실행할 수 있습니다. 이 guide에서는 npx를 사용합니다.

*참고: 이 예제에서는 `npx promptfoo@latest init`를 실행할 필요가 없습니다. 이 directory에 이미 초기화된 `promptfooconfig.yaml` 파일이 있습니다.*

공식 문서는 [여기](https://www.promptfoo.dev/docs/getting-started)를 참고하세요.

### 시작하기
Evaluation은 `promptfooconfig.yaml` 파일로 orchestration합니다. 이 파일에서 다음 절을 정의합니다.

- Prompts
    - Promptfoo는 다양한 형식으로 prompt를 import할 수 있습니다. 자세한 내용은 [여기](https://www.promptfoo.dev/docs/configuration/parameters)를 참고하세요.
    - 이 예제에서는 `prompts.py` 파일에서 `guide.ipynb`에 사용한 것과 같은 prompt 3개를 불러옵니다.
        - 함수는 Claude API를 호출하는 대신 prompt만 반환한다는 점을 제외하면 `guide.ipynb`의 함수와 같습니다. 이후 Promptfoo가 API 호출과 결과 저장의 orchestration을 처리합니다.
        - Prompt 함수에 대한 자세한 내용은 [여기](https://www.promptfoo.dev/docs/configuration/parameters#prompt-functions)를 참고하세요. Python을 사용하면 RAG에 필요한 VectorDB class를 재사용할 수 있으며, 이는 `vectordb.py`에 정의되어 있습니다.
- Providers
    - Promptfoo로 여러 platform의 다양한 LLM에 연결할 수 있습니다. 자세한 내용은 [여기](https://www.promptfoo.dev/docs/providers)를 참고하세요. `guide.ipynb`에서는 기본 temperature 0.0으로 Haiku를 사용했습니다. Promptfoo로 여러 temperature 설정을 실험하여 use case에 가장 적합한 선택을 찾습니다.
- Tests
    - `guide.ipynb`에 사용한 것과 같은 데이터를 사용하며, 이는 [`dataset.csv`](./dataset.csv)에 있습니다.
    - Promptfoo에는 다양한 내장 test가 있으며 [여기](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic)에서 확인할 수 있습니다.
    - 이 예제에서는 evaluation 조건이 행마다 달라지므로 `dataset.csv`에 test를 정의하고, 모든 test case에서 일정한 조건은 `promptfooconfig.yaml`에 test로 정의합니다. 자세한 내용은 [여기](https://www.promptfoo.dev/docs/configuration/parameters/#import-from-csv)를 참고하세요.
- Transform
    - `defaultTest` 절에서 transform 함수를 정의합니다. 이는 LLM response에서 테스트할 특정 출력을 추출하는 Python 함수입니다.
- Output
    - 출력 파일 경로를 정의합니다. Promptfoo는 여러 형식으로 결과를 출력할 수 있습니다. [여기](https://www.promptfoo.dev/docs/configuration/parameters/#output-file)를 참고하세요. 또는 Promptfoo의 web UI를 사용할 수 있습니다. [여기](https://www.promptfoo.dev/docs/usage/web-ui)를 참고하세요.

### Eval 실행

Promptfoo를 시작하려면 terminal을 열고 이 directory(`./evaluation`)로 이동합니다.

Evaluation을 실행하기 전에 다음 환경 변수를 정의해야 합니다.

`export ANTHROPIC_API_KEY=YOUR_API_KEY`
`export VOYAGE_API_KEY=YOUR_API_KEY`

`evaluation` directory에서 다음 명령을 실행합니다.

`npx promptfoo@latest eval`

요청의 concurrency(기본값 = 4)를 늘리려면 다음 명령을 실행합니다.

`npx promptfoo@latest eval -j 25`

Evaluation이 완료되면 terminal에 dataset의 각 행에 대한 결과가 출력됩니다.

이제 `guide.ipynb`로 돌아가 결과를 분석할 수 있습니다!
