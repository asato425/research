from ..tools.linter import LintResult
from pydantic import BaseModel
from ..tools.llm import llm

class LintParseResult(BaseModel):
    """
    status:
        None: 未実行またはパスが存在しない
        'success': lintエラーなし
        'fail': lintエラーあり
        'linter_error': linter自体の実行失敗（コマンドエラー等）
    """
    status: str | None = None
    local_path: str | None = None
    error_details: str | None = None
    fix_suggestion: str | None = None

def lintresult_parser(lint_result: LintResult, llm: llm = llm("gemini")) -> LintParseResult:
	"""
	LintResult型の変数をLLMプロンプト用に整形し、
	エラー内容と修正案をわかりやすく辞書形式で返す。
	"""
	local_path = lint_result.local_path
	status = lint_result.status
	error_message = lint_result.error_message
	raw_output = lint_result.raw_output

	error_details = ""
	fix_suggestion = ""

	if status is None:
		error_details = f"Lint未実行または対象ディレクトリが存在しません。{error_message or ''}"
	elif status == "linter_error":
		error_details = f"Linter自体の実行に失敗しました。エラーメッセージ: {error_message or ''}"
	elif status == "success":
		error_details = "Lint結果: 問題は検出されませんでした。"
	else:
		# failの場合
		llm_prompt = (
			"以下はGitHub Actionsのlint結果です。エラー内容を分かりやすく要約し、修正案を提案してください。\n"
			f"local_path: {local_path}\n"
			f"status: {status}\n"
			f"error_message: {error_message}\n"
			f"raw_output: {raw_output}\n"
		)

		return llm.with_structured_output(LintParseResult).invoke(llm_prompt)

	return LintParseResult(
		status=status,
		local_path=local_path,
		error_details=error_details,
		fix_suggestion=fix_suggestion
	)