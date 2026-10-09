import json
import os

from anthropic import Anthropic
from vectordb import SummaryIndexedVectorDB, VectorDB

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# VectorDB 초기화
db = VectorDB("anthropic_docs")
# Claude 문서 로드
with open("../data/anthropic_docs.json") as f:
    anthropic_docs = json.load(f)
db.load_data(anthropic_docs)


def _retrieve_base(query, db):
    results = db.search(query, k=3)
    context = ""
    for result in results:
        chunk = result["metadata"]
        context += f"\n{chunk['text']}\n"
    return results, context


def answer_query_base(context):
    input_query = context["vars"]["query"]
    documents, document_context = _retrieve_base(input_query, db)
    prompt = f"""
    You have been tasked with helping us to answer the following query:
    <query>
    {input_query}
    </query>
    You have access to the following documents which are meant to provide context as you answer the query:
    <documents>
    {document_context}
    </documents>
    Please remain faithful to the underlying context, and only deviate from it if you are 100% sure that you know the answer already.
    Answer the question now, and avoid providing preamble such as 'Here is the answer', etc
    """

    return prompt


# VectorDB 초기화
db_summary = SummaryIndexedVectorDB("anthropic_docs_summaries")
# Claude 문서 로드
with open("../data/anthropic_summary_indexed_docs.json") as f:
    anthropic_docs_summaries = json.load(f)
db_summary.load_data(anthropic_docs_summaries)


def retrieve_level_two(query):
    results = db_summary.search(query, k=3)
    context = ""
    for result in results:
        chunk = result["metadata"]
        context += f"\n <document> \n {chunk['chunk_heading']}\n\nText\n {chunk['text']} \n\nSummary: \n {chunk['summary']} \n </document> \n"  # 모델에 세 항목 모두 표시
    return results, context


def answer_query_level_two(context):
    input_query = context["vars"]["query"]
    documents, document_context = retrieve_level_two(input_query)
    prompt = f"""
    You have been tasked with helping us to answer the following query:
    <query>
    {input_query}
    </query>
    You have access to the following documents which are meant to provide context as you answer the query:
    <documents>
    {document_context}
    </documents>
    Please remain faithful to the underlying context, and only deviate from it if you are 100% sure that you know the answer already.
    Answer the question now, and avoid providing preamble such as 'Here is the answer', etc
    """

    return prompt


# VectorDB 초기화
db_rerank = SummaryIndexedVectorDB("anthropic_docs_rerank")
# Claude 문서 로드
with open("../data/anthropic_summary_indexed_docs.json") as f:
    anthropic_docs_summaries = json.load(f)
db_rerank.load_data(anthropic_docs_summaries)


def _rerank_results(query: str, results: list[dict], k: int = 5) -> list[dict]:
    # Index와 함께 요약 준비
    summaries = []
    print(len(results))
    for i, result in enumerate(results):
        summary = "[{}] Document: {} {}".format(
            i, result["metadata"]["chunk_heading"], result["metadata"]["summary"]
        )
        summary += " \n {}".format(result["metadata"]["text"])
        summaries.append(summary)

    # Newline으로 요약 결합
    joined_summaries = "\n".join(summaries)

    prompt = f"""
    Query: {query}
    You are about to be given a group of documents, each preceded by its index number in square brackets. Your task is to select the only {k} most relevant documents from the list to help us answer the query.

    {joined_summaries}

    Output only the indices of {k} most relevant documents in order of relevance, separated by commas, enclosed in XML tags here:
    <relevant_indices>put the numbers of your indices here, seeparted by commas</relevant_indices>
    """
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=50,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "<relevant_indices>"},
            ],
            temperature=0,
            stop_sequences=["</relevant_indices>"],
        )

        # 응답에서 index 추출
        response_text = response.content[0].text.strip()
        indices_str = response_text
        relevant_indices = []
        for idx in indices_str.split(","):
            try:
                relevant_indices.append(int(idx.strip()))
            except ValueError:
                continue  # 잘못된 index 건너뛰기
        print(indices_str)
        print(relevant_indices)
        # 유효한 index가 충분하지 않으면 원래 순서의 상위 k개 사용
        if len(relevant_indices) == 0:
            relevant_indices = list(range(min(k, len(results))))

        # 범위를 벗어난 index가 없는지 확인
        relevant_indices = [idx for idx in relevant_indices if idx < len(results)]

        # Reranking된 결과 반환
        reranked_results = [results[idx] for idx in relevant_indices[:k]]
        # 내림차순 relevance score 할당
        for i, result in enumerate(reranked_results):
            result["relevance_score"] = (
                100 - i
            )  # 최고 score는 100, 순위마다 1씩 감소

        return reranked_results

    except Exception as e:
        print(f"An error occurred during reranking: {str(e)}")
        # Fallback으로 reranking 없이 상위 k개 결과 반환
        return results[:k]


def _retrieve_advanced(query: str, k: int = 3, initial_k: int = 20) -> tuple[list[dict], str]:
    # 1단계: 초기 결과 조회
    initial_results = db_rerank.search(query, k=initial_k)

    # 2단계: 결과 re-ranking
    reranked_results = _rerank_results(query, initial_results, k=k)

    # 3단계: Re-ranking 결과에서 새 context 문자열 생성
    new_context = ""
    for result in reranked_results:
        chunk = result["metadata"]
        new_context += (
            f"\n <document> \n {chunk['chunk_heading']}\n\n{chunk['text']} \n </document> \n"
        )

    return reranked_results, new_context


# answer_query_advanced 함수는 변경 없음
def answer_query_level_three(context):
    input_query = context["vars"]["query"]
    documents, document_context = _retrieve_advanced(input_query)
    prompt = f"""
    You have been tasked with helping us to answer the following query:
    <query>
    {input_query}
    </query>
    You have access to the following documents which are meant to provide context as you answer the query:
    <documents>
    {document_context}
    </documents>
    Please remain faithful to the underlying context, and only deviate from it if you are 100% sure that you know the answer already.
    Answer the question now, and avoid providing preamble such as 'Here is the answer', etc
    """
    return prompt
