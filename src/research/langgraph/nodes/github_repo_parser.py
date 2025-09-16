# github_repo_parser.py
"""
このモジュールはGitHubリポジトリ情報の取得を担当します。
"""
from ....research.log_output.log import log
from ....research.tools.github import GitHubTool
from ..state import WorkflowState
from typing import Any


class GitHubRepoParser:
    """GitHubリポジトリ情報の取得を担当するクラス"""

    def __call__(self, state:WorkflowState) -> dict[str, Any]:
        """入力データをパースするメソッドの例"""
        log("info", "これからリポジトリ情報を取得します")
        github = GitHubTool()

        # リポジトリ情報の取得
        repo_info_result = github.get_repository_info(state.repo_url)
        repo_info = repo_info_result.info

        # リポジトリのクローン
        clone_result = github.clone_repository(state.repo_url)
        local_path = clone_result.local_path

        # ファイルツリーの取得
        file_tree_result = github.get_file_tree(local_path)
        
        return {
            "local_path": local_path,
            "file_tree": file_tree_result.info,
            "repo_info": repo_info,
            "language": repo_info.language,
            "prev_node": "github_repo_parser"
        }
