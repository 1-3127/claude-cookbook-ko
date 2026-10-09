import os
import re

from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def llm_call(prompt: str, system_prompt: str = "", model="claude-sonnet-4-6") -> str:
    """
    주어진 프롬프트로 model을 호출하고 응답을 반환합니다.

    Args:
        prompt (str): model에 보낼 user prompt.
        system_prompt (str, optional): model에 보낼 system prompt. 기본값은 ""입니다.
        model (str, optional): 호출에 사용할 model. 기본값은 "claude-sonnet-4-6"입니다.

    Returns:
        str: language model의 응답.
    """
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": prompt}]
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
        temperature=0.1,
    )
    return response.content[0].text


def extract_xml(text: str, tag: str) -> str:
    """
    주어진 텍스트에서 지정한 XML tag의 내용을 추출합니다. 구조화된 응답을 parsing하는 데 사용합니다.

    Args:
        text (str): XML이 포함된 텍스트.
        tag (str): 내용을 추출할 XML tag.

    Returns:
        str: 지정한 XML tag의 내용. tag를 찾지 못하면 빈 문자열.
    """
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1) if match else ""
