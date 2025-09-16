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
        
        repo_info_result = github.get_repository_info(state.repo_url)
        log(repo_info_result.status, repo_info_result.message)
        repo_info = repo_info_result.info
        
        clone_result = github.clone_repository(state.repo_url)
        log(clone_result.status, clone_result.message)
        
        local_path = clone_result.local_path
        
        file_tree_result = github.get_file_tree(local_path)
        log(file_tree_result.status, file_tree_result.message)
        
        return {
            "local_path": local_path,
            "file_tree": file_tree_result.info,
            "repo_info": repo_info,
            "language": repo_info.language,
            "prev_node": "github_repo_parser"
        }
