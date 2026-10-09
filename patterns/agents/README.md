# 효과적인 Agent 구축 Cookbook

Erik Schluntz와 Barry Zhang의 [효과적인 Agent 구축](https://anthropic.com/research/building-effective-agents)에 대한 reference implementation입니다.

이 repository에는 블로그에서 다룬 일반적인 agent workflow의 최소 구현 예제가 있습니다.

- 기본 구성 요소
  - Prompt Chaining
  - Routing
  - Multi-LLM Parallelization
- 고급 Workflow
  - Orchestrator-Subagents
  - Evaluator-Optimizer

## 시작하기
자세한 예제는 Jupyter notebook을 참조하세요.

- [기본 Workflow](basic_workflows.ipynb)
- [Evaluator-Optimizer Workflow](evaluator_optimizer.ipynb) 
- [Orchestrator-Workers Workflow](orchestrator_workers.ipynb)
- [Async Multi-Agent Orchestration](async_multi_agent_orchestration.ipynb)
- [Latency 압박과 Budget 아래의 Multi-Agent 팀](latency_multi_agent.ipynb)
