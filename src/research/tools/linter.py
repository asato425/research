from pydantic import BaseModel
from typing import Any
import subprocess
import os
import json
from ..log_output.log import log

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
    def __init__(self, log_is: bool = True):
        """
        Returns:
            None
        """
        self.log_is = log_is

    def actionlint(self, local_path: str) -> LintResult:
        """
        Returns:
            LintResult: local_path(str|None), raw_output(Any), status(str|None), error_message(str|None)
        """
        if not os.path.exists(local_path):
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status=None,
                error_message="Directory not found."
            )
            log(result.status, f"actionlint: {result.error_message}", self.log_is)
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
            else:
                status = "success" if not parsed else "fail"
            result = LintResult(
                local_path=local_path,
                raw_output=parsed,
                status=status,
                error_message=None if status != "linter_error" else proc.stderr.strip()
            )
            log(result.status, f"actionlint: {result.error_message}", self.log_is)
            return result
        except Exception as e:
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status="linter_error",
                error_message=str(e)
            )
            log(result.status, f"actionlint: {result.error_message}", self.log_is)
            return result


    def ghalint(self, local_path: str) -> LintResult:
        """
        ghalintの出力をそのままprintし、返り値はLintResult（raw_outputのみセット）
        status: None=未実行, success=エラーなし, fail=lintエラー, linter_error=コマンド実行失敗

        Returns:
            LintResult: local_path(str|None), raw_output(Any), status(str|None), error_message(str|None)
        """
        if not os.path.exists(local_path):
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status=None,
                error_message="Directory not found."
            )
            log(result.status, f"ghalint: {result.error_message}", self.log_is)
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
            log(result.status, f"ghalint: {result.error_message}", self.log_is)
            return result
        except Exception as e:
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status="linter_error",
                error_message=str(e)
            )
            log(result.status, f"ghalint: {result.error_message}", self.log_is)
            return result

