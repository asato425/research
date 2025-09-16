# explanation_generator.py
from ..state import WorkflowState
"""
このモジュールは説明文の生成を担当します。
"""


class ExplanationGenerator:
    """説明文の生成を担当するクラス"""

    def __call__(self, state: WorkflowState):
        """解説文を生成するメソッド"""
        result = None
        return {
            "generate_explanation": result,
            "prev_node": "explanation_generator"
        }
