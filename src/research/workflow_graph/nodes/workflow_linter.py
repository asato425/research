# workflow_linter.py
from research.tools.linter import LinterTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import LintResult,WorkflowState
from research.log_output.log import log
from typing import Any
import time

"""
GitHub Actionsワークフローの構文解析や静的チェック（例: actionlint）を行うモジュール。

actionlintを行って、successになってから、pinactでSHAに変換し、ghalintを行う流れにするかも
その場合LintResultはactionlintとghalintで区別する必要はないかも？どちらを行っているかだけのフラグを用意する
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
        
        # 開始時間の記録
        start_time = time.time()

        if state.run_linter:

            linter = LinterTool()
            parser = ParserTool(model_name=self.model_name)

            local_path = state.local_path

            # actionlintによるチェック
            if state.run_actionlint:
                log("info", "actionlintによるLintを開始します")
                actionlint_result = linter.actionlint(local_path)
                parse_result = parser.lint_result_parse(actionlint_result)
                actionlint_result = LintResult(
                    status=actionlint_result.status,
                    raw_error=actionlint_result.raw_output,
                    parsed_error=parse_result
                )
            else:
                log("info", "actionlintによるLintはスキップされました")
                actionlint_result = LintResult(
                    status="success",
                    raw_error=None,
                    parsed_error=None
                )

            if state.run_ghalint:
                log("info", "ghalintによるLintを開始します")
                # ghalintによるチェック
                ghalint_result = linter.ghalint(local_path)
                parse_result = parser.lint_result_parse(ghalint_result)
                ghalint_result = LintResult(
                    status=ghalint_result.status,
                    raw_error=ghalint_result.raw_output,
                    parsed_error=parse_result
                )
            else:
                log("info", "ghalintによるLintはスキップされました")
                ghalint_result = LintResult(
                    status="success",
                    raw_error=None,
                    parsed_error=None
                )
        else:
            log("info", "WorkflowLinterはスキップされました")
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
    
        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"WorkflowLinter実行時間: {elapsed:.2f}秒")
        return {
            "actionlint_results": [actionlint_result],
            "ghalint_results": [ghalint_result],
            "prev_node": "workflow_linter",
            "node_history": ["workflow_linter"]
        }