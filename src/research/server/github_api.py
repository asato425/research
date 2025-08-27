"""
FastAPIを用いたGitHub操作APIのサーバー側実装例。
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxをターミナルで実行しておく必要があります
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import subprocess
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

@app.post("/github/push", response_model=PushResponse)
def push_changes(req: PushRequest):
    repo_dir = req.repo_path or os.getcwd()
    # ~ で始まる場合は絶対パスに展開
    repo_dir = os.path.expanduser(repo_dir)
    try:
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", req.message], cwd=repo_dir, check=True)
        subprocess.run(["git", "push"], cwd=repo_dir, check=True)
        commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True).stdout.decode().strip()
        return PushResponse(status="success", message=f"Committed and pushed in {repo_dir}: {req.message}", commit_sha=commit_sha)
    except subprocess.CalledProcessError as e:
        return PushResponse(status="error", message=str(e), commit_sha=None)

@app.get("/github/info", response_model=RepoInfoResponse)
def get_repository_info(repo_url: str):
    # ここでリポジトリ情報取得処理を実装
    return RepoInfoResponse(status="success", info={"info": f"Info for {repo_url}"})
