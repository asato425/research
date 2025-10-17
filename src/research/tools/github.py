
"""
GitHub APIクライアント側のラッパーやAPI呼び出し用関数を実装するモジュール。
"""

import requests
import subprocess
import getpass
import atexit
import time
import os
import shutil
from pydantic import BaseModel
from research.log_output.log import log
from dotenv import load_dotenv

load_dotenv()
class RepoOpResult(BaseModel):
    status: str
    message: str

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

class PullRequestResult(BaseModel):
    status: str
    message: str
    pr_url: str | None = None


class GitHubTool:
    _server_process = None

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        GitHubToolのインスタンスを初期化し、APIサーバーを起動する。

        Args:
            base_url (str): APIサーバーのベースURL（デフォルト: http://localhost:8000）
        """
        self.base_url = base_url
        self._start_github_api_server()
        atexit.register(self._stop_github_api_server)

    def _start_github_api_server(self) -> None:
        """
        FastAPIベースのGitHub APIサーバーをバックグラウンドで起動する。
        """
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
        """
        バックグラウンドで起動したGitHub APIサーバーを停止する。
        """
        if GitHubTool._server_process is not None:
            GitHubTool._server_process.terminate()
            GitHubTool._server_process.wait()
            GitHubTool._server_process = None


    def _set_github_token(self) -> None:
        """
        ターミナルからGitHubトークンを安全に入力させ、環境変数GITHUB_TOKENにセットする。

        Returns:
            None
        """
        token = getpass.getpass("GitHubトークンを入力してください（入力は非表示です）: ")
        os.environ["GITHUB_TOKEN"] = token
        log("info", "GITHUB_TOKENをセットしました。")

    def _is_github_token_set(self) -> bool:
        """
        GITHUB_TOKENが環境変数にセットされているか確認する。

        Returns:
            bool: セットされていればTrue、なければFalse
        """
        return bool(os.environ.get("GITHUB_TOKEN"))
    
    def fork_repository(self, repo_url: str) -> ForkResult:
        """
        指定したGitHubリポジトリをforkし、fork先のURLを返す。

        Args:
            repo_url (str): ForkしたいGitHubリポジトリのURL

        Returns:
            ForkResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
                fork_url (str|None): フォーク先リポジトリのURL（成功時のみ）
        """
        if not self._is_github_token_set():
            log("error", "GITHUB_TOKENがセットされていないため、リポジトリをフォークできません")
            self._set_github_token()

        resp = requests.post(f"{self.base_url}/github/fork", json={"repo_url": repo_url})
        result = ForkResult(**resp.json())
        log(result.status, result.message)
        return result

    def get_repository_info(self, repo_url: str) -> RepoInfoResult:
        """
        指定したGitHubリポジトリの情報（説明、スター数、フォーク数、デフォルトブランチなど）を取得する。

        Args:
            repo_url (str): 情報取得したいGitHubリポジトリのURL

        Returns:
            RepoInfoResult:
                status (str): "success" または "error" など、処理結果のステータス
                info (dict|None): リポジトリ情報の辞書（full_name, description, stargazers_count, forks_count, ...）
                message (str|None): 実行結果の説明メッセージ
        """
        if not self._is_github_token_set():
            log("error", "GITHUB_TOKENがセットされていないため、リポジトリをフォークできません")
            self._set_github_token()

        resp = requests.get(f"{self.base_url}/github/info", json={"repo_url": repo_url})
        result = RepoInfoResult(**resp.json())
        log(result.status, result.message+str(result.info))
        return result

    def clone_repository(self, repo_url: str, local_path: str = None) -> CloneResult:
        """
        指定したGitHubリポジトリをローカルにクローンする。

        Args:
            repo_url (str): クローンしたいGitHubリポジトリのURL
            local_path (str, optional): クローン先のローカルパス。未指定時はデフォルトディレクトリに作成。

        Returns:
            CloneResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
                local_path (str|None): クローン先のローカルパス
                repo_url (str|None): クローン元リポジトリのURL
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
        指定したローカルリポジトリでadd/commit/pushを実行し、コミットSHAを返す。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            message (str): コミットメッセージ

        Returns:
            PushResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
                commit_sha (str|None): 最新コミットのSHA（成功時のみ）
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
            workflow_id (str): ワークフローのファイル名またはID（例: ci.yml, 1234567）

        Returns:
            WorkflowDispatchResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str|None): 実行結果の説明メッセージ
        """
        if not self._is_github_token_set():
            log("error", "GITHUB_TOKENがセットされていないため、リポジトリをフォークできません")
            self._set_github_token()
            
        payload = {"repo_url": repo_url, "ref": ref, "workflow_id": workflow_id}
        resp = requests.post(f"{self.base_url}/workflow/dispatch", json=payload)
        result = WorkflowDispatchResult(**resp.json())
        log(result.status, result.message)
        return result
    
    def get_latest_workflow_logs(self, repo_url: str, commit_sha: str) -> WorkflowResult:
        """
        指定したコミットSHAに対応する最新のGitHub Actionsワークフローの実行結果・ログを取得する。

        Args:
            repo_url (str): GitHubリポジトリのURL
            commit_sha (str): 対象コミットのSHA

        Returns:
            WorkflowResult:
                status (str): ワークフローの状態（例: "completed", "in_progress", "error" など）
                message (str): 実行結果の説明メッセージ
                conclusion (str|None): ワークフローの最終結論（"success", "failure" など）
                html_url (str|None): 実行結果のGitHubページURL
                logs_url (str|None): ログ取得用URL
                failure_reason (str|None): 失敗時の詳細ログや理由
        """
        if not self._is_github_token_set():
            log("error", "GITHUB_TOKENがセットされていないため、リポジトリをフォークできません")
            self._set_github_token()

        payload = {"repo_url": repo_url, "commit_sha": commit_sha}
        resp = requests.post(f"{self.base_url}/workflow/latest", json=payload)
        result = WorkflowResult(**resp.json())
        log(result.status, result.message)
        return result

    def create_working_branch(self, local_path: str, branch_name: str = "work/llm") -> RepoOpResult:
        """
        指定したローカルリポジトリで新しい作業用ブランチを作成する。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            branch_name (str): 作成するブランチ名

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        dev_repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
        local_path_abs = os.path.abspath(local_path) if local_path else None
        if not local_path_abs:
            result = RepoOpResult(status="error", message="cloneに失敗しているため作業用ブランチを作成できません。")
            log(result.status, result.message)
            return result
        if local_path_abs == dev_repo_path:
            result = RepoOpResult(status="error", message="開発リポジトリ自身では作業用ブランチを作成できません。cloneしたリポジトリで実行してください。")
            log(result.status, result.message)
            return result
        
        # 現在あるブランチ名を確認し、すでに存在する場合はそのまま成功を返す
        try:
            subprocess.run(["git", "checkout", branch_name], cwd=local_path, check=True)
            result = RepoOpResult(status="success", message=f"{branch_name}ブランチはすでに存在します")
        except subprocess.CalledProcessError:
            try:
                subprocess.run(["git", "checkout", "-b", branch_name], cwd=local_path, check=True)
                result = RepoOpResult(status="success", message=f"{branch_name}ブランチを作成しました")
            except subprocess.CalledProcessError as e:
                result = RepoOpResult(status="error", message=str(e))
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e))

        log(result.status, result.message)
        return result

    def create_file(self, local_path: str, relative_path: str) -> RepoOpResult:
        """
        指定したローカルリポジトリ内に新しいファイルを作成する。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            relative_path (str): 作成するファイルのパス（リポジトリルートからの相対パス）

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        file_path = os.path.join(local_path, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            result = RepoOpResult(status="success", message=f"{file_path} は既に存在します。")
            log(result.status, result.message)
            return result
        try:
            with open(file_path, "w"):
                pass
            result = RepoOpResult(status="success", message=f"{file_path}を作成しました")
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e))

        log(result.status, result.message)
        return result

    def write_to_file(self, local_path: str, relative_path: str, content: str) -> RepoOpResult:
        """
        指定したファイルに内容を書き込む。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            relative_path (str): 書き込み対象ファイルのパス（リポジトリルートからの相対パス）
            content (str): 書き込む内容

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        file_path = os.path.join(local_path, relative_path)
        try:
            with open(file_path, "w") as f:
                f.write(content or "")
            result = RepoOpResult(status="success", message=f"{file_path}に書き込みました")
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e))

        log(result.status, result.message)
        return result

    def delete_file(self, local_path: str, relative_path: str) -> RepoOpResult:
        """
        指定したファイルを削除する。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            relative_path (str): 削除対象ファイルのパス（リポジトリルートからの相対パス）

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        file_path = os.path.join(local_path, relative_path)
        if not os.path.exists(file_path):
            result = RepoOpResult(status="not_found", message=f"{file_path} は存在しません。")
            return result
        try:
            os.remove(file_path)
            result = RepoOpResult(status="success", message=f"{file_path}を削除しました")
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e))

        log(result.status, result.message)
        return result

    def delete_folder(self, local_path: str, relative_path: str) -> RepoOpResult:
        """
        指定したフォルダを削除する。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            relative_path (str): 削除対象フォルダのパス（リポジトリルートからの相対パス）

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        folder_path = os.path.join(local_path, relative_path)
        if not os.path.exists(folder_path):
            result = RepoOpResult(status="not_found", message=f"{folder_path} は存在しません。")
            log(result.status, result.message)
            return result
        try:
            shutil.rmtree(folder_path)
            result = RepoOpResult(status="success", message=f"{folder_path}を削除しました")
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e))

        log(result.status, result.message)
        return result

    def delete_cloned_repository(self, local_path: str) -> RepoOpResult:
        """
        指定したローカルリポジトリのディレクトリを削除する。

        Args:
            local_path (str): 削除対象リポジトリのローカルパス

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        if not local_path:
            result = RepoOpResult(status="error", message="local_pathが未設定です。clone後に実行してください。")
            log(result.status, result.message)
            return result
        elif not os.path.exists(local_path):
            result = RepoOpResult(status="not_found", message=f"{local_path} は存在しません。")
            log(result.status, result.message)
            return result
        try:
            shutil.rmtree(local_path)
            result = RepoOpResult(status="success", message=f"{local_path}を削除しました")
            log(result.status, result.message)
            return result
        except Exception as e:
            result = RepoOpResult(status="error", message=str(e))
            log(result.status, result.message)
            return result
    
    def read_file(self, local_path: str, relative_path: str) -> RepoInfoResult:
        """
        指定したファイルの内容を読み込む。

        Args:
            local_path (str): 対象リポジトリのローカルパス
            relative_path (str): 読み込み対象ファイルのパス（リポジトリルートからの相対パス）

        Returns:
            RepoInfoResult:
                status (str): "success" または "error" など、処理結果のステータス
                info (dict|None): {"file_path": ファイルパス, "content": ファイル内容}
                message (str): 実行結果の説明メッセージ
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
        指定したローカルリポジトリのファイルツリー情報を取得する。

        Args:
            local_path (str): 対象リポジトリのローカルパス

        Returns:
            RepoInfoResult:
                status (str): "success" または "error" など、処理結果のステータス
                info (dict|None): {ファイルパス: {"size": サイズ, "modified": 更新時刻}, ...}
                message (str): 実行結果の説明メッセージ
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

    def get_file_tree_sub(self, local_path: str) -> RepoInfoResult:
        """
        指定したローカルリポジトリのファイルツリー情報をtreeコマンドで取得し、文字列で返す。

        Args:
            local_path (str): 対象リポジトリのローカルパス

        Returns:
            RepoInfoResult:
                status (str): "success" または "error" など、処理結果のステータス
                info (dict|None): {"tree": treeコマンドの出力文字列}
                message (str): 実行結果の説明メッセージ
        """
        if not os.path.exists(local_path):
            result = RepoInfoResult(status="not_found", info=None, message=f"{local_path} は存在しません。")
            log(result.status, result.message)
            return result
        try:
            import subprocess
            tree_output = subprocess.run(
                ["tree", local_path],
                capture_output=True, text=True, check=True
            ).stdout
            result = RepoInfoResult(
                status="success",
                info={"tree": tree_output},
                message=f"{local_path}のファイルツリー（treeコマンド）を取得しました"
            )
        except Exception as e:
            result = RepoInfoResult(status="error", info=None, message=str(e))
        log(result.status, result.message)
        return result

    def create_pull_request(self, repo_url: str, head: str, base: str, title: str, body: str = "") -> PullRequestResult:
        """
        指定したリポジトリにプルリクエストを作成する。

        Args:
            repo_url (str): リポジトリURL
            head (str): プルリクエストの元ブランチ名
            base (str): プルリクエストの先ブランチ名
            title (str): プルリクエストのタイトル
            body (str, optional): プルリクエストの説明

        Returns:
            PullRequestResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
                pr_url (str|None): 作成されたプルリクエストのURL（成功時のみ）
        """
        if not self._is_github_token_set():
            log("error", "GITHUB_TOKENがセットされていないため、プルリクエストを作成できません")
            self._set_github_token()

        payload = {"repo_url": repo_url, "head": head, "base": base, "title": title, "body": body}
        resp = requests.post(f"{self.base_url}/github/pull_request", json=payload)
        result = PullRequestResult(**resp.json())
        log(result.status, result.message)
        return result
    
    def delete_remote_repository(self, repo_url: str) -> RepoOpResult:
        """
        指定したGitHubリポジトリを削除する。

        Args:
            repo_url (str): 削除したいGitHubリポジトリのURL

        Returns:
            RepoOpResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        if not self._is_github_token_set():
            log("error", "GITHUB_TOKENがセットされていないため、リポジトリを削除できません")
            self._set_github_token()

        resp = requests.post(f"{self.base_url}/github/delete_repository", json={"repo_url": repo_url})
        result = RepoOpResult(**resp.json())
        log(result.status, result.message)
        return result

    def folder_exists_in_repo(self, local_path: str, folder_name: str) -> RepoOpResult:
        """
        指定したローカルリポジトリ内に特定のフォルダが存在するかどうかを判定する関数。

        Args:
            local_path (str): リポジトリのローカルパス
            folder_name (str): 存在を調べたいフォルダ名（例: 'src'）

        Returns:
            bool: フォルダが存在すればTrue、なければFalse
        """
        target_path = os.path.join(local_path, folder_name)
        status = "success" if os.path.exists(target_path) else "error"
        if os.path.exists(target_path):
            result = RepoOpResult(status=status, message=f"{target_path}の存在確認をしました")
        else:
            result = RepoOpResult(status=status, message=f"{target_path}は存在しません。")

        log(result.status, result.message)
        return result