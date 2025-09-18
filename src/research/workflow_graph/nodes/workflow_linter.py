# workflow_linter.py
from research.tools.linter import LinterTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import LintResult,WorkflowState
from research.log_output.log import log
from typing import Any

"""
GitHub Actionsワークフローの構文解析や静的チェック（例: actionlint）を行うモジュール。
"""

class WorkflowLinter:
    """ワークフローのlint（構文・脆弱性チェック）を担当するクラス"""
    def __init__(self, model_name: str = "gemini"):
        self.model_name = model_name

    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        """
        指定したYAMLファイルのワークフローを構文解析し、エラーや脆弱性をチェックするメソッドの例。
        実装例: actionlint等の外部ツールを呼び出してチェックする。
        """

        if not state.run_linter:
            log("info", "Lintはスキップされました")
            actionlint_result = LintResult(
                status="success",
                raw_error=None,
                parsed_error=None
            )
            ghalint_result = LintResult(
                status="success",
                raw_error=None,
                parsed_error=None
            )
            return {
                "actionlint_results": [actionlint_result],
                "ghalint_results": [ghalint_result],
                "prev_node": "workflow_linter",
                "node_history": ["workflow_linter"]
            }

        linter = LinterTool()
        parser = ParserTool(model_name=self.model_name)

        local_path = state.local_path

        # actionlintによるチェック
        actionlint_result = linter.actionlint(local_path)
        parse_result = parser.lint_result_parse(actionlint_result)
        actionlint_result = LintResult(
            status=actionlint_result.status,
            raw_error=actionlint_result.raw_output,
            parsed_error=parse_result
        )

        # ghalintによるチェック
        ghalint_result = linter.ghalint(local_path)
        parse_result = parser.lint_result_parse(ghalint_result)
        ghalint_result = LintResult(
            status=ghalint_result.status,
            raw_error=ghalint_result.raw_output,
            parsed_error=parse_result
        )
        return {
            "actionlint_results": [actionlint_result],
            "ghalint_results": [ghalint_result],
            "prev_node": "workflow_linter",
            "node_history": ["workflow_linter"]
        }