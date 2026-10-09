
# Promptfoo로 평가하기

### 이 평가 Suite에 대한 참고 사항

1) 아래 지침, 특히 필요한 package에 대한 사전 준비 사항을 반드시 따르세요.

2) 전체 평가 suite를 실행하려면 평소보다 높은 rate limit이 필요할 수 있습니다. Promptfoo에서 테스트 일부만 실행하는 것을 고려하세요.

3) 모든 테스트가 그대로 통과하지는 않습니다. 평가를 적당히 어렵게 설계했습니다.

### 사전 준비 
Promptfoo를 사용하려면 시스템에 node.js 및 npm이 설치되어 있어야 합니다. 자세한 내용은 [이 가이드](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)를 따르세요  

npm으로 promptfoo를 설치하거나 npx로 직접 실행할 수 있습니다. 이 가이드에서는 npx를 사용합니다.  

*참고: 이 예제에서는 디렉터리에 이미 초기화된 `promptfooconfig.yaml` 파일이 있으므로 `npx promptfoo@latest init`을 실행할 필요가 없습니다*  

[여기](https://www.promptfoo.dev/docs/getting-started)에서 공식 문서를 확인하세요  

#### 참고 - 추가 Dependency
이 예제의 custom_evals를 올바르게 실행하려면 다음 dependency를 설치해야 합니다.

`pip install nltk rouge-score`

### 시작하기

시작하려면 ANTHROPIC_API_KEY 환경 변수 또는 선택한 provider에 필요한 다른 key를 설정하세요. `export ANTHROPIC_API_KEY=YOUR_API_KEY`를 사용할 수 있습니다.

그런 다음 `cd`로 `evaluation` 디렉터리에 이동하여 `npx promptfoo@latest eval -c promptfooconfig.yaml --output ../data/results.csv`를 입력하세요

이후 `npx promptfoo@latest view`를 실행하여 결과를 볼 수 있습니다.

### 작동 방식

promptfooconfig.yaml 파일은 평가 설정의 핵심입니다. 중요한 여러 절을 정의합니다:

Prompt:
- Prompt를 prompts.py 파일에서 import합니다.
- LM 성능의 다양한 측면을 테스트하도록 설계된 prompt입니다.


Provider:
- 다양한 Claude 버전 및 설정을 여기서 구성합니다.
- 여러 모델 또는 다양한 parameter(예: 서로 다른 temperature 설정)를 테스트할 수 있습니다.


테스트:
- 테스트 사례를 이 파일에 정의하거나, 이 사례에서는 tests.yaml에서 import합니다.
- 평가의 input 및 예상 output을 지정합니다.
- Promptfoo는 다양한 built-in 테스트 유형을 제공하며(문서 참조) 직접 정의할 수도 있습니다. Custom 평가 3개와 기본 제공 평가 1개(contains method)가 있습니다:
    - `bleu_eval.py`: 기계 생성 텍스트와 reference 텍스트의 유사성을 측정하는 BLEU (Bilingual Evaluation Understudy) score를 구현합니다.
    - `rouge_eval.py`: Reference 요약과 비교하여 요약 품질을 평가하는 ROUGE (Recall-Oriented Understudy for Gisting Evaluation) score를 구현합니다.
    - `llm_eval.py`: Language Model로 생성된 텍스트의 일관성, 관련성 또는 사실 정확성 등 다양한 측면을 평가하는 custom metric을 포함합니다.

Output:
- 평가 결과의 형식 및 위치를 지정합니다.
- Promptfoo는 다양한 output 형식도 지원합니다!

### Python binary 재정의

기본적으로 promptfoo는 shell의 python을 실행합니다. Python이 적절한 실행 파일을 가리키는지 확인하세요.

Python binary가 없으면 "python: command not found" 오류가 표시됩니다.

Python binary를 재정의하려면 PROMPTFOO_PYTHON 환경 변수를 설정하세요. 경로(/path/to/python3.11 등) 또는 PATH의 실행 파일(python3.11 등)로 설정할 수 있습니다.