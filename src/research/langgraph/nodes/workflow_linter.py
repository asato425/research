# workflow_linter.py
from ....research.tools.linter import LinterTool
from ....research.tools.parser import ParserTool
from ..state import LintResult
"""
GitHub Actionsワークフローの構文解析や静的チェック（例: actionlint）を行うモジュール。
"""

class WorkflowLinter:
    """ワークフローのlint（構文・脆弱性チェック）を担当するクラス"""

    def __call__(self, local_path: str):
        """
        指定したYAMLファイルのワークフローを構文解析し、エラーや脆弱性をチェックするメソッドの例。
        実装例: actionlint等の外部ツールを呼び出してチェックする。
        """

        linter = LinterTool()
        parser = ParserTool()
        
        lint_result = linter.actionlint(local_path)
        parse_result = parser.lint_result_parse(lint_result)

        return LintResult(
            status=lint_result.status,
            raw_error=lint_result.raw_output,
            parsed_error=parse_result
        )
