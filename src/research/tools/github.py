"""
GitHub APIクライアント側のラッパーやAPI呼び出し用関数を実装するモジュール。
"""
from pydantic import BaseModel
import requests
import subprocess
import atexit
import time
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


class GitHubTool:
    _server_process = None

    def __init__(self, base_url: str = "http://localhost:8000", log_is: bool = True):
        self.base_url = base_url
        self.log_is = log_is
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
        log(result.status, result.message, self.log_is)
        return result

    def get_repository_info(self, repo_url: str) -> RepoInfoResult:
        """
        Returns:
            RepoInfoResult: status(str), info(dict|None), message(str|None)
        """
        resp = requests.get(f"{self.base_url}/github/info", params={"repo_url": repo_url})
        result = RepoInfoResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def clone_repository(self, repo_url: str, local_path: str = None) -> CloneResult:
        """
        Returns:
            CloneResult: status(str), message(str), local_path(str|None), repo_url(str|None)
        """
        payload = {"repo_url": repo_url}
        if local_path:
            payload["local_path"] = local_path
        resp = requests.post(f"{self.base_url}/github/clone", json=payload)
        result = CloneResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def commit_and_push(self, local_path: str, message: str) -> PushResult:
        """
        Returns:
            PushResult: status(str), message(str), commit_sha(str|None)
        """
        payload = {"repo_path": local_path, "message": message}
        resp = requests.post(f"{self.base_url}/github/push", json=payload)
        result = PushResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def get_latest_workflow_logs(self, repo_url: str, commit_sha: str) -> WorkflowResult:
        """
        Returns:
            WorkflowResult: status(str), message(str), conclusion(str|None), html_url(str|None), logs_url(str|None), failure_reason(str|None)
        """
        payload = {"repo_url": repo_url, "commit_sha": commit_sha}
        resp = requests.post(f"{self.base_url}/workflow/latest", json=payload)
        result = WorkflowResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def create_working_branch(self, local_path: str, branch_name: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        payload = {"repo_path": local_path, "branch_name": branch_name}
        resp = requests.post(f"{self.base_url}/github/create-branch", json=payload)
        result = RepoOpResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def create_empty_file(self, local_path: str, filename: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        payload = {"repo_path": local_path, "filename": filename}
        resp = requests.post(f"{self.base_url}/github/create-empty-file", json=payload)
        result = RepoOpResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def create_yml_file(self, local_path: str, filename: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        payload = {"repo_path": local_path, "filename": filename}
        resp = requests.post(f"{self.base_url}/github/create-yml-file", json=payload)
        result = RepoOpResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def write_to_yml_file(self, local_path: str, filename: str, content: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        payload = {"repo_path": local_path, "filename": filename, "content": content}
        resp = requests.post(f"{self.base_url}/github/write-yml-file", json=payload)
        result = RepoOpResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def delete_yml_file(self, local_path: str, filename: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        payload = {"repo_path": local_path, "filename": filename}
        resp = requests.post(f"{self.base_url}/github/delete-yml-file", json=payload)
        result = RepoOpResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result

    def delete_cloned_repository(self, local_path: str) -> RepoOpResult:
        """
        Returns:
            RepoOpResult: status(str), message(str), path(str|None)
        """
        payload = {"repo_path": local_path}
        resp = requests.post(f"{self.base_url}/github/delete-repo", json=payload)
        result = RepoOpResult(**resp.json())
        log(result.status, result.message, self.log_is)
        return result
