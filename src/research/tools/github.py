"""
GitHub APIクライアント側のラッパーやAPI呼び出し用関数を実装するモジュール。
"""

from pydantic import BaseModel
import requests
import subprocess
import sys
import time
import atexit
import os
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

class RepoInfoResult(BaseModel):
    status: str
    info: dict | None = None
    message: str | None = None

_server_process = None

def _start_github_api_server():
    """
    github_api.pyのFastAPIサーバーをサブプロセスで起動し、起動確認を行う。
    """
    global _server_process
    if _server_process is not None:
        return  # すでに起動済み
    _server_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "research.server.github_api:app", "--host", "127.0.0.1", "--port", "8000"
    ])
    # サーバーの起動確認
    for _ in range(20):
        try:
            resp = requests.get("http://127.0.0.1:8000/docs")
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.2)
    else:
        print("[ERROR] github_apiサーバーの起動に失敗しました")

def _stop_github_api_server():
    global _server_process
    if _server_process is not None:
        _server_process.terminate()
        _server_process.wait()
        _server_process = None

atexit.register(_stop_github_api_server)

class GitHubAPIClient:
    """
    サーバー側のGitHub APIエンドポイントを呼び出すクライアントクラス。
    インスタンス生成時にサーバーを起動する。
    プログラム終了時にサーバーも自動終了。
    """
    def __init__(self, repo_url: str, base_url: str = "http://localhost:8000", local_path: str = None):
        self.base_url = base_url
        self.repo_url = repo_url  # GitHubリポジトリのURL（必須）
        self.local_path = local_path  # クローンしたローカルパス
        _start_github_api_server() # サーバー起動


    def delete_cloned_repository(self) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリを削除する。
        ディレクトリが存在しない場合は何もしない。
        """
        import shutil
        if not os.path.exists(self.local_path):
            return RepoOpResult(status="not_found", message=f"{self.local_path} は存在しません。", path=self.local_path)
        try:
            shutil.rmtree(self.local_path) # ディレクトリ削除
            return RepoOpResult(status="success", message=f"Deleted: {self.local_path}", path=self.local_path)
        except Exception as e:
            return RepoOpResult(status="error", message=str(e), path=self.local_path)
    def create_empty_file(self, filename: str) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリに空ファイルを生成する。
        既にファイルが存在する場合は何もしない。
        """
        file_path = os.path.join(self.local_path, filename)
        if os.path.exists(file_path):
            return RepoOpResult(status="exists", message=f"{file_path} は既に存在します。", path=file_path)
        try:
            with open(file_path, "w"):
                # 空ファイル作成
                pass
            return RepoOpResult(status="success", message=f"Created empty file: {file_path}", path=file_path)
        except Exception as e:
            return RepoOpResult(status="error", message=str(e), path=file_path)

    def fork_repository(self) -> ForkResult:
        resp = requests.post(f"{self.base_url}/github/fork", json={"repo_url": self.repo_url})
        return ForkResult(**resp.json())

    def push_changes(self, message: str) -> PushResult:
        resp = requests.post(f"{self.base_url}/github/push", json={"repo_path": self.local_path, "message": message})
        return PushResult(**resp.json())

    def get_repository_info(self) -> RepoInfoResult:
        resp = requests.get(f"{self.base_url}/github/info", params={"repo_url": self.repo_url})
        return RepoInfoResult(**resp.json())

    def clone_repository(self, local_dir: str = None) -> RepoOpResult:
        """
        指定したリポジトリURLをローカルにcloneする。
        local_dirが指定されていなければ、~/research_clones/配下にリポジトリ名でclone。
        """
        if local_dir is None:
            repo_name = self.repo_url.rstrip('/').split('/')[-1]
            base_dir = os.path.expanduser('~/Desktop/research_clones')
            os.makedirs(base_dir, exist_ok=True)
            local_dir = os.path.join(base_dir, repo_name)
        if os.path.exists(local_dir):
            self.local_path = local_dir
            return RepoOpResult(status="exists", message=f"{local_dir} は既に存在します。", path=local_dir)
        try:
            subprocess.run(["git", "clone", self.repo_url, local_dir], check=True)
            self.local_path = local_dir
            return RepoOpResult(status="success", message=f"Cloned to {local_dir}", path=local_dir)
        except subprocess.CalledProcessError as e:
            return RepoOpResult(status="error", message=str(e), path=local_dir)
