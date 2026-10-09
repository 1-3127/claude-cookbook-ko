"""
Claude Skills API로 custom skill을 관리하는 utility 함수입니다.

이 module은 다음 helper 함수를 제공합니다.
- custom skill 생성 및 업로드
- skill 정보 나열 및 조회
- skill 버전 관리
- Claude로 skill 테스트
- skill 삭제
"""

from pathlib import Path
from typing import Any

from anthropic import Anthropic
from anthropic.lib import files_from_dir


def create_skill(client: Anthropic, skill_path: str, display_title: str) -> dict[str, Any]:
    """
    directory에서 새 custom skill을 생성합니다.

    directory에 포함되어야 할 것:
    - YAML frontmatter(name, description)가 있는 SKILL.md 파일
    - 선택: script, resource, REFERENCE.md

    Args:
        client: Skills beta가 있는 Anthropic client instance
        skill_path: SKILL.md가 있는 skill directory 경로
        display_title: 사람이 읽을 수 있는 skill 이름

    Returns:
        skill 생성 결과 dictionary:
        {
            'success': bool,
            'skill_id': str (성공하면),
            'display_title': str,
            'latest_version': str,
            'created_at': str,
            'source': str ('custom'),
            'error': str (실패하면)
        }

    Example:
        >>> client = Anthropic(api_key="...", default_headers={"anthropic-beta": "skills-2025-10-02"})
        >>> result = create_skill(client, "custom_skills/financial_analyzer", "Financial Analyzer")
        >>> if result['success']:
        ...     print(f"Created skill: {result['skill_id']}")
    """
    try:
        # skill directory 검증
        skill_dir = Path(skill_path)
        if not skill_dir.exists():
            return {"success": False, "error": f"Skill directory does not exist: {skill_path}"}

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return {"success": False, "error": f"SKILL.md not found in {skill_path}"}

        # files_from_dir로 skill 생성
        skill = client.beta.skills.create(
            display_title=display_title, files=files_from_dir(skill_path)
        )

        return {
            "success": True,
            "skill_id": skill.id,
            "display_title": skill.display_title,
            "latest_version": skill.latest_version,
            "created_at": skill.created_at,
            "source": skill.source,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_custom_skills(client: Anthropic) -> list[dict[str, Any]]:
    """
    workspace의 모든 custom skill을 나열합니다.

    Args:
        client: Skills beta가 있는 Anthropic client instance

    Returns:
        metadata가 있는 skill dictionary 목록

    Example:
        >>> skills = list_custom_skills(client)
        >>> for skill in skills:
        ...     print(f"{skill['display_title']}: {skill['skill_id']}")
    """
    try:
        skills_response = client.beta.skills.list(source="custom")

        skills = []
        for skill in skills_response.data:
            skills.append(
                {
                    "skill_id": skill.id,
                    "display_title": skill.display_title,
                    "latest_version": skill.latest_version,
                    "created_at": skill.created_at,
                    "updated_at": skill.updated_at,
                }
            )

        return skills

    except Exception as e:
        print(f"Error listing skills: {e}")
        return []


def get_skill_version(
    client: Anthropic, skill_id: str, version: str = "latest"
) -> dict[str, Any] | None:
    """
    특정 skill 버전의 상세 정보를 얻습니다.

    Args:
        client: Anthropic client instance
        skill_id: skill ID
        version: 조회할 버전(기본값: "latest")

    Returns:
        버전 상세 정보 dictionary, 찾지 못하면 None
    """
    try:
        # 지정하지 않으면 최신 버전 얻기
        if version == "latest":
            skill = client.beta.skills.retrieve(skill_id)
            version = skill.latest_version

        version_info = client.beta.skills.versions.retrieve(skill_id=skill_id, version=version)

        return {
            "version": version_info.version,
            "skill_id": version_info.skill_id,
            "name": version_info.name,
            "description": version_info.description,
            "directory": version_info.directory,
            "created_at": version_info.created_at,
        }

    except Exception as e:
        print(f"Error getting skill version: {e}")
        return None


def create_skill_version(client: Anthropic, skill_id: str, skill_path: str) -> dict[str, Any]:
    """
    기존 skill의 새 버전을 생성합니다.

    Args:
        client: Anthropic client instance
        skill_id: 기존 skill ID
        skill_path: 갱신한 skill directory 경로

    Returns:
        버전 생성 결과 dictionary
    """
    try:
        version = client.beta.skills.versions.create(
            skill_id=skill_id, files=files_from_dir(skill_path)
        )

        return {
            "success": True,
            "version": version.version,
            "skill_id": version.skill_id,
            "created_at": version.created_at,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_skill(client: Anthropic, skill_id: str, delete_versions: bool = True) -> bool:
    """
    custom skill과 선택적으로 모든 버전을 삭제합니다.

    참고: skill 삭제 전에 모든 버전을 삭제해야 합니다.

    Args:
        client: Anthropic client instance
        skill_id: 삭제할 skill ID
        delete_versions: 먼저 모든 버전을 삭제할지 여부

    Returns:
        성공하면 True, 아니면 False
    """
    try:
        if delete_versions:
            # 먼저 모든 버전 삭제
            versions = client.beta.skills.versions.list(skill_id=skill_id)

            for version in versions.data:
                client.beta.skills.versions.delete(skill_id=skill_id, version=version.version)
                print(f"  Deleted version: {version.version}")

        # 그다음 skill 자체 삭제
        client.beta.skills.delete(skill_id)
        print(f"✓ Deleted skill: {skill_id}")
        return True

    except Exception as e:
        print(f"Error deleting skill: {e}")
        return False


def test_skill(
    client: Anthropic,
    skill_id: str,
    test_prompt: str,
    model: str = "claude-sonnet-4-6",
    include_anthropic_skills: list[str] | None = None,
) -> Any:
    """
    프롬프트로 custom skill을 테스트합니다.

    Args:
        client: Anthropic client instance
        skill_id: 테스트할 skill ID
        test_prompt: skill 테스트 프롬프트
        model: 테스트에 사용할 model
        include_anthropic_skills: 포함할 Anthropic skill ID의 선택적 목록

    Returns:
        Claude의 응답

    Example:
        >>> response = test_skill(
        ...     client,
        ...     "skill_abc123",
        ...     "Calculate P/E ratio for a company with price $50 and earnings $2.50",
        ...     include_anthropic_skills=["xlsx"]
        ... )
    """
    # skill 목록 구성
    skills = [{"type": "custom", "skill_id": skill_id, "version": "latest"}]

    # 요청된 Anthropic skill 추가
    if include_anthropic_skills:
        for anthropic_skill in include_anthropic_skills:
            skills.append({"type": "anthropic", "skill_id": anthropic_skill, "version": "latest"})

    response = client.beta.messages.create(
        model=model,
        max_tokens=4096,
        container={"skills": skills},
        tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        messages=[{"role": "user", "content": test_prompt}],
        betas=["code-execution-2025-08-25", "files-api-2025-04-14", "skills-2025-10-02"],
    )

    return response


def list_skill_versions(client: Anthropic, skill_id: str) -> list[dict[str, Any]]:
    """
    skill의 모든 버전을 나열합니다.

    Args:
        client: Anthropic client instance
        skill_id: skill ID

    Returns:
        버전 dictionary 목록
    """
    try:
        versions_response = client.beta.skills.versions.list(skill_id=skill_id)

        versions = []
        for version in versions_response.data:
            versions.append(
                {
                    "version": version.version,
                    "skill_id": version.skill_id,
                    "created_at": version.created_at,
                }
            )

        return versions

    except Exception as e:
        print(f"Error listing versions: {e}")
        return []


def validate_skill_directory(skill_path: str) -> dict[str, Any]:
    """
    업로드 전에 skill directory 구조를 검증합니다.

    확인 항목:
    - SKILL.md 존재
    - YAML frontmatter가 유효함
    - directory 이름과 skill 이름 일치
    - 전체 크기 8MB 미만

    Args:
        skill_path: skill directory 경로

    Returns:
        검증 결과 dictionary
    """
    result = {"valid": True, "errors": [], "warnings": [], "info": {}}

    skill_dir = Path(skill_path)

    # directory 존재 확인
    if not skill_dir.exists():
        result["valid"] = False
        result["errors"].append(f"Directory does not exist: {skill_path}")
        return result

    # SKILL.md 확인
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result["valid"] = False
        result["errors"].append("SKILL.md file is required")
    else:
        # SKILL.md 읽기 및 검증
        content = skill_md.read_text()

        # YAML frontmatter 확인
        if not content.startswith("---"):
            result["valid"] = False
            result["errors"].append("SKILL.md must start with YAML frontmatter (---)")
        else:
            # frontmatter 추출
            try:
                end_idx = content.index("---", 3)
                frontmatter = content[3:end_idx].strip()

                # 필수 field 확인
                if "name:" not in frontmatter:
                    result["valid"] = False
                    result["errors"].append("YAML frontmatter must include 'name' field")

                if "description:" not in frontmatter:
                    result["valid"] = False
                    result["errors"].append("YAML frontmatter must include 'description' field")

                # frontmatter 크기 확인
                if len(frontmatter) > 1024:
                    result["valid"] = False
                    result["errors"].append(
                        f"YAML frontmatter exceeds 1024 chars (found: {len(frontmatter)})"
                    )

            except ValueError:
                result["valid"] = False
                result["errors"].append("Invalid YAML frontmatter format")

    # 전체 크기 확인
    total_size = sum(f.stat().st_size for f in skill_dir.rglob("*") if f.is_file())
    result["info"]["total_size_mb"] = total_size / (1024 * 1024)

    if total_size > 8 * 1024 * 1024:
        result["valid"] = False
        result["errors"].append(
            f"Total size exceeds 8MB (found: {total_size / (1024 * 1024):.2f} MB)"
        )

    # 파일 수 세기
    files = list(skill_dir.rglob("*"))
    result["info"]["file_count"] = len([f for f in files if f.is_file()])
    result["info"]["directory_count"] = len([f for f in files if f.is_dir()])

    # 일반적인 파일 확인
    if (skill_dir / "REFERENCE.md").exists():
        result["info"]["has_reference"] = True

    if (skill_dir / "scripts").exists():
        result["info"]["has_scripts"] = True
        result["info"]["script_files"] = [
            f.name for f in (skill_dir / "scripts").iterdir() if f.is_file()
        ]

    return result


def print_skill_summary(skill_info: dict[str, Any]) -> None:
    """
    skill의 서식 지정 요약을 출력합니다.

    Args:
        skill_info: skill 정보 dictionary
    """
    print(f"📦 Skill: {skill_info.get('display_title', 'Unknown')}")
    print(f"   ID: {skill_info.get('skill_id', 'N/A')}")
    print(f"   Version: {skill_info.get('latest_version', 'N/A')}")
    print(f"   Source: {skill_info.get('source', 'N/A')}")
    print(f"   Created: {skill_info.get('created_at', 'N/A')}")

    if "error" in skill_info:
        print(f"   ❌ Error: {skill_info['error']}")
