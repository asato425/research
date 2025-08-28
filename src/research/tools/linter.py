from pydantic import BaseModel
from typing import Any
import subprocess
import os
import json
from typing import Optional

class LintResult(BaseModel):
    """
    status:
        None: 未実行またはパスが存在しない
        'success': lintエラーなし
        'fail': lintエラーあり
        'linter_error': linter自体の実行失敗（コマンドエラー等）
    """
    local_path: Optional[str] = None
    raw_output: Any = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class Linter:
    @staticmethod
    def actionlint(local_path: str) -> LintResult:
        if not os.path.exists(local_path):
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status=None,
                error_message="Directory not found."
            )
            print(result)
            return result
        try:
            result = subprocess.run(
                ["actionlint", "-format", "{{json .}}"],
                cwd=local_path,
                capture_output=True, text=True, check=False
            )
            output = result.stdout.strip()
            try:
                parsed = json.loads(output)
            except Exception:
                parsed = output
            # actionlintがコマンドとして失敗した場合
            if result.returncode != 0 and not output:
                status = "linter_error"
            else:
                status = "success" if not parsed else "fail"
            lint_result = LintResult(
                local_path=local_path,
                raw_output=parsed,
                status=status,
                error_message=None if status != "linter_error" else result.stderr.strip()
            )
            print(lint_result)
            return lint_result
        except Exception as e:
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status="linter_error",
                error_message=str(e)
            )
            print(result)
            return result

    @staticmethod
    def ghalint(local_path: str) -> LintResult:
        """
        ghalintの出力をそのままprintし、返り値はLintResult（raw_outputのみセット）
        status: None=未実行, success=エラーなし, fail=lintエラー, linter_error=コマンド実行失敗
        """
        if not os.path.exists(local_path):
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status=None,
                error_message="Directory not found."
            )
            print(result)
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
            print(result)
            return result
        except Exception as e:
            result = LintResult(
                local_path=local_path,
                raw_output=None,
                status="linter_error",
                error_message=str(e)
            )  
            print(result)
            return result

