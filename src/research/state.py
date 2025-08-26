from pydantic import BaseModel, Field
from typing import Any, Optional

"""
ワークフロー全体の状態（State）を管理するためのPydanticモデル。
LangGraphのグラフ構築時に各ノード間で受け渡すデータ構造として利用。
"""

class WorkflowState(BaseModel):
    """
    ワークフローの進行状況や各ノード間で共有する情報を保持するPydanticモデル。
    必要に応じて属性を追加・修正してください。
    """
    parse_result: Optional[Any] = Field(default=None, description="パーサーの出力結果")
    workflow: Optional[Any] = Field(default=None, description="ワークフロー情報")
    lint_result: Optional[Any] = Field(default=None, description="linterの出力結果")
    exec_result: Optional[Any] = Field(default=None, description="executorの出力結果")
    explanation: Optional[Any] = Field(default=None, description="説明文や生成結果")
