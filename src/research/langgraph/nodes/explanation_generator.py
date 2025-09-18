# explanation_generator.py
from ..state import WorkflowState
from typing import Any
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
        result = None
        return {
            "generate_explanation": result,
            "prev_node": "explanation_generator",
            "node_history": ["explanation_generator"]
        }
