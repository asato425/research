# explanation_generator.py
from research.workflow_graph.state import WorkflowState
from typing import Any
from research.log_output.log import log
import time
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
        
        # 開始時間の記録
        start_time = time.time()
        
        if state.run_explanation_generator:
            result = "テスト用、まだ実装されていません"
            # 実際の解説文生成処理
            
            # 解説文をファイル形式にしてリポジトリに保存orプルリクのコメントに追加するなどの処理もここで行う

            # 最後にコミットプッシュなどをして、リポジトリを削除する
        else:
            log("info", "Explanation Generatorはスキップされました")
            result = ""
            
        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"ExplanationGenerator実行時間: {elapsed:.2f}秒")
        return {
            "generate_explanation": result,
            "prev_node": "explanation_generator",
            "node_history": ["explanation_generator"]
        }
