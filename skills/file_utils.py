"""
Claude Skills와 Files API 작업용 utility 함수입니다.

이 module은 다음 helper 함수를 제공합니다.
- Claude API 응답에서 file ID 추출
- Files API로 파일 다운로드
- disk에 파일 저장
"""

import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic


def extract_file_ids(response) -> list[str]:
    """
    Claude API 응답에서 모든 file ID를 추출합니다.

    Skills는 code execution 중 파일을 생성하고 tool result에
    file_id attribute를 반환합니다. 이 함수는 응답을 parse하여 모든 file ID를 찾습니다.

    Args:
        response: client.beta.messages.create()의 response 객체

    Returns:
        응답에서 찾은 file ID 목록

    Example:
        >>> response = client.beta.messages.create(...)
        >>> file_ids = extract_file_ids(response)
        >>> print(f"Found {len(file_ids)} files")
    """
    file_ids = []

    for block in response.content:
        # bash_code_execution_tool_result 확인(beta API 형식)
        if block.type == "bash_code_execution_tool_result":
            try:
                if hasattr(block, "content") and hasattr(block.content, "content"):
                    # content array 순회
                    for item in block.content.content:
                        if hasattr(item, "file_id"):
                            file_ids.append(item.file_id)
            except Exception as e:
                print(f"Warning: Error parsing bash_code_execution_tool_result: {e}")
                continue

        # legacy tool_result block 확인(하위 호환용)
        elif block.type == "tool_result":
            try:
                if hasattr(block, "output"):
                    output_str = str(block.output)

                    # 출력의 file_id 패턴 찾기
                    if "file_id" in output_str.lower():
                        # 먼저 JSON으로 parsing 시도
                        try:
                            output_json = json.loads(output_str)
                            if isinstance(output_json, dict) and "file_id" in output_json:
                                file_ids.append(output_json["file_id"])
                            elif isinstance(output_json, list):
                                for item in output_json:
                                    if isinstance(item, dict) and "file_id" in item:
                                        file_ids.append(item["file_id"])
                        except json.JSONDecodeError:
                            # JSON이 아니면 regex로 file_id 패턴 찾기
                            import re

                            pattern = r"file_id['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]+)"
                            matches = re.findall(pattern, output_str)
                            file_ids.extend(matches)
            except Exception as e:
                print(f"Warning: Error parsing tool_result block: {e}")
                continue

    # 순서를 유지하며 중복 제거
    seen = set()
    unique_file_ids = []
    for fid in file_ids:
        if fid not in seen:
            seen.add(fid)
            unique_file_ids.append(fid)

    return unique_file_ids


def download_file(
    client: Anthropic, file_id: str, output_path: str, overwrite: bool = True
) -> dict[str, Any]:
    """
    Claude Files API에서 파일을 다운로드해 로컬에 저장합니다.

    Args:
        client: Anthropic client instance
        file_id: Skills가 반환한 file ID
        output_path: 파일을 저장할 로컬 경로
        overwrite: 기존 파일을 덮어쓸지 여부(기본값: True)

    Returns:
        다운로드 metadata dictionary:
        {
            'file_id': str,
            'output_path': str,
            'size': int,
            'success': bool,
            'error': Optional[str]
        }

    Example:
        >>> client = Anthropic(api_key="...")
        >>> result = download_file(client, "file_abc123", "outputs/report.xlsx")
        >>> if result['success']:
        ...     if result.get('overwritten'):
        ...         print(f"Overwrote existing file: {result['output_path']}")
        ...     print(f"Downloaded {result['size']} bytes to {result['output_path']}")
    """
    result = {
        "file_id": file_id,
        "output_path": output_path,
        "size": 0,
        "success": False,
        "error": None,
    }

    try:
        # 파일 존재 여부 확인
        file_exists = os.path.exists(output_path)
        if file_exists and not overwrite:
            result["error"] = f"File already exists: {output_path} (set overwrite=True to replace)"
            return result

        # 없으면 output directory 생성
        output_dir = os.path.dirname(output_path)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Files API에서 파일 content 다운로드(beta namespace)
        file_content = client.beta.files.download(file_id=file_id)

        # disk에 저장
        with open(output_path, "wb") as f:
            f.write(file_content.read())

        # 파일 크기 얻기
        result["size"] = os.path.getsize(output_path)
        result["success"] = True
        result["overwritten"] = file_exists  # 기존 파일 덮어쓰기 여부 추적

    except Exception as e:
        result["error"] = str(e)

    return result


