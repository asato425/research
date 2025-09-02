"""
FastAPIを用いたGitHub操作APIのサーバー側実装例。
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxをターミナルで実行しておく必要があります
"""
import os
import subprocess
import shutil
import time
import logging
import requests
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

class PushRequest(BaseModel):
    repo_path: str = Field(..., description="ローカルリポジトリのパス")
    message: str = Field(..., description="コミットメッセージ")

class PushResponse(BaseModel):
    status: str
    message: str
    commit_sha: str | None = None # コミットSHA

class RepoInfoRequest(BaseModel):
    repo_url: str = Field(..., description="情報取得したいGitHubリポジトリのURL")

class RepoInfoResponse(BaseModel):
    status: str
    info: dict | None = None
    message: str | None = None

class CloneRequest(BaseModel):
    repo_url: str = Field(..., description="cloneしたいGitHubリポジトリのURL")
    local_path: str | None = Field(None, description="clone先のローカルパス")

class CloneResponse(BaseModel):
    status: str
    message: str
    local_path: str | None = None
    repo_url: str | None = None

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

class BranchRequest(BaseModel):
    repo_path: str = Field(..., description="ローカルリポジトリのパス")
    branch_name: str = Field(..., description="作成するブランチ名") 

class FileRequest(BaseModel):
    repo_path: str = Field(..., description="ローカルリポジトリのパス")
    filename: str = Field(..., description="作成するファイル名")
    content: str | None = Field(None, description="ファイルの内容")

class DeleteRepoRequest(BaseModel):
    repo_path: str = Field(..., description="削除したいローカルリポジトリのパス")


@app.post("/github/fork", response_model=ForkResponse)
def fork_repository(req: ForkRequest):
    """
    指定したGitHubリポジトリをforkし、fork先のURLを返す。
    """
    try:
        from github import Github
        import os
        # 環境変数からGitHubアクセストークンを取得
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return ForkResponse(status="error", message="GITHUB_TOKENが設定されていません", fork_url=None)
        g = Github(token)
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

@app.post("/github/clone", response_model=CloneResponse)
def clone_repository(req: CloneRequest):
    repo_url = req.repo_url
    local_path = req.local_path
    if local_path is None:
        repo_name = repo_url.rstrip('/').split('/')[-1]
        base_dir = os.path.expanduser('~/Desktop/research_clones')
        os.makedirs(base_dir, exist_ok=True)
        local_path = os.path.join(base_dir, repo_name)
    if os.path.exists(local_path):
        return CloneResponse(status="exists", message=f"{local_path} は既に存在します。", local_path=local_path, repo_url=repo_url)
    try:
        subprocess.run(["git", "clone", repo_url, local_path], check=True)
        return CloneResponse(status="success", message=f"{local_path}のクローンに成功しました", local_path=local_path, repo_url=repo_url)
    except subprocess.CalledProcessError as e:
        return CloneResponse(status="error", message=str(e), local_path=local_path, repo_url=repo_url)
    except Exception as e:
        return CloneResponse(status="error", message=str(e), local_path=local_path, repo_url=repo_url)

@app.post("/github/create-branch", response_model=RepoInfoResponse)
def create_working_branch(req: BranchRequest):
    dev_repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    local_path_abs = os.path.abspath(req.repo_path) if req.repo_path else None
    if not local_path_abs:
        return RepoInfoResponse(status="error", info=None, message="cloneに失敗しているため作業用ブランチを作成できません。")
    if local_path_abs == dev_repo_path:
        return RepoInfoResponse(status="error", info=None, message="開発リポジトリ自身では作業用ブランチを作成できません。cloneしたリポジトリで実行してください。")
    try:
        subprocess.run(["git", "checkout", "-b", req.branch_name], cwd=req.repo_path, check=True)
        return RepoInfoResponse(status="success", info=None, message=f"{req.branch_name}を作成しました")
    except subprocess.CalledProcessError as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/push", response_model=PushResponse)
def commit_and_push(req: PushRequest):
    repo_dir = req.repo_path or os.getcwd()
    repo_dir = os.path.expanduser(repo_dir)
    # add/commit
    try:
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", req.message], cwd=repo_dir, check=True)
    except subprocess.CalledProcessError as e:
        return PushResponse(status="error", message=f"コミットエラー: {str(e)}", commit_sha=None)

    # 現在のブランチ名を取得
    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir, check=True, capture_output=True)
        branch = res.stdout.decode().strip()
    except Exception as e:
        return PushResponse(status="error", message=f"branch check error: {str(e)}", commit_sha=None)

    # push（upstream未設定なら-u付きで再push）
    try:
        subprocess.run(["git", "push"], cwd=repo_dir, check=True)
    except subprocess.CalledProcessError:
        try:
            subprocess.run(["git", "push", "-u", "origin", branch], cwd=repo_dir, check=True)
        except subprocess.CalledProcessError as e:
            return PushResponse(status="error", message=f"push error: {str(e)}", commit_sha=None)

    # コミットハッシュ取得
    try:
        commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True).stdout.decode().strip()
    except Exception:
        commit_sha = None
    return PushResponse(status="success", message=f"{branch}にコミットとプッシュをしました", commit_sha=commit_sha)


