"""
FastAPIを用いたGitHub操作APIのサーバー側実装例。
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxをターミナルで実行しておく必要があります
"""
import time
import logging
import requests
import os
from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class ForkRequest(BaseModel):
    repo_url: str = Field(..., description="ForkしたいGitHubリポジトリのURL")

class ForkResponse(BaseModel):
    status: str
    message: str
    fork_url: str | None = None

class RepoInfoRequest(BaseModel):
    repo_url: str = Field(..., description="情報取得したいGitHubリポジトリのURL")

class RepoInfoResponse(BaseModel):
    status: str
    info: dict | None = None
    message: str | None = None


class WorkflowRequest(BaseModel):
    repo_url: str = Field(..., description="GitHubリポジトリのURL")
    commit_sha: str = Field(..., description="対象コミットのSHA")

class WorkflowResponse(BaseModel):
    status: str
    message: str
    conclusion: str | None = None
    html_url: str | None = None
    logs_url: str | None = None
    failure_reason: str | None = None
    
class WorkflowDispatchRequest(BaseModel):
    repo_url: str = Field(..., description="GitHubリポジトリのURL")
    ref: str = Field(..., description="実行したいブランチ名（例: main）")
    workflow_id: str = Field(..., description="ワークフローのファイル名、またはID（例: ci.yml, 1234567）")
class WorkflowDispatchResponse(BaseModel):
    status: str
    message: str | None = None

class PullRequestRequest(BaseModel):
    repo_url: str = Field(..., description="GitHubリポジトリのURL")
    head: str = Field(..., description="プルリクエストの元ブランチ名")
    base: str = Field(..., description="プルリクエストの先ブランチ名")
    title: str = Field(..., description="プルリクエストのタイトル")
    body: str | None = Field(None, description="プルリクエストの説明")

class PullRequestResponse(BaseModel):
    status: str
    message: str
    pr_url: str | None = None
   
class DeleteRemoteRepoRequest(BaseModel):
    repo_url: str = Field(..., description="削除したいGitHubリポジトリのURL") 
class DeleteRemoteRepoResponse(BaseModel):
    status: str
    message: str

def is_github_token_set() -> bool:
    """
    GITHUB_TOKENが環境変数にセットされているか確認する
    Returns:
        bool: セットされていればTrue、なければFalse
    """
    return bool(os.environ.get("GITHUB_TOKEN"))

@app.post("/github/fork", response_model=ForkResponse)
def fork_repository(req: ForkRequest):
    """
    指定したGitHubリポジトリをforkし、fork先のURLを返す。
    """
    try:
        from github import Github
        import os
        # 環境変数からGitHubアクセストークンを取得
        if not is_github_token_set():
            return ForkResponse(status="error", message="GITHUB_TOKENがセットされていません", fork_url=None)
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
        g = Github(GITHUB_TOKEN)
        # URLからowner/repo名を抽出
        import re
        m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
        if not m:
            return ForkResponse(status="error", message="リポジトリURLの形式が不正です", fork_url=None)
        owner, repo = m.group(1), m.group(2)
        repo_obj = g.get_repo(f"{owner}/{repo}")
        user = g.get_user()
        forked_repo = user.create_fork(repo_obj)
        return ForkResponse(status="success", message=f" {req.repo_url}をforkしました", fork_url=forked_repo.html_url)
    except Exception as e:
        return ForkResponse(status="error", message=str(e), fork_url=None)

@app.post("/workflow/dispatch", response_model=WorkflowDispatchResponse)
def dispatch_workflow(req: WorkflowDispatchRequest):
    """
    指定したワークフローをworkflow_dispatchで手動実行する。
    存在しないエラーの場合は10秒待機して最大5分（30回）までリトライする。
    """
    import re
    import time
    if not is_github_token_set():
        return WorkflowDispatchResponse(status="error", message="GITHUB_TOKENがセットされていません")
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
    if not m:
        return WorkflowDispatchResponse(status="error", message="リポジトリURLの形式が不正です")
    owner, repo = m.group(1), m.group(2)
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{req.workflow_id}/dispatches"
    data = {"ref": req.ref}
    max_retries = 30  # 10秒×30回＝5分
    for retry in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 204:
                return WorkflowDispatchResponse(status="success", message="ワークフローの手動実行をトリガーしました")
            elif resp.status_code == 404:
                # 存在しない場合は10秒待機してリトライ
                if retry < max_retries - 1:
                    time.sleep(10)
                    continue
                else:
                    return WorkflowDispatchResponse(
                        status="error",
                        message=f"APIエラー: 404（5分間リトライしても存在しませんでした） {resp.text}"
                    )
            else:
                return WorkflowDispatchResponse(status="error", message=f"APIエラー: {resp.status_code} {resp.text}")
        except Exception as e:
            return WorkflowDispatchResponse(status="error", message=str(e))


