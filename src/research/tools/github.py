
"""
GitHub APIクライアント側のラッパーやAPI呼び出し用関数を実装するモジュール。
"""

import requests
import subprocess
import atexit
import time
import os
import shutil
from pydantic import BaseModel
from ..log_output.log import log

class RepoOpResult(BaseModel):
    status: str
    message: str
    path: str | None = None

class RepoInfoResult(BaseModel):
    status: str
    info: dict | None = None
    message: str | None = None

class ForkResult(BaseModel):
    status: str
    message: str
    fork_url: str | None = None

class PushResult(BaseModel):
    status: str
    message: str
    commit_sha: str | None = None

class WorkflowResult(BaseModel):
    status: str
    message: str
    conclusion: str | None = None
    html_url: str | None = None
    logs_url: str | None = None
    failure_reason: str | None = None

class CloneResult(BaseModel):
    status: str
    message: str
    local_path: str | None = None
    repo_url: str | None = None

class WorkflowDispatchResult(BaseModel):
    status: str
    message: str | None = None

class GitHubTool:
    _server_process = None

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._start_github_api_server()
        atexit.register(self._stop_github_api_server)

    def _start_github_api_server(self) -> None:
        if GitHubTool._server_process is not None:
            return
        GitHubTool._server_process = subprocess.Popen([
            "uvicorn", "research.server.github_api:app", "--host", "127.0.0.1", "--port", "8000"
        ])
        # サーバーの起動確認
        for _ in range(20):
            try:
                import requests
                resp = requests.get(f"{self.base_url}/docs")
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            log("error", "github_apiサーバーの起動に失敗しました")

    def _stop_github_api_server(self) -> None:
        if GitHubTool._server_process is not None:
            GitHubTool._server_process.terminate()
            GitHubTool._server_process.wait()
            GitHubTool._server_process = None

    def fork_repository(self, repo_url: str) -> ForkResult:
        """
        Returns:
            ForkResult: status(str), message(str), fork_url(str|None)
        """
        resp = requests.post(f"{self.base_url}/github/fork", json={"repo_url": repo_url})
        result = ForkResult(**resp.json())
        log(result.status, result.message)
        return result

    def get_repository_info(self, repo_url: str) -> RepoInfoResult:
        """
        Returns:
            RepoInfoResult: status(str), info(dict|None), message(str|None)
        """
        resp = requests.get(f"{self.base_url}/github/info", params={"repo_url": repo_url})
        result = RepoInfoResult(**resp.json())
        log(result.status, result.message)
        return result

    def clone_repository(self, repo_url: str, local_path: str = None) -> CloneResult:
        """
        Returns:
            CloneResult: status(str), message(str), local_path(str|None), repo_url(str|None)
        """
        if local_path is None:
            repo_name = repo_url.rstrip('/').split('/')[-1]
            base_dir = os.path.expanduser('~/Desktop/research_clones')
            os.makedirs(base_dir, exist_ok=True)
            local_path = os.path.join(base_dir, repo_name)
        if os.path.exists(local_path):
            result = CloneResult(status="success", message=f"{local_path} は既に存在します。", local_path=local_path, repo_url=repo_url)
            log(result.status, result.message)
            return result
        try:
            subprocess.run(["git", "clone", repo_url, local_path], check=True)
            result = CloneResult(status="success", message=f"{local_path}のクローンに成功しました", local_path=local_path, repo_url=repo_url)
        except subprocess.CalledProcessError as e:
            result = CloneResult(status="error", message=str(e), local_path=local_path, repo_url=repo_url)
        except Exception as e:
            result = CloneResult(status="error", message=str(e), local_path=local_path, repo_url=repo_url)

        log(result.status, result.message)
        return result

    def commit_and_push(self, local_path: str, message: str) -> PushResult:
        """
        Returns:
            PushResult: status(str), message(str), commit_sha(str|None)
        """
        # add/commit
        try:
            subprocess.run(["git", "add", "."], cwd=local_path, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=local_path, check=True)
            log("info", f"{local_path}をコミットに成功しました。")
        except subprocess.CalledProcessError as e:
            result = PushResult(status="error", message=f"コミットエラー: {str(e)}", commit_sha=None)
            log(result.status, result.message)
            return result

        # 現在のブランチ名を取得
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=local_path, check=True, capture_output=True)
            branch = res.stdout.decode().strip()
        except Exception as e:
            result = PushResult(status="error", message=f"branch check error: {str(e)}", commit_sha=None)
            log(result.status, result.message)
            return result

        # push（upstream未設定なら-u付きで再push）
        try:
            subprocess.run(["git", "push"], cwd=local_path, check=True)
            log("info", f"{branch}のプッシュに成功しました。")
        except subprocess.CalledProcessError:
            try:
                subprocess.run(["git", "push", "-u", "origin", branch], cwd=local_path, check=True)
            except subprocess.CalledProcessError as e:
                result = PushResult(status="error", message=f"push error: {str(e)}", commit_sha=None)
                log(result.status, result.message)
                return result

        # コミットハッシュ取得
        try:
            commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=local_path, check=True, capture_output=True).stdout.decode().strip()
            log("info", f"コミットハッシュの取得に成功しました。最新のコミットSHA: {commit_sha}")
        except Exception:
            commit_sha = None
        result = PushResult(status="success", message=f"{branch}にコミットとプッシュをしました", commit_sha=commit_sha)
        log(result.status, result.message)
        return result

    def dispatch_workflow(self, repo_url: str, ref: str, workflow_id: str) -> WorkflowDispatchResult:
        """
        指定したワークフローをworkflow_dispatchで手動実行する。
        Args:
            repo_url (str): リポジトリURL
            ref (str): 実行したいブランチ名（例: main）
            file_name (str): ワークフローのファイル名（例: ci.yml）
        Returns:
            WorkflowDispatchResult: status(str), message(str)
        """
        payload = {"repo_url": repo_url, "ref": ref, "workflow_id": workflow_id}
        resp = requests.post(f"{self.base_url}/workflow/dispatch", json=payload)
        result = WorkflowDispatchResult(**resp.json())
        log(result.status, result.message)
        return result
    
    def get_latest_workflow_logs(self, repo_url: str, commit_sha: str) -> WorkflowResult:
        """
        Returns:
            WorkflowResult: status(str), message(str), conclusion(str|None), html_url(str|None), logs_url(str|None), failure_reason(str|None)
        """
        payload = {"repo_url": repo_url, "commit_sha": commit_sha}
        resp = requests.post(f"{self.base_url}/workflow/latest", json=payload)
        result = WorkflowResult(**resp.json())
        log(result.status, result.message)
        return result

    def create_working_branch(self, local_path: str, branch_name: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        dev_repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
        local_path_abs = os.path.abspath(local_path) if local_path else None
        if not local_path_abs:
            result = RepoInfoResult(status="error", info=None, message="cloneに失敗しているため作業用ブランチを作成できません。")
            log(result.status, result.message)
            return result
        if local_path_abs == dev_repo_path:
            result = RepoInfoResult(status="error", info=None, message="開発リポジトリ自身では作業用ブランチを作成できません。cloneしたリポジトリで実行してください。")
            log(result.status, result.message)
            return result
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=local_path, check=True)
            result = RepoInfoResult(status="success", info=None, message=f"{branch_name}を作成しました")
        except subprocess.CalledProcessError as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))

        log(result.status, result.message)
        return result

    def create_file(self, local_path: str, relative_path: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        file_path = os.path.join(local_path, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            result = RepoInfoResult(status="success", info=None, message=f"{file_path} は既に存在します。")
            log(result.status, result.message)
            return result
        try:
            with open(file_path, "w"):
                pass
            result = RepoInfoResult(status="success", info=None, message=f"{file_path}を作成しました")
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))

        log(result.status, result.message)
        return result

    def write_to_file(self, local_path: str, relative_path: str, content: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        file_path = os.path.join(local_path, relative_path)
        try:
            with open(file_path, "w") as f:
                f.write(content or "")
            result = RepoInfoResult(status="success", info=None, message=f"{file_path}に書き込みました")
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))

        log(result.status, result.message)
        return result

    def delete_file(self, local_path: str, relative_path: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        file_path = os.path.join(local_path, relative_path)
        if not os.path.exists(file_path):
            result = RepoInfoResult(status="not_found", info=None, message=f"{file_path} は存在しません。")
            return result
        try:
            os.remove(file_path)
            result = RepoInfoResult(status="success", info=None, message=f"{file_path}を削除しました")
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))

        log(result.status, result.message)
        return result

    def delete_cloned_repository(self, local_path: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        if not local_path:
            result = RepoOpResult(status="error", message="local_pathが未設定です。clone後に実行してください。", path=None)
            log(result.status, result.message)
            return result
        elif not os.path.exists(local_path):
            result = RepoOpResult(status="not_found", message=f"{local_path} は存在しません。", path=None)
            log(result.status, result.message)
            return result
        try:
            shutil.rmtree(local_path)
            result = RepoOpResult(status="success", message=f"{local_path}を削除しました", path=None)
            log(result.status, result.message)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e), path=None)
            log(result.status, result.message)
            return result

    def read_file(self, local_path: str, relative_path: str) -> RepoOpResult:
        """
        Returns:
            RepoInfoResult: status(str), info(dict|None), message(str)
        """
        file_path = os.path.join(local_path, relative_path)
        if not os.path.exists(file_path):
            result = RepoInfoResult(status="not_found", info=None, message=f"{file_path} は存在しないため読み込めません。")
            log(result.status, result.message)
            return result
        try:
            with open(file_path, "r") as f:
                content = f.read()
            info = {"file_path": file_path, "content": content}
            result = RepoInfoResult(status="success", info=info, message=f"{file_path}を読み込みました")
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))
        log(result.status, result.message)
        return result

    def get_file_tree(self, local_path: str) -> RepoInfoResult:
        """
        Returns:
            RepoInfoResult: status(str), info(dict|None), message(str)
        """
        if not os.path.exists(local_path):
            result = RepoInfoResult(status="not_found", info=None, message=f"{local_path} は存在しません。")
            log(result.status, result.message)
            return result
        try:
            file_tree = {}
            for root, dirs, files in os.walk(local_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    file_tree[file_path] = {"size": os.path.getsize(file_path), "modified": os.path.getmtime(file_path)}
            result = RepoInfoResult(status="success", info=file_tree, message=f"{local_path}のファイルツリーを取得しました")
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))
        log(result.status, result.message)
        return result