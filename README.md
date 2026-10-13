# Claude Cookbooks

Claude Cookbooks는 개발자가 Claude로 개발하는 데 도움이 되도록 설계된 코드와 가이드를 제공하며, 자신의 프로젝트에 쉽게 통합할 수 있는 복사 가능한 코드 스니펫을 제공합니다.

## 사전 준비

이 cookbook의 예제를 최대한 활용하려면 Claude API key가 필요합니다([여기](https://www.anthropic.com)에서 무료로 가입하세요).

코드 예제는 주로 Python으로 작성되어 있지만, 개념은 Claude API와 상호작용할 수 있는 모든 프로그래밍 언어에 적용할 수 있습니다.

Claude API를 처음 사용한다면, 탄탄한 기초를 쌓기 위해 [Claude API Fundamentals 과정](https://github.com/anthropics/courses/tree/master/anthropic_api_fundamentals)부터 시작하는 것을 권장합니다.

## 더 알아보기

Claude와 AI assistant를 더 잘 활용할 수 있는 자료를 찾고 계신가요? 다음 유용한 링크를 확인하세요.

- [Anthropic 개발자 문서](https://docs.claude.com/claude/docs/guide-to-anthropics-prompt-engineering-resources)
- [Anthropic 지원 문서](https://support.anthropic.com)
- [Anthropic Discord 커뮤니티](https://www.anthropic.com/discord)

## 기여하기

Claude Cookbooks는 개발자 커뮤니티의 기여를 바탕으로 발전합니다. 아이디어 제안, 오타 수정, 새로운 가이드 추가, 기존 가이드 개선 등 여러분의 참여를 소중하게 생각합니다. 기여를 통해 이 자료가 모두에게 더욱 유용해지도록 도울 수 있습니다.

작업이 중복되지 않도록 기여하기 전에 기존 issue와 pull request를 검토해 주세요.

새로운 예제나 가이드에 대한 아이디어가 있다면 [issue 페이지](https://github.com/1-3127/claude-cookbook-ko/issues)에 공유해 주세요.

## 레시피 목록

### 기능
- [Classification](./capabilities/classification): Claude를 사용한 텍스트와 데이터 classification 기법을 살펴봅니다.
- [Retrieval Augmented Generation](./capabilities/retrieval_augmented_generation): 외부 지식으로 Claude의 응답을 개선하는 방법을 배웁니다.
- [Summarization](./capabilities/summarization): Claude를 사용한 효과적인 텍스트 요약 기법을 알아봅니다.

### Tool Use와 통합
- [Tool use](./tool_use): Claude를 외부 도구 및 함수와 통합하여 기능을 확장하는 방법을 배웁니다.
  - [고객 서비스 agent](./tool_use/customer_service_agent.ipynb)
  - [계산기 통합](./tool_use/calculator_tool.ipynb)
  - [SQL query](./misc/how_to_make_sql_queries.ipynb)

### 서드파티 통합
- [Retrieval augmented generation](./third_party): 외부 데이터 소스로 Claude의 지식을 보완합니다.
  - [Vector database (Pinecone)](./third_party/Pinecone/rag_using_pinecone.ipynb)
  - [Wikipedia](./third_party/Wikipedia/wikipedia-search-cookbook.ipynb)
  - [웹 페이지](./misc/read_web_pages_with_haiku.ipynb)
- [Voyage AI를 사용한 Embeddings](./third_party/VoyageAI/how_to_create_embeddings.md)

### Multimodal 기능
- [Claude의 Vision](./multimodal):
  - [이미지로 시작하기](./multimodal/getting_started_with_vision.ipynb)
  - [Vision 모범 사례](./multimodal/best_practices_for_vision.ipynb)
  - [차트와 그래프 해석하기](./multimodal/reading_charts_graphs_powerpoints.ipynb)
  - [양식에서 내용 추출하기](./multimodal/how_to_transcribe_text.ipynb)
- Claude로 이미지 생성하기: Stable Diffusion과 함께 Claude를 사용하여 이미지를 생성합니다.

### 고급 기법
- [Sub-agent](./multimodal/using_sub_agents.ipynb): Opus와 함께 Haiku를 sub-agent로 사용하는 방법을 배웁니다.
- [Claude에 PDF 업로드하기](./misc/pdf_upload_summarization.ipynb): PDF를 파싱하여 텍스트로 Claude에 전달합니다.
- [자동화된 evaluation](./misc/building_evals.ipynb): Claude를 사용하여 prompt evaluation 과정을 자동화합니다.
- [JSON mode 활성화하기](./misc/how_to_enable_json_mode.ipynb): Claude에서 일관된 JSON 출력을 얻도록 합니다.
- [Moderation filter 만들기](./misc/building_moderation_filter.ipynb): Claude를 사용하여 애플리케이션을 위한 content moderation filter를 만듭니다.
- [Prompt caching](./misc/prompt_caching.ipynb): Claude를 사용한 효율적인 prompt caching 기법을 배웁니다.
- [비용 최적화](./cost_optimization/cost_optimization.ipynb): Agent에 비용 최적화 체크리스트를 적용하면서 통과율과 작업당 비용을 측정하여 Pareto-optimal 구성을 찾습니다.

## 추가 자료

- [Anthropic on AWS](https://github.com/aws-samples/anthropic-on-aws): AWS 인프라에서 Claude를 사용하는 예제와 솔루션을 살펴봅니다.
- [AWS Samples](https://github.com/aws-samples/): Claude와 함께 사용하도록 조정할 수 있는 코드 샘플 모음입니다. 일부 샘플은 Claude와 최적으로 작동하도록 수정해야 할 수 있습니다.
