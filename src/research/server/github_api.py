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

class WorkflowRunRequest(BaseModel):
    repo_url: str = Field(..., description="GitHubリポジトリのURL")
    commit_sha: str = Field(..., description="対象コミットのSHA")

class WorkflowRunResponse(BaseModel):
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
    content: str | None = Field(..., description="ファイルの内容")

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
        return ForkResponse(status="success", message=f"Forked {req.repo_url}", fork_url=forked_repo.html_url)
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
        return CloneResponse(status="success", message=f"Cloned to {local_path}", local_path=local_path, repo_url=repo_url)
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
        return RepoInfoResponse(status="success", info=None, message=f"Created working branch: {req.branch_name}")
    except subprocess.CalledProcessError as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/push", response_model=PushResponse)
def push_changes(req: PushRequest):
    repo_dir = req.repo_path or os.getcwd()
    repo_dir = os.path.expanduser(repo_dir)
    try:
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", req.message], cwd=repo_dir, check=True)
        subprocess.run(["git", "push"], cwd=repo_dir, check=True)
        commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True).stdout.decode().strip()
        return PushResponse(status="success", message=f"Committed and pushed in {repo_dir}: {req.message}", commit_sha=commit_sha)
    except subprocess.CalledProcessError as e:
        return PushResponse(status="error", message=str(e), commit_sha=None)
    except Exception as e:
        return PushResponse(status="error", message=str(e), commit_sha=None)


@app.post("/workflow/latest", response_model=WorkflowRunResponse)
def get_latest_workflow_logs(req: WorkflowRunRequest):
    import os
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    # 環境変数からGitHubアクセストークンを取得
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return WorkflowRunResponse(status="error", message="GITHUB_TOKENが設定されていません", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
    # URLからowner/repo名を抽出
    import re
    m = re.match(r"https://github.com/([\w\-]+)/([\w\-]+)", req.repo_url)
    if not m:
        return WorkflowRunResponse(status="error", message="リポジトリURLの形式が不正です", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
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
            return WorkflowRunResponse(status="not_found", message="commit_shaに一致するワークフローが見つかりませんでした", conclusion=None, html_url=None, logs_url=None, failure_reason=None)
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
        return WorkflowRunResponse(
            status=run["status"],
            message="ワークフロー結果取得成功",
            conclusion=run["conclusion"],
            html_url=run["html_url"],
            logs_url=run["logs_url"],
            failure_reason=failure_reason
        )
    except Exception as e:
        return WorkflowRunResponse(status="error", message=str(e), conclusion=None, html_url=None, logs_url=None, failure_reason=None)

@app.get("/github/info", response_model=RepoInfoResponse)
def get_repository_info(repo_url: str):
    # ここでリポジトリ情報取得処理を実装
    return RepoInfoResponse(status="success", info={"info": f"Info for {repo_url}"})

@app.post("/github/create-empty-file", response_model=RepoInfoResponse)
def create_empty_file(req: FileRequest):
    import os
    file_path = os.path.join(req.repo_path, req.filename)
    if os.path.exists(file_path):
        return RepoInfoResponse(status="exists", info=None, message=f"{file_path} は既に存在します。")
    try:
        with open(file_path, "w"):
            pass
        return RepoInfoResponse(status="success", info=None, message=f"Created empty file: {file_path}")
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
        return RepoInfoResponse(status="success", info=None, message=f"Created empty file: {file_path}")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))

@app.post("/github/write-yml-file", response_model=RepoInfoResponse)
def write_to_yml_file(req: FileRequest):
    import os
    file_path = os.path.join(req.repo_path, ".github", "workflows", req.filename)
    try:
        with open(file_path, "w") as f:
            f.write(req.content or "")
        return RepoInfoResponse(status="success", info=None, message=f"Wrote to file: {file_path}")
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
        return RepoInfoResponse(status="success", info=None, message=f"Deleted file: {file_path}")
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
        return RepoInfoResponse(status="success", info=None, message=f"Deleted: {req.repo_path}")
    except Exception as e:
        return RepoInfoResponse(status="error", info=None, message=str(e))
