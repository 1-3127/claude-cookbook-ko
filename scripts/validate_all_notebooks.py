#!/usr/bin/env python3
"""
Dashboard와 보고 기능이 있는 종합적인 Notebook 검증 도구입니다.

기능:
- Checkpoint를 사용하는 점진적 검증
- 문제 분류와 자동 수정
- 추세를 포함한 dashboard 생성
- GitHub issue 내보내기
- 상태를 영속적으로 저장하며 idempotent하게 동작
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

NO_CREDS_WARNING = (
    "⚠️  Warning: neither ANTHROPIC_API_KEY nor ANTHROPIC_AUTH_TOKEN is set. "
    "Execution tests will be skipped."
)


def has_anthropic_credentials() -> bool:
    """Notebook 실행에 필요한 Anthropic API credential의 사용 가능 여부입니다."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


class NotebookValidator:
    """Jupyter Notebook의 일반적인 문제를 검증합니다."""

    def __init__(self):
        self.state_file = Path(".notebook_validation_state.json")
        self.checkpoint_file = Path(".notebook_validation_checkpoint.json")
        self.state = self.load_state()

    def load_state(self) -> dict:
        """이전 검증 상태가 있으면 불러옵니다."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Could not parse state file, starting fresh")

        return {
            "version": "1.0",
            "last_full_run": None,
            "notebooks": {},
            "history": [],
            "ignored": {},
        }

    def save_state(self):
        """현재 상태를 파일에 저장합니다."""
        # 이력 업데이트
        total = len(self.state["notebooks"])
        passing = sum(1 for n in self.state["notebooks"].values() if n.get("status") == "pass")

        today = datetime.now().strftime("%Y-%m-%d")

        # 오늘 항목 업데이트 또는 추가
        if self.state["history"] and self.state["history"][-1]["date"] == today:
            self.state["history"][-1] = {"date": today, "passing": passing, "total": total}
        else:
            self.state["history"].append({"date": today, "passing": passing, "total": total})

        # 최근 30일 이력만 유지
        self.state["history"] = self.state["history"][-30:]

        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def validate_notebook(self, notebook_path: Path, mode: str = "full") -> dict:
        """단일 Notebook을 검증합니다."""
        result = {"status": "pass", "issues": [], "last_validated": datetime.now().isoformat()}

        # 빠른 구조 검사
        try:
            with open(notebook_path) as f:
                nb = json.load(f)
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(
                {"type": "invalid_json", "severity": "critical", "details": str(e)}
            )
            return result

        # 빈 셀 확인
        for i, cell in enumerate(nb.get("cells", [])):
            if not cell.get("source"):
                result["issues"].append(
                    {
                        "type": "empty_cell",
                        "severity": "info",
                        "cell": i,
                        "details": "Empty cell found",
                    }
                )

        # 오류 출력 확인
        for i, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") == "code":
                for output in cell.get("outputs", []):
                    if output.get("output_type") == "error":
                        result["status"] = (
                            "warning" if result["status"] == "pass" else result["status"]
                        )
                        result["issues"].append(
                            {
                                "type": "error_output",
                                "severity": "warning",
                                "cell": i,
                                "details": "Cell contains error output",
                            }
                        )

        # Deprecated model 확인
        deprecated_models = {
            "claude-3-5-sonnet-20240620": "claude-sonnet-5",
            "claude-3-5-sonnet-20241022": "claude-sonnet-5",
            "claude-3-5-sonnet-latest": "claude-sonnet-5",
            "claude-3-haiku-20240307": "claude-haiku-4-5",
            "claude-3-5-haiku-20241022": "claude-haiku-4-5",
            "claude-3-opus-20240229": "claude-opus-4-8",
            "claude-3-opus-latest": "claude-opus-4-8",
            "claude-sonnet-4-20250514": "claude-sonnet-5",
            "claude-opus-4-20250514": "claude-opus-4-8",
            "claude-opus-4-1": "claude-opus-4-8",
            "claude-sonnet-4-5-20250929": "claude-sonnet-5",
            "claude-sonnet-4-5": "claude-sonnet-5",
            "claude-opus-4-5-20251101": "claude-opus-4-8",
            "claude-opus-4-5": "claude-opus-4-8",
        }

        for i, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))

                # 날짜가 있는 API model ID 확인(날짜가 필요한 Bedrock ID 제외)
                dated_pattern = r"(?<!anthropic\.)claude-\w+-[\d.]+-\d{8}"
                dated_matches = re.findall(dated_pattern, source)
                for dated_model in dated_matches:
                    result["status"] = "warning" if result["status"] == "pass" else result["status"]
                    result["issues"].append(
                        {
                            "type": "dated_model_id",
                            "severity": "warning",
                            "cell": i,
                            "details": f"Dated model ID '{dated_model}' found. Use non-dated alias instead.",
                        }
                    )

                # Deprecated model 확인
                for old_model, new_model in deprecated_models.items():
                    if old_model in source:
                        result["status"] = (
                            "warning" if result["status"] == "pass" else result["status"]
                        )
                        result["issues"].append(
                            {
                                "type": "deprecated_model",
                                "severity": "warning",
                                "cell": i,
                                "details": {"current": old_model, "suggested": new_model},
                            }
                        )

                # Hardcoded API key 확인
                if "sk-ant-" in source:
                    result["status"] = "error"
                    result["issues"].append(
                        {
                            "type": "hardcoded_api_key",
                            "severity": "critical",
                            "cell": i,
                            "details": "Hardcoded Claude API key detected",
                        }
                    )
                elif (
                    "api_key=" in source.lower()
                    and "os.environ" not in source
                    and "getenv" not in source
                ):
                    result["status"] = "error"
                    result["issues"].append(
                        {
                            "type": "api_key_not_env",
                            "severity": "critical",
                            "cell": i,
                            "details": "API key not using environment variable",
                        }
                    )

        # Full mode이면 Notebook 실행
        if mode == "full" and result["status"] != "error":
            if has_anthropic_credentials():
                exec_result = self.execute_notebook(notebook_path)
                if not exec_result["success"]:
                    result["status"] = "error"
                    result["issues"].append(
                        {
                            "type": "execution_failure",
                            "severity": "error",
                            "details": exec_result["error"],
                        }
                    )

        return result

    def execute_notebook(self, notebook_path: Path) -> dict:
        """Notebook을 실행하고 성공 상태를 반환합니다."""
        cmd = [
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--ExecutePreprocessor.timeout=120",
            "--output",
            "/dev/null",
            "--stdout",
            str(notebook_path),
        ]

        try:
            # cmd가 완전히 통제되므로 여기서 shell=False인 subprocess.run은 안전함
            result = subprocess.run(cmd, capture_output=True, timeout=130, text=True)  # noqa: S603
            if result.returncode == 0:
                return {"success": True}
            else:
                # Stderr에서 오류 추출
                error_lines = result.stderr.split("\n")
                error_msg = next(
                    (line for line in error_lines if "Error" in line or "error" in line),
                    "Execution failed",
                )
                return {"success": False, "error": error_msg[:200]}  # 오류 메시지 길이 제한
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout (>120s)"}
        except FileNotFoundError:
            return {"success": False, "error": "jupyter command not found"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def generate_dashboard(self) -> str:
        """검증 결과의 dashboard 보기를 생성합니다."""
        if not self.state["notebooks"]:
            return "No notebooks validated yet. Run validation first."

        total = len(self.state["notebooks"])
        passing = sum(1 for n in self.state["notebooks"].values() if n.get("status") == "pass")

        # 백분율 계산
        percentage = (passing / total * 100) if total > 0 else 0

        # 문제 분류
        issues_by_type = {}
        for path, data in self.state["notebooks"].items():
            for issue in data.get("issues", []):
                issue_type = issue["type"]
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append((path, issue))

        # Dashboard 구성
        dashboard = f"""
