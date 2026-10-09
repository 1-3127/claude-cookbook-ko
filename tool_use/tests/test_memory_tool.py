"""
Memory tool handler의 unit test.

보안 검증, 명령 실행, 오류 처리를 테스트합니다.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from memory_tool import MemoryToolHandler


class TestMemoryToolHandler(unittest.TestCase):
    """MemoryToolHandler의 test suite."""

    def setUp(self):
        """각 테스트에 임시 디렉터리를 생성합니다."""
        self.test_dir = tempfile.mkdtemp()
        self.handler = MemoryToolHandler(base_path=self.test_dir)

    def tearDown(self):
        """각 테스트 후 임시 디렉터리를 정리합니다."""
        shutil.rmtree(self.test_dir)

    # 보안 테스트

    def test_path_validation_requires_memories_prefix(self):
        """경로가 /memories로 시작해야 함을 테스트합니다."""
        result = self.handler.execute(command="view", path="/etc/passwd")
        self.assertIn("error", result)
        self.assertIn("must start with /memories", result["error"])

    def test_path_validation_prevents_traversal_dotdot(self):
        """.. traversal이 차단됨을 테스트합니다."""
        result = self.handler.execute(command="view", path="/memories/../../../etc/passwd")
        self.assertIn("error", result)
        self.assertIn("escape", result["error"].lower())

    def test_path_validation_prevents_traversal_encoded(self):
        """URL-encoded traversal이 차단됨을 테스트합니다."""
        result = self.handler.execute(command="view", path="/memories/%2e%2e/%2e%2e/etc/passwd")
        # 경로를 처리하며 검증에 실패해야 합니다
        self.assertIn("error", result)

    def test_path_validation_allows_valid_paths(self):
        """유효한 memory 경로가 허용됨을 테스트합니다."""
        result = self.handler.execute(command="create", path="/memories/test.txt", file_text="test")
        self.assertIn("success", result)

    # View 명령 테스트

    def test_view_empty_directory(self):
        """빈 /memories 디렉터리 보기를 테스트합니다."""
        result = self.handler.execute(command="view", path="/memories")
        self.assertIn("success", result)
        self.assertIn("empty", result["success"].lower())

    def test_view_directory_with_files(self):
        """파일이 있는 디렉터리 보기를 테스트합니다."""
        # 테스트 파일 생성
        self.handler.execute(command="create", path="/memories/file1.txt", file_text="content1")
        self.handler.execute(command="create", path="/memories/file2.txt", file_text="content2")

        result = self.handler.execute(command="view", path="/memories")
        self.assertIn("success", result)
        self.assertIn("file1.txt", result["success"])
        self.assertIn("file2.txt", result["success"])

    def test_view_file_with_line_numbers(self):
        """줄 번호가 포함된 파일 보기를 테스트합니다."""
        content = "line 1\nline 2\nline 3"
        self.handler.execute(command="create", path="/memories/test.txt", file_text=content)

        result = self.handler.execute(command="view", path="/memories/test.txt")
        self.assertIn("success", result)
        self.assertIn("   1: line 1", result["success"])
        self.assertIn("   2: line 2", result["success"])
        self.assertIn("   3: line 3", result["success"])

    def test_view_file_with_range(self):
        """특정 줄 범위 보기를 테스트합니다."""
        content = "line 1\nline 2\nline 3\nline 4"
        self.handler.execute(command="create", path="/memories/test.txt", file_text=content)

        result = self.handler.execute(command="view", path="/memories/test.txt", view_range=[2, 3])
        self.assertIn("success", result)
        self.assertIn("   2: line 2", result["success"])
        self.assertIn("   3: line 3", result["success"])
        self.assertNotIn("line 1", result["success"])
        self.assertNotIn("line 4", result["success"])

    def test_view_nonexistent_path(self):
        """존재하지 않는 경로 보기를 테스트합니다."""
        result = self.handler.execute(command="view", path="/memories/notfound.txt")
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    # Create 명령 테스트

    def test_create_file(self):
        """파일 생성을 테스트합니다."""
        result = self.handler.execute(
            command="create", path="/memories/test.txt", file_text="Hello, World!"
        )
        self.assertIn("success", result)

        # 파일 존재 확인
        file_path = Path(self.test_dir) / "memories" / "test.txt"
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.read_text(), "Hello, World!")

    def test_create_file_in_subdirectory(self):
        """하위 디렉터리의 파일 생성을 테스트합니다(디렉터리 자동 생성)."""
        result = self.handler.execute(
            command="create",
            path="/memories/subdir/test.txt",
            file_text="Nested content",
        )
        self.assertIn("success", result)

        file_path = Path(self.test_dir) / "memories" / "subdir" / "test.txt"
        self.assertTrue(file_path.exists())

    def test_create_requires_file_extension(self):
        """Create가 text 파일 extension만 허용함을 테스트합니다."""
        result = self.handler.execute(command="create", path="/memories/noext", file_text="content")
        self.assertIn("error", result)
        self.assertIn("text files are supported", result["error"])

    def test_create_overwrites_existing_file(self):
        """Create가 기존 파일을 덮어씀을 테스트합니다."""
        self.handler.execute(command="create", path="/memories/test.txt", file_text="original")
        result = self.handler.execute(
            command="create", path="/memories/test.txt", file_text="updated"
        )
        self.assertIn("success", result)

        file_path = Path(self.test_dir) / "memories" / "test.txt"
        self.assertEqual(file_path.read_text(), "updated")

    # String Replace 명령 테스트

    def test_str_replace_success(self):
        """성공적인 문자열 교체를 테스트합니다."""
        self.handler.execute(
            command="create",
            path="/memories/test.txt",
            file_text="Hello World",
        )

        result = self.handler.execute(
            command="str_replace",
            path="/memories/test.txt",
            old_str="World",
            new_str="Universe",
        )
        self.assertIn("success", result)

        file_path = Path(self.test_dir) / "memories" / "test.txt"
        self.assertEqual(file_path.read_text(), "Hello Universe")

    def test_str_replace_string_not_found(self):
        """문자열이 없을 때의 교체를 테스트합니다."""
        self.handler.execute(command="create", path="/memories/test.txt", file_text="Hello World")

        result = self.handler.execute(
            command="str_replace",
            path="/memories/test.txt",
            old_str="Missing",
            new_str="Text",
        )
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_str_replace_multiple_occurrences(self):
        """여러 번 나타나면 교체가 실패함을 테스트합니다."""
        self.handler.execute(
            command="create",
            path="/memories/test.txt",
            file_text="Hello World Hello World",
        )

        result = self.handler.execute(
            command="str_replace",
            path="/memories/test.txt",
            old_str="Hello",
            new_str="Hi",
        )
        self.assertIn("error", result)
        self.assertIn("appears 2 times", result["error"])

    def test_str_replace_file_not_found(self):
        """존재하지 않는 파일의 교체를 테스트합니다."""
        result = self.handler.execute(
            command="str_replace",
            path="/memories/notfound.txt",
            old_str="old",
            new_str="new",
        )
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    # Insert 명령 테스트

    def test_insert_at_beginning(self):
        """0번 줄(시작)에 삽입하는 것을 테스트합니다."""
        self.handler.execute(
            command="create", path="/memories/test.txt", file_text="line 1\nline 2"
        )

        result = self.handler.execute(
            command="insert",
            path="/memories/test.txt",
            insert_line=0,
            insert_text="new line",
        )
        self.assertIn("success", result)

        file_path = Path(self.test_dir) / "memories" / "test.txt"
        self.assertEqual(file_path.read_text(), "new line\nline 1\nline 2\n")

    def test_insert_in_middle(self):
        """중간 삽입을 테스트합니다."""
        self.handler.execute(
            command="create", path="/memories/test.txt", file_text="line 1\nline 2"
        )

        result = self.handler.execute(
            command="insert",
            path="/memories/test.txt",
            insert_line=1,
            insert_text="inserted",
        )
        self.assertIn("success", result)

        file_path = Path(self.test_dir) / "memories" / "test.txt"
        self.assertEqual(file_path.read_text(), "line 1\ninserted\nline 2\n")

    def test_insert_at_end(self):
        """끝 삽입을 테스트합니다."""
        self.handler.execute(
            command="create", path="/memories/test.txt", file_text="line 1\nline 2"
        )

        result = self.handler.execute(
            command="insert",
            path="/memories/test.txt",
            insert_line=2,
            insert_text="last line",
        )
        self.assertIn("success", result)

    def test_insert_invalid_line(self):
        """잘못된 줄 번호로 삽입하는 것을 테스트합니다."""
        self.handler.execute(command="create", path="/memories/test.txt", file_text="line 1")

        result = self.handler.execute(
            command="insert",
            path="/memories/test.txt",
            insert_line=99,
            insert_text="text",
        )
        self.assertIn("error", result)
        self.assertIn("invalid", result["error"].lower())

    # Delete 명령 테스트

    def test_delete_file(self):
        """파일 삭제를 테스트합니다."""
        self.handler.execute(command="create", path="/memories/test.txt", file_text="content")

        result = self.handler.execute(command="delete", path="/memories/test.txt")
        self.assertIn("success", result)

        file_path = Path(self.test_dir) / "memories" / "test.txt"
        self.assertFalse(file_path.exists())

    def test_delete_directory(self):
        """디렉터리 삭제를 테스트합니다."""
        self.handler.execute(
            command="create", path="/memories/subdir/test.txt", file_text="content"
        )

        result = self.handler.execute(command="delete", path="/memories/subdir")
        self.assertIn("success", result)

        dir_path = Path(self.test_dir) / "memories" / "subdir"
        self.assertFalse(dir_path.exists())

    def test_delete_cannot_delete_root(self):
        """Root /memories 디렉터리를 삭제할 수 없음을 테스트합니다."""
        result = self.handler.execute(command="delete", path="/memories")
        self.assertIn("error", result)
        self.assertIn("cannot delete", result["error"].lower())

    def test_delete_nonexistent_path(self):
        """존재하지 않는 경로 삭제를 테스트합니다."""
        result = self.handler.execute(command="delete", path="/memories/notfound.txt")
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    # Rename 명령 테스트

    def test_rename_file(self):
        """파일 이름 변경을 테스트합니다."""
        self.handler.execute(command="create", path="/memories/old.txt", file_text="content")

        result = self.handler.execute(
            command="rename", old_path="/memories/old.txt", new_path="/memories/new.txt"
        )
        self.assertIn("success", result)

        old_path = Path(self.test_dir) / "memories" / "old.txt"
        new_path = Path(self.test_dir) / "memories" / "new.txt"
        self.assertFalse(old_path.exists())
        self.assertTrue(new_path.exists())

    def test_rename_to_subdirectory(self):
        """파일을 하위 디렉터리로 이동하는 것을 테스트합니다."""
        self.handler.execute(command="create", path="/memories/file.txt", file_text="content")

        result = self.handler.execute(
            command="rename",
            old_path="/memories/file.txt",
            new_path="/memories/subdir/file.txt",
        )
        self.assertIn("success", result)

        new_path = Path(self.test_dir) / "memories" / "subdir" / "file.txt"
        self.assertTrue(new_path.exists())

    def test_rename_source_not_found(self):
        """Source가 없을 때 이름 변경을 테스트합니다."""
        result = self.handler.execute(
            command="rename",
            old_path="/memories/notfound.txt",
            new_path="/memories/new.txt",
        )
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_rename_destination_exists(self):
        """Destination이 이미 존재할 때 이름 변경을 테스트합니다."""
        self.handler.execute(command="create", path="/memories/file1.txt", file_text="content1")
        self.handler.execute(command="create", path="/memories/file2.txt", file_text="content2")

        result = self.handler.execute(
            command="rename",
            old_path="/memories/file1.txt",
            new_path="/memories/file2.txt",
        )
        self.assertIn("error", result)
        self.assertIn("already exists", result["error"].lower())

    # 오류 처리 테스트

    def test_unknown_command(self):
        """알 수 없는 명령 처리를 테스트합니다."""
        result = self.handler.execute(command="invalid", path="/memories")
        self.assertIn("error", result)
        self.assertIn("unknown command", result["error"].lower())

    def test_missing_required_parameters(self):
        """누락된 parameter에 대한 오류 처리를 테스트합니다."""
        result = self.handler.execute(command="view")
        self.assertIn("error", result)

    # Utility 테스트

    def test_clear_all_memory(self):
        """모든 memory 지우기를 테스트합니다."""
        # 파일 생성
        self.handler.execute(command="create", path="/memories/file1.txt", file_text="content1")
        self.handler.execute(command="create", path="/memories/file2.txt", file_text="content2")

        result = self.handler.clear_all_memory()
        self.assertIn("success", result)

        # 디렉터리가 존재하지만 비어 있는지 확인
        memory_root = Path(self.test_dir) / "memories"
        self.assertTrue(memory_root.exists())
        self.assertEqual(len(list(memory_root.iterdir())), 0)


if __name__ == "__main__":
    unittest.main()
