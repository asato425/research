"""
GitHub APIクライアント側のラッパーやAPI呼び出し用関数を実装するモジュール。
"""
from pydantic import BaseModel
import requests
import subprocess
import atexit
import time

class RepoOpResult(BaseModel):
    status: str
    message: str
    path: str | None = None

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

class RepoInfoResult(BaseModel):
    status: str
    info: dict | None = None
    message: str | None = None

class CloneResult(BaseModel):
    status: str
    message: str
    local_path: str | None = None
    repo_url: str | None = None
    
def print_result(result):
    """
    各操作の結果（BaseModel）を色付きでSUCCESS/FAIL表示するユーティリティ関数。
    """
    status = getattr(result, 'status', None)
    message = getattr(result, 'message', None)
    path = getattr(result, 'path', None)
    extra = ''
    if hasattr(result, 'fork_url') and getattr(result, 'fork_url'):
        extra = f"\nfork_url: {result.fork_url}"
    if hasattr(result, 'commit_sha') and getattr(result, 'commit_sha'):
        extra += f"\ncommit_sha: {result.commit_sha}"
    if hasattr(result, 'info') and getattr(result, 'info'):
        extra += f"\ninfo: {result.info}"
    if hasattr(result, 'repo_url') and getattr(result, 'repo_url'):
        extra += f"\nrepo_url: {result.repo_url}"
    # 色分け
    if status == 'success' or status == 'exists' or status == 'completed':
        label = '\033[92mSUCCESS\033[0m'  # 緑
    elif status == 'not_found':
        label = '\033[93mNOT FOUND\033[0m'  # 黄
    else:
        label = '\033[91mFAIL\033[0m'     # 赤
    print(f"[{label}] {message}\npath: {path if path else ''}{extra}")
    print(f"raw_result: {result}")

class GitHubTool:
    _server_process = None

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._start_github_api_server()
        atexit.register(self._stop_github_api_server)

    def _start_github_api_server(self):
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
            print("[ERROR] github_apiサーバーの起動に失敗しました")

    def _stop_github_api_server(self):
        if GitHubTool._server_process is not None:
            GitHubTool._server_process.terminate()
            GitHubTool._server_process.wait()
            GitHubTool._server_process = None

    def fork_repository(self, repo_url: str) -> ForkResult:
        resp = requests.post(f"{self.base_url}/github/fork", json={"repo_url": repo_url})
        result = ForkResult(**resp.json())
        print_result(result)
        return result

    def get_repository_info(self, repo_url: str) -> RepoInfoResult:
        resp = requests.get(f"{self.base_url}/github/info", params={"repo_url": repo_url})
        result = RepoInfoResult(**resp.json())
        print_result(result)
        return result

    def clone_repository(self, repo_url: str, local_path: str = None) -> CloneResult:
        payload = {"repo_url": repo_url}
        if local_path:
            payload["local_path"] = local_path
        resp = requests.post(f"{self.base_url}/github/clone", json=payload)
        result = CloneResult(**resp.json())
        print_result(result)
        return result

    def commit_and_push(self, local_path: str, message: str) -> PushResult:
        payload = {"repo_path": local_path, "message": message}
        resp = requests.post(f"{self.base_url}/github/push", json=payload)
        result = PushResult(**resp.json())
        print_result(result)
        return result

    def get_latest_workflow_logs(self, repo_url: str, commit_sha: str) -> WorkflowResult:
        payload = {"repo_url": repo_url, "commit_sha": commit_sha}
        resp = requests.post(f"{self.base_url}/workflow/latest", json=payload)
        result = WorkflowResult(**resp.json())
        print_result(result)
        return result

    def create_working_branch(self, local_path: str, branch_name: str) -> RepoOpResult:
        payload = {"repo_path": local_path, "branch_name": branch_name}
        resp = requests.post(f"{self.base_url}/github/create-branch", json=payload)
        result = RepoOpResult(**resp.json())
        print_result(result)
        return result

    def create_empty_file(self, local_path: str, filename: str) -> RepoOpResult:
        payload = {"repo_path": local_path, "filename": filename}
        resp = requests.post(f"{self.base_url}/github/create-empty-file", json=payload)
        result = RepoOpResult(**resp.json())
        print_result(result)
        return result

    def create_yml_file(self, local_path: str, filename: str) -> RepoOpResult:
        payload = {"repo_path": local_path, "filename": filename}
        resp = requests.post(f"{self.base_url}/github/create-yml-file", json=payload)
        result = RepoOpResult(**resp.json())
        print_result(result)
        return result

    def write_to_yml_file(self, local_path: str, filename: str, content: str) -> RepoOpResult:
        payload = {"repo_path": local_path, "filename": filename, "content": content}
        resp = requests.post(f"{self.base_url}/github/write-yml-file", json=payload)
        result = RepoOpResult(**resp.json())
        print_result(result)
        return result

    def delete_yml_file(self, local_path: str, filename: str) -> RepoOpResult:
        payload = {"repo_path": local_path, "filename": filename}
        resp = requests.post(f"{self.base_url}/github/delete-yml-file", json=payload)
        result = RepoOpResult(**resp.json())
        print_result(result)
        return result

    def delete_cloned_repository(self, local_path: str) -> RepoOpResult:
        payload = {"repo_path": local_path}
        resp = requests.post(f"{self.base_url}/github/delete-repo", json=payload)
        result = RepoOpResult(**resp.json())
        print_result(result)
        return result