📊 Notebook Validation Dashboard
════════════════════════════════════════════

Overall: {passing}/{total} notebooks passing ({percentage:.1f}%)
"""

        # Progress bar 추가
        bar_length = 20
        filled = int(bar_length * passing / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        dashboard += f"Progress: [{bar}]\n"

        # 이력이 있으면 추세 추가
        if len(self.state["history"]) > 1:
            prev = self.state["history"][-2]
            prev_pct = (prev["passing"] / prev["total"] * 100) if prev["total"] > 0 else 0
            change = percentage - prev_pct
            trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            dashboard += f"Trend: {trend} {change:+.1f}% from last run\n"

        dashboard += "\n" + "─" * 45 + "\n"

        # 심각도별로 문제 묶기
        critical_issues = []
        error_issues = []
        warning_issues = []
        info_issues = []

        for _issue_type, notebooks in issues_by_type.items():
            for path, issue in notebooks:
                if issue["severity"] == "critical":
                    critical_issues.append((path, issue))
                elif issue["severity"] == "error":
                    error_issues.append((path, issue))
                elif issue["severity"] == "warning":
                    warning_issues.append((path, issue))
                else:
                    info_issues.append((path, issue))

        # 심각도별 표시
        if critical_issues:
            dashboard += f"\n🔴 Critical Issues ({len(critical_issues)})\n"
            dashboard += "Must fix immediately:\n"
            for path, issue in critical_issues[:5]:
                dashboard += f"  • {Path(path).name}: {issue['type'].replace('_', ' ')}\n"
            if len(critical_issues) > 5:
                dashboard += f"  ... and {len(critical_issues) - 5} more\n"

        if error_issues:
            dashboard += f"\n🟠 Errors ({len(error_issues)})\n"
            for path, issue in error_issues[:5]:
                dashboard += f"  • {Path(path).name}: {issue.get('details', issue['type'])[:50]}\n"
            if len(error_issues) > 5:
                dashboard += f"  ... and {len(error_issues) - 5} more\n"

        if warning_issues:
            dashboard += f"\n🟡 Warnings ({len(warning_issues)})\n"
            # 유형별로 경고 묶기
            warning_types = {}
            for _path, issue in warning_issues:
                wtype = issue["type"]
                if wtype not in warning_types:
                    warning_types[wtype] = 0
                warning_types[wtype] += 1

            for wtype, count in warning_types.items():
                dashboard += f"  • {wtype.replace('_', ' ').title()}: {count} notebooks\n"

        # 빠른 조치 추가
        dashboard += "\n" + "─" * 45 + "\n"
        dashboard += "Quick Actions:\n"

        if any(i[1]["type"] == "deprecated_model" for i in warning_issues):
            dashboard += "  → Run with --auto-fix to update deprecated models\n"
        if critical_issues:
            dashboard += "  → Fix critical security issues first\n"
        if not has_anthropic_credentials():
            dashboard += (
                "  → Set ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) to enable execution tests\n"
            )

        return dashboard

    def export_github_issue(self) -> str:
        """결과를 GitHub issue Markdown으로 내보냅니다."""
        if not self.state["notebooks"]:
            return "No validation results to export. Run validation first."

        total = len(self.state["notebooks"])
        passing = sum(1 for n in self.state["notebooks"].values() if n.get("status") == "pass")
        percentage = (passing / total * 100) if total > 0 else 0

        # 문제 묶기
        critical = []
        errors = []
        warnings = []

        for path, data in self.state["notebooks"].items():
            for issue in data.get("issues", []):
                if issue["severity"] == "critical":
                    critical.append((path, issue))
                elif issue["severity"] == "error":
                    errors.append((path, issue))
                elif issue["severity"] == "warning":
                    warnings.append((path, issue))

        # Markdown 구성
        markdown = f"""## 📊 Notebook Validation Report

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Status:** {passing}/{total} notebooks passing ({percentage:.1f}%)
"""

        # Progress bar 추가
        bar_length = 30
        filled = int(bar_length * passing / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        markdown += f"**Progress:** `[{bar}]`\n\n"

        # 가능한 경우 이력 차트 추가
        if len(self.state["history"]) > 1:
            markdown += "<details>\n<summary>📈 Trend (last 7 runs)</summary>\n\n```\n"
            for entry in self.state["history"][-7:]:
                pct = (entry["passing"] / entry["total"] * 100) if entry["total"] > 0 else 0
                bar_len = int(pct / 5)  # 20자에 맞춰 크기 조정
                markdown += f"{entry['date']}: {'█' * bar_len:<20} {pct:.1f}% ({entry['passing']}/{entry['total']})\n"
            markdown += "```\n\n</details>\n\n"

        # 중대한 문제
        if critical:
            markdown += f"### 🔴 Critical Issues ({len(critical)})\n"
            markdown += "**Must fix immediately** - Security risks:\n\n"

            for path, issue in critical:
                rel_path = Path(path).relative_to(".") if Path(path).is_absolute() else path
                markdown += f"- [ ] `{rel_path}`\n"
                markdown += f"  - **Issue:** {issue['type'].replace('_', ' ').title()}\n"
                markdown += f"  - **Cell:** {issue.get('cell', 'N/A')}\n"
                markdown += f"  - **Details:** {issue.get('details', 'N/A')}\n\n"

        # 오류
        if errors:
            markdown += f"### 🟠 Execution Errors ({len(errors)})\n"
            markdown += "Notebooks that fail to run:\n\n"

            error_dict = {}
            for path, issue in errors:
                rel_path = str(Path(path).relative_to(".") if Path(path).is_absolute() else path)
                if rel_path not in error_dict:
                    error_dict[rel_path] = []
                error_dict[rel_path].append(issue)

            for path, issues in list(error_dict.items())[:10]:
                markdown += f"- [ ] `{path}`\n"
                for issue in issues:
                    details = issue.get("details", "")
                    if isinstance(details, str) and len(details) > 100:
                        details = details[:100] + "..."
                    markdown += f"  - {details}\n"
                markdown += "\n"

            if len(error_dict) > 10:
                markdown += f"\n*... and {len(error_dict) - 10} more notebooks with errors*\n\n"

        # 경고
        if warnings:
            markdown += f"### 🟡 Warnings ({len(warnings)})\n"

            # 유형별로 묶기
            warning_types = {}
            for path, issue in warnings:
                wtype = issue["type"]
                if wtype not in warning_types:
                    warning_types[wtype] = []
                warning_types[wtype].append((path, issue))

            for wtype, items in warning_types.items():
                markdown += f"\n**{wtype.replace('_', ' ').title()} ({len(items)} notebooks):**\n\n"

                for path, issue in items[:5]:
                    rel_path = Path(path).relative_to(".") if Path(path).is_absolute() else path
                    markdown += f"- [ ] `{rel_path}`"

                    details = issue.get("details", {})
                    if isinstance(details, dict) and "current" in details:
                        markdown += f" - `{details['current']}` → `{details['suggested']}`"
                    markdown += "\n"

                if len(items) > 5:
                    markdown += f"  - *... and {len(items) - 5} more*\n"
                markdown += "\n"

        # 수정 명령 추가
        markdown += "### 🔧 Quick Fix Commands\n\n```bash\n"
        markdown += "# Auto-fix deprecated models\n"
        markdown += "python scripts/validate_all_notebooks.py --auto-fix\n\n"
        markdown += "# Run full validation\n"
        markdown += "python scripts/validate_all_notebooks.py --full\n\n"
        markdown += "# Generate updated report\n"
        markdown += "python scripts/validate_all_notebooks.py --export > report.md\n"
        markdown += "```\n"

        return markdown

    def run_validation(self, mode="quick", pattern="**/*.ipynb"):
        """모든 Notebook에 검증을 실행합니다."""
        notebooks = list(Path(".").glob(pattern))
        notebooks = [n for n in notebooks if ".ipynb_checkpoints" not in str(n)]

        if not notebooks:
            print(f"No notebooks found matching pattern: {pattern}")
            return

        print(f"\n🔍 Validating {len(notebooks)} notebooks in {mode} mode...")
        print("─" * 50)

        failed = []
        warned = []

        for i, notebook in enumerate(notebooks, 1):
            # 재검증이 필요한지 확인
            nb_stat = notebook.stat()
            nb_mtime = datetime.fromtimestamp(nb_stat.st_mtime).isoformat()

            stored = self.state["notebooks"].get(str(notebook), {})

            # 변경되지 않았고 전체 검증을 강제하지 않으면 건너뛰기
            if (
                stored.get("last_modified") == nb_mtime
                and mode == "quick"
                and stored.get("last_validated")
            ):
                status = stored.get("status", "unknown")
                icon = "✅" if status == "pass" else "⚠️" if status == "warning" else "❌"
                print(f"[{i:3}/{len(notebooks)}] {icon} {notebook} (cached)")
                if status == "error":
                    failed.append(notebook)
                elif status == "warning":
                    warned.append(notebook)
                continue

            # 검증
            print(f"[{i:3}/{len(notebooks)}] ", end="")
            result = self.validate_notebook(notebook, mode)

            # 결과 저장
            self.state["notebooks"][str(notebook)] = {**result, "last_modified": nb_mtime}

            # 결과 표시
            if result["status"] == "pass":
                print(f"✅ {notebook}")
            elif result["status"] == "warning":
                print(f"⚠️  {notebook}")
                warned.append(notebook)
                for issue in result["issues"][:2]:  # 처음 2개 문제 표시
                    details = issue.get("details", "")
                    if isinstance(details, dict):
                        details = str(details.get("current", details))
                    print(f"     → {issue['type']}: {str(details)[:60]}")
            else:
                print(f"❌ {notebook}")
                failed.append(notebook)
                for issue in result["issues"][:2]:
                    details = issue.get("details", "")
                    if isinstance(details, dict):
                        details = str(details.get("current", details))
                    print(f"     → {issue['type']}: {str(details)[:60]}")

            # 주기적으로 상태 저장
            if i % 10 == 0:
                self.save_state()

        self.save_state()

        # 요약
        print("\n" + "═" * 50)
        total = len(notebooks)
        passed = total - len(failed) - len(warned)
        print(f"✅ Passed: {passed}/{total}")
        if warned:
            print(f"⚠️  Warnings: {len(warned)}/{total}")
        if failed:
            print(f"❌ Failed: {len(failed)}/{total}")

        print(self.generate_dashboard())

    def run_progressive_validation(self):
        """사용자 제어에 따라 batch로 검증을 실행합니다."""
        notebooks = list(Path(".").glob("**/*.ipynb"))
        notebooks = [n for n in notebooks if ".ipynb_checkpoints" not in str(n)]

        if not notebooks:
            print("No notebooks found")
            return

        batch_size = 5
        total_batches = (len(notebooks) - 1) // batch_size + 1

        print("\n📚 Progressive Validation")
        print(f"Total: {len(notebooks)} notebooks in {total_batches} batches")
        print("─" * 50)

        for batch_num, i in enumerate(range(0, len(notebooks), batch_size), 1):
            batch = notebooks[i : i + batch_size]
            print(f"\n📦 Batch {batch_num}/{total_batches}")

            batch_failed = []
            batch_warned = []

            for notebook in batch:
                print(f"  Validating {notebook}...", end=" ")
                result = self.validate_notebook(notebook, mode="quick")
                self.state["notebooks"][str(notebook)] = result

                if result["status"] == "pass":
                    print("✅")
                elif result["status"] == "warning":
                    print("⚠️")
                    batch_warned.append(notebook)
                    for issue in result["issues"][:1]:
                        print(f"    → {issue['type']}")
                else:
                    print("❌")
                    batch_failed.append(notebook)
                    for issue in result["issues"][:1]:
                        details = issue.get("details", issue["type"])
                        if isinstance(details, dict):
                            details = str(details)
                        print(f"    → {str(details)[:50]}")

            self.save_state()

            # Batch 요약
            if batch_failed or batch_warned:
                print(
                    f"\n  Batch summary: {len(batch_failed)} failed, {len(batch_warned)} warnings"
                )

            # 계속할지 묻기
            if i + batch_size < len(notebooks):
                print("\nOptions:")
                print("  [c]ontinue to next batch")
                print("  [d]ashboard - show current stats")
                print("  [q]uit and save progress")

                choice = input("\nChoice (c/d/q): ").strip().lower()

                if choice == "d":
                    print(self.generate_dashboard())
                    input("\nPress Enter to continue...")
                elif choice == "q":
                    print("Progress saved. Run with --resume to continue.")
                    break

    def auto_fix_issues(self):
        """Deprecated model과 같은 안전한 문제를 자동 수정합니다."""
        print("\n🔧 Auto-fixing safe issues...")
        print("─" * 50)

        fixable_notebooks = []

        # 수정 가능한 문제가 있는 Notebook 검색
        for path, data in self.state["notebooks"].items():
            if not Path(path).exists():
                continue

            has_deprecated = any(i["type"] == "deprecated_model" for i in data.get("issues", []))
            if has_deprecated:
                fixable_notebooks.append(Path(path))

        if not fixable_notebooks:
            print("No auto-fixable issues found!")
            return

        print(f"Found {len(fixable_notebooks)} notebooks with deprecated models\n")

        fixed_count = 0
        for notebook_path in fixable_notebooks:
            print(f"Fixing {notebook_path}...", end=" ")
            if self.fix_deprecated_models(notebook_path):
                print("✅")
                fixed_count += 1
                # 재검증
                result = self.validate_notebook(notebook_path, mode="quick")
                self.state["notebooks"][str(notebook_path)] = result
            else:
                print("❌ (failed)")

        self.save_state()

        print(f"\n✅ Successfully fixed {fixed_count}/{len(fixable_notebooks)} notebooks")

        if fixed_count > 0:
            print("\nRe-run validation to verify all issues are resolved.")

    def fix_deprecated_models(self, notebook_path: Path) -> bool:
        """Notebook의 deprecated model을 수정합니다."""
        try:
            with open(notebook_path) as f:
                nb = json.load(f)

            replacements = {
                "claude-3-5-sonnet-20240620": "claude-sonnet-5",
                "claude-3-5-sonnet-20241022": "claude-sonnet-5",
                "claude-3-5-sonnet-latest": "claude-sonnet-5",
                "claude-3-haiku-20240307": "claude-haiku-4-5",
                "claude-3-5-haiku-20241022": "claude-haiku-4-5",
                "claude-3-opus-20240229": "claude-opus-4-8",
                "claude-3-opus-latest": "claude-opus-4-8",
                "claude-sonnet-4-20250514": "claude-sonnet-5",
                "claude-opus-4-20250514": "claude-opus-4-8",
                "claude-opus-4-1": "claude-opus-4-8",
                "claude-sonnet-4-5-20250929": "claude-sonnet-5",
                "claude-sonnet-4-5": "claude-sonnet-5",
                "claude-opus-4-5-20251101": "claude-opus-4-8",
                "claude-opus-4-5": "claude-opus-4-8",
            }

            modified = False
            for cell in nb.get("cells", []):
                if cell.get("cell_type") == "code":
                    source = cell.get("source", [])
                    new_source = []

                    for line in source:
                        new_line = line
                        for old, new in replacements.items():
                            if old in line:
                                new_line = new_line.replace(old, new)
                                modified = True
                        new_source.append(new_line)

                    if modified:
                        cell["source"] = new_source

            if modified:
                # 보기 좋은 포맷으로 저장
                with open(notebook_path, "w") as f:
                    json.dump(nb, f, indent=1, ensure_ascii=False)

            return modified

        except Exception as e:
            print(f"Error: {e}")
            return False

    def interactive_menu(self):
        """주 interactive menu입니다."""
        while True:
            print("\n" + "═" * 50)
            print("📓 Notebook Validation Tool")
            print("═" * 50)
            print("1. Quick scan (structure only, cached)")
            print("2. Full validation (with execution)")
            print("3. Progressive validation (interactive)")
            print("4. Show dashboard")
            print("5. Export GitHub issue")
            print("6. Auto-fix deprecated models")
            print("7. Validate specific directory")
            print("8. Clear cache and re-validate")
            print("9. Exit")
            print("─" * 50)

            choice = input("Select option (1-9): ").strip()

            if choice == "1":
                self.run_validation(mode="quick")
            elif choice == "2":
                if not has_anthropic_credentials():
                    print("\n" + NO_CREDS_WARNING)
                    cont = input("Continue anyway? (y/n): ")
                    if cont.lower() != "y":
                        continue
                self.run_validation(mode="full")
            elif choice == "3":
                self.run_progressive_validation()
            elif choice == "4":
                print(self.generate_dashboard())
            elif choice == "5":
                print("\n" + self.export_github_issue())
                save = input("\nSave to file? (y/n): ")
                if save.lower() == "y":
                    filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
                    with open(filename, "w") as f:
                        f.write(self.export_github_issue())
                    print(f"✅ Saved to {filename}")
            elif choice == "6":
                self.auto_fix_issues()
            elif choice == "7":
                directory = input("Enter directory path (e.g., skills/): ").strip()
                pattern = (
                    f"{directory}**/*.ipynb"
                    if directory.endswith("/")
                    else f"{directory}/**/*.ipynb"
                )
                self.run_validation(mode="quick", pattern=pattern)
            elif choice == "8":
                self.state = {
                    "version": "1.0",
                    "last_full_run": None,
                    "notebooks": {},
                    "history": self.state.get("history", []),
                    "ignored": {},
                }
                print("Cache cleared!")
                self.run_validation(mode="quick")
            elif choice == "9":
                print("👋 Goodbye!")
                break
            else:
                print("Invalid option. Please try again.")


def main():
    """주 entry point입니다."""
    parser = argparse.ArgumentParser(
        description="Validate Jupyter notebooks for common issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Interactive mode
  %(prog)s --quick           # Quick validation (cached)
  %(prog)s --full            # Full validation with execution
  %(prog)s --auto-fix        # Fix deprecated models
  %(prog)s --export          # Export GitHub issue markdown
  %(prog)s --dashboard       # Show validation dashboard
        """,
    )

    parser.add_argument(
        "--quick", action="store_true", help="Run quick validation (structure only)"
    )
    parser.add_argument("--full", action="store_true", help="Run full validation (with execution)")
    parser.add_argument("--dashboard", action="store_true", help="Show validation dashboard")
    parser.add_argument(
        "--export", action="store_true", help="Export results as GitHub issue markdown"
    )
    parser.add_argument("--auto-fix", action="store_true", help="Auto-fix deprecated models")
    parser.add_argument("--dir", metavar="PATH", help="Validate specific directory")

    args = parser.parse_args()

    validator = NotebookValidator()

    # 명령줄 인수 처리
    if args.quick:
        validator.run_validation(mode="quick")
    elif args.full:
        if not has_anthropic_credentials():
            print(NO_CREDS_WARNING)
        validator.run_validation(mode="full")
    elif args.dashboard:
        print(validator.generate_dashboard())
    elif args.export:
        print(validator.export_github_issue())
    elif args.auto_fix:
        validator.auto_fix_issues()
    elif args.dir:
        pattern = (
            f"{args.dir}/**/*.ipynb" if not args.dir.endswith("/") else f"{args.dir}**/*.ipynb"
        )
        validator.run_validation(mode="quick", pattern=pattern)
    else:
        # Interactive mode
        validator.interactive_menu()


if __name__ == "__main__":
    main()
