from pydantic import BaseModel, Field
from ..log_output.log import log
from ..tools.llm import llm
from langchain_core.prompts import ChatPromptTemplate
from ..tools.github import WorkflowResult
from ..tools.linter import LintResult

class ParseResult(BaseModel):
    error_details: str | None = Field(None, description="エラーの詳細")


class ParserTool:
    def __init__(self, llm: llm = llm("gemini"), log_is: bool = True):
        """
        Returns:
            None
        """
        self.llm = llm.with_structured_output(ParseResult)
        self.log_is = log_is

    def workflow_log_parse(self, workflow_result: WorkflowResult) -> ParseResult:

        """
		WorkflowResult型の変数をLLMプロンプト用に整形し、
		エラー内容をわかりやすく辞書形式で返す。

		Returns:
			WorkflowLogParseResult: error_details(str|None)
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
                        "あなたは日本のソフトウェア開発の専門家です。",
                    ),
                    (
                        "human",
                        "以下のGitHub Actionsのワークフロー実行結果に基づいてエラーがあればそのエラーの詳細をわかりやすく教えてください。\n"
                        "ワークフローの実行状態: {status}\n"
                        "ワークフローの実行結果: {conclusion}\n"
                        "ワークフロー実行結果の内容: {message}\n"
                        "ワークフロー実行の失敗理由: {failure_reason}\n"
                    )
                ]
            )
            chain = prompt | llm

            log(conclusion, f"ワークフロー実行ログパーサー結果: {error_details}", self.log_is)
            return chain.invoke(
                {
                    "status": status,
                    "conclusion": conclusion,
                    "message": message,
                    "failure_reason": failure_reason,
                }
            )

        log(conclusion, f"ワークフロー実行ログパーサー結果: {error_details or 'No error details'}", self.log_is)

        return ParseResult(
            error_details=error_details
        )

    def lint_result_parse(self, lint_result: LintResult) -> ParseResult:

        """
        LintResult型の変数をLLMプロンプト用に整形し、
        エラー内容と修正案をわかりやすく辞書形式で返す。

        Returns:
            LintParseResult: error_details(str|None)
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

            chain = llm_prompt | llm
            result = chain.invoke({
                "local_path": local_path,
                "status": status,
                "error_message": error_message,
                "raw_output": raw_output
            })
            log("info", f"Lintパーサー結果: {result.error_details}", self.log_is)
            return result

        log("info", f"Lintパーサー結果: {error_details or 'No error details'}", self.log_is)
        return ParseResult(
            error_details=error_details,
        )

    def repo_info_parse(self) -> ParseResult:
        """
        Repository情報をパースして返す。

        Returns:
            ParseResult: パース結果
        """
        # ここにリポジトリ情報のパース処理を実装
        return ParseResult(
            error_details=None
        )