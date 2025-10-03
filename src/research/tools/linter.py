
from pydantic import BaseModel
from typing import Any
import subprocess
import os
import json
from research.log_output.log import log

class LintResult(BaseModel):
    """
    status:
        None: 未実行またはパスが存在しない
        'success': lintエラーなし
        'fail': lintエラーあり
        'linter_error': linter自体の実行失敗（コマンドエラー等）
    """
    local_path: str | None = None
    raw_output: Any = None
    status: str | None = None
    error_message: str | None = None


class LinterTool:
    def __init__(self):
        """
        LinterToolのインスタンスを初期化する。

        Returns:
            None
        """

    def actionlint(self, local_path: str) -> LintResult:
        """
        指定ディレクトリでactionlintを実行し、結果をLintResultで返す。

        Args:
            local_path (str): プロジェクトのルートディレクトリ

        Returns:
            LintResult:
                local_path (str|None): 対象ディレクトリのパス
                raw_output (Any): actionlintの生出力（JSONまたはstr）
                status (str|None): 実行結果のステータス（None=未実行, 'success'=エラーなし, 'fail'=lintエラー, 'linter_error'=コマンド失敗）
                error_message (str|None): エラーメッセージや説明
        """
        if not os.path.exists(local_path):
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status=None,
                error_message="Directory not found."
            )
            log(result.status, f"actionlint: {result.error_message}")
            return result
        try:
            proc = subprocess.run(
                ["actionlint", "-format", "{{json .}}"],
                cwd=local_path,
                capture_output=True, text=True, check=False
            )
            output = proc.stdout.strip()
            try:
                parsed = json.loads(output)
            except Exception:
                parsed = output
            # actionlintがコマンドとして失敗した場合
            if proc.returncode != 0 and not output:
                status = "linter_error"
                error_message = "Linterの実行に失敗しました。"
            else:
                status = "success" if not parsed else "fail"
                if status == "success":
                    error_message = "Lintエラーは検出されませんでした。"
                else:
                    error_message = "Lintエラーが検出されました。"
            result = LintResult(
                local_path=local_path,
                raw_output=parsed,
                status=status,
                error_message=error_message
            )
            log(result.status, f"actionlint: {result.error_message}")
            return result
        except Exception as e:
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status="linter_error",
                error_message=str(e)
            )
            log(result.status, f"actionlint: {result.error_message}")
            return result


    def ghalint(self, local_path: str) -> LintResult:
        """
        指定ディレクトリでghalintを実行し、結果をLintResultで返す。

        Args:
            local_path (str): プロジェクトのルートディレクトリ

        Returns:
            LintResult:
                local_path (str|None): 対象ディレクトリのパス
                raw_output (Any): ghalintの標準エラー出力（str）
                status (str|None): 実行結果のステータス（None=未実行, 'success'=エラーなし, 'fail'=lintエラー, 'linter_error'=コマンド失敗）
                error_message (str|None): エラーメッセージや説明
        """
        if not os.path.exists(local_path):
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status=None,
                error_message="Directory not found."
            )
            log(result.status, f"ghalint: {result.error_message}")
            return result
        try:
            proc = subprocess.run(
                ["ghalint", "run"],
                cwd=local_path,
                capture_output=True, text=True, check=False
            )
            output = proc.stderr.strip()
            # ghalintがコマンドとして失敗した場合
            if proc.returncode != 0 and not output:
                status = "linter_error"
            else:
                status = "success" if not output else "fail"
            result = LintResult(
                local_path=local_path,
                raw_output=output,
                status=status,
                error_message=None if status != "linter_error" else proc.stderr.strip()
            )
            log(result.status, f"ghalint: {result.error_message}")
            return result
        except Exception as e:
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status="linter_error",
                error_message=str(e)
            )
            log(result.status, f"ghalint: {result.error_message}")
            return result

    def pinact(self, local_path: str) -> dict:
        """
        指定ディレクトリでpinact runを実行し、結果をdictで返す。

        Args:
            local_path (str): プロジェクトのルートディレクトリ

        Returns:
            dict:
                status (str): "success"=正常終了, "error"=エラー発生
                stdout (str): 標準出力
                stderr (str): 標準エラー出力
                returncode (int): プロセスの終了コード
        """
        try:
            result = subprocess.run(
                ["pinact", "run"],
                cwd=local_path,
                capture_output=True,
                text=True,
                check=False
            )
            status = "success" if result.returncode == 0 else "error"
            
            result = {
                "status": status,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            result = {
                "status": "error",
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
        
        log(result["status"], f"pinactの結果 stdout:{result['stdout']}、stderr:{result['stderr']}")
        return result
