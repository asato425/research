from ..tools.github import WorkflowResult
from pydantic import BaseModel
from ..tools.llm import llm

class WorkflowLogParseResult(BaseModel):
    status: str
    message: str
    error_details_yml: str | None = None
    fix_suggestion_yml: str | None = None
    error_details_other: str | None = None
    fix_suggestion_other: str | None = None

def workflow_log_parser(workflow_result: WorkflowResult, llm: llm = llm("gemini")) -> WorkflowLogParseResult:
	"""
	WorkflowResult型の変数をLLMプロンプト用に整形し、
	エラー内容と修正案をわかりやすく辞書形式で返す。
	"""

	status = workflow_result.conclusion
	message = workflow_result.message
	failure_reason = workflow_result.failure_reason

	if status is None:
		return WorkflowLogParseResult(
			status="not_found",
			message = f"ワークフロー結果が存在しません。{message or ''}",
			error_details_yml=None,
			fix_suggestion_yml=None,
			error_details_other=None,
			fix_suggestion_other=None
		)
	elif status == "success":
		return WorkflowLogParseResult(
			status="success",
			message=f"ワークフロー結果は成功しました。{message or ''}",
			error_details_yml=None,
			fix_suggestion_yml=None,
			error_details_other=None,
			fix_suggestion_other=None
		)
	else:
		# failの場合
		llm_prompt = (
			"以下はGitHub Actionsのワークフロー実行結果です。"\
			"エラー内容をymlファイル（.github/workflows/配下や拡張子がyml/yaml）に起因するものと、それ以外に分類してください。"\
			"statusはymlファイルを修正する必要のあるエラーがあれば'fail'、ymlファイルを修正する必要がなければ'success'としてください。"\
			"それぞれについて、エラー内容（日本語で要約）と修正案（日本語で具体的に）を出力してください。修正案はymlファイルを修正する内容にしてください"\
			"messageにはエラーの内容を簡潔にまとめてください。"\
			f"\n---\nワークフロー実行結果: {status}\nメッセージ: {message}\n失敗理由: {failure_reason}\n"
		)
		result = llm.with_structured_output(WorkflowLogParseResult).invoke(llm_prompt)

		if result.error_details_yml is None:
			result.status = "success"

		return result