def download_all_files(
    client: Anthropic,
    response,
    output_dir: str = "outputs",
    prefix: str = "",
    overwrite: bool = True,
) -> list[dict[str, Any]]:
    """
    Claude API 응답에서 모든 파일을 추출하고 다운로드합니다.

    extract_file_ids()와 download_file()을 결합해 한 호출로
    모든 파일을 다운로드하는 편의 함수입니다.

    Args:
        client: Anthropic client instance
        response: client.messages.create()의 response 객체
        output_dir: 파일을 저장할 directory
        prefix: 선택적 파일명 prefix(예: "financial_report_")
        overwrite: 기존 파일을 덮어쓸지 여부(기본값: True)

    Returns:
        다운로드 결과 목록(파일당 하나)

    Example:
        >>> response = client.messages.create(...)
        >>> results = download_all_files(client, response, output_dir="outputs")
        >>> for result in results:
        ...     if result['success']:
        ...         print(f"✓ Downloaded: {result['output_path']}")
        ...     else:
        ...         print(f"✗ Failed: {result['error']}")
    """
    file_ids = extract_file_ids(response)
    results = []

    for i, file_id in enumerate(file_ids, 1):
        # 올바른 파일명을 위해 파일 metadata 조회 시도
        try:
            file_info = client.beta.files.retrieve_metadata(file_id=file_id)
            filename = file_info.filename
        except Exception:
            # metadata를 얻지 못하면 일반 파일명 사용
            filename = f"file_{i}.bin"

        # 제공된 prefix 추가
        if prefix:
            filename = f"{prefix}{filename}"

        # 전체 output 경로 구성
        output_path = os.path.join(output_dir, filename)

        # 파일 다운로드
        result = download_file(client, file_id, output_path, overwrite=overwrite)
        results.append(result)

    return results


def get_file_info(client: Anthropic, file_id: str) -> dict[str, Any] | None:
    """
    Files API에서 파일 metadata를 조회합니다.

    Args:
        client: Anthropic client instance
        file_id: query할 file ID

    Returns:
        파일 metadata dictionary, 찾지 못하면 None

    Example:
        >>> info = get_file_info(client, "file_abc123")
        >>> if info:
        ...     print(f"Filename: {info['filename']}")
        ...     print(f"Size: {info['size']} bytes")
        ...     print(f"Created: {info['created_at']}")
    """
    try:
        file_info = client.beta.files.retrieve_metadata(file_id=file_id)
        return {
            "file_id": file_info.id,
            "filename": file_info.filename,
            "size": file_info.size_bytes,
            "mime_type": file_info.mime_type,
            "created_at": file_info.created_at,
            "type": file_info.type,
            "downloadable": file_info.downloadable,
        }
    except Exception as e:
        print(f"Error retrieving file info: {e}")
        return None


def print_download_summary(results: list[dict[str, Any]]) -> None:
    """
    파일 다운로드 결과의 서식 지정 요약을 출력합니다.

    Args:
        results: download_all_files()의 다운로드 결과 목록

    Example:
        >>> results = download_all_files(client, response)
        >>> print_download_summary(results)

        File Download Summary
        =====================
        ✓ outputs/budget.xlsx (45.2 KB)
        ✓ outputs/presentation.pptx (127.8 KB)
        ✗ outputs/report.pdf - Error: File not found

        Total: 2/3 files downloaded successfully
    """
    print("\nFile Download Summary")
    print("=" * 50)

    success_count = 0
    total_size = 0

    for result in results:
        if result["success"]:
            size_kb = result["size"] / 1024
            overwrite_notice = " [overwritten]" if result.get("overwritten", False) else ""
            print(f"✓ {result['output_path']} ({size_kb:.1f} KB){overwrite_notice}")
            success_count += 1
            total_size += result["size"]
        else:
            print(f"✗ {result['output_path']} - Error: {result['error']}")

    print(f"\nTotal: {success_count}/{len(results)} files downloaded successfully")
    if success_count > 0:
        total_mb = total_size / (1024 * 1024)
        print(f"Total size: {total_mb:.2f} MB")
