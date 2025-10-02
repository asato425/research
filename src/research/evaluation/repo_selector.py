import requests
import os
from dotenv import load_dotenv

load_dotenv()

# GitHub API トークンを環境変数から取得
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("環境変数 GITHUB_TOKEN を設定してください")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def search_repositories(query: str, per_page: int = 10, page: int = 1):
    """GitHub API でリポジトリを検索する関数"""
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": page
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def get_languages(repo_full_name: str):
    """リポジトリの言語ごとのコード量を取得"""
    url = f"https://api.github.com/repos/{repo_full_name}/languages"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code} for {repo_full_name}")
        return {}

def main_language_ratio(repo_full_name: str, threshold: float = 0.7):
    """主言語の割合を計算し、しきい値を超えているか判定"""
    langs = get_languages(repo_full_name)
    if not langs:
        return None, 0.0, False
    
    total = sum(langs.values())
    main_lang, main_size = max(langs.items(), key=lambda x: x[1])
    ratio = main_size / total if total > 0 else 0.0
    return main_lang, ratio, ratio >= threshold

def get_file_count(repo_full_name: str):
    """リポジトリのファイル数を取得"""
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        tree = response.json().get("tree", [])
        return sum(1 for item in tree if item["type"] == "blob")
    else:
        print(f"Error {response.status_code} for {repo_full_name}")
        return None

def get_root_folder_count(repo_full_name: str):
    """ルートディレクトリのフォルダ数を取得"""
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        tree = response.json().get("tree", [])
        root_folders = set()
        for item in tree:
            if item["type"] == "tree" and "/" not in item["path"]:
                root_folders.add(item["path"])
        return len(root_folders)
    else:
        print(f"Error {response.status_code} for {repo_full_name}")
        return None

def main():
    #languages = ["Python", "Java", "JavaScript"]
    languages = ["Java"]
    star_threshold = 100
    pushed_after = "2025-01-01"
    main_lang_threshold = 0.9
    max_file_count = 100          # 最大ファイル数
    max_root_folder_count = 20     # 最大ルートフォルダ数

    for lang in languages:
        count = 0
        print(f"\n=== Language: {lang} ===")
        query = f"language:{lang} stars:>{star_threshold} pushed:>{pushed_after}"
        result = search_repositories(query, per_page=100, page=1)

        for repo in result["items"]:
            name = repo["full_name"]
            stars = repo["stargazers_count"]
            url = repo["html_url"]

            # 主言語割合チェック
            main_lang, ratio, ok_lang = main_language_ratio(name, threshold=main_lang_threshold)
            if not ok_lang:
                continue  # 条件外はスキップ

            # ファイル数チェック
            file_count = get_file_count(name)
            if file_count is None or file_count > max_file_count:
                continue

            # ルートフォルダ数チェック
            root_folders = get_root_folder_count(name)
            if root_folders is None or root_folders > max_root_folder_count:
                continue

            print(f"- {name} ({stars}★) {url} | 主言語={main_lang}, 割合={ratio:.2%}, "
                  f"ファイル数={file_count}, ルートフォルダ数={root_folders}")
            count += 1


# 実行方法:
# poetry run python src/research/evaluation/repo_selector.py
if __name__ == "__main__":
    main()
