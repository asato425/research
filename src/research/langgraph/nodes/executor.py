# executor.py
from ....research.tools.github import GitHubTool
"""
このモジュールはワークフローの実行を担当します。
"""


class WorkflowExecutor:
    """ワークフローの実行を担当するクラス"""

    def __call__(self, workflow):
        """ワークフローを実行するメソッドの例"""
        github = GitHubTool()
        result = github.run_workflow(workflow)
        return result
