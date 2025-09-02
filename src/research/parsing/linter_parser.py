from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from ..tools.llm import llm
from ..tools.linter import LintResult
from ..log_output.log import log

class LintParseResult(BaseModel):
    error_details: str | None = Field(None, description="エラーの詳細")

def lintresult_parser(lint_result: LintResult, llm: llm = llm("gemini"), log_is: bool = True) -> LintParseResult:
	"""
	LintResult型の変数をLLMプロンプト用に整形し、
	エラー内容と修正案をわかりやすく辞書形式で返す。
	"""
	local_path = lint_result.local_path
	status = lint_result.status
	error_message = lint_result.error_message
	raw_output = lint_result.raw_output

	error_details = None

	if status is None:
		error_details = f"Lint未実行または対象ディレクトリが存在しません。{error_message or ''}"
	elif status == "linter_error":
		error_details = f"Linter自体の実行に失敗しました。エラーメッセージ: {error_message or ''}"
	elif status == "success":
		error_details = "Lint結果: 問題は検出されませんでした。"
	else:
		# failの場合
		llm_prompt = ChatPromptTemplate.from_messages(
			[
				(
					"system",
					"あなたは日本のソフトウェア開発の専門家です。",
				),
				(
					"human",
					"以下はGitHub Actionsのlint結果です。エラーがあればその内容を分かりやすく要約してください。\n"
					"local_path: {local_path}\n"
					"status: {status}\n"
					"error_message: {error_message}\n"
					"raw_output: {raw_output}\n"
				)
			]
		)

		chain = llm_prompt | llm.with_structured_output(LintParseResult)
		result = chain.invoke({
			"local_path": local_path,
			"status": status,
			"error_message": error_message,
			"raw_output": raw_output
		})
		log("info", f"Lintパーサー結果: {result.error_details}", log_is)
		return result

	log("info", f"Lintパーサー結果: {error_details or 'No error details'}", log_is)
	return LintParseResult(
		error_details=error_details,
	)