@app.post("/workflow/latest", response_model=WorkflowResponse)
def get_latest_workflow_logs(req: WorkflowRequest):
    import os
    # 環境変数からGitHubアクセストークンを取得
    if not is_github_token_set():
        return WorkflowResponse(status="error", message="GITHUB_TOKENがセットされていません", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    # URLからowner/repo名を抽出
    import re
    m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
    if not m:
        return WorkflowResponse(status="error", message="リポジトリURLの形式が不正です", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
    owner, repo = m.group(1), m.group(2)
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page=5"
    try:
        poll_count = 0
        found = False
        run = None
        # 最大60回(=最大5分)までポーリング
        while poll_count < 60:
            resp = requests.get(url, headers=headers)
            data = resp.json()
            logging.info("------------------------------------------")
            logging.info({"poll_count": poll_count})
            if "workflow_runs" not in data or not data["workflow_runs"]:
                time.sleep(5)
                poll_count += 1
                continue
            # head_shaが一致するrunを探す
            for r in data["workflow_runs"]:
                if r.get("head_sha") == req.commit_sha:
                    run = r
                    found = True
                    break
            if found:
                # 進行中なら完了まで待機
                while run["status"] in ("in_progress", "queued") and poll_count < 60:
                    time.sleep(5)
                    resp = requests.get(url, headers=headers)
                    data = resp.json()
                    # head_shaが一致するrunを再取得
                    run = None
                    for r in data["workflow_runs"]:
                        if r.get("head_sha") == req.commit_sha:
                            run = r
                            break
                    if run is None:
                        break
                    poll_count += 1
                break
            else:
                # head_sha一致するrunがまだ出てこない場合は少し待つ
                time.sleep(5)
                poll_count += 1
        if not run:
            return WorkflowResponse(status="not_found", message="commit_shaに一致するワークフローが見つかりませんでした", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
        logging.info("------------------------------------------")
        logging.info("run: %s", run)
        failure_reason = None
        # 失敗時はlogs_urlからログを取得し、そのままfailure_reasonに格納（LLMで抽出するため）
        if run["conclusion"] == "failure" and run.get("logs_url"):
            try:
                logs_resp = requests.get(run["logs_url"], headers=headers)
                if logs_resp.status_code == 200:
                    import zipfile
                    import io
                    import os
                    z = zipfile.ZipFile(io.BytesIO(logs_resp.content))
                    log_texts = []
                    log_dir = os.path.join(os.getcwd(), "log")
                    os.makedirs(log_dir, exist_ok=True)
                    for name in z.namelist():
                        if not ("test" in name.lower() or "run" in name.lower()):
                            #continue
                            pass
                        with z.open(name) as f:
                            try:
                                content = f.read().decode(errors="ignore")
                                log_texts.append(f"===== {name} =====\n{content}")
                                # ファイルとして保存
                                # file_path = os.path.join(log_dir, name.replace("/", "_"))
                                # with open(file_path, "w", encoding="utf-8", errors="ignore") as out_f:
                                #     out_f.write(content)
                            except Exception:
                                continue
                    failure_reason = "\n\n".join(log_texts) if log_texts else "(No test/run logs found)"
                else:
                    failure_reason = f"Failed to fetch logs: {logs_resp.status_code}"
            except Exception as ex:
                failure_reason = f"Log parse error: {ex}"
        return WorkflowResponse(
            status=run["status"],
            message="ワークフロー結果取得成功",
            conclusion=run["conclusion"],
            html_url=run["html_url"],
            logs_url=run["logs_url"],
            failure_reason=failure_reason
        )
    except Exception as e:
        return WorkflowResponse(status="error", message=str(e), conclusion=None, html_url=None, logs_url=None, failure_reason=None)

@app.get("/github/info", response_model=RepoInfoResponse)
def get_repository_info(req: RepoInfoRequest):
    """
    指定したGitHubリポジトリの情報（説明、スター数、フォーク数、デフォルトブランチなど）を取得する。
    """
    import re
    import os
    import requests
    if not is_github_token_set():
        return RepoInfoResponse(status="error", info=None, message="GITHUB_TOKENがセットされていません")
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
    if not m:
        return RepoInfoResponse(status="error", info=None, message="リポジトリURLの形式が不正です")
    owner, repo = m.group(1), m.group(2)

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    topics_url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    languages_url = f"https://api.github.com/repos/{owner}/{repo}/languages"

    # 1. デフォルトブランチのSHA取得
    try:
        resp = requests.get(api_url, headers=headers)
        if resp.status_code != 200:
            return RepoInfoResponse(status="error", info=None, message=f"GitHub APIエラー: {resp.status_code}")
        data = resp.json()
        default_branch = data.get("default_branch")
        # ブランチ情報取得
        branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{default_branch}"
        branch_resp = requests.get(branch_url, headers=headers)
        if branch_resp.status_code != 200:
            return RepoInfoResponse(status="error", info=None, message=f"ブランチ情報取得エラー: {branch_resp.status_code}")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=f"Git Trees API準備エラー: {str(e)}")
    # 2. topics
    try:
        topics_resp = requests.get(topics_url, headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"})
        topics = topics_resp.json().get("names", []) if topics_resp.status_code == 200 else []
    except Exception:
        topics = []
    # 3. languages
    try:
        languages_resp = requests.get(languages_url, headers=headers)
        language = list(languages_resp.json().keys())[0].lower() if languages_resp.status_code == 200 else []
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=f"languageの取得ができませんでした。エラー: {str(e)}")

    info = {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "stargazers_count": data.get("stargazers_count"),
        "forks_count": data.get("forks_count"),
        "open_issues_count": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "html_url": data.get("html_url"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
        "language": language,
        "archived": data.get("archived"),
        "disabled": data.get("disabled"),
        "topics": topics,
    }
    return RepoInfoResponse(status="success", info=info, message="リポジトリ情報の取得が完了しました")

@app.post("/github/pull_request", response_model=PullRequestResponse)
def create_pull_request(req: PullRequestRequest):
    """
    指定したリポジトリにプルリクエストを作成する
    Args:
        repo_url (str): リポジトリURL
            head (str): プルリクのheadブランチ名
            base (str): マージ先のbaseブランチ名
            title (str): PRタイトル
            body (str): PR本文
        Returns:
            PullRequestResult: status(str), message(str), pr_url(str|None)
        """
    if not is_github_token_set():
        return PullRequestResponse(status="error", message="GITHUB_TOKENがセットされていません", pr_url=None)
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    import re
    m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
    if not m:
        return PullRequestResponse(status="error", message="リポジトリURLの形式が不正です", pr_url=None)
    owner, repo = m.group(1), m.group(2)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    data = {
        "title": req.title,
        "body": req.body,
        "head": req.head,
        "base": req.base
    }
    try:
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code in (200, 201):
            pr_url = resp.json().get("html_url")
            result = PullRequestResponse(status="success", message="プルリクエストを作成しました", pr_url=pr_url)
        else:
            result = PullRequestResponse(status="error", message=f"APIエラー: {resp.status_code} {resp.text}", pr_url=None)
    except Exception as e:
        result = PullRequestResponse(status="error", message=str(e), pr_url=None)
    return result

@app.post("/github/delete_repository", response_model=DeleteRemoteRepoResponse)
def delete_remote_repository(req: DeleteRemoteRepoRequest) -> DeleteRemoteRepoResponse:
        """
        指定したGitHubリポジトリ（リモート）を削除する。

        Args:
            repo_url (str): 削除したいGitHubリポジトリのURL

        Returns:
            DeleteRemoteRepoResult:
                status (str): "success" または "error" など、処理結果のステータス
                message (str): 実行結果の説明メッセージ
        """
        if not is_github_token_set():
            return DeleteRemoteRepoResponse(status="error", message="GITHUB_TOKENがセットされていません")

        try:
            from github import Github
            import re
            GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
            g = Github(GITHUB_TOKEN)
            m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
            if not m:
                return DeleteRemoteRepoResponse(status="error", message="リポジトリURLの形式が不正です")
            owner, repo = m.group(1), m.group(2)
            repo_obj = g.get_repo(f"{owner}/{repo}")
            
            # フォークでないリポジトリは削除しない
            if not repo_obj.fork:
                return DeleteRemoteRepoResponse(status="error", message="このリポジトリはフォークではないため削除できません")

            # フォークリポジトリを削除
            repo_obj.delete()
            result = DeleteRemoteRepoResponse(status="success", message=f"{req.repo_url} を削除しました")
        except Exception as e:
            result = DeleteRemoteRepoResponse(status="error", message=str(e))
        return result