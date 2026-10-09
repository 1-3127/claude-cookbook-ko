"""
Claude의 memory_20250818 tool을 위한 production용 memory tool handler.

이 구현은 경로 검증, 오류 처리, 포괄적인 보안 조치로
memory 작업의 안전한 client-side 실행을 제공합니다.
"""

import shutil
from pathlib import Path
from typing import Any


class MemoryToolHandler:
    """
    Claude memory tool 명령 실행을 처리합니다.

    Memory tool은 표준화된 tool interface를 통해 Claude가 memory
    시스템의 파일을 읽고 쓰고 관리하게 합니다. 이 handler는 보안 제어가
    포함된 client-side 구현을 제공합니다.

    Attributes:
        base_path: Memory 저장소의 root 디렉터리
        memory_root: base_path 내 /memories 디렉터리
    """

    def __init__(self, base_path: str = "./memory_storage"):
        """
        Memory tool handler를 초기화합니다.

        Args:
            base_path: 모든 memory 작업의 root 디렉터리
        """
        self.base_path = Path(base_path).resolve()
        self.memory_root = self.base_path / "memories"
        self.memory_root.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, path: str) -> Path:
        """
        Directory traversal 공격을 방지하기 위해 memory 경로를 검증하고 해석합니다.

        Args:
            path: 검증할 경로(/memories로 시작해야 함)

        Returns:
            memory_root 내에서 해석된 절대 Path 객체

        Raises:
            ValueError: 경로가 잘못되었거나 memory 디렉터리를 벗어나려는 경우
        """
        if not path.startswith("/memories"):
            raise ValueError(
                f"Path must start with /memories, got: {path}. "
                "All memory operations must be confined to the /memories directory."
            )

        # /memories prefix와 앞쪽 slash 제거
        relative_path = path[len("/memories") :].lstrip("/")

        # memory_root 내 절대 경로로 해석
        if relative_path:
            full_path = (self.memory_root / relative_path).resolve()
        else:
            full_path = self.memory_root.resolve()

        # 해석된 경로가 여전히 memory_root 내인지 확인
        try:
            full_path.relative_to(self.memory_root.resolve())
        except ValueError as e:
            raise ValueError(
                f"Path '{path}' would escape /memories directory. "
                "Directory traversal attempts are not allowed."
            ) from e

        return full_path

    def execute(self, **params: Any) -> dict[str, str]:
        """
        Memory tool 명령을 실행합니다.

        Args:
            **params: Claude의 tool use에서 받은 명령 parameter

        Returns:
            'success' 또는 'error' key가 있는 Dict

        지원 명령:
            - view: 디렉터리 내용 또는 파일 내용 표시
            - create: 파일 생성 또는 덮어쓰기
            - str_replace: 파일의 텍스트 교체
            - insert: 특정 줄에 텍스트 삽입
            - delete: 파일 또는 디렉터리 삭제
            - rename: 파일/디렉터리 이름 변경 또는 이동
        """
        command = params.get("command")

        try:
            if command == "view":
                return self._view(params)
            elif command == "create":
                return self._create(params)
            elif command == "str_replace":
                return self._str_replace(params)
            elif command == "insert":
                return self._insert(params)
            elif command == "delete":
                return self._delete(params)
            elif command == "rename":
                return self._rename(params)
            else:
                return {
                    "error": f"Unknown command: '{command}'. "
                    "Valid commands are: view, create, str_replace, insert, delete, rename"
                }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Unexpected error executing {command}: {e}"}

    def _view(self, params: dict[str, Any]) -> dict[str, str]:
        """디렉터리 내용 또는 파일 내용을 봅니다."""
        path = params.get("path")
        view_range = params.get("view_range")

        if not path:
            return {"error": "Missing required parameter: path"}

        full_path = self._validate_path(path)

        # 디렉터리 목록 처리
        if full_path.is_dir():
            try:
                items = []
                for item in sorted(full_path.iterdir()):
                    if item.name.startswith("."):
                        continue
                    items.append(f"{item.name}/" if item.is_dir() else item.name)

                if not items:
                    return {"success": f"Directory: {path}\n(empty)"}

                return {
                    "success": f"Directory: {path}\n" + "\n".join([f"- {item}" for item in items])
                }
            except Exception as e:
                return {"error": f"Cannot read directory {path}: {e}"}

        # 파일 읽기 처리
        elif full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                # 지정된 경우 view 범위 적용
                if view_range:
                    start_line = max(1, view_range[0]) - 1  # 0부터 시작하는 index로 변환
                    end_line = len(lines) if view_range[1] == -1 else view_range[1]
                    lines = lines[start_line:end_line]
                    start_num = start_line + 1
                else:
                    start_num = 1

                # 줄 번호를 포함하여 형식 지정
                numbered_lines = [f"{i + start_num:4d}: {line}" for i, line in enumerate(lines)]
                return {"success": "\n".join(numbered_lines)}

            except UnicodeDecodeError:
                return {"error": f"Cannot read {path}: File is not valid UTF-8 text"}
            except Exception as e:
                return {"error": f"Cannot read file {path}: {e}"}

        else:
            return {"error": f"Path not found: {path}"}

    def _create(self, params: dict[str, Any]) -> dict[str, str]:
        """파일을 생성하거나 덮어씁니다."""
        path = params.get("path")
        file_text = params.get("file_text", "")

        if not path:
            return {"error": "Missing required parameter: path"}

        full_path = self._validate_path(path)

        # 디렉터리를 직접 생성하지 못하게 함
        if not path.endswith((".txt", ".md", ".json", ".py", ".yaml", ".yml")):
            return {
                "error": f"Cannot create {path}: Only text files are supported. "
                "Use file extensions: .txt, .md, .json, .py, .yaml, .yml"
            }

        try:
            # 필요하면 상위 디렉터리 생성
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 쓰기
            full_path.write_text(file_text, encoding="utf-8")
            return {"success": f"File created successfully at {path}"}

        except Exception as e:
            return {"error": f"Cannot create file {path}: {e}"}

    def _str_replace(self, params: dict[str, Any]) -> dict[str, str]:
        """파일의 텍스트를 교체합니다."""
        path = params.get("path")
        old_str = params.get("old_str")
        new_str = params.get("new_str", "")

        if not path or old_str is None:
            return {"error": "Missing required parameters: path, old_str"}

        full_path = self._validate_path(path)

        if not full_path.is_file():
            return {"error": f"File not found: {path}"}

        try:
            content = full_path.read_text(encoding="utf-8")

            # old_str 존재 여부 확인
            count = content.count(old_str)
            if count == 0:
                return {
                    "error": f"String not found in {path}. The exact text must exist in the file."
                }
            elif count > 1:
                return {
                    "error": f"String appears {count} times in {path}. "
                    "The string must be unique. Use more specific context."
                }

            # 교체 수행
            new_content = content.replace(old_str, new_str, 1)
            full_path.write_text(new_content, encoding="utf-8")

            return {"success": f"File {path} has been edited successfully"}

        except Exception as e:
            return {"error": f"Cannot edit file {path}: {e}"}

    def _insert(self, params: dict[str, Any]) -> dict[str, str]:
        """특정 줄에 텍스트를 삽입합니다."""
        path = params.get("path")
        insert_line = params.get("insert_line")
        insert_text = params.get("insert_text", "")

        if not path or insert_line is None:
            return {"error": "Missing required parameters: path, insert_line"}

        full_path = self._validate_path(path)

        if not full_path.is_file():
            return {"error": f"File not found: {path}"}

        try:
            lines = full_path.read_text(encoding="utf-8").splitlines()

            # insert_line 검증
            if insert_line < 0 or insert_line > len(lines):
                return {
                    "error": f"Invalid insert_line {insert_line}. "
                    f"Must be between 0 and {len(lines)}"
                }

            # 텍스트 삽입
            lines.insert(insert_line, insert_text.rstrip("\n"))

            # 다시 쓰기
            full_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            return {"success": f"Text inserted at line {insert_line} in {path}"}

        except Exception as e:
            return {"error": f"Cannot insert into {path}: {e}"}

    def _delete(self, params: dict[str, Any]) -> dict[str, str]:
        """파일 또는 디렉터리를 삭제합니다."""
        path = params.get("path")

        if not path:
            return {"error": "Missing required parameter: path"}

        # Root memories 디렉터리 삭제 방지
        if path == "/memories":
            return {"error": "Cannot delete the /memories directory itself"}

        full_path = self._validate_path(path)

        # Memory 디렉터리 밖의 우발적 삭제를 방지하기 위해 경로가 /memories 내인지 확인
        # _validate_path 외에 추가 안전 확인을 제공합니다
        try:
            full_path.relative_to(self.memory_root.resolve())
        except ValueError:
            return {
                "error": f"Invalid operation: Path '{path}' is not within /memories directory. "
                "Only paths within /memories can be deleted."
            }

        if not full_path.exists():
            return {"error": f"Path not found: {path}"}

        try:
            if full_path.is_file():
                full_path.unlink()
                return {"success": f"File deleted: {path}"}
            elif full_path.is_dir():
                shutil.rmtree(full_path)
                return {"success": f"Directory deleted: {path}"}

        except Exception as e:
            return {"error": f"Cannot delete {path}: {e}"}

    def _rename(self, params: dict[str, Any]) -> dict[str, str]:
        """파일/디렉터리 이름을 변경하거나 이동합니다."""
        old_path = params.get("old_path")
        new_path = params.get("new_path")

        if not old_path or not new_path:
            return {"error": "Missing required parameters: old_path, new_path"}

        old_full_path = self._validate_path(old_path)
        new_full_path = self._validate_path(new_path)

        if not old_full_path.exists():
            return {"error": f"Source path not found: {old_path}"}

        if new_full_path.exists():
            return {
                "error": f"Destination already exists: {new_path}. "
                "Cannot overwrite existing files/directories."
            }

        try:
            # 필요하면 상위 디렉터리 생성
            new_full_path.parent.mkdir(parents=True, exist_ok=True)

            # 이름 변경/이동 수행
            old_full_path.rename(new_full_path)

            return {"success": f"Renamed {old_path} to {new_path}"}

        except Exception as e:
            return {"error": f"Cannot rename {old_path} to {new_path}: {e}"}

    def clear_all_memory(self) -> dict[str, str]:
        """
        모든 memory 파일을 지웁니다(테스트나 새로 시작할 때 유용).

        ⚠️ 경고: 이 method는 시연과 테스트 목적으로만 사용합니다.
        Production에서는 모든 memory 파일을 삭제해야 하는지 신중히
        고려해야 합니다. 학습한 모든 패턴과 저장된 지식을 영구적으로
        제거하기 때문입니다. 대신 선택적 삭제를 고려하세요.

        Returns:
            성공 message가 있는 Dict
        """
        try:
            if self.memory_root.exists():
                shutil.rmtree(self.memory_root)
            self.memory_root.mkdir(parents=True, exist_ok=True)
            return {"success": "All memory cleared successfully"}
        except Exception as e:
            return {"error": f"Cannot clear memory: {e}"}