@app.post("/workflow/latest", response_model=WorkflowResponse)
def get_latest_workflow_logs(req: WorkflowRequest):
    import os
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    # 環境変数からGitHubアクセストークンを取得
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return WorkflowResponse(status="error", message="GITHUB_TOKENが設定されていません", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
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
def get_repository_info(repo_url: str):
    """
    指定したGitHubリポジトリの情報（説明、スター数、フォーク数、デフォルトブランチなど）を取得する。
    """
    import re
    import os
    import requests
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", repo_url)
    if not m:
        return RepoInfoResponse(status="error", info=None, message="リポジトリURLの形式が不正です")
    owner, repo = m.group(1), m.group(2)

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    topics_url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    # Git Trees API
    trees_url = None

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
        branch_data = branch_resp.json()
        tree_sha = branch_data.get("commit", {}).get("commit", {}).get("tree", {}).get("sha")
        if not tree_sha:
            # fallback: 1階層のみ
            trees_url = branch_data.get("commit", {}).get("commit", {}).get("url")
        else:
            trees_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1"
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=f"Git Trees API準備エラー: {str(e)}")

    # 2. topics
    try:
        topics_resp = requests.get(topics_url, headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"})
        topics = topics_resp.json().get("names", []) if topics_resp.status_code == 200 else []
    except Exception:
        topics = []

    # 3. Git Trees APIで全ファイルパス一覧取得
    file_tree = []
    try:
        if trees_url:
            trees_resp = requests.get(trees_url, headers=headers)
            if trees_resp.status_code == 200:
                tree_data = trees_resp.json()
                for item in tree_data.get("tree", []):
                    file_tree.append({
                        "path": item.get("path"),
                        "type": item.get("type")  # "blob"=file, "tree"=dir
                    })
    except Exception:
        pass

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
        "language": data.get("language"),
        "archived": data.get("archived"),
        "disabled": data.get("disabled"),
        "topics": topics,
        "file_tree": file_tree,
    }
    return RepoInfoResponse(status="success", info=info, message="リポジトリ情報の取得が完了しました")

@app.post("/github/create-empty-file", response_model=RepoInfoResponse)
def create_empty_file(req: FileRequest):
    import os
    file_path = os.path.join(req.repo_path, req.filename)
    if os.path.exists(file_path):
        return RepoInfoResponse(status="exists", info=None, message=f"{file_path} は既に存在します。")
    try:
        with open(file_path, "w"):
            pass
        return RepoInfoResponse(status="success", info=None, message=f"{file_path}を作成しました")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/create-yml-file", response_model=RepoInfoResponse)
def create_yml_file(req: FileRequest):
    import os
    file_path = os.path.join(req.repo_path, ".github", "workflows", req.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if os.path.exists(file_path):
        return RepoInfoResponse(status="exists", info=None, message=f"{file_path} は既に存在します。")
    try:
        with open(file_path, "w"):
            pass
        return RepoInfoResponse(status="success", info=None, message=f"{file_path}を作成しました")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/write-yml-file", response_model=RepoInfoResponse)
def write_to_yml_file(req: FileRequest):
    import os
    file_path = os.path.join(req.repo_path, ".github", "workflows", req.filename)
    try:
        with open(file_path, "w") as f:
            f.write(req.content or "")
        return RepoInfoResponse(status="success", info=None, message=f"{file_path}に書き込みました")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/delete-yml-file", response_model=RepoInfoResponse)
def delete_yml_file(req: FileRequest):
    import os
    file_path = os.path.join(req.repo_path, ".github", "workflows", req.filename)
    if not os.path.exists(file_path):
        return RepoInfoResponse(status="not_found", info=None, message=f"{file_path} は存在しません。")
    try:
        os.remove(file_path)
        return RepoInfoResponse(status="success", info=None, message=f"{file_path}を削除しました")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/delete-repo", response_model=RepoInfoResponse)
def delete_cloned_repository(req: DeleteRepoRequest):
    if not req.repo_path:
        return RepoInfoResponse(status="error", info=None, message="local_pathが未設定です。clone後に実行してください。")
    if not os.path.exists(req.repo_path):
        return RepoInfoResponse(status="not_found", info=None, message=f"{req.repo_path} は存在しません。")
    try:
        shutil.rmtree(req.repo_path)
        return RepoInfoResponse(status="success", info=None, message=f"{req.repo_path}を削除しました")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))
