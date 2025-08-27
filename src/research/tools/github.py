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

def print_result(result):
    """
    各操作の結果（BaseModel）をわかりやすく表示するユーティリティ関数。
    色付きでSUCCESS/FAILを表示。
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
    # 色分け
    if status == 'success':
        label = '\033[92mSUCCESS\033[0m'  # 緑
    else:
        label = '\033[91mFAIL\033[0m'     # 赤
    print(f"[{label}] {message}\npath: {path if path else ''}{extra}")
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
        self.branch_name = "main"
        _start_github_api_server() # サーバー起動

    def delete_cloned_repository(self) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリを削除する。
        ディレクトリが存在しない場合は何もしない。
        """
        import shutil
        if not os.path.exists(self.local_path):
            result = RepoOpResult(status="not_found", message=f"{self.local_path} は存在しません。", path=self.local_path)
            print_result(result)
            return result
        try:
            shutil.rmtree(self.local_path) # ディレクトリ削除
            result = RepoOpResult(status="success", message=f"Deleted: {self.local_path}", path=self.local_path)
            print_result(result)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e), path=self.local_path)
            print_result(result)
            return result
        
    def create_empty_file(self, filename: str) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリに空ファイルを生成する。
        既にファイルが存在する場合は何もしない。
        """
        file_path = os.path.join(self.local_path, filename)
        if os.path.exists(file_path):
            result = RepoOpResult(status="exists", message=f"{file_path} は既に存在します。", path=file_path)
            print_result(result)
            return result
        try:
            with open(file_path, "w"):
                # 空ファイル作成
                pass
            result = RepoOpResult(status="success", message=f"Created empty file: {file_path}", path=file_path)
            print_result(result)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e), path=file_path)
            print_result(result)
            return result

    def create_yml_file(self, filename: str) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリに空のYAMLファイルを生成する。
        既にファイルが存在する場合は何もしない。
        """
        # file_pathはsrc/.github/workflows/配下に作成
        file_path = os.path.join(self.local_path, ".github", "workflows", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            result = RepoOpResult(status="exists", message=f"{file_path} は既に存在します。", path=file_path)
            print_result(result)
            return result
        try:
            with open(file_path, "w"):
                # 空ファイル作成
                pass
            result = RepoOpResult(status="success", message=f"Created empty file: {file_path}", path=file_path)
            print_result(result)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e), path=file_path)
            print_result(result)
            return result
        
    def write_to_yml_file(self, filename: str, content: str) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリにファイルを書き込む。
        """
        file_path = os.path.join(self.local_path, ".github", "workflows", filename)
        try:
            with open(file_path, "w") as f:
                f.write(content)
            result = RepoOpResult(status="success", message=f"Wrote to file: {file_path}", path=file_path)
            print_result(result)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e), path=file_path)
            print_result(result)
            return result

    def delete_yml_file(self, filename: str) -> RepoOpResult:
        """
        指定したローカルリポジトリディレクトリからファイルを削除する。
        """
        file_path = os.path.join(self.local_path, ".github", "workflows", filename)
        if not os.path.exists(file_path):
            result = RepoOpResult(status="not_found", message=f"{file_path} は存在しません。", path=file_path)
            print_result(result)
            return result
        try:
            os.remove(file_path)
            result = RepoOpResult(status="success", message=f"Deleted file: {file_path}", path=file_path)
            print_result(result)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e), path=file_path)
            print_result(result)
            return result

    def fork_repository(self) -> ForkResult:
        resp = requests.post(f"{self.base_url}/github/fork", json={"repo_url": self.repo_url})
        result = ForkResult(**resp.json())
        print_result(result)
        return result

    def push_changes(self, message: str) -> PushResult:
        """
        変更をコミットし、現在のブランチがリモートに存在しなければ -u オプション付きでpushする。
        """
        # まずadd/commit
        try:
            subprocess.run(["git", "add", "."], cwd=self.local_path, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=self.local_path, check=True)
        except subprocess.CalledProcessError as e:
            result = PushResult(status="error", message=f"commit error: {str(e)}", commit_sha=None)
            print_result(result)
            return result

        # 現在のブランチ名を取得
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.local_path, check=True, capture_output=True)
            branch = res.stdout.decode().strip()
        except Exception as e:
            result = PushResult(status="error", message=f"branch check error: {str(e)}", commit_sha=None)
            print_result(result)
            return result

        # git push（upstream未設定なら-u付きで再push）
        try:
            subprocess.run(["git", "push"], cwd=self.local_path, check=True)
        except subprocess.CalledProcessError:
            # upstream未設定の場合は-u付きでpush
            try:
                subprocess.run(["git", "push", "-u", "origin", branch], cwd=self.local_path, check=True)
            except subprocess.CalledProcessError as e:
                result = PushResult(status="error", message=f"push error: {str(e)}", commit_sha=None)
                print_result(result)
                return result

        # コミットハッシュ取得
        try:
            commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.local_path, check=True, capture_output=True).stdout.decode().strip()
        except Exception:
            commit_sha = None
        result = PushResult(status="success", message=f"Committed and pushed on branch {branch}", commit_sha=commit_sha)
        print_result(result)
        return result

    def get_repository_info(self) -> RepoInfoResult:
        resp = requests.get(f"{self.base_url}/github/info", params={"repo_url": self.repo_url})
        result = RepoInfoResult(**resp.json())
        print_result(result)
        return result

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
            result = RepoOpResult(status="exists", message=f"{local_dir} は既に存在します。", path=local_dir)
            print_result(result)
            return result
        try:
            subprocess.run(["git", "clone", self.repo_url, local_dir], check=True)
            self.local_path = local_dir
            result = RepoOpResult(status="success", message=f"Cloned to {local_dir}", path=local_dir)
            print_result(result)
            return result
        except subprocess.CalledProcessError as e:
            result = RepoOpResult(status="error", message=str(e), path=local_dir)
            print_result(result)
            return result

    def create_working_branch(self, branch_name: str) -> RepoOpResult:
        """
        作業用ブランチを作成する。
        """
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.local_path, check=True)
            self.branch_name = branch_name
            return RepoOpResult(status="success", message=f"Created working branch: {branch_name}", path=self.local_path)
        except subprocess.CalledProcessError as e:
            return RepoOpResult(status="error", message=str(e), path=self.local_path)

