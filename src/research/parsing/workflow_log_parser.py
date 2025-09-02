from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from ..tools.llm import llm
from ..tools.github import WorkflowResult
from ..log_output.log import log

class WorkflowLogParseResult(BaseModel):
    error_details: str | None = Field(None, description="エラーの詳細")

def workflow_log_parser(workflow_result: WorkflowResult, llm: llm = llm("gemini"), log_is: bool = True) -> WorkflowLogParseResult:
	"""
	WorkflowResult型の変数をLLMプロンプト用に整形し、
	エラー内容をわかりやすく辞書形式で返す。
	"""
	status = workflow_result.status
	conclusion = workflow_result.conclusion
	message = workflow_result.message
	failure_reason = workflow_result.failure_reason

	error_details = None

	if conclusion is None:
		error_details = f"ワークフロー結果が存在しません。{message or ''}"
	elif conclusion == "success":
		error_details = f"ワークフロー結果は成功したためエラーはありませんでした。{message or ''}"
	else:
		# failの場合
		prompt = ChatPromptTemplate.from_messages(
			[
				(
					"system",
					"あなたは日本のソフトウェア開発の専門家です。GitHub Actionsワークフローの実行結果を解析し、エラーの詳細や修正案をすべて日本語でわかりやすく要約・提案してください。エラー詳細（error_details_yml, error_details_other）も必ず日本語で要約してください。",
				),
				(
					"human",
					"以下のGitHub Actionsのワークフロー実行結果に基づいてエラーがあればそのエラーの詳細と修正案を考えてください。\n"
					"ワークフローの実行状態: {status}\n"
					"ワークフローの実行結果: {conclusion}\n"
					"ワークフロー実行結果の内容: {message}\n"
					"ワークフロー実行の失敗理由: {failure_reason}\n"
				)
			]
		)
		chain = prompt | llm.with_structured_output(WorkflowLogParseResult)

		log(conclusion, f"ワークフロー実行ログパーサー結果: {error_details}", log_is)
		return chain.invoke(
			{
				"status": status,
				"conclusion": conclusion,
				"message": message,
				"failure_reason": failure_reason,
			}
		)

	log(conclusion, f"ワークフロー実行ログパーサー結果: {error_details or 'No error details'}", log_is)

	return WorkflowLogParseResult(
		error_details=error_details
	)