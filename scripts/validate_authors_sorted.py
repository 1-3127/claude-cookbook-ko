#!/usr/bin/env python3
"""authors.yaml 정렬을 검증하고 선택적으로 수정합니다(대소문자를 구분하지 않는 알파벳순)."""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

# Windows에서 UTF-8 출력 보장
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

AUTHORS_FILE = Path(__file__).parent.parent / "authors.yaml"

HEADER = """\
# yaml-language-server: $schema=./.github/authors_schema.json
# Authors mapping: GitHub username -> Author details
# This file maps author GitHub usernames (used in registry.yaml) to their full details
# for display on the website.

"""


def load_authors() -> dict[str, Any] | None:
    """authors.yaml을 불러오고 데이터를 반환합니다."""
    with open(AUTHORS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_sorted(data: dict) -> bool:
    """Key가 알파벳순으로 정렬되어 있는지 확인합니다(대소문자 구분 없음)."""
    keys = list(data.keys())
    return keys == sorted(keys, key=str.lower)


def sort_authors(data: dict, check_only: bool = False) -> bool:
    """authors.yaml을 정렬하여 저장합니다. 파일이 변경되었거나 변경될 예정이면 True를 반환합니다."""
    sorted_data = dict(sorted(data.items(), key=lambda x: x[0].lower()))

    if check_only:
        return list(data.keys()) != list(sorted_data.keys())

    with open(AUTHORS_FILE, "w", encoding="utf-8") as f:
        f.write(HEADER)
        yaml.dump(sorted_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return True


def show_diff(keys: list, sorted_keys: list) -> None:
    """현재 순서와 예상 순서의 차이를 보여줍니다."""
    print("authors.yaml is not sorted alphabetically (case-insensitive).")
    print("\nCurrent order:")
    for k in keys:
        print(f"  {k}")

    print("\nExpected order:")
    for k in sorted_keys:
        print(f"  {k}")

    print("\nOut of place entries:")
    for i, (current, expected) in enumerate(zip(keys, sorted_keys, strict=False)):
        if current != expected:
            print(f"  Position {i}: got '{current}', expected '{expected}'")


def main():
    parser = argparse.ArgumentParser(description="Validate or fix authors.yaml sorting")
    parser.add_argument(
        "--fix", action="store_true", help="Sort the file instead of just validating"
    )
    args = parser.parse_args()

    data = load_authors()

    if not data:
        print("authors.yaml is empty")
        sys.exit(0)

    already_sorted = is_sorted(data)

    if args.fix:
        if already_sorted:
            print("1 file left unchanged")
        else:
            sort_authors(data)
            print("1 file reformatted")
        sys.exit(0)

    # 검증 mode
    if already_sorted:
        print("1 file left unchanged")
        sys.exit(0)

    keys = list(data.keys())
    sorted_keys = sorted(keys, key=str.lower)
    show_diff(keys, sorted_keys)
    print("\nRun with --fix to sort automatically")
    sys.exit(1)


if __name__ == "__main__":
    main()
