from pydantic import BaseModel, Field
import operator
from typing import Annotated, Optional


"""
ワークフロー全体の状態（State）を管理するためのPydanticモデル。
LangGraphのグラフ構築時に各ノード間で受け渡すデータ構造として利用。
"""

class GenerateWorkflow(BaseModel):
    """
    ワークフロー生成のためのPydanticモデル。
    """
    status: str = Field(..., description="ワークフローの生成結果の状態、生成に成功したらsuccess、失敗したらfail")
    file_name: Optional[str] = Field(None, description="生成されたファイルの名前")
    generated_text: Optional[str] = Field(None, description="生成されたテキスト")
    tokens_used: Optional[int] = Field(None, description="使用されたトークン数")


class LintResult(BaseModel):
    """
    Lint結果を表すPydanticモデル。
    Lint結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="Lint結果の状態")
    raw_error: Optional[str] = Field(None, description="Lintエラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str] = Field(None, description="LLM等で要約したLintエラー")

class WorkflowRunResult(BaseModel):
    """
    ワークフローの実行結果を表すPydanticモデル。
    実行結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="ワークフロー実行結果の状態")
    raw_error: Optional[str] = Field(None, description="ワークフロー実行エラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str] = Field(None, description="LLM等で要約したワークフロー実行エラー")


class WorkflowState(BaseModel):
    """
    ワークフローの進行状況や各ノード間で共有する情報を保持するPydanticモデル。
    必要に応じて属性を追加・修正してください。
    """
    loop_count: int = Field(0, description="ワークフローのループ回数")

    repo_url: str = Field(..., description="リポジトリのURL")
    local_path: Optional[str] = Field(None, description="リポジトリのクローン先のローカルパス")   
    repo_info: dict = Field(None, description="リポジトリ情報")
    language: Optional[str] = Field(None, description="対象のプロジェクトに使用されている主要プログラミング言語")
    best_practice_num: int = Field(10, description="言語固有のベストプラクティスの数")

    generate_workflows: Annotated[list[GenerateWorkflow], operator.add] = Field(
        default_factory=list, description="生成ワークフローのリスト"
    )

    lint_results: Annotated[list[LintResult], operator.add] = Field(
        default_factory=list, description="Lint結果のリスト"
    )

    workflow_run_results: Annotated[list[WorkflowRunResult], operator.add] = Field(
        default_factory=list, description="ワークフロー実行結果のリスト"
    )