from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from research.log_output.log import log
from research.tools.llm import LLMTool
from research.tools.github import WorkflowResult
from research.tools.linter import LintResult

class ParseResult(BaseModel):
    parse_details: str | None = Field(None, description="パースの詳細")


class ParserTool:
    def __init__(self, model_name: str = "gemini"):
        """
        Returns:
            None
        """
        self.llm = LLMTool().create_model(
            model_name=model_name, 
            output_model=ParseResult
        )

    def workflow_log_parse(self, workflow_result: WorkflowResult) -> ParseResult:

        """
		WorkflowResult型の変数をLLMプロンプト用に整形し、
		エラー内容をわかりやすく辞書形式で返す。

		Returns:
			ParseResult: parse_details(str|None)
		"""
		
        status = workflow_result.status
        conclusion = workflow_result.conclusion
        message = workflow_result.message
        failure_reason = workflow_result.failure_reason

        parse_details = None

        if conclusion is None:
            parse_details = f"ワークフロー結果が存在しません。{message or ''}"
        elif conclusion == "success":
            parse_details = f"ワークフロー結果は成功したためエラーはありませんでした。{message or ''}"
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
            chain = prompt | self.llm

            log(conclusion, f"ワークフロー実行ログパーサー結果: {parse_details}")
            return chain.invoke(
                {
                    "status": status,
                    "conclusion": conclusion,
                    "message": message,
                    "failure_reason": failure_reason,
                }
            )

        log(conclusion, f"ワークフロー実行ログパーサー結果: {parse_details or 'No parse details'}")

        return ParseResult(
            parse_details=parse_details
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

        parse_details = None

        if status is None:
            parse_details = f"Lint未実行または対象ディレクトリが存在しません。{error_message or ''}"
        elif status == "linter_error":
            parse_details = f"Linter自体の実行に失敗しました。エラーメッセージ: {error_message or ''}"
        elif status == "success":
            parse_details = "問題は検出されませんでした。"
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

            chain = llm_prompt | self.llm
            result = chain.invoke({
                "local_path": local_path,
                "status": status,
                "error_message": error_message,
                "raw_output": raw_output
            })
            log("info", f"Lintパーサー結果: {result.parse_details}")
            return result

        log("info", f"Lintパーサー結果: {parse_details or 'No parse details'}")
        return ParseResult(
            parse_details=parse_details,
        )

    def repo_info_parse(self) -> ParseResult:
        """
        Repository情報をパースして返す。

        Returns:
            ParseResult: パース結果
        """
        # ここにリポジトリ情報のパース処理を実装
        return ParseResult(
            parse_details=None
        )