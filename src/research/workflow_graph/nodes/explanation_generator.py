# explanation_generator.py
from research.workflow_graph.state import WorkflowState
from typing import Any
from research.log_output.log import log
"""
このモジュールは説明文の生成を担当します。
"""

class ExplanationGenerator:
    """説明文の生成を担当するクラス"""

    def __init__(self, model_name: str = "gemini", agent_is : bool = False):
        self.model_name = model_name
        self.agent_is = agent_is
        
    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        """解説文を生成するメソッド"""
        
        if not state.run_explanation_generator:
            log("info", "Explanation Generatorはスキップされました")
            return {
                "generate_explanation": None,
                "prev_node": "explanation_generator",
                "node_history": ["explanation_generator"]
            }

        # 実際の解説文生成処理
        
        # 解説文をファイル形式にしてリポジトリに保存orプルリクのコメントに追加するなどの処理もここで行う

        # 最後にコミットプッシュなどをして、リポジトリを削除する

        result = "テスト用、まだ実装されていません"
        return {
            "generate_explanation": result,
            "prev_node": "explanation_generator",
            "node_history": ["explanation_generator"]
        }
